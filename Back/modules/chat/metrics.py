"""Low-cardinality HTTP and WebSocket traffic metrics (one Uvicorn worker)."""
from fastapi import APIRouter, Response, Depends
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import insert
from uuid import UUID
from pathlib import Path
import json

QUESTION_TOPICS = json.loads(Path(__file__).with_name("question_topics.json").read_text())
from Back.infra.db.db import Base, get_db
from Back.modules.chat.models import Message, Role
from prometheus_client.core import GaugeMetricFamily, CounterMetricFamily
from prometheus_client import CollectorRegistry, Counter, CONTENT_TYPE_LATEST, generate_latest

registry = CollectorRegistry()
http_requests = Counter('alpharag_http_requests_total', 'Completed HTTP requests, excluding scrapes and health probes.',
                        ['method', 'route', 'status'], registry=registry)
ws_commands = Counter('alpharag_ws_commands_total', 'Validated WebSocket commands successfully queued in Redis; excludes PING.',
                      ['event'], registry=registry)
router = APIRouter()
EXCLUDED_PATHS = {'/metrics', '/api/health', '/api/redis/ping', '/api/db/ping'}
METHODS = {'GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'OPTIONS', 'HEAD', 'CONNECT', 'TRACE'}


question_analytics = sa.Table(
    'bot_question_analytics', Base.metadata,
    sa.Column('question_id', sa.Uuid, primary_key=True),
    sa.Column('topic', sa.String(120), nullable=False),
)


async def record_question(db, meta):
    if not meta.get('question_id') or not meta.get('question_topic'):
        return
    topic = str(meta['question_topic'])
    if topic not in QUESTION_TOPICS:
        topic = 'other'
    await db.execute(insert(question_analytics).values(
        question_id=UUID(meta['question_id']), topic=topic,
    ).on_conflict_do_nothing(index_elements=['question_id']))


async def collect_business_metrics(db):
    reactions = (await db.execute(sa.select(Message.reaction, sa.func.count()).where(
        Message.user_role == Role.BOT,
    ).group_by(Message.reaction))).all()
    topics = (await db.execute(sa.select(question_analytics.c.topic, sa.func.count()).group_by(
        question_analytics.c.topic,
    ))).all()
    return render_business_metrics(reactions, topics)


def render_business_metrics(reactions, topics):
    counts = dict(reactions)
    reaction_metric = GaugeMetricFamily('alpharag_bot_reactions',
        'Current reactions on stored bot messages; changes/removals are reflected. Do not use rate().', labels=['reaction'])
    for value, label in ((1, 'like'), (-1, 'dislike'), (0, 'none')):
        reaction_metric.add_metric([label], counts.get(value, 0))
    question_metric = CounterMetricFamily('alpharag_questions',
        'Classified bot requests since instrumentation; deduplicated by request identity.', labels=['topic'])
    topic_counts = dict.fromkeys(QUESTION_TOPICS, 0)
    topic_counts.update(dict(topics))
    for topic, count in sorted(topic_counts.items()):
        question_metric.add_metric([topic], count)
    class Snapshot:
        def collect(self):
            yield reaction_metric
            yield question_metric
    snapshot = CollectorRegistry()
    snapshot.register(Snapshot())
    return generate_latest(snapshot)


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
async def metrics(db=Depends(get_db)):
    business = await collect_business_metrics(db)
    return Response(generate_latest(registry) + business, headers={'Content-Type': CONTENT_TYPE_LATEST})
