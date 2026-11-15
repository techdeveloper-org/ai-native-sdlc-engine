"""Custom exceptions module for the AI-Native SDLC Engine."""

from sdlc_engine.shared.errors.exceptions import (
    BackupCreationError,
    BackupError,
    ConfigurationError,
    GitHubAPIError,
    GitOperationError,
    IntegrityValidationError,
    PathNormalizationError,
    PolicyExecutionError,
    PreflightCheckError,
    PreflightError,
    RestoreError,
    SessionNotFoundError,
    StepExecutionError,
    WorkflowEngineError,
)

__all__ = [
    "WorkflowEngineError",
    "PolicyExecutionError",
    "SessionNotFoundError",
    "GitOperationError",
    "GitHubAPIError",
    "ConfigurationError",
    "StepExecutionError",
    "PreflightError",
    "PreflightCheckError",
    "IntegrityValidationError",
    "PathNormalizationError",
    "BackupError",
    "BackupCreationError",
    "RestoreError",
]
