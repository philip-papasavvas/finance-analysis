"""
Base loader abstract class for platform-specific data loaders.
"""
import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional

import pandas as pd

from portfolio.core.models import Platform, TaxWrapper, Transaction, TransactionType


logger = logging.getLogger(__name__)


class BaseLoader(ABC):
    """Abstract base class for platform-specific data loaders."""

    platform: Platform

    def __init__(self, data_directory: Path):
        """
        Initialise the loader.

        Args:
            data_directory: Path to directory containing CSV files.
        """
        self.data_directory = Path(data_directory)
        logger.info(f"Initialised {self.__class__.__name__} with {self.data_directory}")

    @abstractmethod
    def load(self) -> list[Transaction]:
        """
        Load all transactions from CSV files.

        Returns:
            List of Transaction objects.
        """
        pass

    @abstractmethod
    def _parse_row(self, row: pd.Series) -> Optional[Transaction]:
        """
        Parse a single row into a Transaction.

        Args:
            row: A pandas Series representing one CSV row.

        Returns:
            Transaction object or None if row should be skipped.
        """
        pass

    @abstractmethod
    def _determine_tax_wrapper(self, row: pd.Series) -> TaxWrapper:
        """
        Determine the tax wrapper from a row.

        Args:
            row: A pandas Series representing one CSV row.

        Returns:
            TaxWrapper enum value.
        """
        pass

    @abstractmethod
    def _determine_transaction_type(self, row: pd.Series) -> TransactionType:
        """
        Determine the transaction type from a row.

        Args:
            row: A pandas Series representing one CSV row.

        Returns:
            TransactionType enum value.
        """
        pass
