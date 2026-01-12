"""
Portfolio Analyzer

A Python package for analysing investment portfolio transactions
from Fidelity and Interactive Investor platforms.

Example usage:
    from portfolio_analyzer import (
        FidelityLoader,
        InteractiveInvestorLoader,
        TransactionReport,
        ReturnCalculator,
        Platform,
        TaxWrapper,
    )

    # Load transactions
    loader = FidelityLoader(Path("./data/fidelity"))
    transactions = loader.load()

    # Generate report
    report = TransactionReport(transactions)
    df = report.generate_fund_report("Global Index Fund", tax_wrapper=TaxWrapper.ISA)
    print(df)
"""

from portfolio.core.models import (
    CashFlow,
    Holding,
    Platform,
    PortfolioSummary,
    TaxWrapper,
    Transaction,
    TransactionType,
)
from portfolio.loaders import (
    BaseLoader,
    FidelityLoader,
    InteractiveInvestorLoader,
)
from portfolio.utils.calculators import (
    ReturnCalculator,
)


__version__ = "0.1.0"

__all__ = [
    # Models
    "CashFlow",
    "Holding",
    "Platform",
    "PortfolioSummary",
    "TaxWrapper",
    "Transaction",
    "TransactionType",
    # Loaders
    "BaseLoader",
    "FidelityLoader",
    "InteractiveInvestorLoader",
    # Calculators
    "ReturnCalculator",
]
