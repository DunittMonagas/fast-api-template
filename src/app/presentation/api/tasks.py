"""FastAPI router for task endpoints."""
import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import JSONResponse

from app.application.services.task_service import TaskService
from app.domain.exceptions import (
    BusinessRuleViolationException,
    DomainException,
    EntityNotFoundException,
)
from app.domain.models import TaskPriority, TaskStatus
from app.presentation.api.schemas import (
    ErrorResponse,
    MessageResponse,
    TaskAssignRequest,
    TaskCancelRequest,
    TaskCreateRequest,
    TaskListResponse,
    TaskResponse,
    TaskStatisticsResponse,
    TaskUpdateRequest,
)

logger = logging.getLogger(__name__)


def create_task_router(task_service: TaskService) -> APIRouter:
    """Create task router with dependency injection."""

    router = APIRouter(
        prefix="/tasks",
        tags=["tasks"],
        responses={
            404: {"model": ErrorResponse, "description": "Task not found"},
            422: {"model": ErrorResponse, "description": "Validation error"},
        },
    )

    @router.post(
        "/",
        response_model=TaskResponse,
        status_code=status.HTTP_201_CREATED,
        summary="Create a new task",
        description="Create a new task with the provided details",
    )
    async def create_task(request: TaskCreateRequest, req: Request) -> TaskResponse:
        """Create a new task."""
        try:
            # Get user ID from request context (would come from auth middleware)
            user_id = req.headers.get("X-User-ID")

            # Call synchronous service from async endpoint
            task = task_service.create_task(
                title=request.title,
                description=request.description,
                priority=request.priority,
                assigned_to=request.assigned_to,
                user_id=user_id,
            )

            return TaskResponse(
                id=task.id,
                title=task.title,
                description=task.description,
                status=task.status,
                priority=task.priority,
                assigned_to=task.assigned_to,
                created_at=task.created_at,
                updated_at=task.updated_at,
                completed_at=task.completed_at,
            )

        except BusinessRuleViolationException as e:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={"error": e.__class__.__name__, "message": e.message, "details": e.details},
            )
        except Exception as e:
            logger.error(f"Error creating task: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={"error": "InternalServerError", "message": "An unexpected error occurred"},
            )

    @router.get(
        "/{task_id}",
        response_model=TaskResponse,
        summary="Get a task by ID",
        description="Retrieve a specific task by its ID",
    )
    async def get_task(task_id: UUID) -> TaskResponse:
        """Get a task by ID."""
        try:
            task = task_service.get_task(task_id)

            return TaskResponse(
                id=task.id,
                title=task.title,
                description=task.description,
                status=task.status,
                priority=task.priority,
                assigned_to=task.assigned_to,
                created_at=task.created_at,
                updated_at=task.updated_at,
                completed_at=task.completed_at,
            )

        except EntityNotFoundException as e:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"error": e.__class__.__name__, "message": e.message, "details": e.details},
            )
        except Exception as e:
            logger.error(f"Error getting task {task_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={"error": "InternalServerError", "message": "An unexpected error occurred"},
            )

    @router.get(
        "/",
        response_model=TaskListResponse,
        summary="List tasks",
        description="List tasks with optional filtering and pagination",
    )
    async def list_tasks(
        status: Optional[TaskStatus] = Query(None, description="Filter by status"),
        assigned_to: Optional[str] = Query(None, description="Filter by assignee"),
        priority: Optional[TaskPriority] = Query(None, description="Filter by priority"),
        limit: int = Query(100, ge=1, le=1000, description="Maximum number of results"),
        offset: int = Query(0, ge=0, description="Number of results to skip"),
    ) -> TaskListResponse:
        """List tasks with optional filtering."""
        try:
            tasks = task_service.list_tasks(
                status=status,
                assigned_to=assigned_to,
                priority=priority,
                limit=limit,
                offset=offset,
            )

            # Get total count
            total = task_service.task_repository.count(status=status, assigned_to=assigned_to)

            return TaskListResponse(
                tasks=[
                    TaskResponse(
                        id=task.id,
                        title=task.title,
                        description=task.description,
                        status=task.status,
                        priority=task.priority,
                        assigned_to=task.assigned_to,
                        created_at=task.created_at,
                        updated_at=task.updated_at,
                        completed_at=task.completed_at,
                    )
                    for task in tasks
                ],
                total=total,
                limit=limit,
                offset=offset,
            )

        except Exception as e:
            logger.error(f"Error listing tasks: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={"error": "InternalServerError", "message": "An unexpected error occurred"},
            )

    @router.patch(
        "/{task_id}",
        response_model=TaskResponse,
        summary="Update a task",
        description="Update task details (title and/or description)",
    )
    async def update_task(task_id: UUID, request: TaskUpdateRequest) -> TaskResponse:
        """Update task details."""
        try:
            task = task_service.update_task(
                task_id=task_id, title=request.title, description=request.description
            )

            return TaskResponse(
                id=task.id,
                title=task.title,
                description=task.description,
                status=task.status,
                priority=task.priority,
                assigned_to=task.assigned_to,
                created_at=task.created_at,
                updated_at=task.updated_at,
                completed_at=task.completed_at,
            )

        except EntityNotFoundException as e:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"error": e.__class__.__name__, "message": e.message, "details": e.details},
            )
        except BusinessRuleViolationException as e:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={"error": e.__class__.__name__, "message": e.message, "details": e.details},
            )
        except Exception as e:
            logger.error(f"Error updating task {task_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={"error": "InternalServerError", "message": "An unexpected error occurred"},
            )

    @router.post(
        "/{task_id}/start",
        response_model=TaskResponse,
        summary="Start a task",
        description="Change task status to IN_PROGRESS",
    )
    async def start_task(task_id: UUID, req: Request) -> TaskResponse:
        """Start working on a task."""
        try:
            user_id = req.headers.get("X-User-ID")

            task = task_service.start_task(task_id, user_id)

            return TaskResponse(
                id=task.id,
                title=task.title,
                description=task.description,
                status=task.status,
                priority=task.priority,
                assigned_to=task.assigned_to,
                created_at=task.created_at,
                updated_at=task.updated_at,
                completed_at=task.completed_at,
            )

        except EntityNotFoundException as e:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"error": e.__class__.__name__, "message": e.message, "details": e.details},
            )
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={"error": "InvalidOperation", "message": str(e)},
            )
        except Exception as e:
            logger.error(f"Error starting task {task_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={"error": "InternalServerError", "message": "An unexpected error occurred"},
            )

    @router.post(
        "/{task_id}/complete",
        response_model=TaskResponse,
        summary="Complete a task",
        description="Mark a task as completed",
    )
    async def complete_task(task_id: UUID, req: Request) -> TaskResponse:
        """Mark a task as completed."""
        try:
            user_id = req.headers.get("X-User-ID")

            task = task_service.complete_task(task_id, user_id)

            return TaskResponse(
                id=task.id,
                title=task.title,
                description=task.description,
                status=task.status,
                priority=task.priority,
                assigned_to=task.assigned_to,
                created_at=task.created_at,
                updated_at=task.updated_at,
                completed_at=task.completed_at,
            )

        except EntityNotFoundException as e:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"error": e.__class__.__name__, "message": e.message, "details": e.details},
            )
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={"error": "InvalidOperation", "message": str(e)},
            )
        except Exception as e:
            logger.error(f"Error completing task {task_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={"error": "InternalServerError", "message": "An unexpected error occurred"},
            )

    @router.post(
        "/{task_id}/cancel",
        response_model=TaskResponse,
        summary="Cancel a task",
        description="Cancel a task with an optional reason",
    )
    async def cancel_task(task_id: UUID, request: TaskCancelRequest, req: Request) -> TaskResponse:
        """Cancel a task."""
        try:
            user_id = req.headers.get("X-User-ID")

            task = task_service.cancel_task(task_id, request.reason, user_id)

            return TaskResponse(
                id=task.id,
                title=task.title,
                description=task.description,
                status=task.status,
                priority=task.priority,
                assigned_to=task.assigned_to,
                created_at=task.created_at,
                updated_at=task.updated_at,
                completed_at=task.completed_at,
            )

        except EntityNotFoundException as e:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"error": e.__class__.__name__, "message": e.message, "details": e.details},
            )
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={"error": "InvalidOperation", "message": str(e)},
            )
        except Exception as e:
            logger.error(f"Error cancelling task {task_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={"error": "InternalServerError", "message": "An unexpected error occurred"},
            )

    @router.post(
        "/{task_id}/assign",
        response_model=TaskResponse,
        summary="Assign a task",
        description="Assign a task to someone",
    )
    async def assign_task(task_id: UUID, request: TaskAssignRequest, req: Request) -> TaskResponse:
        """Assign a task to someone."""
        try:
            user_id = req.headers.get("X-User-ID")

            task = task_service.assign_task(task_id, request.assignee, user_id)

            return TaskResponse(
                id=task.id,
                title=task.title,
                description=task.description,
                status=task.status,
                priority=task.priority,
                assigned_to=task.assigned_to,
                created_at=task.created_at,
                updated_at=task.updated_at,
                completed_at=task.completed_at,
            )

        except EntityNotFoundException as e:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"error": e.__class__.__name__, "message": e.message, "details": e.details},
            )
        except BusinessRuleViolationException as e:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={"error": e.__class__.__name__, "message": e.message, "details": e.details},
            )
        except Exception as e:
            logger.error(f"Error assigning task {task_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={"error": "InternalServerError", "message": "An unexpected error occurred"},
            )

    @router.delete(
        "/{task_id}",
        response_model=MessageResponse,
        summary="Delete a task",
        description="Delete a task by ID",
    )
    async def delete_task(task_id: UUID) -> MessageResponse:
        """Delete a task."""
        try:
            deleted = task_service.delete_task(task_id)

            if deleted:
                return MessageResponse(message=f"Task {task_id} deleted successfully")
            else:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail={
                        "error": "EntityNotFound",
                        "message": f"Task with id {task_id} not found",
                    },
                )

        except EntityNotFoundException as e:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"error": e.__class__.__name__, "message": e.message, "details": e.details},
            )
        except Exception as e:
            logger.error(f"Error deleting task {task_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={"error": "InternalServerError", "message": "An unexpected error occurred"},
            )

    @router.get(
        "/statistics",
        response_model=TaskStatisticsResponse,
        summary="Get task statistics",
        description="Get aggregated statistics about tasks",
    )
    async def get_task_statistics(
        assigned_to: Optional[str] = Query(None, description="Filter by assignee")
    ) -> TaskStatisticsResponse:
        """Get task statistics."""
        try:
            stats = task_service.get_task_statistics(assigned_to)

            return TaskStatisticsResponse(
                total=stats["total"], by_status=stats["by_status"], by_priority=stats["by_priority"]
            )

        except Exception as e:
            logger.error(f"Error getting task statistics: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={"error": "InternalServerError", "message": "An unexpected error occurred"},
            )

    return router
