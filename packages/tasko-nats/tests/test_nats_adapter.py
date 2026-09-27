"""Unit tests for NatsAdapter, a fake JetStream client, no real broker.

Fixture numbers below match a real ``nats-server -js`` session (two streams,
one with a durable consumer that had partially consumed its backlog, one
nobody had ever consumed from), not guessed.
"""

from __future__ import annotations

import datetime

import pytest
from nats.js.api import ConsumerConfig, ConsumerInfo, StreamConfig, StreamInfo, StreamState
from nats.js.errors import NotFoundError, ServiceUnavailableError
from tasko_core.adapters import QueueStats
from tasko_nats.adapter import NatsAdapter

_NOW = datetime.datetime.now(datetime.UTC)


def _stream(name: str, subject: str, messages: int) -> StreamInfo:
    return StreamInfo(
        config=StreamConfig(name=name, subjects=[subject]),
        state=StreamState(
            messages=messages, bytes=0, first_seq=1, last_seq=messages, consumer_count=0
        ),
    )


def _consumer(name: str, stream: str, *, num_pending: int, num_ack_pending: int) -> ConsumerInfo:
    return ConsumerInfo(
        name=name,
        stream_name=stream,
        config=ConsumerConfig(durable_name=name),
        created=_NOW,
        num_pending=num_pending,
        num_ack_pending=num_ack_pending,
    )


EMAILS_STREAM = _stream("emails_stream", "emails_tasks", messages=5)
REPORTS_STREAM = _stream("reports_stream", "reports_tasks", messages=2)
EMAILS_CONSUMER = _consumer("taskiq_durable", "emails_stream", num_pending=3, num_ack_pending=1)


class FakeJetStream:
    """Stands in for ``nats.js.client.JetStreamContext`` — only the methods
    the adapter actually calls."""

    def __init__(self, streams, consumers_by_stream, *, account_error=None):
        self._streams = {s.config.name: s for s in streams}
        self._consumers = consumers_by_stream
        self._account_error = account_error

    async def account_info(self):
        if self._account_error:
            raise self._account_error
        return object()

    async def streams_info(self):
        return list(self._streams.values())

    async def stream_info(self, name):
        if name not in self._streams:
            raise NotFoundError()
        return self._streams[name]

    async def consumers_info(self, stream):
        return self._consumers.get(stream, [])


def _adapter(js: FakeJetStream, **options) -> NatsAdapter:
    adapter = NatsAdapter(**options)
    adapter._js = js
    return adapter


async def test_list_queues_maps_fields_and_sorts():
    js = FakeJetStream(
        streams=[REPORTS_STREAM, EMAILS_STREAM],  # deliberately out of name order
        consumers_by_stream={"emails_stream": [EMAILS_CONSUMER], "reports_stream": []},
    )
    adapter = _adapter(js)
    queues = await adapter.list_queues()

    assert [q.name for q in queues] == ["emails_stream", "reports_stream"]
    assert queues[0] == QueueStats(
        name="emails_stream", depth=3, in_flight=1, extra={"consumers": 1}
    )
    # no consumer ever attached -> falls back to the stream's own message count
    assert queues[1] == QueueStats(
        name="reports_stream", depth=2, in_flight=0, extra={"consumers": 0}
    )


async def test_list_queues_sums_multiple_consumers_on_one_stream():
    second = _consumer("other_consumer", "emails_stream", num_pending=2, num_ack_pending=0)
    js = FakeJetStream(
        streams=[EMAILS_STREAM],
        consumers_by_stream={"emails_stream": [EMAILS_CONSUMER, second]},
    )
    adapter = _adapter(js)
    queues = await adapter.list_queues()
    assert queues[0].depth == 3 + 2
    assert queues[0].in_flight == 1 + 0
    assert queues[0].extra == {"consumers": 2}


async def test_list_queues_filters_by_prefix():
    js = FakeJetStream(
        streams=[EMAILS_STREAM, REPORTS_STREAM],
        consumers_by_stream={"emails_stream": [EMAILS_CONSUMER], "reports_stream": []},
    )
    adapter = _adapter(js, stream_prefix="reports")
    queues = await adapter.list_queues()
    assert [q.name for q in queues] == ["reports_stream"]


async def test_get_queue_found():
    js = FakeJetStream(
        streams=[EMAILS_STREAM], consumers_by_stream={"emails_stream": [EMAILS_CONSUMER]}
    )
    adapter = _adapter(js)
    stats = await adapter.get_queue("emails_stream")
    assert stats is not None
    assert stats.depth == 3 and stats.in_flight == 1


async def test_get_queue_not_found_returns_none():
    js = FakeJetStream(streams=[], consumers_by_stream={})
    adapter = _adapter(js)
    assert await adapter.get_queue("ghost_stream") is None


async def test_get_queue_outside_prefix_skips_request():
    calls = []

    class TrackedJetStream(FakeJetStream):
        async def stream_info(self, name):
            calls.append(name)
            return await super().stream_info(name)

    js = TrackedJetStream(
        streams=[EMAILS_STREAM], consumers_by_stream={"emails_stream": [EMAILS_CONSUMER]}
    )
    adapter = _adapter(js, stream_prefix="reports")
    assert await adapter.get_queue("emails_stream") is None
    assert calls == []  # never even asked


async def test_startup_raises_clear_error_when_jetstream_disabled(monkeypatch):
    js = FakeJetStream(streams=[], consumers_by_stream={}, account_error=ServiceUnavailableError())

    class FakeClient:
        def jetstream(self):
            return js

        async def close(self):
            pass

    async def fake_connect(servers, **kwargs):
        return FakeClient()

    monkeypatch.setattr("tasko_nats.adapter.nats.connect", fake_connect)

    adapter = NatsAdapter()
    with pytest.raises(RuntimeError, match="JetStream is not enabled"):
        await adapter.startup()


async def test_startup_succeeds_when_jetstream_enabled(monkeypatch):
    js = FakeJetStream(streams=[], consumers_by_stream={})
    calls = []

    class FakeClient:
        def jetstream(self):
            return js

    async def fake_connect(servers, **kwargs):
        calls.append((servers, kwargs))
        return FakeClient()

    monkeypatch.setattr("tasko_nats.adapter.nats.connect", fake_connect)

    adapter = NatsAdapter(servers="nats://example:4222", token="secret")
    await adapter.startup()
    assert calls == [("nats://example:4222", {"token": "secret"})]


def test_list_workers_not_overridden():
    # Deliberate: telling individual worker connections apart needs NATS's
    # separate (non-default) monitoring HTTP endpoint. See adapter.py's
    # module docstring for why this stays at the BrokerAdapter default.
    assert "list_workers" not in NatsAdapter.__dict__
