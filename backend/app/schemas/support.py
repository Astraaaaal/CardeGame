"""
Schemas — signalements de bug.
"""

from datetime import datetime
from pydantic import BaseModel, Field


class BugReportCreate(BaseModel):
    subject: str = Field(min_length=1, max_length=100)
    body: str = Field(min_length=1, max_length=2000)
    page_context: str | None = Field(default=None, max_length=200)


class BugReportOut(BaseModel):
    id: int
    username: str
    subject: str
    body: str
    page_context: str | None = None
    created_at: datetime
    resolved_at: datetime | None = None
