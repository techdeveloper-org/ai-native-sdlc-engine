"""agents package -- skill/agent loading, lifecycle management, and KG-driven selection.

Re-exports all public symbols from sub-modules so callers can use:
    from sdlc_engine.agents import SkillAgentLoader, get_skill_agent_loader
    from sdlc_engine.agents import SkillManager, get_skill_manager
    from sdlc_engine.agents import build_selection, rank_skills, validate_skill
    from sdlc_engine.agents import DomainKgAdapter, Lexicon, LibraryCatalogue, load_catalogue, select_agents
"""

from .agent_loader import SkillAgentLoader, get_skill_agent_loader  # noqa: F401
from .manager import MAX_RETRIES, SkillManager, get_skill_manager  # noqa: F401
from .selection_criteria import (  # noqa: F401
    are_compatible,
    build_selection,
    detect_conflicts,
    get_conflict_reason,
    rank_skills,
    score_skill,
    validate_skill,
)
from .catalogue import AgentRecord, CatalogueUnavailable, LibraryCatalogue, SkillRecord, load_catalogue  # noqa: F401
from .explainability import (  # noqa: F401
    FR23_FIELDS,
    IncompleteSelectionRecord,
    SelectionShapeChanged,
    emit_selection,
    explain_match,
    explain_selection,
)
from .ids import candidate_refs, normalise_ref  # noqa: F401
from .kg_adapter import DomainKgAdapter, KgEdge, Parsed, ParseError  # noqa: F401
from .lexicon import Lexicon  # noqa: F401
from .risk import RiskSignal, TruncatedRiskSignal, probe_builder_coverage  # noqa: F401
from .selector import (  # noqa: F401
    OUTCOME_LOW_CONFIDENCE,
    OUTCOME_NO_MATCH,
    OUTCOME_SELECTED,
    OUTCOME_UNAVAILABLE,
    REASON_OUTCOMES,
    ConfidenceFloorOutOfRange,
    Degraded,
    EdgeStep,
    Match,
    SelectionResult,
    UnmappedDegradedReason,
    outcome_for,
    select_agents,
)

__all__ = [
    "SkillAgentLoader",
    "get_skill_agent_loader",
    "MAX_RETRIES",
    "SkillManager",
    "get_skill_manager",
    "are_compatible",
    "build_selection",
    "detect_conflicts",
    "get_conflict_reason",
    "rank_skills",
    "score_skill",
    "validate_skill",
    "OUTCOME_LOW_CONFIDENCE",
    "OUTCOME_NO_MATCH",
    "OUTCOME_SELECTED",
    "OUTCOME_UNAVAILABLE",
    "REASON_OUTCOMES",
    "AgentRecord",
    "CatalogueUnavailable",
    "ConfidenceFloorOutOfRange",
    "Degraded",
    "DomainKgAdapter",
    "EdgeStep",
    "FR23_FIELDS",
    "IncompleteSelectionRecord",
    "KgEdge",
    "LibraryCatalogue",
    "Lexicon",
    "Match",
    "Parsed",
    "ParseError",
    "RiskSignal",
    "SelectionResult",
    "SelectionShapeChanged",
    "SkillRecord",
    "TruncatedRiskSignal",
    "UnmappedDegradedReason",
    "candidate_refs",
    "emit_selection",
    "explain_match",
    "explain_selection",
    "load_catalogue",
    "normalise_ref",
    "outcome_for",
    "probe_builder_coverage",
    "select_agents",
]
