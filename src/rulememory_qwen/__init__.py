"""RuleMemory — a Qwen-powered MemoryAgent.

Public API:

    from rulememory_qwen import RuleMemoryAgent, make_reasoner, Memory

The agent ingests free-text rules/notes, uses a Qwen reasoner to extract
structured facts, stores them in a typed, provenance-tracked memory with
semantic recall and cross-session persistence, then answers questions
grounded on the recalled facts while flagging stale assumptions and
conflicts.
"""

from .reasoner import (
    Reasoner,
    QwenLocalReasoner,
    QwenCloudReasoner,
    RuleBasedReasoner,
    make_reasoner,
)
from .memory import Memory, MemoryEntry, SourceRef
from .agent import RuleMemoryAgent

__all__ = [
    "Reasoner",
    "QwenLocalReasoner",
    "QwenCloudReasoner",
    "RuleBasedReasoner",
    "make_reasoner",
    "Memory",
    "MemoryEntry",
    "SourceRef",
    "RuleMemoryAgent",
]

__version__ = "1.0.0"
