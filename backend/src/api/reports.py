from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field
from typing import Optional

from src.db.session import get_db
from src.db.crud.auth import get_user_by_username
from src.db.crud import reports as reports_crud

router = APIRouter(prefix="/reports", tags=["reports"])

REPORT_REASONS = [
    "оскорбление",
    "жесткое обращение с детьми",
    "насилие",
    "незаконные товары и услуги",
    "порнографические материалы",
    "мошенничество",
    "другое",
]


class CreateReportRequest(BaseModel):
    chat_id: int = Field(..., description="ID чата")
    reason: str = Field(..., description="Причина жалобы")
    description: Optional[str] = Field(None, max_length=500, description="Дополнительное описание (для 'другое')")


class ReportResponse(BaseModel):
    id: int
    chat_id: int
    reason: str
    description: Optional[str]
    status: str
    created_at: str

    class Config:
        from_attributes = True


class ReportCreateResponse(BaseModel):
    success: bool
    message: str
    report: Optional[ReportResponse] = None


@router.post("", response_model=ReportCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_report(
    request: CreateReportRequest,
    username: str,
    session: AsyncSession = Depends(get_db),
) -> ReportCreateResponse:
    if request.reason not in REPORT_REASONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Неверная причина. Доступные: {', '.join(REPORT_REASONS)}",
        )
    
    if request.reason == "другое" and not request.description:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Для причины 'другое' необходимо указать описание",
        )
    
    user = await get_user_by_username(session, username)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Пользователь не найден",
        )
    
    from sqlalchemy import select
    from src.db.models import AnonymousChat
    
    chat_stmt = select(AnonymousChat).where(AnonymousChat.id == request.chat_id)
    chat_result = await session.execute(chat_stmt)
    chat = chat_result.scalar_one_or_none()
    
    if not chat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Чат не найден",
        )
    
    reported_user_id = chat.user2_id if chat.user1_id == user.id else chat.user1_id
    
    success, error_message, report = await reports_crud.create_report(
        session,
        reporter_id=user.id,
        reported_user_id=reported_user_id,
        chat_id=request.chat_id,
        reason=request.reason,
        description=request.description,
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_message or "Ошибка создания жалобы",
        )
    
    return ReportCreateResponse(
        success=True,
        message="Жалоба отправлена. Чат заблокирован до рассмотрения.",
        report=ReportResponse(
            id=report.id,
            chat_id=report.chat_id,
            reason=report.reason,
            description=report.description,
            status=report.status,
            created_at=report.created_at.isoformat(),
        ),
    )


@router.delete("/{report_id}", status_code=status.HTTP_200_OK)
async def cancel_report(
    report_id: int,
    username: str,
    session: AsyncSession = Depends(get_db),
) -> dict:
    user = await get_user_by_username(session, username)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Пользователь не найден",
        )
    
    success, error_message = await reports_crud.cancel_report(
        session,
        report_id=report_id,
        user_id=user.id,
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_message or "Ошибка отмены жалобы",
        )
    
    return {
        "success": True,
        "message": "Жалоба отменена. Чат разблокирован.",
    }


@router.get("/my", response_model=list[ReportResponse])
async def get_my_reports(
    username: str,
    session: AsyncSession = Depends(get_db),
) -> list[ReportResponse]:
    user = await get_user_by_username(session, username)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Пользователь не найден",
        )
    
    reports = await reports_crud.get_user_reports(session, user.id)
    
    return [
        ReportResponse(
            id=report.id,
            chat_id=report.chat_id,
            reason=report.reason,
            description=report.description,
            status=report.status,
            created_at=report.created_at.isoformat(),
        )
        for report in reports
    ]


@router.get("/reasons", response_model=list[str])
async def get_report_reasons() -> list[str]:
    return REPORT_REASONS

