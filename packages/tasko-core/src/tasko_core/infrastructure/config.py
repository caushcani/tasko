"""Load and validate ``tasko.yaml``.

Resolution order:
1. ``$TASKO_CONFIG`` if set
2. ``tasko.local.yaml`` in the working directory (gitignored overrides)
3. ``tasko.yaml`` in the working directory
"""

from __future__ import annotations

import os
from pathlib import Path

import yaml
from pydantic import BaseModel, Field

_CANDIDATES = ("tasko.local.yaml", "tasko.yaml")


class ServerConfig(BaseModel):
    host: str = "0.0.0.0"
    port: int = 8000
    #: Browser origins the dashboard is served from — needed because web/ and
    #: core run on different ports/hosts, so the browser's own fetch() calls
    #: (as opposed to Next's server-side prefetch) are cross-origin.
    cors_origins: list[str] = Field(
        default_factory=lambda: [
            "http://localhost:3000",  # `pnpm dev` / `pnpm start` run directly
            "http://localhost:3100",  # docker-compose dev stack's published port
            "http://127.0.0.1:3000",  # same, for browsers that use 127.0.0.1
            "http://127.0.0.1:3100",
        ]
    )


class DatabaseConfig(BaseModel):
    url: str = "sqlite+aiosqlite:///./tasko.db"


class BrokerConfig(BaseModel):
    adapter: str = "redis"
    options: dict[str, object] = Field(default_factory=dict)


class WorkersConfig(BaseModel):
    #: A worker silent for longer than this is considered offline.
    ttl_seconds: int = 30


class RetentionConfig(BaseModel):
    finished_tasks: str = "7d"


class AlertsConfig(BaseModel):
    #: set false to stop the background rule evaluator (e.g. in tests)
    enabled: bool = True
    eval_interval_seconds: int = 30
    #: default "hold" duration offered in the UI when creating a rule
    default_for_seconds: int = 60
    #: how long resolved alert events are kept (not enforced yet)
    event_retention_days: int = 30


class Config(BaseModel):
    server: ServerConfig = Field(default_factory=ServerConfig)
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    broker: BrokerConfig = Field(default_factory=BrokerConfig)
    workers: WorkersConfig = Field(default_factory=WorkersConfig)
    retention: RetentionConfig = Field(default_factory=RetentionConfig)
    alerts: AlertsConfig = Field(default_factory=AlertsConfig)


def _find_config_file() -> Path | None:
    env = os.environ.get("TASKO_CONFIG")
    if env:
        return Path(env)
    for name in _CANDIDATES:
        p = Path(name)
        if p.is_file():
            return p
    return None


def load_config() -> Config:
    path = _find_config_file()
    if path is None:
        return Config()
    data = yaml.safe_load(path.read_text()) or {}
    return Config.model_validate(data)
