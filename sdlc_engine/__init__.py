"""
SDLC Engine - AI-Native Orchestration Engine.

This package provides a StateGraph-based orchestration engine with parallel,
conditional execution, quality gates, and automated software development lifecycle capabilities.
"""

from typing import Any

import sys

__version__ = "2.1.1"

# Bind compatibility aliases into sys.modules
_SUBMODULE_MAP = {
    "orchestrator": "sdlc_engine.pipeline.orchestrator",
    "llm_call": "sdlc_engine.llm.llm_call",
    "checkpoint_manager": "sdlc_engine.pipeline.checkpoint_manager",
    "checkpointer": "sdlc_engine.pipeline.checkpointer",
    "recovery_handler": "sdlc_engine.quality.recovery_handler",
    "flow_state": "sdlc_engine.routing.flow_state",
    "policy_node_adapter": "sdlc_engine.routing.policy_node_adapter",
    "backup_manager": "sdlc_engine.session.backup_manager",
    "session_manager": "sdlc_engine.session.manager",
    "git_operations": "sdlc_engine.session.git_operations",
    "cache_system": "sdlc_engine.session.cache_system",
    "user_interaction": "sdlc_engine.pipeline.user_interaction",
    "coverage_analyzer": "sdlc_engine.analysis.coverage_analyzer",
    "call_graph_analyzer": "sdlc_engine.analysis.call_graph_analyzer",
    "complexity_calculator": "sdlc_engine.analysis.complexity_calculator",
    "quality_gate": "sdlc_engine.quality.gate",
    "test_generator": "sdlc_engine.quality.test_generator",
    "review_criteria": "sdlc_engine.quality.review_criteria",
    "task_validator": "sdlc_engine.quality.task_validator",
    "secrets_manager": "sdlc_engine.security.secrets_manager",
    "effect_ledger": "sdlc_engine.security.effect_ledger",
    "model_fallback": "sdlc_engine.llm.model_fallback",
    "token_manager": "sdlc_engine.llm.token_manager",
    "patterns": "sdlc_engine.llm.patterns",
    "decision_explainer": "sdlc_engine.llm.decision_explainer",
    "standards_integration": "sdlc_engine.standards.integration",
    "standards_selector": "sdlc_engine.standards.selector",
    "standard_selector": "sdlc_engine.standards.selector",
    "version_selector": "sdlc_engine.agents.version_selector",
    "uml_generators": "sdlc_engine.diagrams.uml.legacy_generator",
    "github": "sdlc_engine.integrations.github",
    "runtime_verification": "sdlc_engine.quality.runtime_verification",
    "sdlc_pipeline": "sdlc_engine.nodes",
    "selection": "sdlc_engine.agents",
    "skills": "sdlc_engine.agents",
    "context_sync": "sdlc_engine.context",
    "dependency_resolver": "sdlc_engine.pipeline.dependency_resolver",
    "liveness": "sdlc_engine.metrics.liveness",
    "parsers": "sdlc_engine.analysis.parsers",
    "preflight_guard": "sdlc_engine.security",
    "timeout_wrapper": "sdlc_engine.pipeline.timeout_wrapper",
    "conflict_resolver": "sdlc_engine.pipeline.conflict_resolver",
    "parallel_executor": "sdlc_engine.pipeline.parallel_executor",
    "subgraph": "sdlc_engine.pipeline.subgraph",
}

for _alias, _target in _SUBMODULE_MAP.items():
    try:
        import importlib
        _mod = importlib.import_module(_target)
        sys.modules.setdefault(f"sdlc_engine.{_alias}", _mod)
        globals()[_alias] = _mod
    except Exception:
        pass

# Public exports catalogue - mapped to new canonical locations
_EXPORTS = {
    "FlowState": ("sdlc_engine.routing.flow_state", "FlowState"),
    "create_flow_graph": ("sdlc_engine.pipeline.orchestrator", "create_flow_graph"),
    "PolicyNodeAdapter": ("sdlc_engine.routing.policy_node_adapter", "PolicyNodeAdapter"),
    "with_hooks": ("sdlc_engine.shared.decorators.hooks_decorator", "with_hooks"),
    "CheckpointManager": ("sdlc_engine.pipeline.checkpoint_manager", "CheckpointManager"),
    "create_checkpoint_manager": ("sdlc_engine.pipeline.checkpoint_manager", "create_checkpoint_manager"),
    "MetricsCollector": ("sdlc_engine.metrics.collector", "MetricsCollector"),
    "create_metrics_collector": ("sdlc_engine.metrics.collector", "create_metrics_collector"),
    "RecoveryHandler": ("sdlc_engine.quality.recovery_handler", "RecoveryHandler"),
    "resume_from_checkpoint": ("sdlc_engine.quality.recovery_handler", "resume_from_checkpoint"),
    "ErrorLogger": ("sdlc_engine.shared.logging.error_logger", "ErrorLogger"),
    "create_logger": ("sdlc_engine.shared.logging.error_logger", "create_logger"),
    "BackupManager": ("sdlc_engine.session.backup_manager", "BackupManager"),
    "create_backup_manager": ("sdlc_engine.session.backup_manager", "create_backup_manager"),
}

__all__ = list(_EXPORTS.keys())

_LAZY_SUBMODULES = frozenset(
    {
        "pipeline",
        "nodes",
        "routing",
        "agents",
        "quality",
        "analysis",
        "llm",
        "standards",
        "sonarqube",
        "integrations",
        "mcp",
        "security",
        "context",
        "diagrams",
        "metrics",
        "session",
        "adapters",
        "shared",
        # Backward compatibility aliases
        "github",
        "github_mcp",
        "github_operation_router",
        "sdlc_pipeline",
        "runtime_verification",
        "dependency_resolver",
    }
)


def __getattr__(name: str) -> Any:
    """PEP 562 lazy attribute and submodule loader."""
    import importlib

    if name in _EXPORTS:
        mod_name, attr_name = _EXPORTS[name]
        try:
            module = importlib.import_module(mod_name)
            val = getattr(module, attr_name)
            globals()[name] = val
            return val
        except (ImportError, AttributeError):
            pass

    if name in _LAZY_SUBMODULES:
        try:
            module = importlib.import_module(f"sdlc_engine.{name}")
            globals()[name] = module
            return module
        except ImportError:
            # Fallback for aliases
            if name == "runtime_verification":
                module = importlib.import_module("sdlc_engine.quality.runtime_verification")
                globals()[name] = module
                return module
            if name in {"github", "github_mcp", "github_operation_router"}:
                module = importlib.import_module("sdlc_engine.integrations.github")
                globals()[name] = module
                return module
            if name == "dependency_resolver":
                module = importlib.import_module("sdlc_engine.pipeline.dependency_resolver")
                globals()[name] = module
                return module
            if name == "sdlc_pipeline":
                module = importlib.import_module("sdlc_engine.pipeline")
                globals()[name] = module
                return module
            raise

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
