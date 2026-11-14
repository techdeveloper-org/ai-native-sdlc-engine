"""
Import path rewriter for ai-native-sdlc-engine package restructure.

Rewrites all ``from langgraph_engine.*`` and ``from src.*`` import paths
and dotted module strings to their new ``from sdlc_engine.*`` equivalents.

Usage:
    python scripts/tools/rewrite_imports.py [--dry-run] [--root PATH]

Options:
    --dry-run   Show changes without writing files (safe preview mode)
    --root      Project root path (defaults to current directory)
"""

import argparse
import re
import sys
from pathlib import Path

# Ordered import mapping: old_prefix -> new_prefix
# Order matters: more specific patterns must come BEFORE general ones
IMPORT_MAPPING: list[tuple[str, str]] = [
    # ── root modules mappings ────────────────────────────────────────────────
    ("sdlc_engine.orchestrator", "sdlc_engine.pipeline.orchestrator"),
    ("langgraph_engine.orchestrator", "sdlc_engine.pipeline.orchestrator"),
    ("sdlc_engine.llm_call", "sdlc_engine.llm.llm_call"),
    ("langgraph_engine.llm_call", "sdlc_engine.llm.llm_call"),
    ("sdlc_engine.checkpointer", "sdlc_engine.pipeline.checkpointer"),
    ("langgraph_engine.checkpointer", "sdlc_engine.pipeline.checkpointer"),
    ("sdlc_engine.checkpoint_manager", "sdlc_engine.pipeline.checkpoint_manager"),
    ("langgraph_engine.checkpoint_manager", "sdlc_engine.pipeline.checkpoint_manager"),
    ("sdlc_engine.recovery_handler", "sdlc_engine.quality.recovery_handler"),
    ("langgraph_engine.recovery_handler", "sdlc_engine.quality.recovery_handler"),
    ("sdlc_engine.backup_manager", "sdlc_engine.session.backup_manager"),
    ("langgraph_engine.backup_manager", "sdlc_engine.session.backup_manager"),
    ("sdlc_engine.session_manager", "sdlc_engine.session.session_manager"),
    ("langgraph_engine.session_manager", "sdlc_engine.session.session_manager"),
    ("sdlc_engine.git_operations", "sdlc_engine.session.git_operations"),
    ("langgraph_engine.git_operations", "sdlc_engine.session.git_operations"),
    ("sdlc_engine.cache_system", "sdlc_engine.session.cache_system"),
    ("langgraph_engine.cache_system", "sdlc_engine.session.cache_system"),
    ("sdlc_engine.user_interaction", "sdlc_engine.pipeline.user_interaction"),
    ("langgraph_engine.user_interaction", "sdlc_engine.pipeline.user_interaction"),
    ("sdlc_engine.coverage_analyzer", "sdlc_engine.analysis.coverage_analyzer"),
    ("langgraph_engine.coverage_analyzer", "sdlc_engine.analysis.coverage_analyzer"),
    ("sdlc_engine.complexity_calculator", "sdlc_engine.analysis.complexity_calculator"),
    ("langgraph_engine.complexity_calculator", "sdlc_engine.analysis.complexity_calculator"),
    ("sdlc_engine.call_graph_analyzer", "sdlc_engine.analysis.call_graph_analyzer"),
    ("langgraph_engine.call_graph_analyzer", "sdlc_engine.analysis.call_graph_analyzer"),
    ("sdlc_engine.call_graph_builder", "sdlc_engine.analysis.parsers.call_graph_builder_legacy"),
    ("langgraph_engine.call_graph_builder", "sdlc_engine.analysis.parsers.call_graph_builder_legacy"),
    ("sdlc_engine.quality_gate", "sdlc_engine.quality.gate"),
    ("langgraph_engine.quality_gate", "sdlc_engine.quality.gate"),
    ("sdlc_engine.test_generator", "sdlc_engine.quality.test_generator"),
    ("langgraph_engine.test_generator", "sdlc_engine.quality.test_generator"),
    ("sdlc_engine.review_criteria", "sdlc_engine.quality.review_criteria"),
    ("langgraph_engine.review_criteria", "sdlc_engine.quality.review_criteria"),
    ("sdlc_engine.task_validator", "sdlc_engine.quality.task_validator"),
    ("langgraph_engine.task_validator", "sdlc_engine.quality.task_validator"),
    ("sdlc_engine.secrets_manager", "sdlc_engine.security.secrets_manager"),
    ("langgraph_engine.secrets_manager", "sdlc_engine.security.secrets_manager"),
    ("sdlc_engine.effect_ledger", "sdlc_engine.security.effect_ledger"),
    ("langgraph_engine.effect_ledger", "sdlc_engine.security.effect_ledger"),
    ("sdlc_engine.error_logger", "sdlc_engine.shared.logging.error_logger"),
    ("langgraph_engine.error_logger", "sdlc_engine.shared.logging.error_logger"),
    ("sdlc_engine.metrics_collector", "sdlc_engine.metrics.collector"),
    ("langgraph_engine.metrics_collector", "sdlc_engine.metrics.collector"),
    ("sdlc_engine.metrics_dashboard", "sdlc_engine.metrics.dashboard"),
    ("langgraph_engine.metrics_dashboard", "sdlc_engine.metrics.dashboard"),
    ("sdlc_engine.metrics_exporter", "sdlc_engine.metrics.exporter"),
    ("langgraph_engine.metrics_exporter", "sdlc_engine.metrics.exporter"),
    ("sdlc_engine.policy_node_adapter", "sdlc_engine.routing.policy_node_adapter"),
    ("langgraph_engine.policy_node_adapter", "sdlc_engine.routing.policy_node_adapter"),
    ("sdlc_engine.flow_state", "sdlc_engine.routing.flow_state"),
    ("langgraph_engine.flow_state", "sdlc_engine.routing.flow_state"),
    ("sdlc_engine.model_fallback", "sdlc_engine.llm.model_fallback"),
    ("langgraph_engine.model_fallback", "sdlc_engine.llm.model_fallback"),
    ("sdlc_engine.token_manager", "sdlc_engine.llm.token_manager"),
    ("langgraph_engine.token_manager", "sdlc_engine.llm.token_manager"),
    ("sdlc_engine.patterns", "sdlc_engine.llm.patterns"),
    ("langgraph_engine.patterns", "sdlc_engine.llm.patterns"),
    ("sdlc_engine.decision_explainer", "sdlc_engine.llm.decision_explainer"),
    ("langgraph_engine.decision_explainer", "sdlc_engine.llm.decision_explainer"),
    ("sdlc_engine.standards_integration", "sdlc_engine.standards.integration"),
    ("langgraph_engine.standards_integration", "sdlc_engine.standards.integration"),
    ("sdlc_engine.standards_selector", "sdlc_engine.standards.selector"),
    ("langgraph_engine.standards_selector", "sdlc_engine.standards.selector"),
    ("sdlc_engine.standard_selector", "sdlc_engine.standards.selector"),
    ("langgraph_engine.standard_selector", "sdlc_engine.standards.selector"),
    ("sdlc_engine.version_selector", "sdlc_engine.agents.version_selector"),
    ("langgraph_engine.version_selector", "sdlc_engine.agents.version_selector"),
    ("sdlc_engine.skill_agent_loader", "sdlc_engine.agents.loader"),
    ("langgraph_engine.skill_agent_loader", "sdlc_engine.agents.loader"),
    ("sdlc_engine.skill_manager", "sdlc_engine.agents.manager"),
    ("langgraph_engine.skill_manager", "sdlc_engine.agents.manager"),
    ("sdlc_engine.skill_selection_criteria", "sdlc_engine.agents.catalogue"),
    ("langgraph_engine.skill_selection_criteria", "sdlc_engine.agents.catalogue"),
    ("sdlc_engine.audit_logger", "sdlc_engine.security.audit_logger"),
    ("langgraph_engine.audit_logger", "sdlc_engine.security.audit_logger"),
    ("sdlc_engine.uml_generators", "sdlc_engine.diagrams.uml.legacy_generator"),
    ("langgraph_engine.uml_generators", "sdlc_engine.diagrams.uml.legacy_generator"),
    ("sdlc_engine.build_dependency_resolver", "sdlc_engine.pipeline.builders"),
    ("langgraph_engine.build_dependency_resolver", "sdlc_engine.pipeline.builders"),
    ("sdlc_engine.dependency_resolver", "sdlc_engine.pipeline.dependency_resolver"),
    ("langgraph_engine.dependency_resolver", "sdlc_engine.pipeline.dependency_resolver"),
    ("sdlc_engine.liveness", "sdlc_engine.metrics.liveness"),
    ("langgraph_engine.liveness", "sdlc_engine.metrics.liveness"),
    # ── sdlc_pipeline nodes and helpers ──────────────────────────────────────
    ("sdlc_engine.nodes.nodes", "sdlc_engine.nodes"),
    ("sdlc_engine.sdlc_pipeline.call_graph_analyzer", "sdlc_engine.analysis.call_graph_analyzer"),
    ("langgraph_engine.sdlc_pipeline.call_graph_analyzer", "sdlc_engine.analysis.call_graph_analyzer"),
    ("sdlc_engine.sdlc_pipeline.helpers", "sdlc_engine.nodes.helpers"),
    ("langgraph_engine.sdlc_pipeline.helpers", "sdlc_engine.nodes.helpers"),
    ("sdlc_engine.sdlc_pipeline.nodes", "sdlc_engine.nodes"),
    ("langgraph_engine.sdlc_pipeline.nodes", "sdlc_engine.nodes"),
    ("sdlc_engine.sdlc_pipeline", "sdlc_engine.nodes"),
    ("langgraph_engine.sdlc_pipeline", "sdlc_engine.nodes"),
    # ── langgraph_engine core & logging mappings ─────────────────────────────
    ("sdlc_engine.library.resolver", "sdlc_engine.standards.resolver"),
    ("langgraph_engine.library.resolver", "sdlc_engine.standards.resolver"),
    ("sdlc_engine.library", "sdlc_engine.standards"),
    ("langgraph_engine.library", "sdlc_engine.standards"),
    ("langgraph_engine.core.config_loader", "sdlc_engine.shared.config.config_loader"),
    ("langgraph_engine.core.claude_paths", "sdlc_engine.shared.config.claude_paths"),
    ("langgraph_engine.core.logger_factory", "sdlc_engine.shared.logging.logger_factory"),
    ("langgraph_engine.core.structured_logger", "sdlc_engine.shared.logging.structured_logger"),
    ("langgraph_engine.core.lazy_loader", "sdlc_engine.shared.utils.lazy_loader"),
    ("langgraph_engine.core.step_decorator", "sdlc_engine.shared.decorators.step_decorator"),
    ("langgraph_engine.core.error_handler", "sdlc_engine.shared.errors.error_handler"),
    ("langgraph_engine.core", "sdlc_engine.shared.config"),
    ("langgraph_engine.engine_logging.tracing", "sdlc_engine.metrics.tracing"),
    ("sdlc_engine.shared.logging.tracing", "sdlc_engine.metrics.tracing"),
    ("langgraph_engine.tracing", "sdlc_engine.metrics.tracing"),
    ("sdlc_engine.tracing", "sdlc_engine.metrics.tracing"),
    ("langgraph_engine.engine_logging", "sdlc_engine.shared.logging"),
    ("langgraph_engine.exceptions", "sdlc_engine.shared.errors.exceptions"),
    ("langgraph_engine.error_messages", "sdlc_engine.shared.errors.error_messages"),
    ("langgraph_engine.hooks_decorator", "sdlc_engine.shared.decorators.hooks_decorator"),
    ("langgraph_engine.step_logger", "sdlc_engine.shared.logging.step_logger"),
    # ── src.utils mappings ───────────────────────────────────────────────────
    ("src.utils.import_manager", "sdlc_engine.shared.utils.import_manager"),
    ("src.utils.path_resolver", "sdlc_engine.shared.utils.path_resolver"),
    ("src.utils", "sdlc_engine.shared.utils"),
    # ── subdirectories ───────────────────────────────────────────────────────
    ("langgraph_engine.analysis.parsers", "sdlc_engine.analysis.parsers"),
    ("langgraph_engine.analysis", "sdlc_engine.analysis"),
    ("langgraph_engine.agents", "sdlc_engine.agents"),
    ("langgraph_engine.context_sync", "sdlc_engine.context"),
    ("sdlc_engine.context_sync", "sdlc_engine.context"),
    ("langgraph_engine.context", "sdlc_engine.context"),
    ("langgraph_engine.diagrams.uml", "sdlc_engine.diagrams.uml"),
    ("langgraph_engine.diagrams.drawio", "sdlc_engine.diagrams.drawio"),
    ("langgraph_engine.diagrams", "sdlc_engine.diagrams"),
    ("langgraph_engine.integrations.github", "sdlc_engine.integrations.github"),
    ("sdlc_engine.github", "sdlc_engine.integrations.github"),
    ("langgraph_engine.github", "sdlc_engine.integrations.github"),
    ("langgraph_engine.integrations.jira", "sdlc_engine.integrations.jira"),
    ("langgraph_engine.integrations.figma", "sdlc_engine.integrations.figma"),
    ("langgraph_engine.integrations.jenkins", "sdlc_engine.integrations.jenkins"),
    ("langgraph_engine.integrations.claude", "sdlc_engine.integrations.claude"),
    ("langgraph_engine.integrations", "sdlc_engine.integrations"),
    ("langgraph_engine.llm", "sdlc_engine.llm"),
    ("langgraph_engine.metrics.liveness", "sdlc_engine.metrics.liveness"),
    ("langgraph_engine.metrics", "sdlc_engine.metrics"),
    ("langgraph_engine.nodes", "sdlc_engine.nodes"),
    ("langgraph_engine.pipeline", "sdlc_engine.pipeline"),
    ("langgraph_engine.quality.runtime_verification", "sdlc_engine.quality.runtime_verification"),
    ("sdlc_engine.runtime_verification", "sdlc_engine.quality.runtime_verification"),
    ("langgraph_engine.runtime_verification", "sdlc_engine.quality.runtime_verification"),
    ("langgraph_engine.quality", "sdlc_engine.quality"),
    ("langgraph_engine.routing", "sdlc_engine.routing"),
    ("langgraph_engine.security", "sdlc_engine.security"),
    ("langgraph_engine.session", "sdlc_engine.session"),
    ("langgraph_engine.shared.logging", "sdlc_engine.shared.logging"),
    ("langgraph_engine.shared.config", "sdlc_engine.shared.config"),
    ("langgraph_engine.shared.exceptions", "sdlc_engine.shared.exceptions"),
    ("langgraph_engine.shared.models", "sdlc_engine.shared.models"),
    ("langgraph_engine.shared.utils", "sdlc_engine.shared.utils"),
    ("langgraph_engine.shared", "sdlc_engine.shared"),
    ("langgraph_engine.sonarqube", "sdlc_engine.sonarqube"),
    ("langgraph_engine.standards", "sdlc_engine.standards"),
    ("langgraph_engine.mcp", "sdlc_engine.mcp"),
    # ── Catch-all for langgraph_engine root package ──────────────────────────
    ("langgraph_engine", "sdlc_engine"),
    # ── src.mcp → sdlc_engine.mcp ────────────────────────────────────────────
    ("src.mcp", "sdlc_engine.mcp"),
]

# Regex patterns that match import statements
# Matches: from X import Y / from X import (Y, Z) / import X
_IMPORT_RE = re.compile(
    r'^(\s*(?:from|import)\s+)([\w.]+)',
    re.MULTILINE
)

# Matches dotted module string literals: "langgraph_engine.foo.bar", 'src.utils.baz'
_MODULE_STR_RE = re.compile(
    r'([\'"])((?:langgraph_engine|sdlc_engine|src)\.[\w.]+)([\'"])'
)

# File extensions to process
EXTENSIONS = {".py"}

# Directories to skip entirely
SKIP_DIRS = {
    ".venv", ".git", "__pycache__", ".mypy_cache", ".pytest_cache",
    "node_modules", "dist", "build", ".eggs", "*.egg-info",
}


def should_skip(path: Path) -> bool:
    """Return True if this path is inside a skipped directory."""
    for part in path.parts:
        if part in SKIP_DIRS or part.endswith(".egg-info"):
            return True
    return False


def rewrite_line(line: str) -> tuple[str, bool]:
    """
    Rewrite a single line's import paths and module string references.

    Returns the (possibly rewritten) line and a boolean indicating
    whether any substitution was made.
    """
    changed = False

    def _replace_import(match: re.Match) -> str:
        nonlocal changed
        prefix = match.group(1)   # 'from ' or 'import '
        module = match.group(2)   # module path

        for old, new in IMPORT_MAPPING:
            if module == old or module.startswith(old + "."):
                suffix = module[len(old):]
                rewritten = new + suffix
                changed = True
                return prefix + rewritten
        return match.group(0)

    def _replace_string(match: re.Match) -> str:
        nonlocal changed
        quote_open = match.group(1)
        module = match.group(2)
        quote_close = match.group(3)

        for old, new in IMPORT_MAPPING:
            if module == old or module.startswith(old + "."):
                suffix = module[len(old):]
                rewritten = new + suffix
                changed = True
                return quote_open + rewritten + quote_close
        return match.group(0)

    new_line = _IMPORT_RE.sub(_replace_import, line)
    new_line = _MODULE_STR_RE.sub(_replace_string, new_line)
    return new_line, changed


def process_file(filepath: Path, dry_run: bool) -> int:
    """
    Rewrite imports in a single Python file.

    Returns the number of lines changed.
    """
    if filepath.name == "rewrite_imports.py":
        return 0

    try:
        original = filepath.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        print(f"  [SKIP] {filepath} -- cannot decode as UTF-8")
        return 0

    lines = original.splitlines(keepends=True)
    new_lines = []
    changes = 0

    for lineno, line in enumerate(lines, start=1):
        new_line, changed = rewrite_line(line)
        new_lines.append(new_line)
        if changed:
            changes += 1
            if dry_run:
                print(f"  L{lineno}: {line.rstrip()}")
                print(f"       -> {new_line.rstrip()}")

    if changes > 0 and not dry_run:
        filepath.write_text("".join(new_lines), encoding="utf-8")

    return changes


def scan_and_rewrite(root: Path, dry_run: bool) -> dict[str, int]:
    """Scan root recursively and rewrite imports in all Python files."""
    results: dict[str, int] = {}
    py_files = [
        p for p in root.rglob("*.py")
        if not should_skip(p) and p.is_file() and p.name != "rewrite_imports.py"
    ]
    print(f"\nFound {len(py_files)} Python files to scan...\n")

    for filepath in sorted(py_files):
        count = process_file(filepath, dry_run)
        if count > 0:
            rel = filepath.relative_to(root)
            results[str(rel)] = count
            status = "[DRY]" if dry_run else "[OK]"
            print(f"  {status} {rel}  ({count} lines)")

    return results


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Rewrite import paths for sdlc_engine restructure."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview changes without writing files.",
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=Path.cwd(),
        help="Root path to process (default: current directory).",
    )
    args = parser.parse_args()

    mode = "DRY-RUN (no files will be written)" if args.dry_run else "LIVE REWRITE"
    print("=" * 60)
    print(f"  Import Rewriter -- {mode}")
    print(f"  Root: {args.root.resolve()}")
    print("=" * 60)

    results = scan_and_rewrite(args.root.resolve(), args.dry_run)

    total_files = len(results)
    total_lines = sum(results.values())
    print("\n" + "=" * 60)
    print(f"  Changed: {total_lines} lines across {total_files} files")
    print("=" * 60 + "\n")

    return 0 if total_files >= 0 else 1


if __name__ == "__main__":
    sys.exit(main())
