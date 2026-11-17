"""Comprehensive triad test suite for preflight recovery and guard hardening.

Verifies:
1. Standalone execution without session_id (fallback compile validation):
   - Positive: Valid file with path violation gets auto-fixed and validated with compile() when session_id=None.
   - Negative: Modification resulting in invalid syntax is rejected fail-closed and rolled back to original content.
   - Edge case: Multiple violating files without session_id handled with per-file atomic rollback.
2. State lifecycle transitions:
   - Positive: preflight_guard_errors cleared to [] when preflight_status == "OK" in preflight_guard_merge_node.
   - Positive: windows_path_check_error cleared to None and windows_path_violating_files to [] when clean.
   - Positive/Edge: Non-Windows platform skip cleanly initializes all expected state keys.
   - Negative: preflight_guard_merge_node captures only freshly generated errors on failure.
3. Failure Prevention KB loading:
   - Positive: _load_failure_kb successfully loads entries from policies/common-failures-prevention.md.
   - Negative: Missing KB file fails open and safely returns an empty list.
   - Edge case: Empty or header-only markdown KB file safely returns an empty list.
4. Vendor directory pruning:
   - Positive: _iter_project_py_files discovers project Python files in allowed subtrees.
   - Negative: _iter_project_py_files strictly prunes sessions/, .sdlc/, .claude/, .gemini/, node_modules/, .venv/.
   - Edge case: _iter_project_py_files respects the cap parameter and stops traversal immediately.
5. Docstring preservation during auto-fix:
   - Positive: File with docstring containing drive path example and code containing drive path literal rewrites code while preserving docstring byte-identical.
   - Negative: File containing drive paths exclusively inside docstrings remains unmodified.
   - Edge case: Multiline raw docstrings with mixed escapes and backslashes preserved alongside inline code replacements.
"""

from pathlib import Path
import sys
import pytest

from sdlc_engine.security.preflight_merge import preflight_guard_merge_node
from sdlc_engine.security.preflight_nodes import (
    _iter_project_py_files,
    node_unicode_fix,
    node_windows_path_check,
)
from sdlc_engine.security.preflight_recovery import (
    _load_failure_kb,
    fix_preflight_guard_issues,
)

SEP = chr(92)


def drive_path(*parts: str) -> str:
    """Assemble a Windows drive path at runtime without literal string detection.

    Args:
        *parts: Path segments following the drive letter.

    Returns:
        str: Windows drive path formatted as C:<sep>segment...
    """
    return "C:" + SEP + SEP.join(parts)


def drive_code_literal(variable_name: str, *parts: str) -> str:
    """Format an escaped Python assignment statement holding a Windows drive path.

    Args:
        variable_name: Python identifier to assign.
        *parts: Path segments following the drive letter.

    Returns:
        str: Assignment source line such as VAR = "C:\\\\part\\\\part"\\n.
    """
    escaped_sep = SEP + SEP
    return f'{variable_name} = "C:{escaped_sep}{escaped_sep.join(parts)}"\n'


class TestStandaloneExecutionValidation:
    """Verification for auto-fix execution without session_id or backup manager."""

    def test_standalone_valid_file_path_violation_auto_fixed_and_compiled_without_session(
        self, tmp_path: Path
    ) -> None:
        """Verify that a valid file with path violations is fixed and verified with compile() when session_id is None."""
        target_file = tmp_path / "valid_module.py"
        target_file.write_text(
            drive_code_literal("CONFIG_PATH", "engine", "config.json"),
            encoding="utf-8",
        )

        state = {
            "session_id": None,
            "project_root": str(tmp_path),
            "unicode_check": True,
            "encoding_check": True,
            "windows_path_check": False,
            "windows_path_violating_files": [str(target_file)],
        }

        result = fix_preflight_guard_issues(state)

        assert result["auto_fix_complete"] is True
        assert len(result["preflight_fix_errors"]) == 0
        new_content = target_file.read_text(encoding="utf-8")
        assert "C:/engine/config.json" in new_content
        assert (SEP + SEP) not in new_content
        compile(new_content, str(target_file), "exec")

    def test_standalone_syntax_error_triggers_fail_closed_rollback_without_session(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Verify that a post-fix syntax failure is rejected fail-closed and rolled back to original content."""
        target_file = tmp_path / "syntax_fail_module.py"
        original_content = drive_code_literal("DATA_PATH", "data", "records.csv")
        target_file.write_text(original_content, encoding="utf-8")

        real_compile = compile

        def fail_compile(source, filename, mode, *args, **kwargs):
            if filename == str(target_file):
                raise SyntaxError("Simulated syntax error during standalone validation")
            return real_compile(source, filename, mode, *args, **kwargs)

        monkeypatch.setattr("builtins.compile", fail_compile)

        state = {
            "session_id": None,
            "project_root": str(tmp_path),
            "unicode_check": True,
            "encoding_check": True,
            "windows_path_check": False,
            "windows_path_violating_files": [str(target_file)],
        }

        result = fix_preflight_guard_issues(state)

        assert result["auto_fix_complete"] is False
        assert any(
            f"Validation failed for {target_file.name}, file restored" in err
            for err in result["preflight_fix_errors"]
        )
        assert target_file.read_text(encoding="utf-8") == original_content

    def test_standalone_multiple_violating_files_handled_independently(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Verify that an error in one file triggers isolated rollback without corrupting companion files."""
        file_good = tmp_path / "module_good.py"
        file_bad = tmp_path / "module_bad.py"

        file_good.write_text(drive_code_literal("GOOD_PATH", "app", "good.txt"), encoding="utf-8")
        bad_original = drive_code_literal("BAD_PATH", "app", "bad.txt")
        file_bad.write_text(bad_original, encoding="utf-8")

        real_compile = compile

        def selective_compile(source, filename, mode, *args, **kwargs):
            if filename == str(file_bad):
                raise SyntaxError("Selective failure for bad file")
            return real_compile(source, filename, mode, *args, **kwargs)

        monkeypatch.setattr("builtins.compile", selective_compile)

        state = {
            "session_id": None,
            "project_root": str(tmp_path),
            "unicode_check": True,
            "encoding_check": True,
            "windows_path_check": False,
            "windows_path_violating_files": [str(file_good), str(file_bad)],
        }

        result = fix_preflight_guard_issues(state)

        assert "C:/app/good.txt" in file_good.read_text(encoding="utf-8")
        assert file_bad.read_text(encoding="utf-8") == bad_original
        assert result["auto_fix_complete"] is False
        assert any(
            f"Validation failed for {file_bad.name}, file restored" in err
            for err in result["preflight_fix_errors"]
        )


class TestStateLifecycleTransitions:
    """Verification for Level 0 state lifecycle invariants and cleanup guarantees."""

    def test_preflight_guard_merge_clears_errors_on_ok_status(self) -> None:
        """Verify that preflight_guard_errors is cleared to [] when all checks report OK."""
        state = {
            "session_id": "test-session-state-1",
            "unicode_check": True,
            "encoding_check": True,
            "windows_path_check": True,
            "preflight_guard_errors": ["Previous unicode failure", "Previous path error"],
            "errors": ["Previous unicode failure", "Previous path error"],
        }

        updates = preflight_guard_merge_node(state)

        assert updates["preflight_status"] == "OK"
        assert updates["auto_fix_complete"] is True
        assert updates["preflight_guard_errors"] == []
        assert "errors" not in updates

    def test_preflight_guard_merge_accumulates_only_fresh_errors_on_failure(self) -> None:
        """Verify that preflight_guard_merge_node returns only newly discovered errors without repeating prior errors."""
        state = {
            "session_id": "test-session-state-2",
            "unicode_check": False,
            "unicode_check_error": "Stdout encoding is cp1252",
            "encoding_check": True,
            "windows_path_check": True,
            "preflight_guard_errors": ["Stale error from prior iteration"],
            "errors": ["Stale error from prior iteration"],
        }

        updates = preflight_guard_merge_node(state)

        assert updates["preflight_status"] == "FAILED"
        assert updates["auto_fix_complete"] is False
        assert updates["preflight_guard_errors"] == ["Unicode check failed: Stdout encoding is cp1252"]
        assert updates["errors"] == ["Unicode check failed: Stdout encoding is cp1252"]

    def test_node_windows_path_check_clears_violating_state_when_clean(self, tmp_path: Path) -> None:
        """Verify that clean scan results reset windows_path_check_error to None and violating files to []."""
        clean_file = tmp_path / "clean_module.py"
        clean_file.write_text('APP_ROOT = "app/resources/clean"\n', encoding="utf-8")

        state = {
            "session_id": "test-session-clean",
            "project_root": str(tmp_path),
            "windows_path_check": False,
            "windows_path_check_error": "Prior path defect",
            "windows_path_violating_files": ["prior_module.py"],
        }

        updates = node_windows_path_check(state)

        assert updates["windows_path_check"] is True
        assert updates["windows_path_check_error"] is None
        assert updates["windows_path_violating_files"] == []

    def test_non_windows_platform_skip_cleanly_initializes_all_keys(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Verify that non-Windows environments cleanly initialize all guard state keys to valid pass states."""
        monkeypatch.setattr(sys, "platform", "linux")

        state = {
            "session_id": "test-session-linux",
            "project_root": str(tmp_path),
            "windows_path_check": False,
            "windows_path_check_error": "Prior failure",
            "windows_path_violating_files": ["bad.py"],
            "unicode_check": False,
            "unicode_check_error": "Prior failure",
        }

        path_updates = node_windows_path_check(state)
        assert path_updates["windows_path_check"] is True
        assert path_updates["windows_path_check_error"] is None
        assert path_updates["windows_path_violating_files"] == []

        unicode_updates = node_unicode_fix(state)
        assert unicode_updates["unicode_check"] is True
        assert unicode_updates["unicode_check_error"] is None

    def test_missing_or_invalid_project_root_handled_gracefully(self) -> None:
        """Verify that non-existent project roots are skipped gracefully with clean state initialization."""
        state = {
            "session_id": "test-session-missing-root",
            "project_root": "C:/non/existent/path/for/sdlc/testing",
            "windows_path_check": False,
            "windows_path_check_error": "Stale error",
            "windows_path_violating_files": ["stale.py"],
        }

        updates = node_windows_path_check(state)

        assert updates["windows_path_check"] is True
        assert updates["windows_path_check_error"] is None
        assert updates["windows_path_violating_files"] == []


class TestFailurePreventionKBLoading:
    """Verification for Failure Prevention Knowledge Base loading and parsing."""

    def test_load_failure_kb_success_from_policy_file(self, tmp_path: Path) -> None:
        """Verify that _load_failure_kb parses signature and prevention strategy pairs from policy documentation."""
        kb_dir = tmp_path / "policies"
        kb_dir.mkdir(parents=True, exist_ok=True)
        kb_file = kb_dir / "common-failures-prevention.md"
        kb_file.write_text(
            "# Failure Prevention KB\n\n"
            "### Rule 1: Windows Path Violation\n"
            "**Signature:** Windows Backslash Paths in Code\n"
            "**Prevention Strategy:** Use forward slashes or pathlib.Path.as_posix()\n\n"
            "### Rule 2: Charset Encoding\n"
            "**Signature:** UnicodeEncodeError 'charmap' codec\n"
            "**Prevention Strategy:** Reconfigure sys.stdout and sys.stderr to utf-8\n",
            encoding="utf-8",
        )

        entries = _load_failure_kb(str(tmp_path))

        assert len(entries) == 2
        assert entries[0]["signature"] == "Windows Backslash Paths in Code"
        assert "forward slashes" in entries[0]["prevention"]
        assert entries[0]["category"] == "auto-fix"
        assert entries[1]["signature"] == "UnicodeEncodeError 'charmap' codec"
        assert "utf-8" in entries[1]["prevention"]

    def test_load_failure_kb_missing_file_returns_empty_list(self, tmp_path: Path) -> None:
        """Verify that _load_failure_kb fails open and returns an empty list when no policy file is found."""
        empty_root = tmp_path / "isolated_empty_project"
        empty_root.mkdir(parents=True, exist_ok=True)

        entries = _load_failure_kb(str(empty_root))

        assert isinstance(entries, list)
        assert len(entries) == 0

    def test_load_failure_kb_malformed_or_empty_file_returns_empty_list(self, tmp_path: Path) -> None:
        """Verify that empty or header-only markdown files safely produce an empty list without exceptions."""
        kb_dir = tmp_path / "policies"
        kb_dir.mkdir(parents=True, exist_ok=True)
        kb_file = kb_dir / "common-failures-prevention.md"
        kb_file.write_text("# Knowledge Base\nNo signatures defined here.\n", encoding="utf-8")

        entries = _load_failure_kb(str(tmp_path))

        assert isinstance(entries, list)
        assert len(entries) == 0


class TestVendorDirectoryPruning:
    """Verification for vendor directory pruning in project file iterators."""

    def test_iter_project_py_files_finds_project_source(self, tmp_path: Path) -> None:
        """Verify that project-owned Python files in source trees are yielded."""
        src_dir = tmp_path / "src" / "submodule"
        src_dir.mkdir(parents=True, exist_ok=True)
        main_file = src_dir / "main.py"
        main_file.write_text("x = 1\n", encoding="utf-8")

        discovered = list(_iter_project_py_files(tmp_path))

        assert main_file.resolve() in [p.resolve() for p in discovered]

    def test_iter_project_py_files_strictly_prunes_vendor_and_engine_directories(
        self, tmp_path: Path
    ) -> None:
        """Verify that vendor directories are pruned in-place and never descended into."""
        normal_file = tmp_path / "valid.py"
        normal_file.write_text("a = 1\n", encoding="utf-8")

        vendor_dirs = [
            tmp_path / "sessions",
            tmp_path / ".sdlc",
            tmp_path / ".claude",
            tmp_path / ".gemini",
            tmp_path / "node_modules",
            tmp_path / ".venv",
            tmp_path / "__pycache__",
        ]

        forbidden_files = []
        for v_dir in vendor_dirs:
            v_dir.mkdir(parents=True, exist_ok=True)
            f = v_dir / "nested_bad.py"
            f.write_text(drive_code_literal("P", "bad", "vendor.py"), encoding="utf-8")
            forbidden_files.append(f.resolve())

        discovered_paths = [p.resolve() for p in _iter_project_py_files(tmp_path)]

        assert normal_file.resolve() in discovered_paths
        for forbidden in forbidden_files:
            assert forbidden not in discovered_paths

    def test_iter_project_py_files_respects_cap_parameter(self, tmp_path: Path) -> None:
        """Verify that iteration terminates immediately once the specified cap is reached."""
        for i in range(10):
            f = tmp_path / f"test_cap_{i}.py"
            f.write_text(f"num = {i}\n", encoding="utf-8")

        discovered = list(_iter_project_py_files(tmp_path, cap=3))

        assert len(discovered) == 3


class TestDocstringPreservation:
    """Verification for docstring preservation during automated code path remediation."""

    def test_auto_fix_preserves_docstring_drive_paths_while_rewriting_code_paths(
        self, tmp_path: Path
    ) -> None:
        """Verify that drive paths in module and function docstrings remain untouched while code paths are converted."""
        target_file = tmp_path / "docstring_and_code.py"
        doc_part = drive_path("example", "docstring", "path")
        code_stmt = drive_code_literal("CONFIG_FILE", "system", "app.ini")

        source = (
            f'r"""Module documentation with {doc_part} reference."""\n\n'
            f"def configure():\n"
            f'    r"""Configure function with {doc_part} note."""\n'
            f"    {code_stmt}"
            f"    return CONFIG_FILE\n"
        )
        target_file.write_text(source, encoding="utf-8")

        state = {
            "session_id": None,
            "project_root": str(tmp_path),
            "unicode_check": True,
            "encoding_check": True,
            "windows_path_check": False,
            "windows_path_violating_files": [str(target_file)],
        }

        result = fix_preflight_guard_issues(state)

        assert result["auto_fix_complete"] is True
        remediated = target_file.read_text(encoding="utf-8")

        assert f'r"""Module documentation with {doc_part} reference."""' in remediated
        assert f'r"""Configure function with {doc_part} note."""' in remediated
        assert 'CONFIG_FILE = "C:/system/app.ini"' in remediated
        compile(remediated, str(target_file), "exec")

    def test_file_with_only_docstring_drive_paths_is_not_modified(self, tmp_path: Path) -> None:
        """Verify that a file containing drive paths solely inside docstrings is never modified."""
        target_file = tmp_path / "only_docstring.py"
        doc_part = drive_path("docs", "sample", "guide")
        source = (
            f'r"""Module documentation referencing {doc_part} example."""\n\n'
            f"def helper():\n"
            f'    r"""Helper method referencing {doc_part} inline."""\n'
            f"    return 42\n"
        )
        target_file.write_text(source, encoding="utf-8")

        state = {
            "session_id": None,
            "project_root": str(tmp_path),
            "unicode_check": True,
            "encoding_check": True,
            "windows_path_check": False,
            "windows_path_violating_files": [str(target_file)],
        }

        result = fix_preflight_guard_issues(state)

        assert result["auto_fix_complete"] is True
        assert target_file.read_text(encoding="utf-8") == source

    def test_multiline_docstring_with_mixed_escapes_preserved_exactly(self, tmp_path: Path) -> None:
        """Verify that multiline raw docstrings with special escape sequences remain byte-identical during code fix."""
        target_file = tmp_path / "multiline_docstring.py"
        doc_part = drive_path("demo", "docs", "test")
        code_stmt = drive_code_literal("LOG_PATH", "logs", "output.log")

        source = (
            f'r"""\n'
            f'Header section.\n'
            f'Windows path example: {doc_part}\n'
            f'Escape demonstration: \\n and \\t without real escapes.\n'
            f'"""\n\n'
            f"def execute():\n"
            f"    {code_stmt}"
            f"    return LOG_PATH\n"
        )
        target_file.write_text(source, encoding="utf-8")

        state = {
            "session_id": None,
            "project_root": str(tmp_path),
            "unicode_check": True,
            "encoding_check": True,
            "windows_path_check": False,
            "windows_path_violating_files": [str(target_file)],
        }

        result = fix_preflight_guard_issues(state)

        assert result["auto_fix_complete"] is True
        remediated = target_file.read_text(encoding="utf-8")
        assert 'Windows path example: ' + doc_part in remediated
        assert 'Escape demonstration: \\n and \\t without real escapes.' in remediated
        assert 'LOG_PATH = "C:/logs/output.log"' in remediated
        compile(remediated, str(target_file), "exec")
