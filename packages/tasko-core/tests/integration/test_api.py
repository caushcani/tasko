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
