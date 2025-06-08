"""Domain exceptions - Custom exceptions for domain-specific errors."""
from typing import Optional
from uuid import UUID


class DomainException(Exception):
    """Base exception for all domain errors."""

    def __init__(self, message: str, details: Optional[dict] = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}


class EntityNotFoundException(DomainException):
    """Raised when a domain entity is not found."""

    def __init__(self, entity_type: str, entity_id: UUID | str):
        super().__init__(
            f"{entity_type} with id {entity_id} not found",
            {"entity_type": entity_type, "entity_id": str(entity_id)},
        )


class BusinessRuleViolationException(DomainException):
    """Raised when a business rule is violated."""

    def __init__(self, rule: str, message: str):
        super().__init__(f"Business rule violation: {message}", {"rule": rule})


class InvalidOperationException(DomainException):
    """Raised when an invalid operation is attempted."""

    pass


class ConcurrencyException(DomainException):
    """Raised when a concurrency conflict occurs."""

    def __init__(self, entity_type: str, entity_id: UUID | str):
        super().__init__(
            f"Concurrency conflict for {entity_type} with id {entity_id}",
            {"entity_type": entity_type, "entity_id": str(entity_id)},
        )
