"""Task service - Application layer service for task use cases."""
import logging
from datetime import datetime
from typing import List, Optional
from uuid import UUID, uuid4

from app.application.repositories import EventPublisher, TaskRepository, UnitOfWork
from app.domain.events import (
    TaskAssignedEvent,
    TaskCancelledEvent,
    TaskCompletedEvent,
    TaskCreatedEvent,
    TaskStartedEvent,
)
from app.domain.exceptions import BusinessRuleViolationException, EntityNotFoundException
from app.domain.models import Task, TaskPriority, TaskStatus

logger = logging.getLogger(__name__)


class TaskService:
    """Service for handling task-related use cases."""

    def __init__(
        self,
        task_repository: TaskRepository,
        unit_of_work: UnitOfWork,
        event_publisher: EventPublisher,
    ):
        self.task_repository = task_repository
        self.unit_of_work = unit_of_work
        self.event_publisher = event_publisher

    def create_task(
        self,
        title: str,
        description: str,
        priority: TaskPriority = TaskPriority.MEDIUM,
        assigned_to: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> Task:
        """Create a new task."""
        logger.info(f"Creating task: {title}")

        # Validate input
        if not title or not title.strip():
            raise BusinessRuleViolationException(
                "task_title_required", "Task title cannot be empty"
            )

        if not description or not description.strip():
            raise BusinessRuleViolationException(
                "task_description_required", "Task description cannot be empty"
            )

        with self.unit_of_work:
            # Create domain entity
            task = Task.create(
                title=title.strip(),
                description=description.strip(),
                priority=priority,
                assigned_to=assigned_to,
            )

            # Save to repository
            saved_task = self.task_repository.save(task)

            # Publish domain event
            event = TaskCreatedEvent(
                event_id=uuid4(),
                occurred_at=datetime.utcnow(),
                task_id=saved_task.id,
                title=saved_task.title,
                assigned_to=saved_task.assigned_to,
                priority=saved_task.priority.value,
            )
            self.event_publisher.publish("task.created", event.to_dict())

            self.unit_of_work.commit()

            logger.info(f"Task created successfully: {saved_task.id}")
            return saved_task

    def get_task(self, task_id: UUID) -> Task:
        """Get a task by ID."""
        task = self.task_repository.get_by_id(task_id)
        if not task:
            raise EntityNotFoundException("Task", task_id)
        return task

    def list_tasks(
        self,
        status: Optional[TaskStatus] = None,
        assigned_to: Optional[str] = None,
        priority: Optional[TaskPriority] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Task]:
        """List tasks with optional filtering."""
        return self.task_repository.get_all(
            status=status, assigned_to=assigned_to, priority=priority, limit=limit, offset=offset
        )

    def start_task(self, task_id: UUID, user_id: Optional[str] = None) -> Task:
        """Start working on a task."""
        logger.info(f"Starting task: {task_id}")

        with self.unit_of_work:
            task = self.get_task(task_id)

            # Apply domain logic
            task.start()

            # Save changes
            saved_task = self.task_repository.save(task)

            # Publish event
            event = TaskStartedEvent(
                event_id=uuid4(), occurred_at=datetime.utcnow(), task_id=task_id, started_by=user_id
            )
            self.event_publisher.publish("task.started", event.to_dict())

            self.unit_of_work.commit()

            logger.info(f"Task started successfully: {task_id}")
            return saved_task

    def complete_task(self, task_id: UUID, user_id: Optional[str] = None) -> Task:
        """Mark a task as completed."""
        logger.info(f"Completing task: {task_id}")

        with self.unit_of_work:
            task = self.get_task(task_id)

            # Apply domain logic
            task.complete()

            # Save changes
            saved_task = self.task_repository.save(task)

            # Publish event
            event = TaskCompletedEvent(
                event_id=uuid4(),
                occurred_at=datetime.utcnow(),
                task_id=task_id,
                completed_by=user_id,
            )
            self.event_publisher.publish("task.completed", event.to_dict())

            self.unit_of_work.commit()

            logger.info(f"Task completed successfully: {task_id}")
            return saved_task

    def cancel_task(
        self, task_id: UUID, reason: Optional[str] = None, user_id: Optional[str] = None
    ) -> Task:
        """Cancel a task."""
        logger.info(f"Cancelling task: {task_id}")

        with self.unit_of_work:
            task = self.get_task(task_id)

            # Apply domain logic
            task.cancel()

            # Save changes
            saved_task = self.task_repository.save(task)

            # Publish event
            event = TaskCancelledEvent(
                event_id=uuid4(),
                occurred_at=datetime.utcnow(),
                task_id=task_id,
                cancelled_by=user_id,
                reason=reason,
            )
            self.event_publisher.publish("task.cancelled", event.to_dict())

            self.unit_of_work.commit()

            logger.info(f"Task cancelled successfully: {task_id}")
            return saved_task

    def assign_task(self, task_id: UUID, assignee: str, user_id: Optional[str] = None) -> Task:
        """Assign a task to someone."""
        logger.info(f"Assigning task {task_id} to {assignee}")

        if not assignee or not assignee.strip():
            raise BusinessRuleViolationException("assignee_required", "Assignee cannot be empty")

        with self.unit_of_work:
            task = self.get_task(task_id)

            # Apply domain logic
            task.assign_to(assignee.strip())

            # Save changes
            saved_task = self.task_repository.save(task)

            # Publish event
            event = TaskAssignedEvent(
                event_id=uuid4(),
                occurred_at=datetime.utcnow(),
                task_id=task_id,
                assigned_to=assignee,
                assigned_by=user_id,
            )
            self.event_publisher.publish("task.assigned", event.to_dict())

            self.unit_of_work.commit()

            logger.info(f"Task assigned successfully: {task_id} -> {assignee}")
            return saved_task

    def update_task(
        self, task_id: UUID, title: Optional[str] = None, description: Optional[str] = None
    ) -> Task:
        """Update task details."""
        logger.info(f"Updating task: {task_id}")

        with self.unit_of_work:
            task = self.get_task(task_id)

            # Validate input
            if title is not None and not title.strip():
                raise BusinessRuleViolationException(
                    "task_title_required", "Task title cannot be empty"
                )

            if description is not None and not description.strip():
                raise BusinessRuleViolationException(
                    "task_description_required", "Task description cannot be empty"
                )

            # Apply domain logic
            task.update_details(
                title=title.strip() if title else None,
                description=description.strip() if description else None,
            )

            # Save changes
            saved_task = self.task_repository.save(task)

            self.unit_of_work.commit()

            logger.info(f"Task updated successfully: {task_id}")
            return saved_task

    def delete_task(self, task_id: UUID) -> bool:
        """Delete a task."""
        logger.info(f"Deleting task: {task_id}")

        with self.unit_of_work:
            # Check if task exists
            if not self.task_repository.exists(task_id):
                raise EntityNotFoundException("Task", task_id)

            # Delete from repository
            deleted = self.task_repository.delete(task_id)

            self.unit_of_work.commit()

            logger.info(f"Task deleted successfully: {task_id}")
            return deleted

    def get_task_statistics(self, assigned_to: Optional[str] = None) -> dict:
        """Get task statistics."""
        stats = {
            "total": self.task_repository.count(assigned_to=assigned_to),
            "by_status": {},
            "by_priority": {},
        }

        # Count by status
        for status in TaskStatus:
            count = self.task_repository.count(status=status, assigned_to=assigned_to)
            if count > 0:
                stats["by_status"][status.value] = count

        # Get tasks to count by priority
        tasks = self.task_repository.get_all(assigned_to=assigned_to, limit=1000)
        priority_counts = {}
        for task in tasks:
            priority_counts[task.priority.value] = priority_counts.get(task.priority.value, 0) + 1

        stats["by_priority"] = priority_counts

        return stats
