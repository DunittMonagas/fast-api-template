"""Pydantic schemas for API request/response models."""
from datetime import datetime
from enum import Enum
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, validator

from app.domain.models import TaskPriority, TaskStatus


# Request schemas
class TaskCreateRequest(BaseModel):
    """Request schema for creating a task."""

    title: str = Field(..., min_length=1, max_length=255, description="Task title")
    description: str = Field(..., min_length=1, description="Task description")
    priority: TaskPriority = Field(default=TaskPriority.MEDIUM, description="Task priority")
    assigned_to: Optional[str] = Field(None, description="Person assigned to the task")

    @validator("title", "description")
    def validate_not_empty(cls, v):
        if not v or not v.strip():
            raise ValueError("Field cannot be empty or contain only whitespace")
        return v.strip()


class TaskUpdateRequest(BaseModel):
    """Request schema for updating a task."""

    title: Optional[str] = Field(None, min_length=1, max_length=255, description="Task title")
    description: Optional[str] = Field(None, min_length=1, description="Task description")

    @validator("title", "description")
    def validate_not_empty(cls, v):
        if v is not None and (not v or not v.strip()):
            raise ValueError("Field cannot be empty or contain only whitespace")
        return v.strip() if v else v


class TaskAssignRequest(BaseModel):
    """Request schema for assigning a task."""

    assignee: str = Field(..., min_length=1, description="Person to assign the task to")

    @validator("assignee")
    def validate_assignee(cls, v):
        if not v or not v.strip():
            raise ValueError("Assignee cannot be empty")
        return v.strip()


class TaskCancelRequest(BaseModel):
    """Request schema for cancelling a task."""

    reason: Optional[str] = Field(None, description="Reason for cancellation")


# Response schemas
class TaskResponse(BaseModel):
    """Response schema for a task."""

    id: UUID
    title: str
    description: str
    status: TaskStatus
    priority: TaskPriority
    assigned_to: Optional[str]
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime]

    class Config:
        orm_mode = True
        json_encoders = {datetime: lambda v: v.isoformat()}


class TaskListResponse(BaseModel):
    """Response schema for a list of tasks."""

    tasks: List[TaskResponse]
    total: int
    limit: int
    offset: int


class TaskStatisticsResponse(BaseModel):
    """Response schema for task statistics."""

    total: int
    by_status: dict[str, int]
    by_priority: dict[str, int]


class HealthCheckResponse(BaseModel):
    """Response schema for health check."""

    status: str
    timestamp: datetime
    services: dict[str, bool]

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class ErrorResponse(BaseModel):
    """Response schema for errors."""

    error: str
    message: str
    details: Optional[dict] = None
    request_id: Optional[str] = None

    class Config:
        schema_extra = {
            "example": {
                "error": "EntityNotFound",
                "message": "Task with id 123e4567-e89b-12d3-a456-426614174000 not found",
                "details": {
                    "entity_type": "Task",
                    "entity_id": "123e4567-e89b-12d3-a456-426614174000",
                },
                "request_id": "req_abc123",
            }
        }


class MessageResponse(BaseModel):
    """Generic message response."""

    message: str

    class Config:
        schema_extra = {"example": {"message": "Operation completed successfully"}}
