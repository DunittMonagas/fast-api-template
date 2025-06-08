"""Unit tests for TaskService."""
from datetime import datetime
from unittest.mock import MagicMock, Mock, call
from uuid import uuid4

import pytest

from app.application.services.task_service import TaskService
from app.domain.exceptions import BusinessRuleViolationException, EntityNotFoundException
from app.domain.models import Task, TaskPriority, TaskStatus


class TestTaskService:
    """Test cases for TaskService."""

    @pytest.fixture
    def mock_repository(self):
        """Create mock task repository."""
        return Mock()

    @pytest.fixture
    def mock_unit_of_work(self):
        """Create mock unit of work."""
        uow = Mock()
        uow.__enter__ = Mock(return_value=uow)
        uow.__exit__ = Mock(return_value=None)
        return uow

    @pytest.fixture
    def mock_event_publisher(self):
        """Create mock event publisher."""
        return Mock()

    @pytest.fixture
    def task_service(self, mock_repository, mock_unit_of_work, mock_event_publisher):
        """Create TaskService instance with mocks."""
        return TaskService(
            task_repository=mock_repository,
            unit_of_work=mock_unit_of_work,
            event_publisher=mock_event_publisher,
        )

    def test_create_task_success(
        self, task_service, mock_repository, mock_unit_of_work, mock_event_publisher
    ):
        """Test successful task creation."""
        # Arrange
        title = "Test Task"
        description = "Test Description"
        priority = TaskPriority.HIGH
        assigned_to = "john.doe"

        # Mock repository save to return the task
        mock_repository.save.return_value = Task(
            id=uuid4(),
            title=title,
            description=description,
            status=TaskStatus.PENDING,
            priority=priority,
            assigned_to=assigned_to,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

        # Act
        result = task_service.create_task(
            title=title,
            description=description,
            priority=priority,
            assigned_to=assigned_to,
            user_id="creator",
        )

        # Assert
        assert result.title == title
        assert result.description == description
        assert result.priority == priority
        assert result.assigned_to == assigned_to
        assert result.status == TaskStatus.PENDING

        # Verify repository was called
        mock_repository.save.assert_called_once()

        # Verify event was published
        mock_event_publisher.publish.assert_called_once()
        event_call = mock_event_publisher.publish.call_args
        assert event_call[0][0] == "task.created"

        # Verify unit of work was committed
        mock_unit_of_work.commit.assert_called_once()

    def test_create_task_empty_title_raises_exception(self, task_service):
        """Test that creating a task with empty title raises exception."""
        # Act & Assert
        with pytest.raises(BusinessRuleViolationException) as exc_info:
            task_service.create_task(
                title="", description="Valid description", priority=TaskPriority.MEDIUM
            )

        assert "Task title cannot be empty" in str(exc_info.value)

    def test_get_task_success(self, task_service, mock_repository):
        """Test successful task retrieval."""
        # Arrange
        task_id = uuid4()
        expected_task = Task(
            id=task_id,
            title="Test Task",
            description="Test Description",
            status=TaskStatus.PENDING,
            priority=TaskPriority.MEDIUM,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        mock_repository.get_by_id.return_value = expected_task

        # Act
        result = task_service.get_task(task_id)

        # Assert
        assert result == expected_task
        mock_repository.get_by_id.assert_called_once_with(task_id)

    def test_get_task_not_found_raises_exception(self, task_service, mock_repository):
        """Test that getting non-existent task raises exception."""
        # Arrange
        task_id = uuid4()
        mock_repository.get_by_id.return_value = None

        # Act & Assert
        with pytest.raises(EntityNotFoundException) as exc_info:
            task_service.get_task(task_id)

        assert f"Task with id {task_id} not found" in str(exc_info.value)

    def test_start_task_success(
        self, task_service, mock_repository, mock_unit_of_work, mock_event_publisher
    ):
        """Test successful task start."""
        # Arrange
        task_id = uuid4()
        task = Task(
            id=task_id,
            title="Test Task",
            description="Test Description",
            status=TaskStatus.PENDING,
            priority=TaskPriority.MEDIUM,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        mock_repository.get_by_id.return_value = task
        mock_repository.save.return_value = task

        # Act
        result = task_service.start_task(task_id, "user123")

        # Assert
        assert task.status == TaskStatus.IN_PROGRESS
        mock_repository.save.assert_called_once_with(task)
        mock_event_publisher.publish.assert_called_once()
        mock_unit_of_work.commit.assert_called_once()

    def test_complete_task_success(
        self, task_service, mock_repository, mock_unit_of_work, mock_event_publisher
    ):
        """Test successful task completion."""
        # Arrange
        task_id = uuid4()
        task = Task(
            id=task_id,
            title="Test Task",
            description="Test Description",
            status=TaskStatus.IN_PROGRESS,
            priority=TaskPriority.MEDIUM,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        mock_repository.get_by_id.return_value = task
        mock_repository.save.return_value = task

        # Act
        result = task_service.complete_task(task_id, "user123")

        # Assert
        assert task.status == TaskStatus.COMPLETED
        assert task.completed_at is not None
        mock_repository.save.assert_called_once_with(task)
        mock_event_publisher.publish.assert_called_once()
        mock_unit_of_work.commit.assert_called_once()

    def test_delete_task_success(self, task_service, mock_repository, mock_unit_of_work):
        """Test successful task deletion."""
        # Arrange
        task_id = uuid4()
        mock_repository.exists.return_value = True
        mock_repository.delete.return_value = True

        # Act
        result = task_service.delete_task(task_id)

        # Assert
        assert result is True
        mock_repository.exists.assert_called_once_with(task_id)
        mock_repository.delete.assert_called_once_with(task_id)
        mock_unit_of_work.commit.assert_called_once()

    def test_delete_task_not_found_raises_exception(self, task_service, mock_repository):
        """Test that deleting non-existent task raises exception."""
        # Arrange
        task_id = uuid4()
        mock_repository.exists.return_value = False

        # Act & Assert
        with pytest.raises(EntityNotFoundException):
            task_service.delete_task(task_id)
