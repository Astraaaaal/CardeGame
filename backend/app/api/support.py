"""
Routes — signalement de bug par un joueur, consultation admin.
"""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.database import get_session
from app.core.dependencies import get_current_user, require_admin
from app.core.ratelimit import rate_limit
from app.models.user import User
from app.models.support import BugReport
from app.schemas.support import BugReportCreate, BugReportOut

router = APIRouter()
admin_router = APIRouter(dependencies=[Depends(require_admin)])


@router.post(
    "/bug-reports", response_model=BugReportOut, status_code=201,
    dependencies=[Depends(rate_limit(10, 300))],
)
async def create_bug_report(
    body: BugReportCreate,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    report = BugReport(
        user_id=user.id, username=user.username,
        subject=body.subject.strip(), body=body.body.strip(), page_context=body.page_context,
    )
    session.add(report)
    await session.commit()
    await session.refresh(report)
    return report


@admin_router.get("/", response_model=list[BugReportOut])
async def list_bug_reports(session: AsyncSession = Depends(get_session)):
    rows = (await session.execute(
        select(BugReport).order_by(BugReport.resolved_at.is_not(None), BugReport.created_at.desc())
    )).scalars().all()
    return rows


@admin_router.post("/{report_id}/resolve", response_model=BugReportOut)
async def resolve_bug_report(report_id: int, session: AsyncSession = Depends(get_session)):
    report = await session.get(BugReport, report_id)
    if not report:
        raise HTTPException(404, "Signalement introuvable.")
    report.resolved_at = datetime.utcnow()
    session.add(report)
    await session.commit()
    await session.refresh(report)
    return report


@admin_router.delete("/{report_id}", status_code=204)
async def delete_bug_report(report_id: int, session: AsyncSession = Depends(get_session)):
    report = await session.get(BugReport, report_id)
    if not report:
        raise HTTPException(404, "Signalement introuvable.")
    await session.delete(report)
    await session.commit()
