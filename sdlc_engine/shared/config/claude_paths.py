"""Backward compatibility shim for claude_paths re-exporting from sdlc_paths.

Maintained for existing callers expecting claude_paths module location.
"""

from __future__ import annotations

from sdlc_engine.shared.config.sdlc_paths import (
    display_path,
    get_claude_home,
    get_claude_logs_dir,
    get_claude_memory_dir,
    get_claude_sessions_dir,
)

__all__ = [
    "display_path",
    "get_claude_home",
    "get_claude_logs_dir",
    "get_claude_memory_dir",
    "get_claude_sessions_dir",
]
