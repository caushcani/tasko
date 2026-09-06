"""Unit tests for TaskoScheduleSource — fake wrapped source, mocked HTTP."""

from __future__ import annotations

import json
from datetime import timedelta

import httpx
import pytest
from taskiq.abc.schedule_source import ScheduleSource
from taskiq.scheduler.scheduled_task import ScheduledTask
from tasko_middleware import TaskoScheduleSource


class FakeSource(ScheduleSource):
    def __init__(self, schedules: list[ScheduledTask]) -> None:
        self._schedules = schedules
        self.started = False

    async def startup(self) -> None:
        self.started = True

    async def get_schedules(self) -> list[ScheduledTask]:
        return self._schedules


def _task(**over) -> ScheduledTask:
    base = dict(task_name="app.tasks.rollup", labels={}, args=[], kwargs={}, schedule_id="s1")
    return ScheduledTask(**{**base, **over})


@pytest.fixture
def captured() -> list[dict]:
    return []


@pytest.fixture
def make(captured):
    def _make(schedules):
        def handler(request: httpx.Request) -> httpx.Response:
            captured.append({"path": request.url.path, "body": json.loads(request.content)})
            return httpx.Response(202, json={"synced": len(schedules), "removed": 0})

        client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        return TaskoScheduleSource(FakeSource(schedules), "http://core:8000", client=client)

    return _make


async def test_startup_syncs_schedules(make, captured):
    src = make([_task(schedule_id="s1", cron="0 3 * * *")])
    await src.startup()

    assert src._source.started  # wrapped source still starts
    assert len(captured) == 1
    assert captured[0]["path"] == "/api/schedules/sync"
    body = captured[0]["body"]
    assert body["source"] == "FakeSource"
    assert body["schedules"][0]["schedule_id"] == "s1"
    assert body["schedules"][0]["cron"] == "0 3 * * *"


async def test_interval_timedelta_normalised_to_seconds(make, captured):
    src = make([_task(cron=None, interval=timedelta(minutes=5))])
    await src.startup()
    assert captured[0]["body"]["schedules"][0]["interval_seconds"] == 300


async def test_get_schedules_passes_through_and_dedupes_sync(make, captured):
    src = make([_task(cron="* * * * *")])
    await src.startup()
    got = await src.get_schedules()
    assert [t.schedule_id for t in got] == ["s1"]
    # identical schedule set → no second POST
    assert len(captured) == 1
