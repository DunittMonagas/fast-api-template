"""SQLAlchemy implementation of TaskRepository."""
import logging
from typing import List, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.application.repositories import TaskRepository
from app.domain.models import Task, TaskPriority, TaskStatus
from app.infrastructure.database.models import TaskModel
from app.infrastructure.database.session import DatabaseSession

logger = logging.getLogger(__name__)


class SQLAlchemyTaskRepository(TaskRepository):
    """Concrete implementation of TaskRepository using SQLAlchemy."""

    def __init__(self, db_session: DatabaseSession):
        self.db_session = db_session

    def _to_domain(self, model: TaskModel) -> Task:
        """Convert SQLAlchemy model to domain entity."""
        return Task(
            id=model.id,
            title=model.title,
            description=model.description,
            status=model.status,
            priority=model.priority,
            created_at=model.created_at,
            updated_at=model.updated_at,
            completed_at=model.completed_at,
            assigned_to=model.assigned_to,
        )

    def _to_model(self, entity: Task) -> TaskModel:
        """Convert domain entity to SQLAlchemy model."""
        return TaskModel(
            id=entity.id,
            title=entity.title,
            description=entity.description,
            status=entity.status,
            priority=entity.priority,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
            completed_at=entity.completed_at,
            assigned_to=entity.assigned_to,
        )

    def get_by_id(self, task_id: UUID) -> Optional[Task]:
        """Get a task by its ID."""
        with self.db_session.get_session() as session:
            model = session.query(TaskModel).filter(TaskModel.id == task_id).first()
            return self._to_domain(model) if model else None

    def get_all(
        self,
        status: Optional[TaskStatus] = None,
        assigned_to: Optional[str] = None,
        priority: Optional[TaskPriority] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Task]:
        """Get all tasks with optional filtering."""
        with self.db_session.get_session() as session:
            query = session.query(TaskModel)

            # Apply filters
            if status is not None:
                query = query.filter(TaskModel.status == status)
            if assigned_to is not None:
                query = query.filter(TaskModel.assigned_to == assigned_to)
            if priority is not None:
                query = query.filter(TaskModel.priority == priority)

            # Order by creation date (newest first)
            query = query.order_by(TaskModel.created_at.desc())
            
            # Apply pagination
            query = query.limit(limit).offset(offset)

            models = query.all()
            return [self._to_domain(model) for model in models]

    def save(self, task: Task) -> Task:
        """Save a task (create or update)."""
        with self.db_session.get_session() as session:
            # Check if task exists
            existing = session.query(TaskModel).filter(TaskModel.id == task.id).first()

            if existing:
                # Update existing task
                existing.title = task.title
                existing.description = task.description
                existing.status = task.status
                existing.priority = task.priority
                existing.assigned_to = task.assigned_to
                existing.updated_at = task.updated_at
                existing.completed_at = task.completed_at

                session.commit()
                session.refresh(existing)
                return self._to_domain(existing)
            else:
                # Create new task
                model = self._to_model(task)
                session.add(model)
                session.commit()
                session.refresh(model)
                return self._to_domain(model)

    def delete(self, task_id: UUID) -> bool:
        """Delete a task by ID. Returns True if deleted, False if not found."""
        with self.db_session.get_session() as session:
            model = session.query(TaskModel).filter(TaskModel.id == task_id).first()
            if model:
                session.delete(model)
                session.commit()
                return True
            return False

    def exists(self, task_id: UUID) -> bool:
        """Check if a task exists."""
        with self.db_session.get_session() as session:
            return session.query(
                session.query(TaskModel).filter(TaskModel.id == task_id).exists()
            ).scalar()

    def count(self, status: Optional[TaskStatus] = None, assigned_to: Optional[str] = None) -> int:
        """Count tasks with optional filtering."""
        with self.db_session.get_session() as session:
            query = session.query(TaskModel)

            if status is not None:
                query = query.filter(TaskModel.status == status)
            if assigned_to is not None:
                query = query.filter(TaskModel.assigned_to == assigned_to)

            return query.count()
