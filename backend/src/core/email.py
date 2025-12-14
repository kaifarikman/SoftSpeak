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
    host: str
    port: int
    use_ssl: bool


SMTP_CONFIGS = {
    "yandex.ru": SmtpConfig("smtp.yandex.ru", 465, True),
    "yandex.com": SmtpConfig("smtp.yandex.ru", 465, True),
    "ya.ru": SmtpConfig("smtp.yandex.ru", 465, True),
    "mail.ru": SmtpConfig("smtp.mail.ru", 465, True),
    "inbox.ru": SmtpConfig("smtp.mail.ru", 465, True),
    "list.ru": SmtpConfig("smtp.mail.ru", 465, True),
    "bk.ru": SmtpConfig("smtp.mail.ru", 465, True),
    "gmail.com": SmtpConfig("smtp.gmail.com", 587, False),
}


def _get_smtp_config_for_email(email: str) -> SmtpConfig:
    domain = email.lower().split("@")[-1]
    if domain in SMTP_CONFIGS:
        return SMTP_CONFIGS[domain]
    return SmtpConfig(settings.smtp_host, settings.smtp_port, not settings.smtp_use_tls)


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
            logger.info(f"[DEV] Отправка email через MailHog на {recipient}")
            with smtplib.SMTP(
                settings.smtp_host, settings.smtp_port, timeout=30
            ) as server:
                server.send_message(msg)
        else:
            smtp_config = _get_smtp_config_for_email(settings.email_from)
            logger.info(
                f"[PROD] Отправка email через {smtp_config.host}:{smtp_config.port} (SSL={smtp_config.use_ssl}) на {recipient}"
            )
            if not settings.smtp_user or not settings.smtp_password:
                raise ValueError(
                    "SMTP_USER и SMTP_PASSWORD должны быть установлены для отправки email в продакшене"
                )
            if smtp_config.use_ssl:
                success = False
                last_error = None
                try:
                    context = ssl.create_default_context()
                    with smtplib.SMTP_SSL(
                        smtp_config.host, smtp_config.port, context=context, timeout=30
                    ) as server:
                        server.login(settings.smtp_user, settings.smtp_password)
                        server.send_message(msg)
                        logger.info(
                            f"Email успешно отправлен на {recipient} (SSL с проверкой сертификата)"
                        )
                        success = True
                except Exception as e:
                    last_error = e
                    logger.warning(
                        f"Не удалось подключиться через SSL с проверкой сертификата: {e}"
                    )
                if not success:
                    try:
                        context = ssl.create_default_context()
                        context.check_hostname = False
                        context.verify_mode = ssl.CERT_NONE
                        with smtplib.SMTP_SSL(
                            smtp_config.host,
                            smtp_config.port,
                            context=context,
                            timeout=30,
                        ) as server:
                            server.login(settings.smtp_user, settings.smtp_password)
                            server.send_message(msg)
                            logger.info(
                                f"Email успешно отправлен на {recipient} (SSL без проверки сертификата)"
                            )
                            success = True
                    except Exception as e:
                        last_error = e
                        logger.warning(
                            f"Не удалось подключиться через SSL без проверки сертификата: {e}"
                        )
                if not success and smtp_config.host == "smtp.yandex.ru":
                    try:
                        logger.info(
                            "Попытка подключения через STARTTLS на порту 587..."
                        )
                        context = ssl.create_default_context()
                        with smtplib.SMTP("smtp.yandex.ru", 587, timeout=30) as server:
                            server.starttls(context=context)
                            server.login(settings.smtp_user, settings.smtp_password)
                            server.send_message(msg)
                            logger.info(
                                f"Email успешно отправлен на {recipient} (STARTTLS на 587)"
                            )
                            success = True
                    except Exception as e:
                        last_error = e
                        logger.warning(f"Не удалось подключиться через STARTTLS: {e}")
                if not success:
                    error_msg = f"Не удалось отправить email через {smtp_config.host}:{smtp_config.port}. Последняя ошибка: {last_error}"
                    logger.error(error_msg)
                    raise RuntimeError(error_msg)
            else:
                try:
                    context = ssl.create_default_context()
                    with smtplib.SMTP(
                        smtp_config.host, smtp_config.port, timeout=30
                    ) as server:
                        server.starttls(context=context)
                        server.login(settings.smtp_user, settings.smtp_password)
                        server.send_message(msg)
                        logger.info(
                            f"Email успешно отправлен на {recipient} (STARTTLS)"
                        )
                except Exception as e:
                    error_msg = f"Не удалось отправить email через STARTTLS {smtp_config.host}:{smtp_config.port}: {e}"
                    logger.error(error_msg)
                    raise RuntimeError(error_msg)

    await anyio.to_thread.run_sync(_send, message, cancellable=True)


async def send_verification_code_email(email: str, code: str) -> None:
    subject = "SoftSpeak: код подтверждения регистрации"
    body = f"Здравствуйте!\n\nВаш код подтверждения для регистрации в SoftSpeak: {code}\nОн будет действителен в течение {settings.verification_code_ttl_min} минут.\n\nЕсли вы не запрашивали код, просто проигнорируйте это письмо."
    await send_email_async(subject, body, email)
