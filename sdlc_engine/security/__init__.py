"""
Security and preflight guard package.
"""

from .preflight_merge import MAX_PREFLIGHT_ATTEMPTS, preflight_guard_merge_node
from .preflight_nodes import node_encoding_validation, node_unicode_fix, node_windows_path_check
from .preflight_recovery import ask_preflight_guard_fix, fix_preflight_guard_issues
from .secrets_manager import validate_secrets

__all__ = [
    "MAX_PREFLIGHT_ATTEMPTS",
    "preflight_guard_merge_node",
    "node_encoding_validation",
    "node_unicode_fix",
    "node_windows_path_check",
    "ask_preflight_guard_fix",
    "fix_preflight_guard_issues",
    "validate_secrets",
]
