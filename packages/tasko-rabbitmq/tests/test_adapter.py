"""Unit tests for RabbitMQAdapter — mocked Management API, no real broker.

Fixture shapes below are trimmed from a real ``rabbitmq:4-management-alpine``
response (captured against actual taskiq-aio-pika-declared queues), not
guessed — only the fields the adapter reads are kept.
"""

from __future__ import annotations

import httpx
import pytest
from tasko_core.adapters import QueueStats, WorkerInfo
from tasko_rabbitmq.adapter import RabbitMQAdapter


def _mocked(handler) -> RabbitMQAdapter:
    adapter = RabbitMQAdapter(management_url="http://mgmt:15672", vhost="/")
    adapter._client = httpx.AsyncClient(
        transport=httpx.MockTransport(handler), base_url="http://mgmt:15672"
    )
    return adapter


QUEUES_RESPONSE = [
    {
        "name": "reports",
        "messages_ready": 2,
        "messages_unacknowledged": 0,
        "consumers": 0,
        "state": "running",
    },
    {
        "name": "emails",
        "messages_ready": 0,
        "messages_unacknowledged": 5,
        "consumers": 1,
        "state": "running",
    },
]


async def test_startup_checks_whoami():
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request.url.path)
        return httpx.Response(200, json={"name": "guest", "tags": ["administrator"]})

    adapter = _mocked(handler)
    await adapter.startup()
    assert calls == ["/api/whoami"]


async def test_startup_raises_on_bad_credentials():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401)

    adapter = _mocked(handler)
    with pytest.raises(httpx.HTTPStatusError):
        await adapter.startup()


async def test_list_queues_maps_fields_and_sorts():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.raw_path == b"/api/queues/%2F"
        return httpx.Response(200, json=QUEUES_RESPONSE)

    adapter = _mocked(handler)
    queues = await adapter.list_queues()

    # sorted by name, regardless of api order
    assert [q.name for q in queues] == ["emails", "reports"]
    assert queues[0] == QueueStats(
        name="emails", depth=0, in_flight=5, extra={"consumers": 1, "state": "running"}
    )
    assert queues[1].depth == 2 and queues[1].in_flight == 0


async def test_list_queues_filters_by_prefix():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=QUEUES_RESPONSE)

    adapter = RabbitMQAdapter(management_url="http://mgmt:15672", queue_prefix="report")
    adapter._client = httpx.AsyncClient(
        transport=httpx.MockTransport(handler), base_url="http://mgmt:15672"
    )
    queues = await adapter.list_queues()
    assert [q.name for q in queues] == ["reports"]


async def test_get_queue_found():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.raw_path == b"/api/queues/%2F/emails"
        return httpx.Response(200, json=QUEUES_RESPONSE[1])

    adapter = _mocked(handler)
    stats = await adapter.get_queue("emails")
    assert stats is not None
    assert stats.name == "emails" and stats.in_flight == 5


async def test_get_queue_not_found_returns_none():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, json={"error": "Object Not Found"})

    adapter = _mocked(handler)
    assert await adapter.get_queue("ghost") is None


async def test_get_queue_outside_prefix_skips_request():
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request.url.path)
        return httpx.Response(200, json=QUEUES_RESPONSE[1])

    adapter = RabbitMQAdapter(management_url="http://mgmt:15672", queue_prefix="report")
    adapter._client = httpx.AsyncClient(
        transport=httpx.MockTransport(handler), base_url="http://mgmt:15672"
    )
    assert await adapter.get_queue("emails") is None
    assert calls == []  # never even asked the API


CONSUMERS_RESPONSE = [
    {
        "consumer_tag": "ctag1.aaa",
        "queue": {"name": "emails", "vhost": "/"},
        "channel_details": {"connection_name": "10.0.0.5:44771 -> 10.0.0.2:5672"},
    },
    {
        "consumer_tag": "ctag1.bbb",
        "queue": {"name": "reports", "vhost": "/"},
        "channel_details": {"connection_name": "10.0.0.5:44771 -> 10.0.0.2:5672"},
    },
    {
        "consumer_tag": "ctag1.ccc",
        "queue": {"name": "emails", "vhost": "/"},
        "channel_details": {"connection_name": "10.0.0.9:51000 -> 10.0.0.2:5672"},
    },
]


async def test_list_workers_groups_consumers_by_connection():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.raw_path == b"/api/consumers/%2F"
        return httpx.Response(200, json=CONSUMERS_RESPONSE)

    adapter = _mocked(handler)
    workers = await adapter.list_workers()

    assert [w.id for w in workers] == [
        "10.0.0.5:44771 -> 10.0.0.2:5672",
        "10.0.0.9:51000 -> 10.0.0.2:5672",
    ]
    # the first connection consumes from both queues it registered on
    first = next(w for w in workers if w.id == "10.0.0.5:44771 -> 10.0.0.2:5672")
    assert first.queues == ["emails", "reports"]
    assert all(isinstance(w, WorkerInfo) for w in workers)


async def test_list_workers_empty_when_no_consumers():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=[])

    adapter = _mocked(handler)
    assert await adapter.list_workers() == []
