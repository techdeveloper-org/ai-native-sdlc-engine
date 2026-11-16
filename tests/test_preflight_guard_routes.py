"""Tests for Level 0 Pre-Flight Guard routing decisions and transition guards.

Verifies conditional routing edges between Level 0 pre-flight checks,
user recovery choice, retry count bounding, and level1_session transitions.
Level 2.2 Docstrings-Only compliant.
"""

import pytest

from sdlc_engine.quality.runtime_verification.verifier import RuntimeVerifier
from sdlc_engine.routing.flow_state import FlowState, StepKeys
from sdlc_engine.routing.preflight_guard_routes import (
    _MAX_PREFLIGHT_ATTEMPTS,
    route_after_preflight_guard,
    route_after_preflight_guard_user_choice,
)


@pytest.fixture(autouse=True)
def reset_verifier(monkeypatch):
    """Enable runtime verification and isolate the singleton instance for each test.

    Args:
        monkeypatch: Pytest monkeypatch fixture.
    """
    monkeypatch.setenv("ENABLE_RUNTIME_VERIFICATION", "1")
    RuntimeVerifier.reset_for_tests()
    yield
    RuntimeVerifier.reset_for_tests()


class TestPreflightGuardRoutes:
    """Test suite for Level 0 conditional edges and transition verification."""

    def test_route_after_preflight_guard_ok_routes_to_level1(self):
        """Positive: Successful preflight checks route directly to level1_session."""
        state: FlowState = {
            StepKeys.PREFLIGHT_STATUS: "OK",
            StepKeys.AUTO_FIX_COMPLETE: True,
        }
        route = route_after_preflight_guard(state)
        assert route == "level1_session"

    def test_route_after_preflight_guard_failed_routes_to_ask(self):
        """Negative: Failed preflight status routes to ask_preflight_guard_fix."""
        state: FlowState = {
            StepKeys.PREFLIGHT_STATUS: "FAILED",
            StepKeys.AUTO_FIX_COMPLETE: False,
        }
        route = route_after_preflight_guard(state)
        assert route == "ask_preflight_guard_fix"

    def test_route_user_choice_autofix_within_budget(self):
        """Positive: auto-fix choice within attempt budget routes to fix_preflight_guard."""
        state: FlowState = {
            StepKeys.PREFLIGHT_USER_CHOICE: "auto-fix",
            StepKeys.PREFLIGHT_RETRY_COUNT: 2,
        }
        route = route_after_preflight_guard_user_choice(state)
        assert route == "fix_preflight_guard"

    def test_route_user_choice_autofix_at_budget_limit(self):
        """Edge-Case: auto-fix choice at attempt 3 routes to fix_preflight_guard."""
        state: FlowState = {
            StepKeys.PREFLIGHT_USER_CHOICE: "auto-fix",
            StepKeys.PREFLIGHT_RETRY_COUNT: _MAX_PREFLIGHT_ATTEMPTS,
        }
        route = route_after_preflight_guard_user_choice(state)
        assert route == "fix_preflight_guard"

    def test_route_user_choice_autofix_exceeded_budget(self):
        """Negative: auto-fix choice exceeding attempt budget falls through to level1_session."""
        state: FlowState = {
            StepKeys.PREFLIGHT_USER_CHOICE: "auto-fix",
            StepKeys.PREFLIGHT_RETRY_COUNT: _MAX_PREFLIGHT_ATTEMPTS + 1,
            StepKeys.AUTO_FIX_COMPLETE: False,
        }
        route = route_after_preflight_guard_user_choice(state)
        assert route == "level1_session"

    def test_route_user_choice_skip_routes_to_level1(self):
        """Positive: Explicit user skip choice routes directly to level1_session."""
        state: FlowState = {
            StepKeys.PREFLIGHT_USER_CHOICE: "skip",
            StepKeys.AUTO_FIX_COMPLETE: False,
        }
        route = route_after_preflight_guard_user_choice(state)
        assert route == "level1_session"

    def test_route_user_choice_force_continue_routes_to_level1(self):
        """Edge-Case: Fatal escalation force_continue choice routes to level1_session."""
        state: FlowState = {
            StepKeys.PREFLIGHT_USER_CHOICE: "force_continue",
            StepKeys.AUTO_FIX_COMPLETE: False,
        }
        route = route_after_preflight_guard_user_choice(state)
        assert route == "level1_session"
