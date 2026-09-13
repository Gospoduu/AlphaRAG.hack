"""Run with .venv/bin/python -m tests.reactions_postgres (configured PostgreSQL).
Creates and removes an isolated schema; never edits existing application rows.
"""
import argparse
import asyncio
import contextlib
import io
from uuid import uuid4

# The existing db module prints DATABASE_URL on import; keep credentials private.
with contextlib.redirect_stdout(io.StringIO()):
    from Back.infra.db.db import Base, engine
    from Back.modules.chat.api import reaction_endpoint, get_messages_endpoint
    from Back.modules.chat.models import Chat, Message
    from Back.modules.chat.schemas import PatchReaction
    from Back.modules.user.models import User
from sqlalchemy import select
from sqlalchemy.schema import CreateSchema, DropSchema
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from fastapi import HTTPException
from pydantic import ValidationError


class CooldownRedis:
    async def get(self, key):
        return '1'

    async def eval(self, *args):
        return 0


async def main(database_url=None):
    test_base = create_async_engine(database_url) if database_url else engine
    test_base.echo = False
    schema = 'reaction_test_' + uuid4().hex
    test_engine = test_base.execution_options(schema_translate_map={None: schema})
    sessions = async_sessionmaker(test_engine, expire_on_commit=False)
    created = False
    try:
        async with test_base.begin() as connection:
            await connection.execute(CreateSchema(schema))
        created = True
        async with test_engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        async with sessions() as db:
            user = User(uuid=uuid4(), role='user')
            db.add(user)
            await db.flush()
            chat = Chat(user_uuid=user.uuid, title='Reaction test')
            db.add(chat)
            await db.flush()
            message = Message(chat_id=chat.id, user_uuid=user.uuid,
                              user_role='bot', text='Test answer', local_id=1)
            db.add(message)
            await db.commit()
            message_id, chat_id = message.id, chat.id
        for reaction in (1, -1, 0):
            async with sessions() as db:
                result = await reaction_endpoint(PatchReaction(message_id=message_id, chat_id=chat_id, user_uuid=user.uuid, reaction=reaction), db, CooldownRedis())
                assert result['status'] == 'ok'
            # A separate session must see the committed value, not just a flush.
            async with sessions() as reader:
                saved = await reader.scalar(select(Message.reaction).where(Message.id == message_id))
                assert saved == reaction, (saved, reaction)
                history = await get_messages_endpoint(chat_id, 0, 50, reader)
                assert history['messages'][0]['reaction'] == reaction
        async with sessions() as db:
            try:
                await reaction_endpoint(PatchReaction(message_id=2147483647, chat_id=chat_id, user_uuid=user.uuid, reaction=1), db, CooldownRedis())
            except HTTPException as error:
                assert error.status_code == 404
            else:
                raise AssertionError('Missing message accepted')
        try:
            PatchReaction(message_id=message_id, chat_id=chat_id, user_uuid=user.uuid, reaction=2)
        except ValidationError:
            pass
        else:
            raise AssertionError('Invalid reaction accepted')
        print('PASS: PostgreSQL commit verified from separate sessions for like/dislike/reset; history, missing ID, invalid value')
    finally:
        if created:
            async with test_engine.begin() as connection:
                await connection.run_sync(Base.metadata.drop_all)
            async with test_base.begin() as connection:
                await connection.execute(DropSchema(schema))
        await test_base.dispose()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--database-url')
    asyncio.run(main(parser.parse_args().database_url))
