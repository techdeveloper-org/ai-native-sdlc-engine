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
import re
from typing import List, Optional, Set

DRIVE_PATH_RE = re.compile(
    r"(?<![A-Za-z0-9_\\?])([A-Za-z]):(?:\\\\|\\)(?:[A-Za-z0-9_\-\.\\/]| (?![ \-\/]|[A-Za-z]:[\\/]))*",
    re.IGNORECASE,
)

_DOCSTRING_OWNERS = (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)


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
    early-exit semantics. The moment a drive path is matched, the walk halts
    immediately.

    Args:
        source: Python source text.

    Returns:
        bool: True when at least one drive path is present.
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
                if id(node) not in docstrings and DRIVE_PATH_RE.search(node.value):
                    return True
    except (SyntaxError, ValueError):
        if DRIVE_PATH_RE.search(source):
            return True

    for line in source.splitlines():
        stripped = line.lstrip()
        if stripped.startswith("#") and DRIVE_PATH_RE.search(stripped):
            return True
    return False
