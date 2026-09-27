"""HTTP endpoints for the settings module."""

from __future__ import annotations

from fastapi import APIRouter

from tasko_core.infrastructure.database import SessionDep
from tasko_core.modules.settings import service, smtp
from tasko_core.modules.settings.models import AppSettings
from tasko_core.modules.settings.schemas import (
    SettingsOut,
    SettingsUpdate,
    SmtpTestIn,
    SmtpTestResult,
)

router = APIRouter(tags=["settings"], prefix="/settings")


def _to_out(row: AppSettings) -> SettingsOut:
    return SettingsOut(
        smtp_host=row.smtp_host,
        smtp_port=row.smtp_port,
        smtp_username=row.smtp_username,
        smtp_password_set=bool(row.smtp_password),
        smtp_from=row.smtp_from,
        smtp_use_tls=row.smtp_use_tls,
        worker_ttl_seconds=row.worker_ttl_seconds,
        alert_eval_interval_seconds=row.alert_eval_interval_seconds,
        updated_at=row.updated_at,
    )


@router.get("", response_model=SettingsOut)
async def get_settings(session: SessionDep) -> SettingsOut:
    return _to_out(await service.get_settings(session))


@router.patch("", response_model=SettingsOut)
async def update_settings(payload: SettingsUpdate, session: SessionDep) -> SettingsOut:
    return _to_out(await service.update_settings(session, payload))


@router.post("/smtp/test", response_model=SmtpTestResult)
async def test_smtp(payload: SmtpTestIn, session: SessionDep) -> SmtpTestResult:
    settings = await service.get_settings(session)
    try:
        await smtp.send_email(
            settings,
            to=[payload.to],
            subject="Tasko test notification",
            body="This is a test email from Tasko — your SMTP relay is reachable.",
        )
        return SmtpTestResult(ok=True, detail=f"sent to {payload.to}")
    except Exception as exc:
        return SmtpTestResult(ok=False, detail=str(exc) or exc.__class__.__name__)
