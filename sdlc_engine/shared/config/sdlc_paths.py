"""Universal bootstrap for the path_resolver API used across AI-Native SDLC Engine.

Consolidates path resolution for all framework modules, providing platform-agnostic
access to engine home, logs, sessions, and memory directories.
"""

from __future__ import annotations

import sys
from pathlib import Path

_SRC_DIR = Path(__file__).resolve().parents[2] / "src"
_SDLC_DIR_NAME = "." + "sdlc"
_CLAUDE_DIR_NAME = "." + "claude"

try:
    if str(_SRC_DIR) not in sys.path:
        sys.path.insert(0, str(_SRC_DIR))
    from utils.path_resolver import (  # noqa: F401
        display_path,
        get_claude_home,
        get_claude_logs_dir,
        get_claude_memory_dir,
        get_claude_sessions_dir,
        get_engine_home,
        get_sdlc_home,
        get_sdlc_logs_dir,
        get_sdlc_memory_dir,
        get_sdlc_sessions_dir,
    )
except ImportError:

    def get_sdlc_home() -> Path:
        """Return the SDLC home directory with fallback to Claude home when present.

        Returns:
            Path: The user's SDLC engine home directory.
        """
        sdlc = Path.home() / _SDLC_DIR_NAME
        claude = Path.home() / _CLAUDE_DIR_NAME
        if sdlc.exists() or not claude.exists():
            return sdlc
        return claude

    def get_engine_home() -> Path:
        """Return the framework engine home directory.

        Returns:
            Path: The framework home directory.
        """
        return get_sdlc_home()

    def get_claude_home() -> Path:
        """Return the Claude home directory for backward compatibility.

        Returns:
            Path: The user's Claude or SDLC home directory.
        """
        return get_sdlc_home()

    def get_sdlc_logs_dir() -> Path:
        """Return the SDLC logs root without the resolver.

        Returns:
            Path: The logs root directory.
        """
        return get_sdlc_home() / "logs"

    def get_claude_logs_dir() -> Path:
        """Return the logs root without the resolver for backward compatibility.

        Returns:
            Path: The logs root directory.
        """
        return get_sdlc_logs_dir()

    def get_sdlc_memory_dir() -> Path:
        """Return the SDLC memory directory without the resolver.

        Returns:
            Path: The memory directory.
        """
        return get_sdlc_home() / "memory"

    def get_claude_memory_dir() -> Path:
        """Return the memory directory for backward compatibility.

        Returns:
            Path: The memory directory.
        """
        return get_sdlc_memory_dir()

    def get_sdlc_sessions_dir() -> Path:
        """Return the SDLC sessions directory without the resolver.

        Returns:
            Path: The sessions directory.
        """
        return get_sdlc_home() / "sessions"

    def get_claude_sessions_dir() -> Path:
        """Return the sessions directory for backward compatibility.

        Returns:
            Path: The sessions directory.
        """
        return get_sdlc_sessions_dir()

    def display_path(*parts: object) -> str:
        """Return the portable display spelling of an engine path.

        Args:
            *parts: Path components to append below the home directory.

        Returns:
            str: Display path using forward slashes on every platform.
        """
        home = get_sdlc_home()
        try:
            base = "~/" + home.relative_to(Path.home()).as_posix()
        except ValueError:
            base = home.as_posix()
        tail = "/".join(str(part).strip("/") for part in parts if str(part).strip("/"))
        return base + "/" + tail if tail else base


__all__ = [
    "display_path",
    "get_claude_home",
    "get_claude_logs_dir",
    "get_claude_memory_dir",
    "get_claude_sessions_dir",
    "get_engine_home",
    "get_sdlc_home",
    "get_sdlc_logs_dir",
    "get_sdlc_memory_dir",
    "get_sdlc_sessions_dir",
]
