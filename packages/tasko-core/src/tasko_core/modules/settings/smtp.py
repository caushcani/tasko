"""Send email through the SMTP relay configured in Settings.

Shared by the settings module's own test endpoint and the alerts module's
email notification channel — one relay config, two callers.
"""

from __future__ import annotations

from email.message import EmailMessage

import aiosmtplib

from tasko_core.modules.settings.models import AppSettings


class SmtpNotConfigured(Exception):
    pass


async def send_email(settings: AppSettings, *, to: list[str], subject: str, body: str) -> None:
    if not settings.smtp_host or not settings.smtp_from:
        raise SmtpNotConfigured("SMTP host and from-address must be configured")

    message = EmailMessage()
    message["From"] = settings.smtp_from
    message["To"] = ", ".join(to)
    message["Subject"] = subject
    message.set_content(body)

    await aiosmtplib.send(
        message,
        hostname=settings.smtp_host,
        port=settings.smtp_port or 587,
        username=settings.smtp_username or None,
        password=settings.smtp_password or None,
        start_tls=settings.smtp_use_tls,
    )
