"""Level 0 (Pre-Flight Sanity Guard) Auto-Fix recovery and interactive fix functions.

Extracted from subgraphs/preflight_guard.py for modularity.
Windows-safe: ASCII only, no Unicode characters.

Contains:
- _load_failure_kb: Load Failure Prevention KB from policy file
- ask_preflight_guard_fix: Interactive user prompt for fix decisions
- fix_preflight_guard_issues: Auto-fix Level 0 (Pre-Flight Sanity Guard) issues with backup & validation
"""

import logging
import os
import sys
import threading
import uuid
from pathlib import Path

from sdlc_engine.routing.flow_state import FlowState
from sdlc_engine.session.backup_manager import BackupManager
from sdlc_engine.shared.logging.error_logger import ErrorLogger

from .preflight_merge import MAX_PREFLIGHT_ATTEMPTS

_logger = logging.getLogger(__name__)


def _atomic_write_text(file_path: Path, content: str, encoding: str = "utf-8") -> None:
    """Atomically write text content using a temporary sibling file and atomic rename.

    Args:
        file_path: Target path to write to.
        content: String content to write.
        encoding: Text encoding to use.
    """
    token = f"{os.getpid()}_{threading.get_ident()}_{uuid.uuid4().hex[:8]}"
    tmp_file = file_path.with_name(f".{file_path.name}.tmp.{token}")
    try:
        tmp_file.write_text(content, encoding=encoding)
        os.replace(tmp_file, file_path)
    except Exception:
        if tmp_file.exists():
            try:
                tmp_file.unlink()
            except OSError:
                pass
        raise


def _safe_rel_path(file_path: Path, root: Path) -> str:
    """Safely return POSIX relative path string without flattening to filename.

    Attempts standard relative path resolution against root. If root resolution
    fails across different drive roots or disjoint paths, attempts unresolved
    relative computation before falling back to full POSIX path.

    Args:
        file_path: Target path to format.
        root: Root directory to make path relative to.

    Returns:
        str: POSIX formatted path relative to root, or full POSIX path on failure.
    """
    try:
        return file_path.resolve().relative_to(root.resolve()).as_posix()
    except (ValueError, RuntimeError):
        try:
            return file_path.relative_to(root).as_posix()
        except (ValueError, RuntimeError):
            return file_path.as_posix()


# ============================================================================
# FAILURE PREVENTION KB
# ============================================================================


def _load_failure_kb(project_root_str="."):
    """Load Failure Prevention KB from common-failures-prevention.md.

    Parses Signature -> Prevention Strategy pairs from the KB policy file.
    Returns list of dicts: [{signature, prevention, category}].

    Fail-open: returns empty list on any error.
    """
    try:
        import re

        candidate_paths = [
            Path(__file__).parent.parent
            / "sdlc_pipeline"
            / "policies"
            / "failure-prevention"
            / "common-failures-prevention.md",
            Path(project_root_str) / "policies" / "common-failures-prevention.md",
            Path(project_root_str)
            / "policies"
            / "03-execution-system"
            / "failure-prevention"
            / "common-failures-prevention.md",
        ]
        kb_path = None
        for p in candidate_paths:
            if p.is_file():
                kb_path = p
                break
        if not kb_path:
            return []

        content = kb_path.read_text(encoding="utf-8", errors="replace")

        entries = []
        sig_pattern = re.compile(
            r"(?:\*\*Signature[:\s]*\*\*|^\s*Signature[:\s]*)\s*\"?([^\n\r\"]+)\"?",
            re.MULTILINE | re.IGNORECASE,
        )
        prev_pattern = re.compile(
            r"(?:\*\*Prevention\s*(?:Strategy)?[:\s]*\*\*|^\s*Prevention\s*(?:Strategy)?[:\s]*)\s*(.+?)(?:\n|\r)",
            re.MULTILINE | re.IGNORECASE,
        )

        signatures = sig_pattern.findall(content)
        preventions = prev_pattern.findall(content)

        for i, sig in enumerate(signatures):
            prevention = preventions[i].strip() if i < len(preventions) else ""
            entries.append(
                {
                    "signature": sig.strip(),
                    "prevention": prevention,
                    "category": "auto-fix",
                }
            )

        return entries
    except Exception as exc:
        _logger.warning("[LEVEL 0 (PRE-FLIGHT SANITY GUARD) KB] Failed to load failure KB: %s", exc)
        return []


# ============================================================================
# INTERACTIVE RECOVERY NODES
# ============================================================================


def ask_preflight_guard_fix(state: FlowState) -> dict:
    """Ask user what to do when Level 0 (Pre-Flight Sanity Guard) checks fail.

    Shows specific PASS/FAIL for each check and offers:
    - "auto-fix": Attempt to fix issues, retry (max 3 times)
    - "skip": Continue anyway (not recommended)

    IMPORTANT: After 3 attempts, automatically continues to Level 1 with warnings,
    regardless of check status. This prevents infinite retry loops.

    IMPORTANT: When running in hook context (no stdin), automatically defaults
    to "auto-fix" for a seamless experience without hanging.

    Args:
        state: FlowState with failed checks

    Returns:
        Updated state with user choice and attempt tracking
    """
    attempt = state.get("preflight_retry_count", 0) + 1

    if attempt > MAX_PREFLIGHT_ATTEMPTS:
        session_id = state.get("session_id")
        log_base_dir = state.get("log_base_dir") or state.get("backup_base_dir")
        logger = ErrorLogger(session_id, log_base_dir=log_base_dir) if session_id else None

        _logger.error(
            "[LEVEL 0 (PRE-FLIGHT SANITY GUARD)] FATAL: MAX ATTEMPTS REACHED (%d/%d)",
            attempt,
            MAX_PREFLIGHT_ATTEMPTS,
        )
        _logger.warning(
            "[LEVEL 0 (PRE-FLIGHT SANITY GUARD)] Continuing to Level 1 despite unresolved checks..."
        )
        if sys.stdout.isatty():
            sys.stdout.write(
                f"\n[LEVEL 0 (PRE-FLIGHT SANITY GUARD)] [ERROR] FATAL: MAX ATTEMPTS REACHED ({attempt}/{MAX_PREFLIGHT_ATTEMPTS})\n"
            )
            sys.stdout.write(
                "[LEVEL 0 (PRE-FLIGHT SANITY GUARD)] Continuing to Level 1 despite unresolved checks...\n"
            )

        logger and logger.log_error(
            "Level 0 (Pre-Flight Sanity Guard)",
            f"Max {MAX_PREFLIGHT_ATTEMPTS} retry attempts exceeded",
            severity="CRITICAL",
            error_type="FatalError",
            recovery_action="Force continue to Level 1",
        )
        logger and logger.save_audit_trail()

        return {
            "preflight_user_choice": "force_continue",
            "preflight_retry_count": attempt,
            "preflight_max_attempts_reached": True,
            "preflight_fatal_failure": True,
            "auto_fix_complete": False,
        }

    failed_checks = []
    if not state.get("unicode_check"):
        failed_checks.append("  [FAIL] Unicode UTF-8 encoding: " + state.get("unicode_check_error", "Failed"))
    else:
        failed_checks.append("  [PASS] Unicode UTF-8 encoding: PASS")

    if not state.get("encoding_check"):
        failed_checks.append("  [FAIL] ASCII-only Python files: " + state.get("encoding_check_error", "Failed"))
    else:
        failed_checks.append("  [PASS] ASCII-only Python files: PASS")

    if not state.get("windows_path_check"):
        failed_checks.append("  [FAIL] Windows path handling: " + state.get("windows_path_check_error", "Failed"))
    else:
        failed_checks.append("  [PASS] Windows path handling: PASS")

    kb_suggestions = []
    kb_loaded = False
    try:
        project_root = state.get("project_root", ".")
        kb_entries = _load_failure_kb(project_root)
        kb_loaded = len(kb_entries) > 0
        if kb_entries:
            for check_msg in failed_checks:
                if "PASS" in check_msg:
                    continue
                for entry in kb_entries:
                    sig_words = entry["signature"].lower().split()
                    if any(w in check_msg.lower() for w in sig_words if len(w) > 3):
                        kb_suggestions.append(entry)
    except Exception as exc:
        _logger.debug("recovery: KB suggestion matching failed (fail-open): %s", exc)

    message = f"\n[LEVEL 0 (PRE-FLIGHT SANITY GUARD)] VALIDATION CHECKS ({attempt}/{MAX_PREFLIGHT_ATTEMPTS}):\n"
    message += "\n".join(failed_checks)

    if kb_suggestions:
        message += "\n\n  KB SUGGESTIONS:\n"
        seen = set()
        for kb in kb_suggestions:
            sig = kb.get("signature", "")
            if sig not in seen:
                seen.add(sig)
                message += "    -> %s: %s\n" % (sig, kb.get("prevention", ""))

    message += "\n\nOPTIONS:\n"
    message += "  1. auto-fix   -> Attempt repair + retry\n"
    message += "  2. skip       -> Continue anyway (NOT RECOMMENDED)\n"

    user_choice = "auto-fix"
    if sys.stdin.isatty() and sys.stdout.isatty():
        sys.stdout.write(message + "\n")
        try:
            user_choice = input("\nYour choice [auto-fix/skip]: ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            _logger.info("Terminal input interrupted, falling back to auto-fix")
            user_choice = "auto-fix"
        except Exception as e:
            _logger.warning("Could not read input from terminal (%s), falling back to auto-fix", e)
            user_choice = "auto-fix"
    else:
        _logger.info(
            "[LEVEL 0 (PRE-FLIGHT SANITY GUARD)] Running in non-interactive / hook context; auto-defaulting to auto-fix"
        )
        user_choice = "auto-fix"

    if user_choice not in ["auto-fix", "skip"]:
        user_choice = "auto-fix"

    return {
        "preflight_user_choice": user_choice,
        "preflight_retry_count": attempt,
        "preflight_failed_checks": failed_checks,
        "failure_kb_loaded": kb_loaded,
        "failure_kb_suggestions": kb_suggestions,
        "auto_fix_complete": False,
    }


def fix_preflight_guard_issues(state: FlowState) -> dict:
    """Auto-fix Level 0 (Pre-Flight Sanity Guard) issues with backup & validation.

    Attempts to fix:
    1. Unicode UTF-8 encoding (Windows)
    2. Non-ASCII Python files (convert or report)
    3. Windows path handling (convert backslashes)

    All fixes are backed up before modification and validated after.

    Args:
        state: FlowState with failed checks

    Returns:
        Updated state with fixes applied
    """
    import io

    session_id = state.get("session_id")
    backup_base_dir = state.get("backup_base_dir")
    log_base_dir = state.get("log_base_dir") or backup_base_dir
    logger = ErrorLogger(session_id, log_base_dir=log_base_dir) if session_id else None
    backup = BackupManager(session_id, backup_base_dir=backup_base_dir) if session_id else None

    fixed_issues = []
    fix_errors = []

    if not state.get("unicode_check") and sys.platform == "win32":
        try:
            if hasattr(sys.stdout, "reconfigure"):
                sys.stdout.reconfigure(encoding="utf-8", errors="replace")
            elif hasattr(sys.stdout, "buffer"):
                sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

            if hasattr(sys.stderr, "reconfigure"):
                sys.stderr.reconfigure(encoding="utf-8", errors="replace")
            elif hasattr(sys.stderr, "buffer"):
                sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

            fixed_issues.append("[FIXED] Unicode UTF-8 encoding reconfigured")
            logger and logger.log_validation_result("Level 0 (Pre-Flight Sanity Guard)", "Unicode UTF-8 Fix", True)
        except Exception as e:
            error_msg = f"Could not fix Unicode: {e}"
            fix_errors.append(error_msg)
            logger and logger.log_error(
                "Level 0 (Pre-Flight Sanity Guard)", str(e), severity="ERROR", error_type="UnicodeError"
            )

    if not state.get("encoding_check"):
        try:
            nonascii_files = state.get("encoding_nonascii_files") or []
            if nonascii_files:
                fix_errors.append(
                    "Non-ASCII files need MANUAL review (%d files): %s%s"
                    % (
                        len(nonascii_files),
                        ", ".join(nonascii_files[:5]),
                        " ... and %d more" % (len(nonascii_files) - 5) if len(nonascii_files) > 5 else "",
                    )
                )
                fixed_issues.append(
                    ">> Encoding: %d non-ASCII files reported (auto-fix disabled per policy)" % len(nonascii_files)
                )
                logger and logger.log_decision(
                    "Level 0 (Pre-Flight Sanity Guard)",
                    "Encoding fix skipped",
                    "Policy requires manual review for non-ASCII content",
                    chosen_option="report-only",
                )
            else:
                fixed_issues.append(">> All Python files are ASCII-safe")
        except Exception as e:
            fix_errors.append("Could not check encoding: %s" % e)

    if not state.get("windows_path_check") and sys.platform == "win32":
        try:
            import re as _re_fix

            from sdlc_engine.security.path_scan import (
                DRIVE_PATH_RE as _DRIVE_PATH_RE,
                get_docstring_spans as _get_docstring_spans,
                has_drive_path as _has_drive_path,
                is_drive_path_match as _is_drive_path_match,
            )
            from sdlc_engine.security.preflight_nodes import _iter_project_py_files

            project_root = Path(state.get("project_root", "."))
            fixed_files = []
            issues = []

            violating_files = state.get("windows_path_violating_files")
            if violating_files is not None and isinstance(violating_files, list):
                _fix_files = []
                for f in violating_files:
                    p = Path(f)
                    target_p = p if p.is_absolute() else (project_root / p)
                    if target_p.exists():
                        _fix_files.append(target_p)
            else:
                _fix_files = list(_iter_project_py_files(project_root, cap=500))
            for py_file in _fix_files:
                try:
                    try:
                        content = py_file.read_text(encoding="utf-8-sig")
                    except UnicodeDecodeError:
                        _logger.warning("Non-UTF-8 file skipped from auto-fix: %s", py_file)
                        continue

                    if not _has_drive_path(content):
                        continue
                    if "\\" in content and ":\\" in content:
                        original_content = content

                        if backup:
                            backup_ok = backup.backup_file(
                                str(py_file), "Level 0 (Pre-Flight Sanity Guard)", "Before path fix"
                            )
                            if not backup_ok:
                                _logger.error("Backup failed for %s, skipping modification (fail-closed)", py_file)
                                fix_errors.append(f"Backup failed for {py_file.name}, auto-fix aborted")
                                continue

                        docstring_spans = _get_docstring_spans(content)

                        def _fix_drive_path(m):
                            if docstring_spans and any(s <= m.start() < e for s, e in docstring_spans):
                                return m.group(0)
                            if not _is_drive_path_match(m):
                                return m.group(0)
                            drive = m.group(1)
                            rest = m.group(3).lstrip("\\/")
                            cleaned_rest = _re_fix.sub(r"\\+", "/", rest)
                            return f"{drive}:/{cleaned_rest}"

                        content = _DRIVE_PATH_RE.sub(_fix_drive_path, content)

                        if content != original_content:
                            _atomic_write_text(py_file, content, encoding="utf-8")

                            if backup:
                                if backup.validate_file_integrity(
                                    str(py_file), "Level 0 (Pre-Flight Sanity Guard)"
                                ):
                                    fixed_files.append(_safe_rel_path(py_file, project_root))
                                    logger and logger.log_validation_result(
                                        "Level 0 (Pre-Flight Sanity Guard)", f"Path fix: {py_file.name}", True
                                    )

                                    diff_path = backup.generate_diff(
                                        str(py_file), "Level 0 (Pre-Flight Sanity Guard)", "path_fix"
                                    )
                                    logger and logger.log_decision(
                                        "Level 0 (Pre-Flight Sanity Guard)",
                                        "File modified and validated",
                                        f"Path fix applied to {py_file.name}",
                                        chosen_option=f"Diff saved: {diff_path}",
                                    )
                                else:
                                    backup.restore_file(str(py_file), "Level 0 (Pre-Flight Sanity Guard)")
                                    fix_errors.append(f"Validation failed for {py_file.name}, file restored")
                                    logger and logger.log_error(
                                        "Level 0 (Pre-Flight Sanity Guard)",
                                        f"Validation failed for {py_file.name}",
                                        severity="ERROR",
                                        recovery_action="File restored from backup",
                                    )
                            else:
                                is_valid = False
                                try:
                                    compile(content, str(py_file), "exec")
                                    is_valid = True
                                except SyntaxError as se:
                                    _logger.error("Syntax error detected in %s: %s", py_file, se)

                                if is_valid:
                                    fixed_files.append(_safe_rel_path(py_file, project_root))
                                    logger and logger.log_validation_result(
                                        "Level 0 (Pre-Flight Sanity Guard)", f"Path fix: {py_file.name}", True
                                    )
                                else:
                                    _atomic_write_text(py_file, original_content, encoding="utf-8")
                                    fix_errors.append(f"Validation failed for {py_file.name}, file restored")
                                    logger and logger.log_error(
                                        "Level 0 (Pre-Flight Sanity Guard)",
                                        f"Validation failed for {py_file.name}",
                                        severity="ERROR",
                                        recovery_action="File restored from original content",
                                    )
                        else:
                            issues.append(_safe_rel_path(py_file, project_root))
                except Exception as e:
                    if backup:
                        backup.restore_file(str(py_file), "Level 0 (Pre-Flight Sanity Guard)")
                    elif "original_content" in locals():
                        try:
                            _atomic_write_text(py_file, original_content, encoding="utf-8")
                        except Exception:
                            pass
                    error_msg = f"Could not fix {py_file.name}: {e}"
                    fix_errors.append(error_msg)
                    logger and logger.log_error(
                        "Level 0 (Pre-Flight Sanity Guard)",
                        str(e),
                        severity="ERROR",
                        recovery_action=f"File restored: {py_file.name}",
                    )

            if fixed_files:
                fixed_issues.append(
                    f"[FIXED] Fixed backslash paths in {len(fixed_files)} files: {', '.join(fixed_files[:3])}"
                )

            if issues:
                fix_errors.append(f"Files with escape sequences only (not path separators): {', '.join(issues[:2])}")

            if not fixed_files and not issues:
                fixed_issues.append("[FIXED] All paths already use forward slashes")

        except Exception as e:
            error_msg = f"Could not fix paths: {e}"
            fix_errors.append(error_msg)
            logger and logger.log_error(
                "Level 0 (Pre-Flight Sanity Guard)", str(e), severity="ERROR", error_type="PathFixError"
            )

    return {
        "preflight_fixes_applied": fixed_issues,
        "preflight_fix_errors": fix_errors,
        "preflight_ready_to_retry": True,
        "auto_fix_complete": len(fix_errors) == 0,
        "auto_fix_applied": list(state.get("auto_fix_applied", [])) + fixed_issues,
    }
