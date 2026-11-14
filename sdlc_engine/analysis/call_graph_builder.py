"""Call graph builder shim -- re-exported from analysis/parsers."""

from sdlc_engine.analysis.parsers.call_graph_builder_legacy import (  # noqa: F401
    CallGraphBuilder,
    _safe_avg,
    build_call_graph,
    get_call_graph_metrics,
    get_impact_analysis,
)
from sdlc_engine.analysis.parsers.graph_model import CallGraph  # noqa: F401
from sdlc_engine.analysis.parsers.python_parser import _CallGraphVisitor  # noqa: F401

__all__ = [
    "CallGraphBuilder",
    "_safe_avg",
    "build_call_graph",
    "get_call_graph_metrics",
    "get_impact_analysis",
    "CallGraph",
    "_CallGraphVisitor",
]
