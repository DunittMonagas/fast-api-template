"""Integration tests for SQLAlchemyTaskRepository."""
from datetime import datetime
from uuid import uuid4

import pytest

from app.domain.models import Task, TaskPriority, TaskStatus
from app.infrastructure.database.models import TaskModel
from app.infrastructure.database.repositories.task_repository import SQLAlchemyTaskRepository


class TestSQLAlchemyTaskRepository:
    """Integration tests for SQLAlchemyTaskRepository."""

    @pytest.fixture
    def repository(self, mock_db_session):
        """Create repository instance."""
        return SQLAlchemyTaskRepository(mock_db_session)

    def test_save_new_task(self, repository, test_session):
        """Test saving a new task."""
        # Arrange
        task = Task.create(
            title="Integration Test Task",
            description="Test Description",
            priority=TaskPriority.HIGH,
            assigned_to="test.user",
        )

        # Act
        saved_task = repository.save(task)

        # Assert
        assert saved_task.id == task.id
        assert saved_task.title == task.title

        # Verify in database
        db_task = test_session.query(TaskModel).filter_by(id=task.id).first()
        assert db_task is not None
        assert db_task.title == task.title
        assert db_task.status == TaskStatus.PENDING

    def test_save_existing_task_updates(self, repository, test_session):
        """Test updating an existing task."""
        # Arrange - Create and save initial task
        task = Task.create(
            title="Original Title", description="Original Description", priority=TaskPriority.LOW
        )
        repository.save(task)

        # Modify the task
        task.title = "Updated Title"
        task.start()

        # Act
        updated_task = repository.save(task)

        # Assert
        assert updated_task.title == "Updated Title"
        assert updated_task.status == TaskStatus.IN_PROGRESS

        # Verify in database
        db_task = test_session.query(TaskModel).filter_by(id=task.id).first()
        assert db_task.title == "Updated Title"
        assert db_task.status == TaskStatus.IN_PROGRESS

    def test_get_by_id(self, repository, test_session):
        """Test retrieving a task by ID."""
        # Arrange - Create task directly in database
        task_id = uuid4()
        db_task = TaskModel(
            id=task_id,
            title="Database Task",
            description="Test Description",
            status=TaskStatus.PENDING,
            priority=TaskPriority.MEDIUM,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        test_session.add(db_task)
        test_session.commit()

        # Act
        retrieved_task = repository.get_by_id(task_id)

        # Assert
        assert retrieved_task is not None
        assert retrieved_task.id == task_id
        assert retrieved_task.title == "Database Task"

    def test_get_by_id_not_found(self, repository):
        """Test retrieving non-existent task returns None."""
        # Act
        result = repository.get_by_id(uuid4())

        # Assert
        assert result is None

    def test_get_all_with_filters(self, repository, test_session):
        """Test retrieving tasks with filters."""
        # Arrange - Create multiple tasks
        tasks_data = [
            ("Task 1", TaskStatus.PENDING, TaskPriority.HIGH, "user1"),
            ("Task 2", TaskStatus.IN_PROGRESS, TaskPriority.HIGH, "user1"),
            ("Task 3", TaskStatus.COMPLETED, TaskPriority.LOW, "user2"),
            ("Task 4", TaskStatus.PENDING, TaskPriority.MEDIUM, "user2"),
        ]

        for title, status, priority, assigned_to in tasks_data:
            task = TaskModel(
                id=uuid4(),
                title=title,
                description="Test",
                status=status,
                priority=priority,
                assigned_to=assigned_to,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
            test_session.add(task)
        test_session.commit()

        # Act - Filter by status
        pending_tasks = repository.get_all(status=TaskStatus.PENDING)
        assert len(pending_tasks) == 2

        # Act - Filter by assigned_to
        user1_tasks = repository.get_all(assigned_to="user1")
        assert len(user1_tasks) == 2

        # Act - Filter by priority
        high_priority_tasks = repository.get_all(priority=TaskPriority.HIGH)
        assert len(high_priority_tasks) == 2

        # Act - Combined filters
        user1_pending = repository.get_all(status=TaskStatus.PENDING, assigned_to="user1")
        assert len(user1_pending) == 1

    def test_delete_task(self, repository, test_session):
        """Test deleting a task."""
        # Arrange
        task = Task.create(title="To Be Deleted", description="Test Description")
        repository.save(task)

        # Act
        deleted = repository.delete(task.id)

        # Assert
        assert deleted is True

        # Verify not in database
        db_task = test_session.query(TaskModel).filter_by(id=task.id).first()
        assert db_task is None

    def test_delete_non_existent_task(self, repository):
        """Test deleting non-existent task returns False."""
        # Act
        deleted = repository.delete(uuid4())

        # Assert
        assert deleted is False

    def test_exists(self, repository, test_session):
        """Test checking if task exists."""
        # Arrange
        task_id = uuid4()
        db_task = TaskModel(
            id=task_id,
            title="Existing Task",
            description="Test",
            status=TaskStatus.PENDING,
            priority=TaskPriority.MEDIUM,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        test_session.add(db_task)
        test_session.commit()

        # Act & Assert
        assert repository.exists(task_id) is True
        assert repository.exists(uuid4()) is False

    def test_count_with_filters(self, repository, test_session):
        """Test counting tasks with filters."""
        # Arrange - Create tasks
        for i in range(5):
            task = TaskModel(
                id=uuid4(),
                title=f"Task {i}",
                description="Test",
                status=TaskStatus.PENDING if i < 3 else TaskStatus.COMPLETED,
                priority=TaskPriority.MEDIUM,
                assigned_to="user1" if i < 2 else "user2",
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
            test_session.add(task)
        test_session.commit()

        # Act & Assert
        assert repository.count() == 5
        assert repository.count(status=TaskStatus.PENDING) == 3
        assert repository.count(assigned_to="user1") == 2
        assert repository.count(status=TaskStatus.PENDING, assigned_to="user1") == 2
