"""
Custom exception hierarchy for the AI-Native SDLC Engine.

Provides a consistent set of typed exceptions used across all pipeline
layers (orchestrator, subgraphs, MCP servers, hook scripts).  Every
exception carries an optional step number and an optional context dict
so that error-handling code can make routing decisions without string
parsing.

Hierarchy
---------
WorkflowEngineError (base)
  PolicyExecutionError   - policy script raised or returned failure
  SessionNotFoundError   - referenced session does not exist
  GitOperationError      - git command / git-ops MCP failure
  GitHubAPIError         - GitHub REST / MCP API failure
  ConfigurationError     - missing or invalid env var / config value
  StepExecutionError     - a numbered pipeline step raised an error

Usage
-----
    from sdlc_engine.shared.errors.exceptions import (
        WorkflowEngineError,
        StepExecutionError,
        GitOperationError,
    )

    try:
        run_step(7)
    except StepExecutionError as exc:
        logger.error("Step %d failed with context: %s", exc.step_number, exc.context)
        raise
"""

from __future__ import annotations

from typing import Any, Dict, Optional

# ---------------------------------------------------------------------------
# Base exception
# ---------------------------------------------------------------------------


class WorkflowEngineError(Exception):
    """Base exception for all AI-Native SDLC Engine errors.

    All pipeline-specific exceptions inherit from this class so callers
    can catch the entire family with a single ``except WorkflowEngineError``
    clause when fine-grained handling is not needed.

    Args:
        message:  Human-readable description of what went wrong.
        step:     Optional pipeline step label or number (e.g. ``"step_3"``
                  or ``3``) where the error originated.
        context:  Optional mapping of extra diagnostic values (session ID,
                  file path, policy name, etc.).
    """

    def __init__(
        self,
        message: str,
        step: Optional[Any] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Build the error with a message, optional step, and context mapping."""
        super().__init__(message)
        self.step: Optional[Any] = step
        self.context: Dict[str, Any] = context if context is not None else {}

    def __repr__(self) -> str:
        cls = type(self).__name__
        step_part = f", step={self.step!r}" if self.step is not None else ""
        ctx_part = f", context={self.context!r}" if self.context else ""
        return f"{cls}({str(self)!r}{step_part}{ctx_part})"


# ---------------------------------------------------------------------------
# Specialised exceptions
# ---------------------------------------------------------------------------


class PolicyExecutionError(WorkflowEngineError):
    """Raised when a policy script fails or returns a non-passing result.

    This covers both hard failures (the script crashed) and soft failures
    (the script ran successfully but determined the policy is not met).

    Args:
        message:     Human-readable description of the policy failure.
        step:        Pipeline step where the policy was evaluated.
        context:     Extra diagnostic values.  Conventionally includes
                     ``policy_name`` (str) and ``policy_output`` (str).
    """


class SessionNotFoundError(WorkflowEngineError):
    """Raised when a required session cannot be located.

    The session file may have been deleted, the session ID may be wrong,
    or the session store may be unavailable.

    Args:
        message:    Human-readable description.
        step:       Pipeline step where the lookup was attempted.
        context:    Extra diagnostic values.  Conventionally includes
                    ``session_id`` (str).
    """


class GitOperationError(WorkflowEngineError):
    """Raised when a git command or git-ops MCP tool call fails.

    Covers: branch creation, commit, push, pull, stash, and any other
    local git operation performed by the pipeline.

    Args:
        message:    Human-readable description of the git failure.
        step:       Pipeline step where the operation was attempted.
        context:    Extra diagnostic values.  Conventionally includes
                    ``command`` (str) and ``returncode`` (int).
    """


class GitHubAPIError(WorkflowEngineError):
    """Raised when a GitHub REST API call or github-api MCP tool fails.

    Covers: issue creation, PR creation, merge, label, and any other
    remote GitHub operation performed by the pipeline.

    Args:
        message:      Human-readable description of the API failure.
        step:         Pipeline step where the API call was made.
        context:      Extra diagnostic values.  Conventionally includes
                      ``status_code`` (int), ``endpoint`` (str), and
                      ``response_body`` (str).
    """


class ConfigurationError(WorkflowEngineError):
    """Raised when required configuration is missing or invalid.

    Examples: GITHUB_TOKEN not set, LLM_PROVIDER misconfigured,
    required policy directory absent, invalid JSON in a config file.

    Args:
        message:    Human-readable description of the configuration problem.
        step:       Pipeline step where the configuration was read.
        context:    Extra diagnostic values.  Conventionally includes
                    ``config_key`` (str) and ``expected_value`` (str).
    """


class StepExecutionError(WorkflowEngineError):
    """Raised when a numbered pipeline step fails during execution.

    Wraps lower-level errors that occur inside a specific step so the
    orchestrator can include the step number without re-raising bare
    exceptions.

    Args:
        message:      Human-readable description of the step failure.
        step_number:  The integer step number (1-14) that failed.
        step:         Optional step label alias; defaults to
                      ``str(step_number)`` when not provided.
        context:      Extra diagnostic values.
    """

    def __init__(
        self,
        message: str,
        step_number: int,
        step: Optional[Any] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Build the error with a message, step number, and optional context."""
        resolved_step = step if step is not None else step_number
        super().__init__(message, step=resolved_step, context=context)
        self.step_number: int = step_number

    def __repr__(self) -> str:
        cls = type(self).__name__
        ctx_part = f", context={self.context!r}" if self.context else ""
        return f"{cls}({str(self)!r}, step_number={self.step_number!r}{ctx_part})"


# ---------------------------------------------------------------------------
# Pre-Flight and Security Policy Exceptions
# ---------------------------------------------------------------------------


class PreflightError(WorkflowEngineError):
    """Base exception for all Level 0 (Pre-Flight Sanity Guard) operations.

    Args:
        message: Human-readable description of the pre-flight failure.
        step: Pipeline step where the check failed.
        context: Extra diagnostic values.
    """


class PreflightCheckError(PreflightError):
    """Raised when a pre-flight sanity check fails non-recoverably.

    Args:
        message: Description of the failed check.
        step: Pre-flight check step name.
        context: Context containing check parameters and violating files.
    """


class IntegrityValidationError(PreflightError):
    """Raised when a file fails post-modification integrity or AST syntax validation.

    Args:
        message: Description of the integrity validation failure.
        step: Step in which modification and validation occurred.
        context: Context containing file path, syntax error, or validation details.
    """


class PathNormalizationError(PreflightError):
    """Raised when path normalization or drive letter resolution encounters an invalid path.

    Args:
        message: Description of the path normalization error.
        step: Step where path normalization was attempted.
        context: Context containing path string and target encoding.
    """


# ---------------------------------------------------------------------------
# Backup and Transactional Rollback Exceptions
# ---------------------------------------------------------------------------


class BackupError(WorkflowEngineError):
    """Base exception for file backup, snapshot, and rollback subsystem failures.

    Args:
        message: Description of the backup subsystem failure.
        step: Step name or label where backup/restore was attempted.
        context: Extra diagnostic values such as file path and session ID.
    """


class BackupCreationError(BackupError):
    """Raised when file backup snapshot creation fails due to I/O, permissions, or disk limits.

    Args:
        message: Description of why backup creation failed.
        step: Step in which backup was attempted.
        context: Context containing original file path and target backup path.
    """


class RestoreError(BackupError):
    """Raised when file restoration from a backup snapshot fails or backup artifact is missing.

    Args:
        message: Description of why file restoration failed.
        step: Step in which restoration was attempted.
        context: Context containing original path, backup path, and error reason.
    """
