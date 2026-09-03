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
    assert [t["id"] for t in listed.json()] == ["abc123"]

    detail = await client.get("/api/tasks/abc123")
    assert detail.json()["kwargs"] == {"to": "a@example.com"}


async def test_queues_from_adapter(client):
    assert (await client.get("/api/queues")).json()[0]["depth"] == 3


async def test_worker_heartbeat_then_list(client):
    assert (await client.get("/api/workers")).json() == []

    hb = {"worker_id": "worker-7", "queues": ["emails", "default"], "active_tasks": 2}
    assert (await client.post("/api/workers/heartbeat", json=hb)).status_code == 202

    workers = (await client.get("/api/workers")).json()
    assert [w["id"] for w in workers] == ["worker-7"]
    assert workers[0]["active_tasks"] == 2
    assert workers[0]["queues"] == ["emails", "default"]
