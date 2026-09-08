"""End-to-end API checks against a live ASGI app + sqlite."""

from __future__ import annotations

from datetime import UTC, datetime


async def test_healthz(client):
    resp = await client.get("/healthz")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


async def test_ingest_then_list(client):
    event = {
        "task_id": "abc123",
        "name": "app.tasks.send_email",
        "queue": "emails",
        "state": "success",
        "kwargs": {"to": "a@example.com"},
        "execution_ms": 42,
        "timestamp": datetime.now(UTC).isoformat(),
    }
    assert (await client.post("/api/tasks/events", json=event)).status_code == 202

    listed = await client.get("/api/tasks")
    assert listed.status_code == 200
    body = listed.json()
    assert body["total_count"] == 1
    assert [t["id"] for t in body["items"]] == ["abc123"]

    detail = await client.get("/api/tasks/abc123")
    assert detail.json()["kwargs"] == {"to": "a@example.com"}


async def _seed(client, **over):
    event = {
        "task_id": over["task_id"],
        "name": over.get("name", "app.tasks.run"),
        "queue": over.get("queue", "default"),
        "state": over.get("state", "success"),
        "execution_ms": over.get("execution_ms", 100),
        "timestamp": datetime.now(UTC).isoformat(),
    }
    assert (await client.post("/api/tasks/events", json=event)).status_code == 202


async def test_list_tasks_filter_sort_search_paginate(client):
    await _seed(client, task_id="a", name="send_email", queue="emails", execution_ms=50)
    await _seed(
        client, task_id="b", name="send_email", queue="emails", state="failure", execution_ms=900
    )
    await _seed(client, task_id="c", name="build_report", queue="reports", execution_ms=300)

    # filter by an explicit typed param
    body = (await client.get("/api/tasks", params={"queue": "emails"})).json()
    assert {t["id"] for t in body["items"]} == {"a", "b"}
    assert body["total_count"] == 2

    # name filter is exact-match (unlike `q`, which is substring)
    body = (await client.get("/api/tasks", params={"name": "build_report"})).json()
    assert [t["id"] for t in body["items"]] == ["c"]
    body = (await client.get("/api/tasks", params={"name": "build_rep"})).json()
    assert body["total_count"] == 0

    # sort: slowest first
    body = (await client.get("/api/tasks", params={"sort": "-execution_ms"})).json()
    assert [t["id"] for t in body["items"]] == ["b", "c", "a"]

    # free-text search across id / name / traceback
    body = (await client.get("/api/tasks", params={"q": "report"})).json()
    assert [t["id"] for t in body["items"]] == ["c"]

    # pagination carries a stable total
    body = (await client.get("/api/tasks", params={"sort": "id", "limit": 2, "offset": 1})).json()
    assert [t["id"] for t in body["items"]] == ["b", "c"]
    assert body["total_count"] == 3 and body["limit"] == 2 and body["offset"] == 1


async def test_list_tasks_rejects_unknown_sort_field(client):
    resp = await client.get("/api/tasks", params={"sort": "-secret_column"})
    assert resp.status_code == 422


async def test_queues_from_adapter(client):
    body = (await client.get("/api/queues")).json()
    assert {q["name"]: q["depth"] for q in body} == {"default": 3, "emails": 0}


async def test_queue_detail(client):
    detail = await client.get("/api/queues/default")
    assert detail.status_code == 200
    assert detail.json()["depth"] == 3
    assert (await client.get("/api/queues/does-not-exist")).status_code == 404


def _schedule(**over):
    base = {
        "schedule_id": "sch-1",
        "task_name": "app.tasks.nightly_rollup",
        "cron": "0 3 * * *",
    }
    return {**base, **over}


async def test_schedule_sync_list_and_detail(client):
    payload = {
        "source": "LabelScheduleSource",
        "schedules": [
            _schedule(schedule_id="sch-1", task_name="app.tasks.rollup", cron="0 3 * * *"),
            _schedule(
                schedule_id="sch-2",
                task_name="app.tasks.ping",
                cron=None,
                interval_seconds=300,
            ),
        ],
    }
    resp = await client.post("/api/schedules/sync", json=payload)
    assert resp.status_code == 202
    assert resp.json() == {"synced": 2, "removed": 0}

    body = (await client.get("/api/schedules")).json()
    assert body["total_count"] == 2
    assert {s["id"] for s in body["items"]} == {"sch-1", "sch-2"}
    by_id = {s["id"]: s for s in body["items"]}
    assert by_id["sch-1"]["next_fire_at"] is not None  # cron → croniter
    assert by_id["sch-2"]["next_fire_at"] is not None  # interval

    detail = await client.get("/api/schedules/sch-1")
    assert detail.status_code == 200
    assert detail.json()["task_name"] == "app.tasks.rollup"
    assert (await client.get("/api/schedules/nope")).status_code == 404


async def test_schedule_sync_removes_dropped(client):
    two = {"source": "S", "schedules": [_schedule(schedule_id="a"), _schedule(schedule_id="b")]}
    await client.post("/api/schedules/sync", json=two)

    one = {"source": "S", "schedules": [_schedule(schedule_id="a")]}
    result = (await client.post("/api/schedules/sync", json=one)).json()
    assert result == {"synced": 1, "removed": 1}
    assert {s["id"] for s in (await client.get("/api/schedules")).json()["items"]} == {"a"}


async def test_schedule_links_task_runs(client):
    await client.post(
        "/api/schedules/sync",
        json={"source": "S", "schedules": [_schedule(schedule_id="sch-x")]},
    )
    event = {
        "task_id": "t-fired",
        "name": "app.tasks.rollup",
        "queue": "reports",
        "state": "success",
        "schedule_id": "sch-x",
        "execution_ms": 10,
        "timestamp": datetime.now(UTC).isoformat(),
    }
    assert (await client.post("/api/tasks/events", json=event)).status_code == 202

    # the schedule now reports a last_fired_at
    detail = (await client.get("/api/schedules/sch-x")).json()
    assert detail["last_fired_at"] is not None

    # ...and the task is reachable by ?schedule_id
    body = (await client.get("/api/tasks", params={"schedule_id": "sch-x"})).json()
    assert [t["id"] for t in body["items"]] == ["t-fired"]


async def test_stats_overview(client):
    now = datetime.now(UTC)
    for i in range(3):
        await client.post(
            "/api/tasks/events",
            json={
                "task_id": f"ok-{i}",
                "name": "app.tasks.run",
                "queue": "default",
                "state": "success",
                "execution_ms": 100,
                "timestamp": now.isoformat(),
            },
        )
    await client.post(
        "/api/tasks/events",
        json={
            "task_id": "bad-1",
            "name": "app.tasks.run",
            "queue": "default",
            "state": "failure",
            "execution_ms": 300,
            "timestamp": now.isoformat(),
        },
    )

    body = (await client.get("/api/stats/overview")).json()
    assert body["tasks_processed"]["value"] == 4
    assert round(body["success_rate"]["value"], 3) == 0.75
    assert body["avg_duration_ms"]["value"] == 150.0  # (100+100+100+300)/4
    assert body["workers_online"] == 0 and body["workers_known"] == 0


async def test_stats_throughput(client):
    now = datetime.now(UTC)
    await client.post(
        "/api/tasks/events",
        json={
            "task_id": "t1",
            "name": "app.tasks.run",
            "queue": "default",
            "state": "success",
            "timestamp": now.isoformat(),
        },
    )

    body = (await client.get("/api/stats/throughput", params={"window": "24h"})).json()
    assert body["window"] == "24h"
    assert body["bucket_seconds"] == 3600
    assert len(body["buckets"]) == 24
    assert body["total_completed"] == 1
    assert body["buckets"][-1]["completed"] == 1  # most recent bucket

    assert (await client.get("/api/stats/throughput", params={"window": "3h"})).status_code == 422


async def test_worker_heartbeat_then_list(client):
    body = (await client.get("/api/workers")).json()
    assert body["items"] == [] and body["total_count"] == 0

    hb = {"worker_id": "worker-7", "queues": ["emails", "default"], "active_tasks": 2}
    assert (await client.post("/api/workers/heartbeat", json=hb)).status_code == 202

    body = (await client.get("/api/workers")).json()
    assert [w["id"] for w in body["items"]] == ["worker-7"]
    assert body["items"][0]["active_tasks"] == 2
    assert body["items"][0]["queues"] == ["emails", "default"]


async def test_workers_filter_sort_and_detail(client):
    await client.post(
        "/api/workers/heartbeat",
        json={"worker_id": "worker-a", "queues": ["emails"], "active_tasks": 1},
    )
    await client.post(
        "/api/workers/heartbeat",
        json={"worker_id": "worker-b", "queues": ["reports"], "active_tasks": 5},
    )

    # sort by active_tasks desc
    body = (await client.get("/api/workers", params={"sort": "-active_tasks"})).json()
    assert [w["id"] for w in body["items"]] == ["worker-b", "worker-a"]

    # filter by exact id
    body = (await client.get("/api/workers", params={"worker_id": "worker-a"})).json()
    assert [w["id"] for w in body["items"]] == ["worker-a"]

    # detail endpoint
    detail = await client.get("/api/workers/worker-b")
    assert detail.status_code == 200
    assert detail.json()["active_tasks"] == 5

    assert (await client.get("/api/workers/does-not-exist")).status_code == 404


# --- alerts ----------------------------------------------------------


async def test_alert_rule_crud_and_validation(client):
    payload = {
        "name": "Emails backlog",
        "type": "queue_backlog",
        "scope": "queue",
        "scope_value": "emails",
        "operator": "gt",
        "threshold": 100,
        "for_seconds": 120,
        "severity": "critical",
    }
    created = await client.post("/api/alerts/rules", json=payload)
    assert created.status_code == 201
    body = created.json()
    rid = body["id"]
    assert body["state"] == "ok"
    assert body["threshold_unit"] == "tasks"

    # bad scope for this type
    bad = await client.post(
        "/api/alerts/rules",
        json={**payload, "scope": "worker", "scope_value": "w1"},
    )
    assert bad.status_code == 422

    # failure_rate needs a window
    bad2 = await client.post(
        "/api/alerts/rules",
        json={"name": "fr", "type": "failure_rate", "operator": "gt", "threshold": 0.1},
    )
    assert bad2.status_code == 422

    listed = await client.get("/api/alerts/rules", params={"type": "queue_backlog"})
    assert listed.json()["total_count"] == 1

    patched = await client.patch(
        f"/api/alerts/rules/{rid}", json={"threshold": 50, "enabled": False}
    )
    assert patched.json()["threshold"] == 50 and patched.json()["enabled"] is False

    ev = await client.post(f"/api/alerts/rules/{rid}/evaluate")
    assert ev.status_code == 200 and ev.json()["last_evaluated_at"] is not None

    assert (await client.delete(f"/api/alerts/rules/{rid}")).status_code == 204
    assert (await client.get(f"/api/alerts/rules/{rid}")).status_code == 404


async def test_alert_channel_crud_and_test(client):
    created = await client.post(
        "/api/alerts/channels",
        json={"name": "hook", "type": "webhook", "config": {"url": "http://127.0.0.1:59991/x"}},
    )
    assert created.status_code == 201
    cid = created.json()["id"]

    # webhook without a url
    bad = await client.post(
        "/api/alerts/channels", json={"name": "x", "type": "webhook", "config": {}}
    )
    assert bad.status_code == 422

    assert len((await client.get("/api/alerts/channels")).json()) == 1

    # nothing is listening on that port -> ok=False, but the endpoint still 200s
    result = await client.post(f"/api/alerts/channels/{cid}/test")
    assert result.status_code == 200 and result.json()["ok"] is False

    assert (await client.delete(f"/api/alerts/channels/{cid}")).status_code == 204


async def test_alert_events_list_empty(client):
    body = (await client.get("/api/alerts/events")).json()
    assert body == {"items": [], "total_count": 0, "offset": 0, "limit": 15}


# --- task lineage --------------------------------------------------


async def test_task_lineage_graph(client):
    async def kick(task_id, parent=None):
        ev = {
            "task_id": task_id,
            "name": f"app.{task_id}",
            "queue": "default",
            "state": "success",
            "timestamp": datetime.now(UTC).isoformat(),
        }
        if parent:
            ev["parent_task_id"] = parent
        assert (await client.post("/api/tasks/events", json=ev)).status_code == 202

    # a -> b -> c, and b -> d
    await kick("a")
    await kick("b", "a")
    await kick("c", "b")
    await kick("d", "b")

    graph = (await client.get("/api/tasks/c/graph")).json()
    assert graph["root_id"] == "c"
    assert {n["id"] for n in graph["nodes"]} == {"a", "b", "c", "d"}
    assert {(e["source"], e["target"]) for e in graph["edges"]} == {
        ("a", "b"),
        ("b", "c"),
        ("b", "d"),
    }

    # parent_task_id lands on the detail payload
    detail = (await client.get("/api/tasks/c")).json()
    assert detail["parent_task_id"] == "b"

    # a task with no lineage → just itself, no edges
    await kick("lonely")
    solo = (await client.get("/api/tasks/lonely/graph")).json()
    assert [n["id"] for n in solo["nodes"]] == ["lonely"] and solo["edges"] == []

    assert (await client.get("/api/tasks/ghost/graph")).status_code == 404


async def test_task_lineage_survives_self_kick(client):
    ev = {
        "task_id": "loop",
        "name": "app.poller",
        "queue": "default",
        "state": "success",
        "parent_task_id": "loop",  # task that re-kicks itself
        "timestamp": datetime.now(UTC).isoformat(),
    }
    assert (await client.post("/api/tasks/events", json=ev)).status_code == 202
    graph = (await client.get("/api/tasks/loop/graph")).json()
    assert [n["id"] for n in graph["nodes"]] == ["loop"]
    assert graph["edges"] == []  # self-edge is filtered out
