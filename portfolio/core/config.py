"""
Configuration loader for portfolio analyzer.

Loads settings from config.yaml and provides access throughout the application.
"""
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


logger = logging.getLogger(__name__)


@dataclass
class FidelityConfig:
    """Configuration for Fidelity data loading."""
    directory: str
    file_pattern: str
    skip_rows: int


@dataclass
class InteractiveInvestorConfig:
    """Configuration for Interactive Investor data loading."""
    directory: str
    file_pattern: str
    skip_rows: int


@dataclass
class DataConfig:
    """Configuration for data paths and platform-specific settings."""
    base_path: str
    fidelity: FidelityConfig
    interactive_investor: InteractiveInvestorConfig

    @property
    def fidelity_path(self) -> Path:
        return Path(self.base_path) / self.fidelity.directory

    @property
    def interactive_investor_path(self) -> Path:
        return Path(self.base_path) / self.interactive_investor.directory


@dataclass
class LoggingConfig:
    """Configuration for logging."""
    level: str
    format: str
    date_format: str


@dataclass
class TransactionTypesConfig:
    """Mapping of transaction types to canonical forms."""
    buy: list[str] = field(default_factory=list)
    sell: list[str] = field(default_factory=list)
    dividend: list[str] = field(default_factory=list)
    transfer_out: list[str] = field(default_factory=list)
    fee: list[str] = field(default_factory=list)


@dataclass
class Config:
    """Main configuration container."""
    data: DataConfig
    logging: LoggingConfig
    transaction_types: TransactionTypesConfig

    @classmethod
    def from_yaml(cls, path: str | Path) -> "Config":
        """Load configuration from a YAML file."""
        path = Path(path)
        logger.debug(f"Loading configuration from {path}")

        with open(path, "r") as f:
            raw = yaml.safe_load(f)

        return cls(
            data=DataConfig(
                base_path=raw["data"]["base_path"],
                fidelity=FidelityConfig(**raw["data"]["fidelity"]),
                interactive_investor=InteractiveInvestorConfig(
                    **raw["data"]["interactive_investor"]
                ),
            ),
            logging=LoggingConfig(**raw["logging"]),
            transaction_types=TransactionTypesConfig(**raw["transaction_types"]),
        )


def setup_logging(config: LoggingConfig) -> None:
    """Configure logging based on configuration."""
    logging.basicConfig(
        level=getattr(logging, config.level.upper()),
        format=config.format,
        datefmt=config.date_format,
    )
    logger.info("Logging configured successfully")


def load_config(path: str | Path = "config.yaml") -> Config:
    """
    Load configuration and set up logging.

    Args:
        path: Path to the YAML configuration file.

    Returns:
        Loaded Config object.
    """
    config = Config.from_yaml(path)
    setup_logging(config.logging)
    return config


if __name__ == "__main__":
    # Example usage
    config = load_config("config.yaml")

    print(f"Data base path: {config.data.base_path}")
    print(f"Fidelity path: {config.data.fidelity_path}")
    print(f"II path: {config.data.interactive_investor_path}")
    print(f"Buy transaction types: {config.transaction_types.buy}")
