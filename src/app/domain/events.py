"""Domain events - Events that occur within the domain."""
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict
from uuid import UUID


@dataclass
class DomainEvent:
    """Base class for all domain events."""

    event_id: UUID
    occurred_at: datetime

    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary for serialization."""
        return {
            "event_type": self.__class__.__name__,
            "event_id": str(self.event_id),
            "occurred_at": self.occurred_at.isoformat(),
            "data": self._get_event_data(),
        }

    def _get_event_data(self) -> Dict[str, Any]:
        """Get event-specific data. Override in subclasses."""
        raise NotImplementedError


@dataclass
class TaskCreatedEvent(DomainEvent):
    """Event raised when a task is created."""

    task_id: UUID
    title: str
    assigned_to: str | None
    priority: str

    def _get_event_data(self) -> Dict[str, Any]:
        return {
            "task_id": str(self.task_id),
            "title": self.title,
            "assigned_to": self.assigned_to,
            "priority": self.priority,
        }


@dataclass
class TaskStartedEvent(DomainEvent):
    """Event raised when a task is started."""

    task_id: UUID
    started_by: str | None

    def _get_event_data(self) -> Dict[str, Any]:
        return {"task_id": str(self.task_id), "started_by": self.started_by}


@dataclass
class TaskCompletedEvent(DomainEvent):
    """Event raised when a task is completed."""

    task_id: UUID
    completed_by: str | None

    def _get_event_data(self) -> Dict[str, Any]:
        return {"task_id": str(self.task_id), "completed_by": self.completed_by}


@dataclass
class TaskCancelledEvent(DomainEvent):
    """Event raised when a task is cancelled."""

    task_id: UUID
    cancelled_by: str | None
    reason: str | None

    def _get_event_data(self) -> Dict[str, Any]:
        return {
            "task_id": str(self.task_id),
            "cancelled_by": self.cancelled_by,
            "reason": self.reason,
        }


@dataclass
class TaskAssignedEvent(DomainEvent):
    """Event raised when a task is assigned to someone."""

    task_id: UUID
    assigned_to: str
    assigned_by: str | None

    def _get_event_data(self) -> Dict[str, Any]:
        return {
            "task_id": str(self.task_id),
            "assigned_to": self.assigned_to,
            "assigned_by": self.assigned_by,
        }
