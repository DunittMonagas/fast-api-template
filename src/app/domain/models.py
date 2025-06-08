"""Domain models - Core business entities with no infrastructure dependencies."""
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4


class TaskStatus(Enum):
    """Task status enumeration."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class TaskPriority(Enum):
    """Task priority enumeration."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class Task:
    """Task domain entity."""

    id: UUID
    title: str
    description: str
    status: TaskStatus
    priority: TaskPriority
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime] = None
    assigned_to: Optional[str] = None

    @classmethod
    def create(
        cls,
        title: str,
        description: str,
        priority: TaskPriority = TaskPriority.MEDIUM,
        assigned_to: Optional[str] = None,
    ) -> "Task":
        """Factory method to create a new task."""
        now = datetime.utcnow()
        return cls(
            id=uuid4(),
            title=title,
            description=description,
            status=TaskStatus.PENDING,
            priority=priority,
            created_at=now,
            updated_at=now,
            completed_at=None,
            assigned_to=assigned_to,
        )

    def start(self) -> None:
        """Start working on the task."""
        if self.status != TaskStatus.PENDING:
            raise ValueError(f"Cannot start task in {self.status} status")
        self.status = TaskStatus.IN_PROGRESS
        self.updated_at = datetime.utcnow()

    def complete(self) -> None:
        """Mark the task as completed."""
        if self.status == TaskStatus.COMPLETED:
            raise ValueError("Task is already completed")
        if self.status == TaskStatus.CANCELLED:
            raise ValueError("Cannot complete a cancelled task")
        self.status = TaskStatus.COMPLETED
        self.completed_at = datetime.utcnow()
        self.updated_at = self.completed_at

    def cancel(self) -> None:
        """Cancel the task."""
        if self.status == TaskStatus.COMPLETED:
            raise ValueError("Cannot cancel a completed task")
        self.status = TaskStatus.CANCELLED
        self.updated_at = datetime.utcnow()

    def update_details(
        self, title: Optional[str] = None, description: Optional[str] = None
    ) -> None:
        """Update task details."""
        if title:
            self.title = title
        if description:
            self.description = description
        self.updated_at = datetime.utcnow()

    def assign_to(self, assignee: str) -> None:
        """Assign the task to someone."""
        self.assigned_to = assignee
        self.updated_at = datetime.utcnow()

    def is_overdue(self, deadline: datetime) -> bool:
        """Check if the task is overdue based on a deadline."""
        return (
            self.status not in [TaskStatus.COMPLETED, TaskStatus.CANCELLED]
            and datetime.utcnow() > deadline
        )
