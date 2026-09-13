import asyncio
import contextlib
import io
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, patch
from uuid import uuid4

with contextlib.redirect_stdout(io.StringIO()):
    from Back.modules.chat import operator_offers as offers


class Redis:
    def __init__(self):
        self.values = {}

    async def get(self, key):
        return self.values.get(key)

    async def set(self, key, value, nx=False, ex=None):
        if nx and key in self.values:
            return False
        self.values[key] = value
        return True

    async def eval(self, script, count, *args):
        if script == offers.CANCEL_SCRIPT:
            key, prefix = args
            if key in self.values and str(self.values[key]).startswith(prefix):
                del self.values[key]
                return 1
            return 0
        key, cooldown, token, duration = args
        if self.values.get(key) != token:
            return 0
        del self.values[key]
        return int(bool(await self.set(cooldown, '1', nx=True, ex=duration)))


class OfferTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.redis = Redis()
        self.user = uuid4()
        self.chat = SimpleNamespace(user_uuid=self.user, is_generate=False, is_blocked=False)
        self.message = SimpleNamespace(chat_id=7, reaction=-1, local_id=2)
        self.question = SimpleNamespace(local_id=1, text='Как подписать контракт?')
        self.db = AsyncMock()
        self.db.__aenter__.return_value = self.db
        self.db.get.side_effect = lambda model, key: self.chat if model is offers.Chat else self.message
        self.db.scalar.return_value = self.question
        self.session = patch.object(offers, 'AsyncSessionLocal', return_value=self.db)
        self.sleep = patch.object(offers.asyncio, 'sleep', new_callable=AsyncMock)
        self.emit = patch.object(offers, 'add_new_emit', new_callable=AsyncMock)
        self.create = patch.object(offers.crud, 'create_message', new_callable=AsyncMock, return_value=SimpleNamespace(id=99))
        self.last = patch.object(offers.crud, 'get_last_message_local_id', new_callable=AsyncMock, return_value=2)
        self.env = patch.dict('os.environ', {'LLM_USER_UUID': str(uuid4())})
        for patcher in (self.session, self.sleep, self.emit, self.create, self.last, self.env):
            patcher.start()
            self.addCleanup(patcher.stop)

    async def run_worker(self, token='10:original'):
        await offers._send_operator_offer_after_delay(self.redis, 7, 10, self.user, token, '2026-09-13T00:00:00Z')

    async def test_offer_after_five_seconds_and_cooldown_survives_unlike(self):
        await self.redis.set(offers.pending_key(7), '10:original')
        await self.run_worker()
        offers.asyncio.sleep.assert_awaited_once_with(5)
        self.db.commit.assert_awaited_once()
        event = offers.add_new_emit.await_args.kwargs['event']
        self.assertTrue(event.meta['is_user_need_support'])
        self.assertEqual(event.meta['message_id'], 99)
        self.assertEqual(event.meta['user_query'], self.question.text)
        await offers.cancel_operator_offer(7, self.redis, 10)
        self.assertTrue(await self.redis.get(offers.cooldown_key(7)))
        await offers.schedule_operator_offer(7, 10, self.user, self.redis)
        self.assertIsNone(await self.redis.get(offers.pending_key(7)))

    async def test_cancel_like_or_next_user_message(self):
        for message_id in (10, None):
            await self.redis.set(offers.pending_key(7), '10:original')
            await offers.cancel_operator_offer(7, self.redis, message_id)
            await self.run_worker()
        offers.add_new_emit.assert_not_awaited()

    async def test_changed_reaction_new_message_or_active_generation(self):
        for field in ('reaction', 'new_question', 'is_generate', 'is_blocked'):
            await self.redis.set(offers.pending_key(7), '10:original')
            self.message.reaction = 0 if field == 'reaction' else -1
            self.question.local_id = 3 if field == 'new_question' else 1
            self.chat.is_generate = field == 'is_generate'
            self.chat.is_blocked = field == 'is_blocked'
            await self.run_worker()
        offers.add_new_emit.assert_not_awaited()

    async def test_old_worker_cannot_delete_replacement_or_other_message(self):
        await self.redis.set(offers.pending_key(7), '10:replacement')
        await self.run_worker()
        self.assertEqual(await self.redis.get(offers.pending_key(7)), '10:replacement')
        await offers.cancel_operator_offer(7, self.redis, 11)
        self.assertEqual(await self.redis.get(offers.pending_key(7)), '10:replacement')
        offers.add_new_emit.assert_not_awaited()

    async def test_concurrent_dislikes_reserve_only_one_task(self):
        gate = asyncio.Event()
        async def wait_for_gate(_):
            await gate.wait()
        with patch.object(offers.asyncio, 'sleep', side_effect=wait_for_gate):
            await asyncio.gather(*(offers.schedule_operator_offer(7, 10, self.user, self.redis) for _ in range(10)))
            tasks = list(offers._tasks)
            self.assertEqual(len(tasks), 1)
            gate.set()
            await asyncio.gather(*tasks)
        offers.add_new_emit.assert_awaited_once()


if __name__ == '__main__':
    unittest.main()
