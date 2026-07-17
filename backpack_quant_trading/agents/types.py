"""Agent 共享类型（一期验收报告字段）。"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class AgentId(str, Enum):
    COORDINATOR = "coordinator"
    US_ANALYST = "us_analyst"
    A_SHARE_ANALYST = "a_share_analyst"
    CRYPTO_ANALYST = "crypto_analyst"
    RESEARCH = "research"
    RISK = "risk"
    EXECUTION = "execution"
    REVIEW = "review"


class Market(str, Enum):
    US_STOCK = "us_stock"
    A_SHARE = "a_share"
    CRYPTO = "crypto"
    UNKNOWN = "unknown"


class MemoryKind(str, Enum):
    PREFS = "agent_prefs"
    REPORTS = "agent_reports"
    RESEARCH = "agent_research"
    REVIEWS = "agent_reviews"


@dataclass
class Citation:
    title: str
    snippet: str = ""
    url: str = ""
    source: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "snippet": self.snippet,
            "url": self.url,
            "source": self.source,
        }


@dataclass
class RiskDecision:
    decision: str  # allow | reject
    reason: str = ""
    mode: str = "heuristic_v1"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "decision": self.decision,
            "reason": self.reason,
            "mode": self.mode,
        }


@dataclass
class AnalyzeRequest:
    symbol: str
    market: Market = Market.UNKNOWN
    agent_id: AgentId = AgentId.COORDINATOR
    user_text: str = ""
    timeframe: str = ""
    staff_id: str = ""
    include_research: bool = True
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AnalyzeReport:
    agent_id: AgentId
    symbol: str
    market: Market
    action: str  # buy | sell | hold | reject
    support: Optional[float] = None
    resistance: Optional[float] = None
    rationale: str = ""
    citations: List[Citation] = field(default_factory=list)
    risk: Optional[RiskDecision] = None
    score: Optional[float] = None
    raw: Dict[str, Any] = field(default_factory=dict)
    error: str = ""
    degraded: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_id": self.agent_id.value if isinstance(self.agent_id, AgentId) else self.agent_id,
            "symbol": self.symbol,
            "market": self.market.value if isinstance(self.market, Market) else self.market,
            "action": self.action,
            "support": self.support,
            "resistance": self.resistance,
            "rationale": self.rationale,
            "citations": [c.to_dict() for c in self.citations],
            "risk": self.risk.to_dict() if self.risk else None,
            "score": self.score,
            "error": self.error,
            "degraded": self.degraded,
            "raw": self.raw,
        }
