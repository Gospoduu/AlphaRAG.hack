"""Check the real application entry point in a fresh interpreter, without services."""
import os
from pathlib import Path
import subprocess
import sys
import unittest


class EventBootstrapTests(unittest.TestCase):
    def test_main_registers_protocol_and_kafka_consumers(self):
        code = r'''
import contextlib
import io
import sys
with contextlib.redirect_stdout(io.StringIO()):
    import Back.main
from Back.core.events_bus.event_manager import event_manager
from Back.core.events_bus.handler_manager import handler_manager
commands = {
    'PING', 'NEW_MESSAGE', 'GENERATION_RESTORE', 'SUPPORT_REQUEST',
    'SUPPORT_MESSAGE', 'END_SUPPORT_DIALOG_REQUEST', 'USER_FEEDBACK_RESPONSE',
}
responses = {
    'ERROR', 'PONG', 'GENERATED_TEXT', 'MESSAGE_RESPONSE', 'NEW_TOKEN',
    'END_GENERATION', 'SUPPORT_RESPONSE', 'USER_FEEDBACK_REQUEST', 'UPDATE_DIALOG_STATUS',
}
for name in commands | responses:
    assert event_manager.get(name) is not None, name
for name in commands:
    assert handler_manager.get(name), name
assert 'Back.infra.kafka.subscribers' in sys.modules
from Back.infra.kafka.broker import broker
assert len(broker._subscribers) == 2, 'LLM and support Kafka consumers must be registered'

# Exercise the actual WS ingress: both commands must reach Redis without UNKNOWN_EVENT.
import asyncio
from unittest.mock import AsyncMock, patch
from uuid import uuid4
from fastapi import WebSocketDisconnect
from Back.ws import ws
async def check_ingress():
    user = uuid4()
    frames = [
        {'event': 'NEW_MESSAGE', 'status': 'OK', 'data': {'user_uuid': str(user), 'chat_id': 1, 'text': 'test'}},
        {'event': 'PING', 'status': 'OK', 'data': {'user_uuid': str(user)}},
    ]
    socket = AsyncMock()
    socket.receive_json.side_effect = frames + [WebSocketDisconnect()]
    with patch.object(ws.manager, 'is_current', AsyncMock(return_value=True)), \
         patch.object(ws.manager, 'send_event', AsyncMock()) as send, \
         patch.object(ws, 'add_new_cmd', AsyncMock()) as enqueue:
        await ws.ws_to_redis_loop(socket, user, 1, AsyncMock())
        assert [call.args[1].event for call in enqueue.await_args_list] == ['NEW_MESSAGE', 'PING']
        send.assert_not_awaited()
asyncio.run(check_ingress())
'''
        env = dict(os.environ, DATABASE_URL='postgresql+asyncpg://test:test@localhost/test',
                   KAFKA_URL='localhost:9092', LLM_REQUEST_TOPIC='test-request',
                   LLM_RESPONSE_TOPIC='test-response', SUPPORT_RESPONSE_TOPIC='test-support',
                   LLM_USER_UUID='00000000-0000-0000-0000-000000000001')
        result = subprocess.run([sys.executable, '-c', code], env=env,
                                cwd=Path(__file__).resolve().parents[1],
                                capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr)
