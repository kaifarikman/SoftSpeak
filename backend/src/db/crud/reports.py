from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional, Tuple

from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import Report, User, AnonymousChat


async def create_report(
    session: AsyncSession,
    reporter_id: int,
    reported_user_id: int,
    chat_id: int,
    reason: str,
    description: Optional[str] = None,
) -> Tuple[bool, Optional[str], Optional[Report]]:
    if reporter_id == reported_user_id:
        return False, "Нельзя пожаловаться на самого себя", None
    
    chat_stmt = select(AnonymousChat).where(AnonymousChat.id == chat_id)
    chat_result = await session.execute(chat_stmt)
    chat = chat_result.scalar_one_or_none()
    
    if not chat:
        return False, "Чат не найден", None
    
    if chat.is_blocked:
        return False, "Чат уже заблокирован", None
    
    if chat.user1_id != reporter_id and chat.user2_id != reporter_id:
        return False, "Вы не являетесь участником этого чата", None
    
    if chat.user1_id != reported_user_id and chat.user2_id != reported_user_id:
        return False, "Пользователь не является участником этого чата", None
    
    existing_pending_stmt = select(Report).where(
        and_(
            Report.reporter_id == reporter_id,
            Report.chat_id == chat_id,
            Report.status == "pending"
        )
    )
    existing_pending_result = await session.execute(existing_pending_stmt)
    existing_pending = existing_pending_result.scalar_one_or_none()
    
    if existing_pending:
        return False, "У вас уже есть активная жалоба на этот чат", None
    
    report = Report(
        reporter_id=reporter_id,
        reported_user_id=reported_user_id,
        chat_id=chat_id,
        reason=reason,
        description=description,
        status="pending",
    )
    session.add(report)
    await session.flush()
    
    chat.is_blocked = True
    chat.blocked_by_report_id = report.id
    await session.commit()
    await session.refresh(report)
    
    return True, None, report


async def cancel_report(
    session: AsyncSession,
    report_id: int,
    user_id: int,
) -> Tuple[bool, Optional[str]]:
    report_stmt = select(Report).where(Report.id == report_id)
    report_result = await session.execute(report_stmt)
    report = report_result.scalar_one_or_none()
    
    if not report:
        return False, "Жалоба не найдена"
    
    if report.reporter_id != user_id:
        return False, "Вы не можете отменить эту жалобу"
    
    if report.status != "pending":
        return False, "Можно отменить только жалобу со статусом 'pending'"
    
    chat_stmt = select(AnonymousChat).where(AnonymousChat.id == report.chat_id)
    chat_result = await session.execute(chat_stmt)
    chat = chat_result.scalar_one_or_none()
    
    if chat:
        chat.is_blocked = False
        chat.blocked_by_report_id = None
    
    report.status = "cancelled"
    await session.commit()
    
    return True, None


async def get_user_reports(
    session: AsyncSession,
    user_id: int,
) -> list[Report]:
    stmt = select(Report).where(Report.reporter_id == user_id).order_by(Report.created_at.desc())
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def get_all_reports(
    session: AsyncSession,
    status: Optional[str] = None,
) -> list[Report]:
    stmt = select(Report).order_by(Report.created_at.desc())
    if status:
        stmt = stmt.where(Report.status == status)
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def get_report_by_id(
    session: AsyncSession,
    report_id: int,
) -> Optional[Report]:
    stmt = select(Report).where(Report.id == report_id)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def ban_user_from_report(
    session: AsyncSession,
    report_id: int,
    admin_id: int,
) -> Tuple[bool, Optional[str]]:
    report_stmt = select(Report).where(Report.id == report_id)
    report_result = await session.execute(report_stmt)
    report = report_result.scalar_one_or_none()
    
    if not report:
        return False, "Жалоба не найдена"
    
    if report.status != "pending":
        return False, "Жалоба уже обработана"
    
    user_stmt = select(User).where(User.id == report.reported_user_id)
    user_result = await session.execute(user_stmt)
    user = user_result.scalar_one_or_none()
    
    if not user:
        return False, "Пользователь не найден"
    
    user.is_banned = True
    report.status = "banned"
    report.resolved_at = datetime.now(timezone.utc)
    report.resolved_by_admin_id = admin_id
    await session.commit()
    
    return True, None


async def reject_report(
    session: AsyncSession,
    report_id: int,
    admin_id: int,
) -> Tuple[bool, Optional[str]]:
    report_stmt = select(Report).where(Report.id == report_id)
    report_result = await session.execute(report_stmt)
    report = report_result.scalar_one_or_none()
    
    if not report:
        return False, "Жалоба не найдена"
    
    if report.status != "pending":
        return False, "Жалоба уже обработана"
    
    user_stmt = select(User).where(User.id == report.reported_user_id)
    user_result = await session.execute(user_stmt)
    user = user_result.scalar_one_or_none()
    
    if not user:
        return False, "Пользователь не найден"
    
    user.reports_count += 1
    
    chat_stmt = select(AnonymousChat).where(AnonymousChat.id == report.chat_id)
    chat_result = await session.execute(chat_stmt)
    chat = chat_result.scalar_one_or_none()
    
    if chat:
        chat.is_blocked = False
        chat.blocked_by_report_id = None
    
    report.status = "rejected"
    report.resolved_at = datetime.now(timezone.utc)
    report.resolved_by_admin_id = admin_id
    await session.commit()
    
    return True, None

