"""Drive-path detection for the Level 0 Windows path check.

WHY THIS IS NOT A RAW-TEXT REGEX
--------------------------------
The check exists to find hardcoded Windows drive paths -- a drive letter, a
colon and a backslash, spelled out here rather than written as an example,
because this module's own scan reads string values and a literal example would
make this file a violation of the rule it implements. That is not hypothetical:
it fired on the first version of this docstring and on the fixtures in the test
module beside it, and both were rewritten to assemble their paths at run time.

Applying a regex to the raw file text cannot distinguish a
backslash that begins a path from a backslash that begins a Python escape
sequence, because both are the same character before the interpreter reads them.

That ambiguity was not theoretical. The previous raw-text pattern matched
``f:`` followed by a newline escape inside this snippet::

    "with open(p) as f:" + chr(92) + "n    pass"

It read ``f`` as a drive letter and the escape plus the following indented text
as a path body, because its character class permitted spaces. The paired
auto-fix then rewrote the backslash to a forward slash, which silently corrupted
the string and removed the match, so the check reported success precisely
because the source had been damaged. Its own comment claimed a negative
lookbehind prevented this; the lookbehind only constrains the character BEFORE
the drive letter, and a single letter preceded by a space satisfies it.

Scanning the VALUES of string literals removes the ambiguity at the root rather
than narrowing the pattern. By the time a literal is a value, an escape has
already become the character it denotes: a newline is a newline and cannot be
mistaken for a path separator. A genuine ``"C:\\\\Users"`` literal still holds a
real backslash in its value and is still found.

Files that do not parse fall back to the raw-text scan, because a file with a
syntax error still deserves the check and no better evidence is available.

KNOWN LIMIT: ONE LEVEL OF QUOTING
---------------------------------
Reading values resolves escapes exactly once. A literal whose value is ITSELF
Python source -- a fixture holding a code snippet, a template, a generator -- is
raw text again at that level, and an escape inside it is once more
indistinguishable from a path separator. The test module beside this one hit
that on its own fixture representing the corrupting snippet, and assembles it at
run time instead.

This is a limit, not a bug: distinguishing the two would require knowing that a
particular string is destined to be parsed as source, which is not decidable
here. The consequence is a possible false positive on code-generating modules,
never a false negative on a real path.
"""

import ast
import io
import re
import tokenize
from typing import List, Optional, Set, Tuple

DRIVE_PATH_RE = re.compile(
    r"(?<![A-Za-z0-9_\\?])([A-Za-z]):(\\\\|\\)((?:[A-Za-z0-9_\-\.\\/()+@#$~{}[\]]| (?![ \-\/]|[A-Za-z]:[\\/]))*)",
    re.IGNORECASE,
)

_DOCSTRING_OWNERS = (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)


def is_drive_path_match(match: re.Match) -> bool:
    """Evaluate whether a regular expression match is a genuine Windows drive path.

    Differentiates authentic Windows drive paths from Python escape sequences
    (such as \\n, \\t, \\r) that follow a single drive-letter identifier and colon.

    Args:
        match: Regular expression match object with capturing groups (drive, sep, rest).

    Returns:
        bool: True if the match represents a genuine drive path, False if it is an escape sequence.
    """
    sep = match.group(2)
    rest = match.group(3).lstrip("\\/")
    if sep == "\\" and rest and rest[0] in "ntr0bfv" and (len(rest) == 1 or rest[1] in " \t\r\n:=#"):
        return False
    return True


def get_docstring_spans(source: str) -> List[Tuple[int, int]]:
    """Compute character start and end index spans for all docstrings in Python source.

    Parses the source into an AST and identifies expression statements that serve as
    module, class, or function docstrings, translating line and column coordinates
    into character offset spans.

    Args:
        source: Python source code string.

    Returns:
        List[Tuple[int, int]]: List of (start_char, end_char) coordinate pairs.
    """
    try:
        tree = ast.parse(source)
    except (SyntaxError, ValueError):
        return []

    lines = source.splitlines(keepends=True)
    line_starts = [0]
    for line in lines:
        line_starts.append(line_starts[-1] + len(line))

    spans: List[Tuple[int, int]] = []
    for node in ast.walk(tree):
        if not isinstance(node, _DOCSTRING_OWNERS):
            continue
        body = getattr(node, "body", None)
        if not body:
            continue
        first = body[0]
        if isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant):
            if isinstance(first.value.value, str):
                val = first.value
                start_line = getattr(val, "lineno", None)
                start_col = getattr(val, "col_offset", None)
                end_line = getattr(val, "end_lineno", None)
                end_col = getattr(val, "end_col_offset", None)
                if (
                    start_line is not None
                    and start_col is not None
                    and end_line is not None
                    and end_col is not None
                    and start_line <= len(line_starts)
                    and end_line <= len(line_starts)
                ):
                    start_char = line_starts[start_line - 1] + start_col
                    end_char = line_starts[end_line - 1] + end_col
                    spans.append((start_char, end_char))
    return spans


def _docstring_nodes(tree: ast.AST) -> Set[int]:
    """Collect the constant nodes that serve as docstrings.

    A docstring is the first statement of a module, class or function body.
    It is documentation rather than code, so a drive path inside one is an
    example being explained, not a path the program will execute.

    Args:
        tree: Parsed module AST.

    Returns:
        Set[int]: Python id() of each docstring constant node.
    """
    found = set()
    for node in ast.walk(tree):
        if not isinstance(node, _DOCSTRING_OWNERS):
            continue
        body = getattr(node, "body", None)
        if not body:
            continue
        first = body[0]
        if isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant):
            if isinstance(first.value.value, str):
                found.add(id(first.value))
    return found


def iter_string_values(source: str) -> Optional[List[str]]:
    """Yield the value of every non-docstring string constant in a source text.

    Executes a single-pass AST walk combining docstring detection and string
    constant extraction without double traversal.

    Args:
        source: Python source text.

    Returns:
        Optional[List[str]]: String values, or None when source fails to parse.
    """
    try:
        tree = ast.parse(source)
    except (SyntaxError, ValueError):
        return None

    docstrings = set()
    values = []
    for node in ast.walk(tree):
        if isinstance(node, _DOCSTRING_OWNERS):
            body = getattr(node, "body", None)
            if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant):
                if isinstance(body[0].value.value, str):
                    docstrings.add(id(body[0].value))
        elif isinstance(node, ast.Constant) and isinstance(node.value, str):
            if id(node) not in docstrings:
                values.append(node.value)
    return values


def has_drive_path(source: str) -> bool:
    """Report whether a Python source text hardcodes a Windows drive path.

    Inspects string literal values directly via a single-pass AST visitor with
    early-exit semantics, filters out docstring examples, examines standalone
    and inline comments using lexical tokenization, and rejects false-positive
    Python escape sequences.

    Args:
        source: Python source text.

    Returns:
        bool: True when at least one genuine Windows drive path is present.
    """
    try:
        tree = ast.parse(source)
        docstrings = set()
        for node in ast.walk(tree):
            if isinstance(node, _DOCSTRING_OWNERS):
                body = getattr(node, "body", None)
                if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant):
                    if isinstance(body[0].value.value, str):
                        docstrings.add(id(body[0].value))
            elif isinstance(node, ast.Constant) and isinstance(node.value, str):
                if id(node) not in docstrings:
                    for match in DRIVE_PATH_RE.finditer(node.value):
                        if is_drive_path_match(match):
                            return True
    except (SyntaxError, ValueError):
        for match in DRIVE_PATH_RE.finditer(source):
            if is_drive_path_match(match):
                return True

    try:
        source_bytes = source.encode("utf-8")
        tokens = tokenize.tokenize(io.BytesIO(source_bytes).readline)
        for tok in tokens:
            if tok.type == tokenize.COMMENT:
                for match in DRIVE_PATH_RE.finditer(tok.string):
                    if is_drive_path_match(match):
                        return True
    except (tokenize.TokenError, IndentationError, SyntaxError):
        for line in source.splitlines():
            stripped = line.lstrip()
            if "#" in stripped:
                comment_part = stripped[stripped.index("#"):]
                for match in DRIVE_PATH_RE.finditer(comment_part):
                    if is_drive_path_match(match):
                        return True

    return False
