"""Low-cardinality HTTP and WebSocket traffic metrics (one Uvicorn worker)."""
from fastapi import APIRouter, Response
from prometheus_client import CollectorRegistry, Counter, CONTENT_TYPE_LATEST, generate_latest

registry = CollectorRegistry()
http_requests = Counter('alpharag_http_requests_total', 'Completed HTTP requests, excluding scrapes and health probes.',
                        ['method', 'route', 'status'], registry=registry)
ws_commands = Counter('alpharag_ws_commands_total', 'Validated WebSocket commands successfully queued in Redis; excludes PING.',
                      ['event'], registry=registry)
router = APIRouter()
EXCLUDED_PATHS = {'/metrics', '/api/health', '/api/redis/ping', '/api/db/ping'}
METHODS = {'GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'OPTIONS', 'HEAD', 'CONNECT', 'TRACE'}


class HttpMetricsMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope['type'] != 'http' or scope.get('path', '').rstrip('/') in EXCLUDED_PATHS:
            return await self.app(scope, receive, send)
        status = 500
        async def capture(message):
            nonlocal status
            if message['type'] == 'http.response.start':
                status = message['status']
            await send(message)
        try:
            await self.app(scope, receive, capture)
        finally:
            route = getattr(scope.get('route'), 'path', None)
            if route is None:
                path = scope.get('path', '')
                if path in {'/docs', '/redoc', '/openapi.json', '/docs/oauth2-redirect'}:
                    route = path
                else:
                    route = '/static/*' if path.startswith('/static/') else 'unmatched'
            method = scope.get('method', 'OTHER')
            http_requests.labels(method if method in METHODS else 'OTHER', route, str(status)).inc()


@router.get('/metrics', include_in_schema=False)
async def metrics():
    return Response(generate_latest(registry), headers={'Content-Type': CONTENT_TYPE_LATEST})
