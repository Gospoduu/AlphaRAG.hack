import unittest
from fastapi import FastAPI
from prometheus_client.parser import text_string_to_metric_families
from Back.modules.chat.metrics import HttpMetricsMiddleware, registry, router
from prometheus_client import generate_latest


class HttpMetricsTests(unittest.IsolatedAsyncioTestCase):
    async def test_templates_errors_and_excluded_scrapes(self):
        app = FastAPI()
        app.add_middleware(HttpMetricsMiddleware)
        app.include_router(router)
        @app.get('/chats/{chat_id}')
        async def chat(chat_id: int):
            return {'id': chat_id}
        @app.get('/broken')
        async def broken():
            raise RuntimeError('test')
        async def request(path):
            async def receive():
                return {'type': 'http.request', 'body': b'', 'more_body': False}
            async def send(message):
                pass
            scope = dict(type='http', asgi={'version': '3.0'}, http_version='1.1',
                method='GET', scheme='http', path=path, raw_path=path.encode(), query_string=b'',
                root_path='', headers=[], server=('test', 80), client=('test', 1))
            await app(scope, receive, send)
        await request('/chats/7')
        await request('/chats/999')
        await request('/missing-unique-id')
        await request('/docs')
        with self.assertRaises(RuntimeError):
            await request('/broken')
        before = generate_latest(registry)
        await request('/metrics')
        await request('/api/health')
        self.assertEqual(before, generate_latest(registry))
        counts = { (s.labels['route'], s.labels['status']): s.value
            for f in text_string_to_metric_families(before.decode()) for s in f.samples
            if s.name == 'alpharag_http_requests_total' }
        self.assertEqual(counts[('/chats/{chat_id}', '200')], 2)
        self.assertEqual(counts[('unmatched', '404')], 1)
        self.assertEqual(counts[('/docs', '200')], 1)
        self.assertEqual(counts[('/broken', '500')], 1)
        self.assertNotIn('/chats/7', before.decode())
