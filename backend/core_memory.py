# backend/core_memory.py

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
import time

@dataclass
class ConsciousState:
    ts: float = field(default_factory=time.time)
    context: Dict[str, Any] = field(default_factory=dict)
    vital_signals: List[Dict[str, Any]] = field(default_factory=list)
    summary: str = ""

@dataclass
class MemorySnapshot:
    facts: Dict[str, Any] = field(default_factory=dict)
    working: Dict[str, Any] = field(default_factory=dict)
    traces: List[Dict[str, Any]] = field(default_factory=list)
    conscious: Optional[ConsciousState] = None
