from __future__ import annotations

from email.message import EmailMessage
import logging
from typing import NamedTuple

import anyio
import smtplib
import ssl

from src.core.config import settings

logger = logging.getLogger(__name__)


class SmtpConfig(NamedTuple):
    """Конфигурация SMTP сервера."""
    host: str
    port: int
    use_ssl: bool  # True = SSL (465), False = STARTTLS (587)


# Конфигурации SMTP серверов для разных провайдеров
SMTP_CONFIGS = {
    # Yandex (SSL на порту 465)
    "yandex.ru": SmtpConfig("smtp.yandex.ru", 465, True),
    "yandex.com": SmtpConfig("smtp.yandex.ru", 465, True),
    "ya.ru": SmtpConfig("smtp.yandex.ru", 465, True),
    
    # Mail.ru (SSL на порту 465)
    "mail.ru": SmtpConfig("smtp.mail.ru", 465, True),
    "inbox.ru": SmtpConfig("smtp.mail.ru", 465, True),
    "list.ru": SmtpConfig("smtp.mail.ru", 465, True),
    "bk.ru": SmtpConfig("smtp.mail.ru", 465, True),
    
    # Gmail (STARTTLS на порту 587)
    "gmail.com": SmtpConfig("smtp.gmail.com", 587, False),
}


def _get_smtp_config_for_email(email: str) -> SmtpConfig:
    """Получает конфигурацию SMTP на основе домена отправителя."""
    domain = email.lower().split("@")[-1]
    
    if domain in SMTP_CONFIGS:
        return SMTP_CONFIGS[domain]
    
    # Fallback на настройки из конфига
    return SmtpConfig(
        settings.smtp_host,
        settings.smtp_port,
        not settings.smtp_use_tls  # smtp_use_tls=True означает STARTTLS, use_ssl=False
    )


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
        if settings.dev_mode:
            # Режим разработки - MailHog (без SSL/TLS)
            logger.info(f"[DEV] Отправка email через MailHog на {recipient}")
            with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as server:
                server.send_message(msg)
        else:
            # Продакшен - реальный SMTP
            smtp_config = _get_smtp_config_for_email(settings.email_from)
            logger.info(
                f"[PROD] Отправка email через {smtp_config.host}:{smtp_config.port} "
                f"(SSL={smtp_config.use_ssl}) на {recipient}"
            )
            
            if smtp_config.use_ssl:
                # SSL соединение (порт 465) - Yandex, Mail.ru
                context = ssl.create_default_context()
                with smtplib.SMTP_SSL(smtp_config.host, smtp_config.port, context=context) as server:
                    if settings.smtp_user and settings.smtp_password:
                        server.login(settings.smtp_user, settings.smtp_password)
                    server.send_message(msg)
            else:
                # STARTTLS соединение (порт 587) - Gmail
                with smtplib.SMTP(smtp_config.host, smtp_config.port) as server:
                    server.starttls(context=ssl.create_default_context())
                    if settings.smtp_user and settings.smtp_password:
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
