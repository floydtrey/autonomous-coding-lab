"""Runtime adapter plugins for ACL Next.

Adapters translate the stable ACL Core/role contracts to external runtimes.
Roles and Controller must not depend on a specific adapter implementation.
"""
from .loader import AdapterConfig, AdapterLoader
from .openai_agent import OpenAICompatibleAgentAdapter
from .openai_compatible import OpenAICompatibleChatAdapter

__all__ = [
    "AdapterConfig",
    "AdapterLoader",
    "OpenAICompatibleAgentAdapter",
    "OpenAICompatibleChatAdapter",
]
