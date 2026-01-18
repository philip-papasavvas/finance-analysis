"""
Transaction analysis package for portfolio analyzer.

Provides comprehensive analysis of trading patterns including:
- Holding period analysis (FIFO lot matching)
- Trading frequency metrics
- Price impact analysis
- Cross-reference matching across platforms
"""

from portfolio.analysis.models import (
    AnalysisResult,
    CrossReferenceMatch,
    HoldingPeriodCategory,
    HoldingPeriodResult,
    Lot,
    PriceImpactClassification,
    PriceImpactResult,
    TradingFrequencyMetrics,
)

__all__ = [
    "Lot",
    "HoldingPeriodResult",
    "HoldingPeriodCategory",
    "TradingFrequencyMetrics",
    "PriceImpactResult",
    "PriceImpactClassification",
    "CrossReferenceMatch",
    "AnalysisResult",
]
