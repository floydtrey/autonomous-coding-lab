"""Runtime adapter plugins for ACL Next.

Adapters translate the stable ACL Core/role contracts to external runtimes.
Roles and Controller must not depend on a specific adapter implementation.
"""
from .agent_session import AgentSession, AgentSessionEvent
from .context_pressure import ContextPressureEstimate, estimate_context_pressure
from .loader import AdapterConfig, AdapterLoader
from .openai_agent import OpenAICompatibleAgentAdapter
from .openai_compatible import OpenAICompatibleChatAdapter

__all__ = [
    "AgentSession",
    "AgentSessionEvent",
    "ContextPressureEstimate",
    "estimate_context_pressure",
    "AdapterConfig",
    "AdapterLoader",
    "OpenAICompatibleAgentAdapter",
    "OpenAICompatibleChatAdapter",
]
