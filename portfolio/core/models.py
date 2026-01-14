"""
Data models for portfolio analyzer.

Contains enums for categorical data and dataclasses for domain objects.
"""
from dataclasses import dataclass, field
from datetime import date
from enum import Enum, auto
from typing import Optional


class Platform(Enum):
    """Supported trading platforms."""

    FIDELITY = auto()
    INTERACTIVE_INVESTOR = auto()
    INVEST_ENGINE = auto()

    def __str__(self) -> str:
        return self.name.replace("_", " ").title()


class TaxWrapper(Enum):
    """Tax wrapper types."""

    ISA = auto()
    SIPP = auto()
    GIA = auto()  # General Investment Account
    OTHER = auto()

    def __str__(self) -> str:
        return self.name


class TransactionType(Enum):
    """Canonical transaction types."""

    BUY = auto()
    SELL = auto()
    DIVIDEND = auto()
    TRANSFER_IN = auto()
    TRANSFER_OUT = auto()
    FEE = auto()
    INTEREST = auto()
    SUBSCRIPTION = auto()  # Cash contribution
    OTHER = auto()

    def __str__(self) -> str:
        return self.name.replace("_", " ").title()

    @property
    def is_purchase(self) -> bool:
        """Returns True if this transaction type represents a purchase."""
        return self in (TransactionType.BUY, TransactionType.TRANSFER_IN)

    @property
    def is_sale(self) -> bool:
        """Returns True if this transaction type represents a sale."""
        return self in (TransactionType.SELL, TransactionType.TRANSFER_OUT)


@dataclass
class Transaction:
    """
    Represents a single investment transaction.

    This is the canonical format that all platform-specific data
    is normalised into.
    """

    platform: Platform
    tax_wrapper: TaxWrapper
    date: date
    fund_name: str
    transaction_type: TransactionType
    units: float
    price_per_unit: float
    value: float
    currency: str = "GBP"
    sedol: Optional[str] = None
    reference: Optional[str] = None
    raw_description: Optional[str] = None

    @property
    def is_buy(self) -> bool:
        """Returns True if this is a buy transaction."""
        return self.transaction_type.is_purchase

    @property
    def is_sell(self) -> bool:
        """Returns True if this is a sell transaction."""
        return self.transaction_type.is_sale

    def to_dict(self) -> dict:
        """Convert to dictionary for DataFrame creation."""
        return {
            "Tax Wrapper": str(self.tax_wrapper),
            "Platform": str(self.platform),
            "Date": self.date.strftime("%d/%m/%Y"),
            "Fund Name": self.fund_name,
            "Buy/Sell": "Buy"
            if self.is_buy
            else "Sell"
            if self.is_sell
            else str(self.transaction_type),
            "Units": self.units,
            "Price (£)": self.price_per_unit,
            "Value (£)": self.value,
        }


@dataclass
class CashFlow:
    """
    Represents a cash flow event for return calculations.

    Positive values = money out (withdrawals, current value)
    Negative values = money in (contributions)
    """

    date: date
    amount: float
    description: str = ""

    @property
    def is_inflow(self) -> bool:
        """Returns True if this is money coming into the account."""
        return self.amount < 0

    @property
    def is_outflow(self) -> bool:
        """Returns True if this is money leaving the account."""
        return self.amount > 0


@dataclass
class Holding:
    """Represents a current holding in the portfolio."""

    platform: Platform
    tax_wrapper: TaxWrapper
    fund_name: str
    units: float
    current_price: float
    current_value: float
    book_cost: float
    currency: str = "GBP"

    @property
    def gain(self) -> float:
        """Unrealised gain/loss in currency terms."""
        return self.current_value - self.book_cost

    @property
    def gain_percentage(self) -> float:
        """Unrealised gain/loss as a percentage."""
        if self.book_cost == 0:
            return 0.0
        return (self.gain / self.book_cost) * 100


@dataclass
class PortfolioSummary:
    """Summary statistics for a portfolio or account."""

    total_contributions: float
    total_withdrawals: float
    current_value: float
    start_date: date
    end_date: date
    holdings: list[Holding] = field(default_factory=list)

    @property
    def net_contributions(self) -> float:
        """Net cash invested (contributions - withdrawals)."""
        return self.total_contributions - self.total_withdrawals

    @property
    def total_gain(self) -> float:
        """Total gain including realised and unrealised."""
        return self.current_value + self.total_withdrawals - self.total_contributions

    @property
    def simple_return(self) -> float:
        """Simple return as a percentage."""
        if self.total_contributions == 0:
            return 0.0
        return (self.total_gain / self.total_contributions) * 100

    @property
    def years_invested(self) -> float:
        """Number of years between start and end date."""
        return (self.end_date - self.start_date).days / 365.25


if __name__ == "__main__":
    # Example usage
    from datetime import date

    # Create a sample transaction
    tx = Transaction(
        platform=Platform.FIDELITY,
        tax_wrapper=TaxWrapper.ISA,
        date=date(2023, 1, 16),
        fund_name="WS Blue Whale Growth Fund",
        transaction_type=TransactionType.BUY,
        units=1231.99,
        price_per_unit=1.62,
        value=2000.00,
    )

    print("Sample Transaction:")
    print(f"  {tx.fund_name}")
    print(f"  {tx.platform} {tx.tax_wrapper} on {tx.date}")
    print(f"  {tx.transaction_type}: {tx.units:.2f} units @ £{tx.price_per_unit:.4f}")
    print(f"  Value: £{tx.value:,.2f}")
    print(f"  Is buy: {tx.is_buy}")
    print()
    print("As dict for DataFrame:")
    print(f"  {tx.to_dict()}")

    # Create a sample holding
    holding = Holding(
        platform=Platform.FIDELITY,
        tax_wrapper=TaxWrapper.ISA,
        fund_name="WS Blue Whale Growth Fund",
        units=11119.21,
        current_price=3.31,
        current_value=36790.00,
        book_cost=23094.00,
    )

    print()
    print("Sample Holding:")
    print(f"  {holding.fund_name}")
    print(f"  Value: £{holding.current_value:,.2f}")
    print(f"  Book Cost: £{holding.book_cost:,.2f}")
    print(f"  Gain: £{holding.gain:,.2f} ({holding.gain_percentage:+.2f}%)")
