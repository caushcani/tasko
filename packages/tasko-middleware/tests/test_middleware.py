"""Unit tests for TaskoMiddleware — fake broker, mocked HTTP transport."""

from __future__ import annotations

import httpx
import pytest
from taskiq import InMemoryBroker, TaskiqMessage, TaskiqResult
from tasko_middleware import TaskoMiddleware
from tasko_middleware.middleware import _current_task_id


@pytest.fixture(autouse=True)
def _reset_lineage_ctx():
    token = _current_task_id.set(None)
    yield
    _current_task_id.reset(token)


@pytest.fixture
def captured() -> list[tuple[str, bytes]]:
    return []


@pytest.fixture
def middleware(captured):
    def handler(request: httpx.Request) -> httpx.Response:
        captured.append((request.url.path, request.content))
        return httpx.Response(202, json={"status": "accepted"})

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    mw = TaskoMiddleware("http://core:8000", worker_id="w-test", client=client)
    mw.set_broker(InMemoryBroker())
    return mw


def _msg(task_id: str = "t1") -> TaskiqMessage:
    return TaskiqMessage(
        task_id=task_id,
        task_name="app.tasks.demo",
        labels={"queue": "emails"},
        args=[],
        kwargs={},
    )


async def test_pre_execute_emits_started_event(middleware, captured):
    await middleware.pre_execute(_msg())
    assert [p for p, _ in captured] == ["/api/tasks/events"]
    assert b'"state":"started"' in captured[0][1]
    assert b'"queue":"emails"' in captured[0][1]


async def test_heartbeat_payload_reflects_inflight(middleware, captured):
    await middleware.pre_execute(_msg("a"))
    await middleware.pre_execute(_msg("b"))
    captured.clear()

    await middleware._send_heartbeat()

    path, body = captured[0]
    assert path == "/api/workers/heartbeat"
    assert b'"worker_id":"w-test"' in body
    assert b'"active_tasks":2' in body
    assert b'"emails"' in body


async def test_post_execute_clears_inflight(middleware):
    await middleware.pre_execute(_msg("a"))
    assert len(middleware._inflight) == 1
    await middleware.post_execute(
        _msg("a"), TaskiqResult(is_err=False, return_value=1, execution_time=0.1)
    )
    assert middleware._inflight == {}


async def test_no_heartbeat_task_on_client_process(middleware):
    # InMemoryBroker.is_worker_process is False → startup starts no loop.
    await middleware.startup()
    assert middleware._heartbeat_task is None
    await middleware.shutdown()


async def test_pre_send_stamps_parent_from_running_task(middleware, captured):
    # a task is executing...
    await middleware.pre_execute(_msg("parent-1"))
    # ...and its code kicks another task
    child = _msg("child-1")
    child.labels.pop("parent_task_id", None)
    returned = await middleware.pre_send(child)
    assert returned.labels["parent_task_id"] == "parent-1"

    # and post_send forwards it in the queued event
    captured.clear()
    await middleware.post_send(child)
    assert b'"parent_task_id":"parent-1"' in captured[0][1]
    assert b'"state":"queued"' in captured[0][1]


async def test_pre_send_no_parent_when_nothing_running(middleware):
    msg = _msg("top-level")
    await middleware.pre_send(msg)
    assert "parent_task_id" not in msg.labels


async def test_pre_send_does_not_override_existing_parent(middleware):
    await middleware.pre_execute(_msg("parent-1"))
    msg = _msg("child")
    msg.labels["parent_task_id"] = "explicit-parent"
    await middleware.pre_send(msg)
    assert msg.labels["parent_task_id"] == "explicit-parent"
