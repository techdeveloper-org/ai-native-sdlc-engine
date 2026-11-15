# Windows Path Validation Policy (Level 0 Pre-Flight Guard)

**Version:** 2.0.0
**Priority:** HIGH
**Status:** ACTIVE
**Stage:** Level 0 (Pre-Flight Sanity Guard, T = 0)
**Graph Node:** `preflight_guard_windows` -> `preflight_guard_merge`
**Scope:** Windows only (`sys.platform == 'win32'`)

---

## 1. Purpose & Architectural Invariants

Hardcoded Windows-style paths (`C:\Users\...`, `D:\projects\...`) in Python source files cause cross-platform execution failures on Linux/macOS and in containerized CI/CD pipelines. This policy mandates:
1. Pure forward slashes (`/`) or `pathlib.Path` / `os.path.join` across all project Python source files.
2. Complete absence of drive-letter backslash strings in executable code.
3. Strict preservation of Python escape sequences (`\n`, `\t`, `\r`, etc.) and docstring examples.
4. Fail-closed, non-destructive file operations with atomic rollback guarantees.

---

## 2. Detection Engine Architecture

The scan inspects up to **500 project Python files** using a dual-pass AST and regex analyzer:

### 2.1 Vendor Directory Exclusion
The scanner automatically isolates and ignores 13 vendor, virtual environment, and cache directories:
`.venv`, `venv`, `env`, `node_modules`, `site-packages`, `.git`, `__pycache__`, `dist`, `build`, `.tox`, `.mypy_cache`, `.pytest_cache`, `.eggs`, and `*.egg-info`.

### 2.2 AST-Based Constant Value Inspection
- Files are parsed into an Abstract Syntax Tree via `ast.parse`.
- String literal **values** are inspected directly (`iter_string_values()`), resolving escape sequences so that `\n`, `\t`, `\r` can never be mistaken for path separators.
- **Docstring Bypass:** The first string statement of modules, classes, and functions (`_docstring_nodes()`) is explicitly bypassed, allowing example drive paths in documentation.
- **Comment Scan:** Comment lines (`#`) are inspected independently for drive paths.
- **SyntaxError Fallback:** If `ast.parse` encounters a `SyntaxError`, the engine safely falls back to raw-regex scanning on the source lines.

### 2.3 Detection Regular Expression
```regex
(?<![A-Za-z0-9_\\?])([A-Za-z]):(?:\\\\|\\)(?:[A-Za-z0-9_\-\.\\/]| (?![ \-\/]|[A-Za-z]:[\\/]))*
```
- **Verbatim Win32 Bypass:** Negative lookbehind `(?<![A-Za-z0-9_\\?])` exempts verbatim namespaces (`\\?\C:\...`).
- **UNC Exemption:** UNC network shares (`\\server\share`) are excluded as they contain no drive letters.
- **URL / URI Exemption:** Standard schemes (`file:///C:/`, `https://`) pass cleanly.

---

## 3. Auto-Fix Strategy & Transactional Rollback

When violations are detected, `fix_preflight_guard_issues` executes an atomic 4-step repair:
1. **Pre-Modification Backup (Fail-Closed):**
   - Exact byte-for-byte backup via `BackupManager` with microsecond timestamp + UUID suffix.
   - Backup is created **only** for files confirmed to contain violations (eliminating backup amplification DoS).
   - If backup creation returns `False` (disk full, permission denied), file modification is immediately aborted.
2. **Escaped String & Drive Path Normalization:**
   - Normalizes matched drive paths to forward slashes (`C:/...`).
   - Handles single (`C:\`) and double (`C:\\`) backslashes cleanly without creating malformed double forward slashes (`C://`).
   - Lookahead boundary checks preserve multi-argument boundaries on a single line and legitimate escapes (`\n`, `\t`, etc.).
3. **Atomic File Writeback:**
   - Writes to a temporary sibling file (`.filename.tmp.PID`) and replaces target via `os.replace` to prevent file truncation on process interruption.
4. **AST Validation & Audit Trail:**
   - Validates post-fix syntax via `compile(content, file, "exec")`.
   - On syntax failure: Immediate non-destructive rollback via `backup.restore_file()`.
   - On success: Emits unified diff to `sessions/{session_id}/backup/diffs/{step}_{label}_{timestamp}.diff`.
5. **Encoding:** Reads with `utf-8-sig` (handling BOMs transparently); writes with UTF-8 without BOM.

---

## 4. Recovery Loop & Bounds

- **Retry Budget:** `MAX_PREFLIGHT_ATTEMPTS = 3` (enforced by `preflight_merge_node`).
- **Interactive Resolution:** Interactive terminals (`sys.stdin.isatty() == True`) offer `[auto-fix/skip]` choices.
- **Non-Interactive Hook Default:** Automatically defaults to `auto-fix` when `sys.stdin.isatty() == False`, preventing CLI hangs.
- **Failure Escalation:** On 3 failed attempts, marks `preflight_fatal_failure = True` and forces continuation to Level 1 with logged warnings.

---

## 5. FlowState Contract Specification

| Field | Type | Description |
|:---|:---|:---|
| `windows_path_check` | `bool` | `True` if no backslash paths exist or on non-Windows; `False` if detected |
| `windows_path_check_error` | `Optional[str]` | Truncated error message containing first 2 problem files, e.g. `Backslash paths found: app.py, utils.py` |
| `preflight_status` | `str` | `"OK"` (all checks passed) or `"FAILED"` (triggering recovery) |
| `preflight_retry_count` | `int` | Attempt counter (1..3) |
| `preflight_fixes_applied` | `List[str]` | Applied repair notifications |
| `preflight_fix_errors` | `List[str]` | Any fix or validation errors encountered |
