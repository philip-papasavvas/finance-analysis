"""
Data models for transaction analysis.

Contains dataclasses for analysis results with confidence scoring.
"""

from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from typing import Optional


class HoldingPeriodCategory(Enum):
    """Categories for holding period classification."""

    VERY_SHORT_TERM = "very_short_term"  # <30 days
    SHORT_TERM = "short_term"  # 30-89 days
    MEDIUM_TERM = "medium_term"  # 90-364 days
    LONG_TERM = "long_term"  # 365+ days

    @classmethod
    def from_days(cls, days: int) -> "HoldingPeriodCategory":
        """Classify based on number of days held."""
        if days < 30:
            return cls.VERY_SHORT_TERM
        elif days < 90:
            return cls.SHORT_TERM
        elif days < 365:
            return cls.MEDIUM_TERM
        else:
            return cls.LONG_TERM

    @property
    def label(self) -> str:
        """Human-readable label."""
        labels = {
            self.VERY_SHORT_TERM: "<30 days",
            self.SHORT_TERM: "30-89 days",
            self.MEDIUM_TERM: "90-364 days",
            self.LONG_TERM: "365+ days",
        }
        return labels[self]

    @property
    def flag(self) -> str:
        """Warning flag for category."""
        flags = {
            self.VERY_SHORT_TERM: "HIGH ATTENTION",
            self.SHORT_TERM: "ATTENTION",
            self.MEDIUM_TERM: "NORMAL",
            self.LONG_TERM: "GOOD",
        }
        return flags[self]


class PriceImpactClassification(Enum):
    """Classification for price impact (favorable/unfavorable)."""

    FAVORABLE = "favorable"
    NEUTRAL = "neutral"
    UNFAVORABLE = "unfavorable"


@dataclass
class Lot:
    """
    A single purchase lot for FIFO tracking.

    Represents units bought at a specific time that can be
    partially consumed by subsequent sells.
    """

    buy_date: date
    units: float
    price_per_unit: float
    remaining_units: float
    fund_name: str
    platform: str
    tax_wrapper: str
    transaction_id: Optional[int] = None

    @property
    def is_exhausted(self) -> bool:
        """Returns True if all units have been sold."""
        return self.remaining_units <= 0.001  # Tolerance for float precision

    @property
    def original_value(self) -> float:
        """Original purchase value."""
        return self.units * self.price_per_unit

    def consume(self, units_to_sell: float) -> float:
        """
        Consume units from this lot.

        Args:
            units_to_sell: Number of units to consume.

        Returns:
            Number of units actually consumed (may be less if lot exhausted).
        """
        consumed = min(units_to_sell, self.remaining_units)
        self.remaining_units -= consumed
        return consumed


@dataclass
class HoldingPeriodResult:
    """Result of a holding period calculation for a single lot sale."""

    fund_name: str
    ticker: Optional[str]
    platform: str
    tax_wrapper: str
    buy_date: date
    sell_date: date
    holding_days: int
    units_sold: float
    buy_price: float
    sell_price: float
    buy_value: float
    sell_value: float
    gain_loss: float
    gain_loss_pct: float
    category: HoldingPeriodCategory
    confidence: float = 1.0

    @property
    def is_quick_flip(self) -> bool:
        """Returns True if sold within 30 days."""
        return self.category == HoldingPeriodCategory.VERY_SHORT_TERM

    def to_dict(self) -> dict:
        """Convert to dictionary for DataFrame/report."""
        return {
            "fund_name": self.fund_name,
            "ticker": self.ticker,
            "platform": self.platform,
            "tax_wrapper": self.tax_wrapper,
            "buy_date": self.buy_date.isoformat(),
            "sell_date": self.sell_date.isoformat(),
            "holding_days": self.holding_days,
            "units_sold": self.units_sold,
            "buy_price": self.buy_price,
            "sell_price": self.sell_price,
            "buy_value": self.buy_value,
            "sell_value": self.sell_value,
            "gain_loss": self.gain_loss,
            "gain_loss_pct": self.gain_loss_pct,
            "category": self.category.value,
            "category_label": self.category.label,
            "confidence": self.confidence,
        }


@dataclass
class TradingFrequencyMetrics:
    """Trading frequency analysis for a fund/platform/wrapper."""

    fund_name: Optional[str] = None
    ticker: Optional[str] = None
    platform: Optional[str] = None
    tax_wrapper: Optional[str] = None
    total_trades: int = 0
    buy_count: int = 0
    sell_count: int = 0
    first_trade_date: Optional[date] = None
    last_trade_date: Optional[date] = None
    active_months: int = 0
    avg_trades_per_month: float = 0.0
    peak_month: Optional[str] = None
    peak_month_trades: int = 0
    confidence: float = 1.0

    def to_dict(self) -> dict:
        """Convert to dictionary for DataFrame/report."""
        return {
            "fund_name": self.fund_name,
            "ticker": self.ticker,
            "platform": self.platform,
            "tax_wrapper": self.tax_wrapper,
            "total_trades": self.total_trades,
            "buy_count": self.buy_count,
            "sell_count": self.sell_count,
            "first_trade_date": self.first_trade_date.isoformat()
            if self.first_trade_date
            else None,
            "last_trade_date": self.last_trade_date.isoformat() if self.last_trade_date else None,
            "active_months": self.active_months,
            "avg_trades_per_month": self.avg_trades_per_month,
            "peak_month": self.peak_month,
            "peak_month_trades": self.peak_month_trades,
            "confidence": self.confidence,
        }


@dataclass
class PriceImpactResult:
    """Price impact analysis for a single transaction."""

    date: date
    fund_name: str
    ticker: str
    transaction_type: str  # BUY or SELL
    execution_price: float
    market_price: float
    price_difference: float
    price_difference_pct: float
    value_impact: float  # In currency terms
    units: float
    classification: PriceImpactClassification
    confidence: float = 0.85  # Default lower due to intraday vs close comparison

    @property
    def is_favorable(self) -> bool:
        """Returns True if trade was executed at a favorable price."""
        return self.classification == PriceImpactClassification.FAVORABLE

    def to_dict(self) -> dict:
        """Convert to dictionary for DataFrame/report."""
        return {
            "date": self.date.isoformat(),
            "fund_name": self.fund_name,
            "ticker": self.ticker,
            "transaction_type": self.transaction_type,
            "execution_price": self.execution_price,
            "market_price": self.market_price,
            "price_difference": self.price_difference,
            "price_difference_pct": self.price_difference_pct,
            "value_impact": self.value_impact,
            "units": self.units,
            "classification": self.classification.value,
            "confidence": self.confidence,
        }


@dataclass
class CrossReferenceMatch:
    """A potential match between funds across platforms/wrappers."""

    fund_a: str
    fund_b: str
    platform_a: str
    platform_b: str
    wrapper_a: str
    wrapper_b: str
    match_type: str  # "ticker", "sedol", "isin", "name_similarity"
    matched_identifier: Optional[str]
    confidence: float
    reason: str

    @property
    def is_verified(self) -> bool:
        """Returns True if confidence meets threshold (0.90+)."""
        return self.confidence >= 0.90

    def to_dict(self) -> dict:
        """Convert to dictionary for DataFrame/report."""
        return {
            "fund_a": self.fund_a,
            "fund_b": self.fund_b,
            "platform_a": self.platform_a,
            "platform_b": self.platform_b,
            "wrapper_a": self.wrapper_a,
            "wrapper_b": self.wrapper_b,
            "match_type": self.match_type,
            "matched_identifier": self.matched_identifier,
            "confidence": self.confidence,
            "reason": self.reason,
            "is_verified": self.is_verified,
        }


@dataclass
class AnalysisResult:
    """Complete analysis result container with all findings."""

    # Metadata
    generated_at: str
    data_start_date: str
    data_end_date: str
    total_transactions: int
    buy_count: int
    sell_count: int

    # Holding period results
    holding_periods: list[HoldingPeriodResult] = field(default_factory=list)
    holding_period_summary: dict = field(default_factory=dict)

    # Trading frequency results
    frequency_by_fund: list[TradingFrequencyMetrics] = field(default_factory=list)
    frequency_by_platform: list[TradingFrequencyMetrics] = field(default_factory=list)
    frequency_by_wrapper: list[TradingFrequencyMetrics] = field(default_factory=list)
    monthly_pattern: dict = field(default_factory=dict)

    # Price impact results
    price_impacts: list[PriceImpactResult] = field(default_factory=list)
    price_impact_summary: dict = field(default_factory=dict)

    # Cross-reference results
    verified_matches: list[CrossReferenceMatch] = field(default_factory=list)
    unsure_matches: list[CrossReferenceMatch] = field(default_factory=list)

    # Data quality notes
    data_quality_notes: list[str] = field(default_factory=list)
    funds_without_ticker: list[str] = field(default_factory=list)
    transactions_missing_prices: int = 0

    # Current holdings (still-held positions)
    current_holdings: list = field(default_factory=list)
    current_holdings_summary: dict = field(default_factory=dict)

    # Performance analysis (TWR/MWR with benchmarks)
    performance_summary: dict = field(default_factory=dict)

    # Overall confidence
    overall_confidence: float = 0.0

    def calculate_overall_confidence(self) -> float:
        """Calculate weighted overall confidence."""
        confidences = []

        # Weight holding period confidence (if we have results)
        if self.holding_periods:
            avg_hp = sum(hp.confidence for hp in self.holding_periods) / len(self.holding_periods)
            confidences.append((avg_hp, 0.4))  # 40% weight

        # Trading frequency is always 1.0 (direct counts)
        confidences.append((1.0, 0.2))  # 20% weight

        # Price impact confidence
        if self.price_impacts:
            avg_pi = sum(pi.confidence for pi in self.price_impacts) / len(self.price_impacts)
            confidences.append((avg_pi, 0.2))  # 20% weight

        # Cross-reference confidence
        all_matches = self.verified_matches + self.unsure_matches
        if all_matches:
            avg_cr = sum(m.confidence for m in all_matches) / len(all_matches)
            confidences.append((avg_cr, 0.2))  # 20% weight

        if not confidences:
            return 0.0

        total_weight = sum(w for _, w in confidences)
        self.overall_confidence = sum(c * w for c, w in confidences) / total_weight
        return self.overall_confidence
