"""Gmail SMTP sender for daily/weekly reports.

Uses stdlib smtplib + StartTLS on port 587 (or SSL on 465).
Supports HTML + plain text + inline image attachments.
"""
from __future__ import annotations

import smtplib
import ssl
from email.message import EmailMessage
from pathlib import Path

from stockdeal.config import get_settings


class EmailNotifier:
    def __init__(self) -> None:
        s = get_settings()
        self._host = s.smtp_host
        self._port = s.smtp_port
        self._user = s.smtp_user
        self._password = s.smtp_password.get_secret_value()
        self._from = s.from_email or s.smtp_user
        self._to = s.to_email or s.smtp_user

    def send(
        self,
        subject: str,
        html: str,
        text: str | None = None,
        attachments: list[Path] | None = None,
    ) -> None:
        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = self._from
        msg["To"] = self._to
        msg.set_content(text or "HTML version required.")
        msg.add_alternative(html, subtype="html")

        for path in attachments or []:
            data = path.read_bytes()
            msg.add_attachment(
                data,
                maintype="image",
                subtype=path.suffix.lstrip("."),
                filename=path.name,
            )

        context = ssl.create_default_context()
        if self._port == 465:
            with smtplib.SMTP_SSL(self._host, self._port, context=context) as s:
                s.login(self._user, self._password)
                s.send_message(msg)
        else:
            with smtplib.SMTP(self._host, self._port) as s:
                s.starttls(context=context)
                s.login(self._user, self._password)
                s.send_message(msg)
