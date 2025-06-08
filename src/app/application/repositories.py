"""Repository interfaces - Abstract base classes for repository implementations."""
from abc import ABC, abstractmethod
from typing import List, Optional
from uuid import UUID

from app.domain.models import Task, TaskPriority, TaskStatus


class TaskRepository(ABC):
    """Abstract interface for Task repository."""

    @abstractmethod
    def get_by_id(self, task_id: UUID) -> Optional[Task]:
        """Get a task by its ID."""
        pass

    @abstractmethod
    def get_all(
        self,
        status: Optional[TaskStatus] = None,
        assigned_to: Optional[str] = None,
        priority: Optional[TaskPriority] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Task]:
        """Get all tasks with optional filtering."""
        pass

    @abstractmethod
    def save(self, task: Task) -> Task:
        """Save a task (create or update)."""
        pass

    @abstractmethod
    def delete(self, task_id: UUID) -> bool:
        """Delete a task by ID. Returns True if deleted, False if not found."""
        pass

    @abstractmethod
    def exists(self, task_id: UUID) -> bool:
        """Check if a task exists."""
        pass

    @abstractmethod
    def count(self, status: Optional[TaskStatus] = None, assigned_to: Optional[str] = None) -> int:
        """Count tasks with optional filtering."""
        pass


class UnitOfWork(ABC):
    """Abstract Unit of Work pattern for managing transactions."""

    @abstractmethod
    def __enter__(self):
        """Begin transaction."""
        pass

    @abstractmethod
    def __exit__(self, exc_type, exc_val, exc_tb):
        """End transaction (commit or rollback)."""
        pass

    @abstractmethod
    def commit(self):
        """Commit the current transaction."""
        pass

    @abstractmethod
    def rollback(self):
        """Rollback the current transaction."""
        pass


class EventPublisher(ABC):
    """Abstract interface for publishing domain events."""

    @abstractmethod
    def publish(self, event_type: str, event_data: dict) -> None:
        """Publish an event."""
        pass
