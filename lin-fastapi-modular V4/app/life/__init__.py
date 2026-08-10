"""Phase 6 Life System public API."""
from .contracts import LifeEvent, LifeState, aware_utc, iso_utc
from .event_normalizer import normalize_calendar, normalize_conversation, normalize_location, normalize_mac, normalize_screentime
from .runtime import ingest_events, ingest_context, ingest_conversation, get_life_state, get_life_context, get_timeline, replay_events, mark_idle, reset_memory_runtime
from .phase7 import create_candidates_for_events, evaluate_candidate, execute_candidate, get_audit, get_candidate, run_life_runtime_tick, drain_outbox
from .tool_brain import run_suggestion, run_backend_suggestion, suggest, suggest_with_backend
from .mcp_registry import Capability, CapabilityRegistry, registry
from .tool_executor import dispatch as dispatch_capability, reset_dispatch_state

__all__ = [
    "LifeEvent", "LifeState", "aware_utc", "iso_utc",
    "normalize_calendar", "normalize_conversation", "normalize_location", "normalize_mac", "normalize_screentime",
    "ingest_events", "ingest_context", "ingest_conversation", "get_life_state", "get_life_context", "get_timeline", "replay_events",
]
