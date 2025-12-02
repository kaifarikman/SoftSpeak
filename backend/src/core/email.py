from __future__ import annotations

from email.message import EmailMessage

import anyio
import smtplib

from src.core.config import settings


def _build_message(subject: str, body: str, recipient: str) -> EmailMessage:

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = settings.email_from
    message["To"] = recipient
    message.set_content(body)
    return message


async def send_email_async(subject: str, body: str, recipient: str) -> None:

    message = _build_message(subject, body, recipient)

    def _send(msg: EmailMessage) -> None:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as server:
            if settings.smtp_use_tls:
                server.starttls()
            if settings.smtp_user:
                server.login(settings.smtp_user, settings.smtp_password)
            server.send_message(msg)

    await anyio.to_thread.run_sync(_send, message, cancellable=True)


async def send_verification_code_email(email: str, code: str) -> None:

    subject = "SoftSpeak: код подтверждения регистрации"
    body = (
        f"Здравствуйте!\n\n"
        f"Ваш код подтверждения для регистрации в SoftSpeak: {code}\n"
        f"Он будет действителен в течение {settings.verification_code_ttl_min} минут.\n\n"
        f"Если вы не запрашивали код, просто проигнорируйте это письмо."
    )
    await send_email_async(subject, body, email)
