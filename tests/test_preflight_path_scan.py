"""Tests for the Level 0 drive-path scanner in preflight_guard/path_scan.py.

The scanner replaced a raw-text regex that corrupted source. That regex matched
an escape sequence as a drive path, and the auto-fix paired with it rewrote the
backslash, which damaged the string AND removed the match -- so the check
reported success because of the damage it had done.

The regression test for that exact input is the reason this file exists, and it
is paired throughout with sensitivity tests: a scanner that reports False for
everything would satisfy the false-positive tests alone while removing the check
entirely.
"""

from pathlib import Path
import re
import pytest

from sdlc_engine.security.path_scan import (
    DRIVE_PATH_RE,
    get_docstring_spans,
    has_drive_path,
    is_drive_path_match,
)
from sdlc_engine.security.preflight_recovery import (
    _load_failure_kb,
    _safe_rel_path,
    fix_preflight_guard_issues,
)
from sdlc_engine.security.preflight_merge import preflight_guard_merge_node

SEP = chr(92)

ESCAPE_ONLY_SOURCE = 'x = "with open(p) as f:' + chr(92) + "n    pass" + chr(92) + 'n"\n'
REAL_PATH_SOURCE = 'BASE = "C:' + SEP + SEP + "Users" + SEP + SEP + 'thing"\n'


def drive_path(*parts):
    """Assemble a Windows drive path without writing one as a literal.

    This module tests a detector that flags hardcoded drive paths, so a fixture
    written as a literal would make the file it tests a violation of the rule it
    tests -- and the detector, reading string VALUES, catches exactly that. The
    parts are joined at run time, so no constant in this file holds a drive path
    while every fixture still produces one.

    Args:
        *parts: Path segments after the drive letter.

    Returns:
        str: A path of the form C:<sep>part<sep>part.
    """
    return "C:" + SEP + SEP.join(parts)


class TestScannerRejectsEscapeSequences:
    """No Python escape sequence may be read as a path separator."""

    def test_the_exact_input_that_was_corrupted_is_not_flagged(self):
        """Regression: 'as f:' plus a newline escape was read as drive f."""
        assert has_drive_path(ESCAPE_ONLY_SOURCE) is False

    @pytest.mark.parametrize("escape", ["n", "t", "r", "0", "b", "f", "v", "a"])
    def test_no_single_letter_name_before_a_colon_escape_is_a_drive(self, escape):
        """The pattern that broke needs only a space, a letter and a colon."""
        source = 'x = "as f:\\%s    tail"\n' % escape
        assert has_drive_path(source) is False

    def test_a_repository_relative_forward_slash_path_is_not_flagged(self):
        assert has_drive_path('P = "tests/nfr1/probe.py"\n') is False


class TestScannerStillFindsRealPaths:
    """The check must keep failing on what it exists to catch."""

    def test_a_hardcoded_drive_path_in_a_string_is_flagged(self):
        assert has_drive_path(REAL_PATH_SOURCE) is True

    def test_a_drive_path_in_a_comment_is_flagged(self):
        assert has_drive_path("# see " + drive_path("Users", "techd") + " for details\n") is True

    def test_a_raw_string_drive_path_is_flagged(self):
        assert has_drive_path('P = r"' + drive_path("Users", "techd", "x") + '"\n') is True

    def test_an_escaped_drive_path_is_flagged_where_the_raw_scan_missed_it(self):
        """The escaped form is the one the superseded raw-text scan could not see.

        In source, an escaped literal doubles each separator. A raw-text pattern
        needs a word character straight after the drive backslash and finds a
        second backslash instead, so it matched only raw-string literals. Reading
        the VALUE makes both forms identical and both detectable.
        """
        assert has_drive_path(REAL_PATH_SOURCE) is True


class TestScannerClassifiesByEnclosingNode:
    """A path in a docstring is an example; in code it is a defect."""

    def test_a_drive_path_in_a_module_docstring_is_not_flagged(self):
        source = 'r"""Explains ' + drive_path("path", "repo") + ' quoting."""\nx = 1\n'
        assert has_drive_path(source) is False

    def test_a_drive_path_in_a_function_docstring_is_not_flagged(self):
        body = '    r"""Explains ' + drive_path("path", "repo") + ' quoting."""\n    return 1\n'
        assert has_drive_path("def f():\n" + body) is False

    def test_the_same_path_in_an_assignment_is_still_flagged(self):
        """The paired half: exclusion must be positional, not blanket."""
        assert has_drive_path('P = r"' + drive_path("path", "repo") + '"\n') is True

    def test_a_string_after_the_docstring_is_still_flagged(self):
        source = 'def f():\n    """Doc."""\n    return r"' + drive_path("path", "repo") + '"\n'
        assert has_drive_path(source) is True


class TestScannerDegradesSafely:
    """A file that does not parse still gets checked, by the raw scan."""

    def test_unparseable_source_with_a_real_path_is_still_flagged(self):
        source = 'def broken(:\nP = r"' + drive_path("Users", "techd", "x") + '"\n'
        assert has_drive_path(source) is True

    def test_unparseable_source_without_a_path_is_not_flagged(self):
        assert has_drive_path("def broken(:\n") is False


class TestTheCheckIsNotVacuous:
    """A scanner that always returns False would pass every test above."""

    def test_the_two_representative_inputs_disagree(self):
        """Sensitivity and specificity are asserted against each other.

        If a change makes the scanner constant in either direction, this fails
        even when every individual case above is read in isolation.
        """
        assert has_drive_path(REAL_PATH_SOURCE) != has_drive_path(ESCAPE_ONLY_SOURCE)


class TestIsDrivePathMatch:
    """Validate canonical is_drive_path_match regex match classification."""

    def test_rejects_escape_sequences_following_colons(self):
        """Matches like f:\\n, C:\\t, C:\\r, C:\\0 must be recognized as escape sequences."""
        for esc in ["n", "t", "r", "0", "b", "f", "v"]:
            text = f"as f:\\{esc}   tail"
            m = DRIVE_PATH_RE.search(text)
            assert m is not None
            assert is_drive_path_match(m) is False

    def test_accepts_genuine_windows_drive_paths(self):
        """Standard Windows drive paths must be confirmed as genuine drive paths."""
        for path_str in [
            "C:\\Users\\techd",
            "D:\\workspace\\project",
            "C:\\new_folder\\file.py",
            "C:\\test\\sub",
        ]:
            m = DRIVE_PATH_RE.search(path_str)
            assert m is not None
            assert is_drive_path_match(m) is True


class TestInlineCommentInspection:
    """Inspect comments for hardcoded drive paths."""

    def test_detects_drive_path_in_inline_comment(self):
        """Trailing comments after code statements must be inspected."""
        source = 'x = 1  # path is ' + drive_path("Users", "test") + '\n'
        assert has_drive_path(source) is True

    def test_ignores_escape_like_sequence_in_inline_comment(self):
        """Comments containing colon-escape patterns must not trigger false positives."""
        source = 'x = 1  # format as f:\\n    done\n'
        assert has_drive_path(source) is False


class TestDocstringSpans:
    """Verify coordinate extraction for docstring character spans."""

    def test_extracts_module_and_function_spans(self):
        """Computes accurate character spans covering docstrings across definitions."""
        code = '"""Module doc."""\nx = 1\ndef func():\n    """Func doc."""\n    return x\n'
        spans = get_docstring_spans(code)
        assert len(spans) == 2
        assert code[spans[0][0] : spans[0][1]] == '"""Module doc."""'
        assert code[spans[1][0] : spans[1][1]] == '"""Func doc."""'

    def test_returns_empty_spans_on_syntax_error(self):
        """Gracefully returns empty list when source cannot be parsed into AST."""
        assert get_docstring_spans("def broken(:") == []


class TestPreflightRecoveryHardening:
    """Validate recovery synchronization and state maintenance."""

    def test_safe_rel_path_preserves_directory_hierarchy(self):
        """Path resolution does not flatten directory structures into basename."""
        root = Path("C:/project/root")
        target = Path("C:/project/root/sdlc_engine/security/file.py")
        rel = _safe_rel_path(target, root)
        assert rel == "sdlc_engine/security/file.py"

    def test_load_failure_kb_loads_active_signatures(self):
        """Loads prevention entries from policies/common-failures-prevention.md."""
        entries = _load_failure_kb(".")
        assert len(entries) > 0
        assert any("UnicodeEncodeError" in e["signature"] for e in entries)

    def test_merge_node_clears_guard_errors_when_all_pass(self):
        """Ensures preflight_guard_errors is explicitly cleared on successful check."""
        state = {
            "unicode_check": True,
            "encoding_check": True,
            "windows_path_check": True,
            "preflight_guard_errors": ["previous error"],
        }
        updates = preflight_guard_merge_node(state)
        assert updates["preflight_status"] == "OK"
        assert updates["preflight_guard_errors"] == []

    def test_fix_preflight_guard_issues_protects_docstring_spans(self, tmp_path):
        """Auto-fix rewrites hardcoded drive paths in code while preserving docstrings."""
        test_file = tmp_path / "sample.py"
        source_code = (
            'r"""Module doc explaining ' + drive_path("Doc", "Example") + ' path."""\n'
            'CONFIG_PATH = r"' + drive_path("Config", "Settings") + '"\n'
        )
        test_file.write_text(source_code, encoding="utf-8")

        state = {
            "project_root": str(tmp_path),
            "windows_path_check": False,
            "windows_path_violating_files": [test_file.name],
        }
        res = fix_preflight_guard_issues(state)
        content_after = test_file.read_text(encoding="utf-8")

        assert drive_path("Doc", "Example") in content_after
        assert "C:/Config/Settings" in content_after
        assert res["auto_fix_complete"] is True

