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
    df = report.generate_fund_report("Blue Whale", tax_wrapper=TaxWrapper.ISA)
    print(df)
"""

from models import (
    CashFlow,
    Holding,
    Platform,
    PortfolioSummary,
    TaxWrapper,
    Transaction,
    TransactionType,
)
from loaders import (
    BaseLoader,
    FidelityLoader,
    InteractiveInvestorLoader,
    load_all_transactions,
)
from reports import (
    TransactionFilter,
    TransactionReport,
    get_fund_transactions,
    get_unique_funds,
)
from calculators import (
    ReturnCalculator,
    ReturnMetrics,
    create_cash_flows_from_summary,
)
from config import Config, load_config


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
    "load_all_transactions",
    # Reports
    "TransactionFilter",
    "TransactionReport",
    "get_fund_transactions",
    "get_unique_funds",
    # Calculators
    "ReturnCalculator",
    "ReturnMetrics",
    "create_cash_flows_from_summary",
    # Config
    "Config",
    "load_config",
]
