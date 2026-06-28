from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import InterestTag, User, UserInterestTag
from src.db.session import get_db

router = APIRouter(prefix="/tags", tags=["tags"])

MAX_INTEREST_TAGS = 5


class TagSchema(BaseModel):
    id: int
    name: str
    emoji: str = ""


class SetUserTagsRequest(BaseModel):
    tag_ids: list[int] = Field(default_factory=list, max_length=MAX_INTEREST_TAGS)


async def _get_user_or_404(session: AsyncSession, email: str) -> User:
    result = await session.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Пользователь не найден"
        )
    return user


@router.get("", response_model=list[TagSchema])
async def get_all_tags(session: AsyncSession = Depends(get_db)) -> list[TagSchema]:
    result = await session.execute(select(InterestTag).order_by(InterestTag.id))
    tags = result.scalars().all()
    return [TagSchema(id=tag.id, name=tag.name, emoji=tag.emoji) for tag in tags]


@router.get("/user/{email}", response_model=list[TagSchema])
async def get_user_tags(
    email: str, session: AsyncSession = Depends(get_db)
) -> list[TagSchema]:
    user = await _get_user_or_404(session, email)
    result = await session.execute(
        select(InterestTag)
        .join(UserInterestTag, UserInterestTag.tag_id == InterestTag.id)
        .where(UserInterestTag.user_id == user.id)
        .order_by(InterestTag.id)
    )
    tags = result.scalars().all()
    return [TagSchema(id=tag.id, name=tag.name, emoji=tag.emoji) for tag in tags]


@router.post("/user/{email}")
async def set_user_tags(
    email: str,
    request: SetUserTagsRequest,
    session: AsyncSession = Depends(get_db),
) -> dict:
    tag_ids = list(dict.fromkeys(request.tag_ids))
    if len(tag_ids) > MAX_INTEREST_TAGS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Максимум {MAX_INTEREST_TAGS} тегов",
        )

    user = await _get_user_or_404(session, email)
    if tag_ids:
        result = await session.execute(
            select(InterestTag.id).where(InterestTag.id.in_(tag_ids))
        )
        existing_ids = set(result.scalars().all())
        missing_ids = [tag_id for tag_id in tag_ids if tag_id not in existing_ids]
        if missing_ids:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Один или несколько тегов не найдены",
            )

    await session.execute(
        delete(UserInterestTag).where(UserInterestTag.user_id == user.id)
    )
    for tag_id in tag_ids:
        session.add(UserInterestTag(user_id=user.id, tag_id=tag_id))
    await session.commit()
    return {"ok": True, "tag_ids": tag_ids}
