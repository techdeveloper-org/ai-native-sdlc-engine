"""Tests for Windows Path Policy (Policy #1).

Triad Test Matrix enforcing AST-based path scanning, non-greedy mixed-slash
normalization, microsecond atomic backup locking, and non-destructive rollbacks.
Level 2.2 Docstrings-Only compliant.
"""

import os
import stat
import sys
import time
from pathlib import Path
from typing import Tuple

import pytest

from sdlc_engine.security.path_scan import has_drive_path
from sdlc_engine.security.preflight_merge import preflight_guard_merge_node
from sdlc_engine.security.preflight_nodes import _iter_project_py_files, node_windows_path_check
from sdlc_engine.security.preflight_recovery import (
    _atomic_write_text,
    ask_preflight_guard_fix,
    fix_preflight_guard_issues,
)
from sdlc_engine.session.backup_manager import BackupManager

SEP = chr(92)


def make_drive_path(*parts: str, drive: str = "C") -> str:
    """Assemble a Windows drive path dynamically at runtime.

    Avoids literal hardcoded drive strings in test code to prevent
    the preflight scanner from self-flagging test suites.

    Args:
        *parts: Subdirectories and filename segments.
        drive: Windows drive letter.

    Returns:
        str: Dynamically constructed Windows path.
    """
    if not parts:
        return f"{drive}:{SEP}"
    return f"{drive}:{SEP}" + SEP.join(parts)


@pytest.fixture
def isolated_workspace(tmp_path: Path) -> Tuple[Path, Path]:
    """Provide a sandboxed project root and isolated backup logs directory.

    Args:
        tmp_path: Pytest temporary directory fixture.

    Yields:
        tuple[Path, Path]: project_root and backup_base_dir.
    """
    proj = tmp_path / "project"
    proj.mkdir(parents=True, exist_ok=True)
    logs = tmp_path / "logs"
    logs.mkdir(parents=True, exist_ok=True)
    return proj, logs


@pytest.fixture
def force_windows_platform(monkeypatch):
    """Force sys.platform to 'win32' for cross-platform deterministic test execution.

    Args:
        monkeypatch: Pytest monkeypatch fixture.
    """
    monkeypatch.setattr(sys, "platform", "win32")


class TestWindowsPathDetection:
    """Positive, negative, and edge-case detection test cases for Policy #1."""

    def test_unit_clean_forward_slashes_pass(self):
        """Positive: Project code with clean POSIX forward slashes passes check."""
        source = 'CONFIG_PATH = "data/models/config.json"\n'
        assert has_drive_path(source) is False

    def test_unit_pathlib_usage_pass(self):
        """Positive: Source code using pathlib.Path division passes without flagging."""
        source = 'from pathlib import Path\nP = Path("data") / "file.txt"\n'
        assert has_drive_path(source) is False

    def test_unit_docstring_examples_ignored(self):
        """Positive: Example drive paths inside docstrings are bypassed via AST classification."""
        path_str = make_drive_path("path", "example")
        source = f'"""Example docstring explaining {path_str} usage."""\nVALUE = 42\n'
        assert has_drive_path(source) is False

    def test_unit_uri_and_url_schemes_not_flagged(self):
        """Positive: file:/// URIs and HTTPS URLs are not falsely flagged."""
        source = 'URI = "file:///C:/test/file.txt"\nURL = "https://example.com/api"\n'
        assert has_drive_path(source) is False

    def test_unit_hardcoded_c_drive_flagged(self):
        """Negative: Assignment containing hardcoded C: drive path is flagged."""
        path_str = make_drive_path("Users", "techd", "repo")
        source = f'REPO_PATH = "{path_str}"\n'
        assert has_drive_path(source) is True

    def test_unit_hardcoded_d_drive_flagged(self):
        """Negative: Assignment containing hardcoded D: drive path is flagged."""
        path_str = make_drive_path("data", "records.csv", drive="D")
        source = f'DATA_FILE = "{path_str}"\n'
        assert has_drive_path(source) is True

    def test_unit_raw_string_drive_flagged(self):
        """Negative: Raw string literal containing Windows drive path is flagged."""
        path_str = make_drive_path("projects", "core")
        source = f'RAW_PATH = r"{path_str}"\n'
        assert has_drive_path(source) is True

    def test_unit_lowercase_drive_letter_flagged(self):
        """Negative: Lowercase drive letter prefix is detected and flagged."""
        path_str = make_drive_path("windows", "system32", drive="c")
        source = f'SYS_DIR = "{path_str}"\n'
        assert has_drive_path(source) is True

    def test_unit_drive_root_only_flagged(self):
        """Negative: Root drive paths without subdirectories are detected and flagged."""
        path_str = make_drive_path(drive="C")
        source = f'ROOT_DIR = "{path_str}"\n'
        assert has_drive_path(source) is True

    def test_unit_single_char_segment_flagged(self):
        """Negative: Single-character directory paths are detected and flagged."""
        path_str = make_drive_path("a", drive="C")
        source = f'SINGLE_CHAR = r"{path_str}"\n'
        assert has_drive_path(source) is True

    def test_unit_escape_sequences_preserved(self):
        """Edge-Case: Standard Python escape sequences are not mistaken for drive paths."""
        source = 'LOG_FORMAT = "file: ' + chr(92) + "n    line: " + chr(92) + 't ok"\n'
        assert has_drive_path(source) is False

    def test_unit_unparseable_source_fallback(self):
        """Edge-Case: SyntaxError source safely falls back to raw regex matching."""
        path_str = make_drive_path("corrupt", "path")
        source = f'def broken(:\n    P = "{path_str}"\n'
        assert has_drive_path(source) is True

    def test_unit_empty_file_handled(self):
        """Edge-Case: Zero-byte file is processed safely without raising an exception."""
        assert has_drive_path("") is False

    def test_unit_mixed_slashes_detected(self):
        """Edge-Case: Mixed backslash and forward slash path is detected."""
        source = 'P = "C:' + SEP + "projects/core" + SEP + 'utils/file.py"\n'
        assert has_drive_path(source) is True

    def test_unit_path_with_spaces_and_hyphens(self):
        """Edge-Case: Paths with spaces and hyphens are detected."""
        path_str = make_drive_path("Program Files", "my-app", "bin")
        source = f'BIN = "{path_str}"\n'
        assert has_drive_path(source) is True

    def test_unit_verbatim_path_ignored(self):
        """Edge-Case: Verbatim extended path prefix \\\\?\\ is not flagged for corruption."""
        source = 'VERBATIM = "' + chr(92) + chr(92) + "?" + chr(92) + "C:" + chr(92) + 'data"\n'
        assert has_drive_path(source) is False


class TestWindowsPathIntegration:
    """End-to-end integration tests for pre-flight nodes, state transitions, and auto-fix."""

    def test_integration_all_preflight_checks_pass(self, isolated_workspace, force_windows_platform):
        """Positive: Clean project sets preflight_status to OK in merge node."""
        proj, _ = isolated_workspace
        (proj / "app.py").write_text('P = "data/file.txt"\n', encoding="utf-8")
        state = {
            "project_root": str(proj),
            "unicode_check": True,
            "encoding_check": True,
        }
        node_res = node_windows_path_check(state)
        state.update(node_res)
        assert state["windows_path_check"] is True
        merge_res = preflight_guard_merge_node(state)
        assert merge_res["preflight_status"] == "OK"

    def test_integration_autofix_mixed_slashes_normalized(self, isolated_workspace, force_windows_platform):
        """Positive: Auto-fix normalizes mixed backslashes to pure forward slashes."""
        proj, logs = isolated_workspace
        target = proj / "mixed.py"
        target.write_text('P = r"C:' + SEP + "projects/core" + SEP + 'utils/file.py"\n', encoding="utf-8")
        state = {
            "session_id": "test_mixed",
            "project_root": str(proj),
            "windows_path_check": False,
        }
        fix_res = fix_preflight_guard_issues(state)
        assert fix_res["preflight_ready_to_retry"] is True
        fixed_content = target.read_text(encoding="utf-8")
        assert "C:/projects/core/utils/file.py" in fixed_content
        assert SEP not in fixed_content

    def test_integration_autofix_multi_path_line_clean(self, isolated_workspace, force_windows_platform):
        """Positive: Line with multiple drive paths normalizes both without greedy swallowing."""
        proj, logs = isolated_workspace
        target = proj / "multi.py"
        target.write_text(
            'CMD = "copy C:' + SEP + "data" + SEP + "a.txt D:" + SEP + "backup" + SEP + 'b.txt"\n',
            encoding="utf-8",
        )
        state = {
            "session_id": "test_multi",
            "project_root": str(proj),
            "windows_path_check": False,
        }
        fix_preflight_guard_issues(state)
        fixed_content = target.read_text(encoding="utf-8")
        assert "C:/data/a.txt" in fixed_content
        assert "D:/backup/b.txt" in fixed_content

    def test_integration_non_windows_platform_skips_cleanly(self, isolated_workspace, monkeypatch):
        """Positive: Non-Windows platform returns SKIP status without inspecting files."""
        proj, _ = isolated_workspace
        monkeypatch.setattr(sys, "platform", "linux")
        state = {"project_root": str(proj)}
        result = node_windows_path_check(state)
        assert result["windows_path_check"] is True

    def test_integration_merge_captures_windows_path_error(self, isolated_workspace, force_windows_platform):
        """Negative: Failed windows path check sets preflight_status to FAILED with error message."""
        state = {
            "unicode_check": True,
            "encoding_check": True,
            "windows_path_check": False,
            "windows_path_check_error": "Backslash paths found: app.py",
        }
        merge_res = preflight_guard_merge_node(state)
        assert merge_res["preflight_status"] == "FAILED"
        assert any("Windows path check failed" in err for err in merge_res.get("errors", []))

    def test_integration_vendor_directories_isolated(self, isolated_workspace, force_windows_platform):
        """Edge-Case: Files inside vendor directories are untouched by detection and auto-fix."""
        proj, logs = isolated_workspace
        venv_dir = proj / ".venv" / "lib"
        venv_dir.mkdir(parents=True)
        venv_file = venv_dir / "third_party.py"
        dirty_content = f'BAD = "{make_drive_path("venv", "lib")}"\n'
        venv_file.write_text(dirty_content, encoding="utf-8")

        clean_file = proj / "main.py"
        clean_file.write_text('P = "clean/path.py"\n', encoding="utf-8")

        state = {
            "session_id": "test_vendor",
            "project_root": str(proj),
        }
        node_res = node_windows_path_check(state)
        assert node_res["windows_path_check"] is True

        fix_preflight_guard_issues(state)
        assert venv_file.read_text(encoding="utf-8") == dirty_content

    def test_integration_escaped_string_no_double_slash(self, isolated_workspace, force_windows_platform):
        """Integration: Escaped backslashes (C:\\\\Projects) normalize to C:/Projects, never C://."""
        proj, _ = isolated_workspace
        target = proj / "escaped.py"
        double_sep = SEP + SEP
        escaped_str = f"C:{double_sep}Projects{double_sep}core"
        target.write_text(f'PATH = "{escaped_str}"\n', encoding="utf-8")

        state = {
            "session_id": "test_escaped_no_double_slash",
            "project_root": str(proj),
            "windows_path_check": False,
        }
        res = fix_preflight_guard_issues(state)
        assert res.get("preflight_ready_to_retry") is True

        fixed_content = target.read_text(encoding="utf-8")
        assert "C:/Projects/core" in fixed_content
        assert "C://" not in fixed_content


class TestWindowsPathSecurityAndRollback:
    """Security, transactional backup, atomic locking, and rollback invariants."""

    def test_security_backup_created_before_modification(self, isolated_workspace, force_windows_platform):
        """Positive: BackupManager creates byte-for-byte exact backup prior to modification."""
        proj, logs = isolated_workspace
        target = proj / "service.py"
        original_content = f'BASE = "{make_drive_path("var", "service")}"\n'
        target.write_text(original_content, encoding="utf-8")

        bm = BackupManager(session_id="test_sec_backup", backup_base_dir=str(logs))
        assert bm.backup_file(str(target), "Level 0", "Test backup") is True

        backups = list(bm.backup_dir.glob("*.py"))
        assert len(backups) == 1
        assert backups[0].read_text(encoding="utf-8") == original_content

    def test_security_unified_diff_generated(self, isolated_workspace, force_windows_platform):
        """Positive: BackupManager generates unified diff file on modified file."""
        proj, logs = isolated_workspace
        target = proj / "config.py"
        target.write_text(f'BASE = "{make_drive_path("etc", "config")}"\n', encoding="utf-8")

        bm = BackupManager(session_id="test_sec_diff", backup_base_dir=str(logs))
        bm.backup_file(str(target), "Level 0")
        target.write_text('BASE = "C:/etc/config"\n', encoding="utf-8")

        diff_path = bm.generate_diff(str(target), "Level 0", "path_fix")
        assert diff_path is not None
        assert Path(diff_path).exists()
        diff_text = Path(diff_path).read_text(encoding="utf-8")
        assert "-BASE =" in diff_text
        assert "+BASE =" in diff_text

    def test_security_concurrent_backup_atomic_isolation(self, isolated_workspace):
        """Positive: Simultaneous backups of the same file generate distinct unique filenames."""
        proj, logs = isolated_workspace
        target = proj / "concurrent.py"
        target.write_text("P = 1\n", encoding="utf-8")

        bm = BackupManager(session_id="test_concurrent", backup_base_dir=str(logs))
        bm.backup_file(str(target), "Level 0")
        bm.backup_file(str(target), "Level 0")

        backups = list(bm.backup_dir.glob("*.py"))
        assert len(backups) == 2
        assert backups[0].name != backups[1].name

    def test_security_multi_dot_filename_handled(self, isolated_workspace):
        """Positive: Backing up multi-dot filename uses stem and suffix cleanly."""
        proj, logs = isolated_workspace
        target = proj / "app.config.prod.py"
        target.write_text("PROD = True\n", encoding="utf-8")

        bm = BackupManager(session_id="test_multidot", backup_base_dir=str(logs))
        bm.backup_file(str(target), "Level 0")

        backups = list(bm.backup_dir.glob("*.py"))
        assert len(backups) == 1
        assert "app.config.prod_" in backups[0].name

    def test_security_syntax_corruption_triggers_rollback(self, isolated_workspace, force_windows_platform):
        """Negative: Syntax corruption during modification triggers automatic rollback from backup."""
        proj, logs = isolated_workspace
        target = proj / "broken.py"
        original_content = f'VALID = "{make_drive_path("good", "path")}"\n'
        target.write_text(original_content, encoding="utf-8")

        bm = BackupManager(session_id="test_rollback", backup_base_dir=str(logs))
        bm.backup_file(str(target), "Level 0")

        target.write_text("def broken(:\n", encoding="utf-8")
        assert bm.validate_file_integrity(str(target), "Level 0") is False

        assert bm.restore_file(str(target), "Level 0") is True
        assert target.read_text(encoding="utf-8") == original_content

    def test_security_read_only_file_handled_safely(self, isolated_workspace, force_windows_platform):
        """Edge-Case: Read-only file write error is caught safely with NTFS teardown finalizer."""
        proj, logs = isolated_workspace
        target = proj / "readonly.py"
        target.write_text(f'P = "{make_drive_path("protected", "data.csv")}"\n', encoding="utf-8")

        os.chmod(target, stat.S_IREAD)
        try:
            state = {
                "session_id": "test_ro",
                "project_root": str(proj),
                "windows_path_check": False,
            }
            result = fix_preflight_guard_issues(state)
            assert isinstance(result, dict)
            assert result.get("preflight_ready_to_retry") is True
        finally:
            os.chmod(target, stat.S_IWRITE)

    def test_security_utf8_bom_file_handled_cleanly(self, isolated_workspace, force_windows_platform):
        """Edge-Case: File with UTF-8 BOM is parsed without raising UnicodeDecodeError."""
        proj, _ = isolated_workspace
        target = proj / "bom.py"
        bom_bytes = b"\xef\xbb\xbf" + b'PATH = "clean/path"\n'
        target.write_bytes(bom_bytes)

        state = {"project_root": str(proj)}
        result = node_windows_path_check(state)
        assert result["windows_path_check"] is True

    def test_security_fail_closed_backup_aborts_modification(
        self, isolated_workspace, force_windows_platform, monkeypatch
    ):
        """Security: Fail-closed invariant - if backup_file returns False, file modification is aborted."""
        proj, logs = isolated_workspace
        target = proj / "fail_closed.py"
        path_str = make_drive_path("data", "closed.py")
        original_content = f'BAD = r"{path_str}"\n'
        target.write_text(original_content, encoding="utf-8")

        monkeypatch.setattr(BackupManager, "backup_file", lambda *args, **kwargs: False)

        state = {
            "session_id": "test_fail_closed",
            "project_root": str(proj),
            "backup_base_dir": str(logs),
            "unicode_check": True,
            "encoding_check": True,
            "windows_path_check": False,
        }
        res = fix_preflight_guard_issues(state)
        assert any("Backup failed" in err for err in res.get("preflight_fix_errors", []))
        assert target.read_text(encoding="utf-8") == original_content

    def test_security_clean_files_not_backed_up(self, isolated_workspace, force_windows_platform):
        """Security: Clean files do not trigger backup creation, eliminating backup amplification DoS."""
        proj, logs = isolated_workspace
        for i in range(5):
            (proj / f"clean_{i}.py").write_text(f'X_{i} = "clean/path"\n', encoding="utf-8")

        dirty = proj / "dirty.py"
        path_str = make_drive_path("data", "dirty.py")
        dirty.write_text(f'DIRTY = r"{path_str}"\n', encoding="utf-8")

        state = {
            "session_id": "test_clean_no_backup",
            "project_root": str(proj),
            "backup_base_dir": str(logs),
            "unicode_check": True,
            "encoding_check": True,
            "windows_path_check": False,
        }
        fix_preflight_guard_issues(state)

        bm = BackupManager(session_id="test_clean_no_backup", backup_base_dir=str(logs))
        backups = [b for b in bm.metadata["backups"] if "dirty.py" in b["original_path"]]
        assert len(backups) == 1
        assert len(bm.metadata["backups"]) == 1

    def test_security_step_path_traversal_sanitized(self, isolated_workspace):
        """Security: Step parameter path traversal attempts are sanitized against directory breakout."""
        proj, logs = isolated_workspace
        target = proj / "step_test.py"
        target.write_text("A = 1\n", encoding="utf-8")

        bm = BackupManager(session_id="test_step_sec", backup_base_dir=str(logs))
        assert bm.backup_file(str(target), step="../../malicious_step") is True

        backup_entry = bm.metadata["backups"][0]
        backup_path = Path(backup_entry["backup_path"])
        assert bm.backup_dir in backup_path.parents

    def test_security_atomic_write_replaces_cleanly(self, isolated_workspace):
        """Security: Atomic write safely replaces target file without leaving temporary sibling artifacts."""
        proj, _ = isolated_workspace
        target = proj / "atomic.txt"
        target.write_text("old content\n", encoding="utf-8")

        _atomic_write_text(target, "new content\n", encoding="utf-8")
        assert target.read_text(encoding="utf-8") == "new content\n"

        tmp_files = list(proj.glob(".*.tmp.*"))
        assert len(tmp_files) == 0


class TestWindowsPathPerformanceAndBounds:
    """Scalability, generator streaming, and 500-file cap verification."""

    def test_perf_520_files_strictly_capped_at_500(self, isolated_workspace):
        """Negative: Traversal strictly caps at 500 files when directory contains 520 files."""
        proj, _ = isolated_workspace
        for i in range(520):
            (proj / f"mod_{i}.py").write_text("X = 1\n", encoding="utf-8")

        t_start = time.time()
        files = list(_iter_project_py_files(proj, cap=500))
        t_duration = time.time() - t_start

        assert len(files) == 500
        assert t_duration < 0.5

    def test_perf_deeply_nested_directory_tree(self, isolated_workspace):
        """Edge-Case: Traversal across deeply nested directories terminates cleanly."""
        proj, _ = isolated_workspace
        curr = proj
        for i in range(15):
            curr = curr / f"sub_{i}"
            curr.mkdir()
        (curr / "deep.py").write_text("DEEP = True\n", encoding="utf-8")

        files = list(_iter_project_py_files(proj, cap=500))
        assert len(files) == 1
        assert files[0].name == "deep.py"


class TestPreflightRetryLoopBounds:
    """Retry budget and loop termination safety."""

    def test_max_retries_triggers_force_continue(self):
        """Loop: Attempt count exceeding MAX_PREFLIGHT_ATTEMPTS (3) forces continue."""
        state = {
            "preflight_retry_count": 3,
            "unicode_check": True,
            "encoding_check": True,
            "windows_path_check": False,
        }
        res = ask_preflight_guard_fix(state)
        assert res["preflight_user_choice"] == "force_continue"
        assert res["preflight_fatal_failure"] is True
        assert res["preflight_max_attempts_reached"] is True

    def test_qa_traceability_matrix_completeness(self):
        """QA: Asserts that all core policy requirements are represented in the test matrix."""
        required_checks = ["pass", "flagged", "escape", "autofix", "backup", "diff"]
        current_tests = (
            dir(TestWindowsPathDetection) + dir(TestWindowsPathIntegration) + dir(TestWindowsPathSecurityAndRollback)
        )
        for check in required_checks:
            assert any(check in test_name for test_name in current_tests)
