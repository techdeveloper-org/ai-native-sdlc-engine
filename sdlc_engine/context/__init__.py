"""context package -- context caching, deduplication, flow tracing, and error tracking.

Re-exports all public symbols from sub-modules so callers can use:
    from sdlc_engine.context import ContextCache, deduplicate_context
    from sdlc_engine.context import convert_flow_state_to_trace
    from sdlc_engine.context import capture_exception, init_sentry
"""

from .cache import (  # noqa: F401
    CACHE_KEY_HASH,
    CACHE_KEY_LENGTH,
    CACHE_MAX_AGE_HOURS,
    CACHE_STATS,
    TRACKED_FILE_PATTERNS,
    CacheStats,
    ContextCache,
)
from .deduplicator import MIN_SAVINGS_RATIO, PRIORITY_ORDER, dedup_savings_estimate, deduplicate_context  # noqa: F401
from .error_tracking import capture_exception, capture_message, init_sentry  # noqa: F401
from .flow_trace_converter import (  # noqa: F401
    convert_flow_state_to_trace,
    print_flow_checkpoint,
    write_flow_trace_json,
)
from .complexity_calculator import node_complexity_calculation  # noqa: F401
from .context_loader import node_context_loader  # noqa: F401
from .helpers import _load_architecture_script  # noqa: F401
from .routing import cleanup_level1_memory, level1_merge_node  # noqa: F401
from .session_loader import node_session_loader  # noqa: F401
