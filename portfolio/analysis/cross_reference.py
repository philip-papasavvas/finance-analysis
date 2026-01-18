"""
Cross-reference matching for funds across platforms.

Identifies when the same underlying fund is held across different
platforms or tax wrappers using various identifiers.
"""

import logging
import sqlite3
from collections import defaultdict
from pathlib import Path

from portfolio.analysis.models import CrossReferenceMatch

logger = logging.getLogger(__name__)

# Confidence threshold for verified matches (user specified: strict 0.90+)
VERIFIED_THRESHOLD = 0.90


class CrossReferenceAnalyzer:
    """Analyzes and matches funds across platforms/wrappers."""

    def __init__(self, db_path: str | Path = "portfolio.db"):
        """Initialize analyzer with database path."""
        self.db_path = Path(db_path)
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row

    def _get_fund_identifiers(self) -> list[dict]:
        """Get all funds with their identifiers."""
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT DISTINCT
                t.fund_name,
                t.platform,
                t.tax_wrapper,
                t.sedol as tx_sedol,
                ftm.ticker,
                ftm.sedol as map_sedol,
                ftm.isin
            FROM transactions t
            LEFT JOIN fund_ticker_mapping ftm ON t.fund_name = ftm.fund_name
            WHERE t.excluded = 0
              AND t.transaction_type IN ('BUY', 'SELL')
            ORDER BY t.fund_name
        """
        )
        return [dict(row) for row in cursor.fetchall()]

    def _build_lookup_tables(self, funds: list[dict]) -> tuple[dict, dict, dict, dict]:
        """
        Build lookup tables for matching.

        Returns:
            (ticker_to_funds, sedol_to_funds, isin_to_funds, fund_details)
        """
        ticker_to_funds: dict[str, list[dict]] = defaultdict(list)
        sedol_to_funds: dict[str, list[dict]] = defaultdict(list)
        isin_to_funds: dict[str, list[dict]] = defaultdict(list)
        fund_details: dict[str, dict] = {}

        for fund in funds:
            key = (fund["fund_name"], fund["platform"], fund["tax_wrapper"])
            fund_details[key] = fund

            if fund["ticker"]:
                ticker_to_funds[fund["ticker"]].append(fund)

            sedol = fund["tx_sedol"] or fund["map_sedol"]
            if sedol:
                sedol_to_funds[sedol].append(fund)

            if fund["isin"]:
                isin_to_funds[fund["isin"]].append(fund)

        return ticker_to_funds, sedol_to_funds, isin_to_funds, fund_details

    def _find_ticker_matches(
        self, ticker_to_funds: dict[str, list[dict]]
    ) -> list[CrossReferenceMatch]:
        """Find matches based on shared ticker."""
        matches = []

        for ticker, funds in ticker_to_funds.items():
            if len(funds) < 2:
                continue

            # Compare all pairs
            for i, fund_a in enumerate(funds):
                for fund_b in funds[i + 1 :]:
                    # Skip if same platform and wrapper
                    if (
                        fund_a["platform"] == fund_b["platform"]
                        and fund_a["tax_wrapper"] == fund_b["tax_wrapper"]
                    ):
                        continue

                    # Check for ISIN confirmation
                    has_isin_match = (
                        fund_a.get("isin")
                        and fund_b.get("isin")
                        and fund_a["isin"] == fund_b["isin"]
                    )

                    confidence = 1.0 if has_isin_match else 0.95

                    match = CrossReferenceMatch(
                        fund_a=fund_a["fund_name"],
                        fund_b=fund_b["fund_name"],
                        platform_a=fund_a["platform"],
                        platform_b=fund_b["platform"],
                        wrapper_a=fund_a["tax_wrapper"],
                        wrapper_b=fund_b["tax_wrapper"],
                        match_type="ticker" + ("+isin" if has_isin_match else ""),
                        matched_identifier=ticker,
                        confidence=confidence,
                        reason=f"Same ticker: {ticker}"
                        + (f" and ISIN: {fund_a['isin']}" if has_isin_match else ""),
                    )
                    matches.append(match)

        return matches

    def _find_sedol_matches(
        self,
        sedol_to_funds: dict[str, list[dict]],
        existing_pairs: set,
    ) -> list[CrossReferenceMatch]:
        """Find matches based on shared SEDOL."""
        matches = []

        for sedol, funds in sedol_to_funds.items():
            if len(funds) < 2:
                continue

            for i, fund_a in enumerate(funds):
                for fund_b in funds[i + 1 :]:
                    # Skip if same platform and wrapper
                    if (
                        fund_a["platform"] == fund_b["platform"]
                        and fund_a["tax_wrapper"] == fund_b["tax_wrapper"]
                    ):
                        continue

                    # Skip if already matched by ticker
                    pair = tuple(sorted([fund_a["fund_name"], fund_b["fund_name"]]))
                    if pair in existing_pairs:
                        continue

                    match = CrossReferenceMatch(
                        fund_a=fund_a["fund_name"],
                        fund_b=fund_b["fund_name"],
                        platform_a=fund_a["platform"],
                        platform_b=fund_b["platform"],
                        wrapper_a=fund_a["tax_wrapper"],
                        wrapper_b=fund_b["tax_wrapper"],
                        match_type="sedol",
                        matched_identifier=sedol,
                        confidence=0.98,
                        reason=f"Same SEDOL: {sedol}",
                    )
                    matches.append(match)
                    existing_pairs.add(pair)

        return matches

    def _find_isin_matches(
        self,
        isin_to_funds: dict[str, list[dict]],
        existing_pairs: set,
    ) -> list[CrossReferenceMatch]:
        """Find matches based on shared ISIN."""
        matches = []

        for isin, funds in isin_to_funds.items():
            if len(funds) < 2:
                continue

            for i, fund_a in enumerate(funds):
                for fund_b in funds[i + 1 :]:
                    # Skip if same platform and wrapper
                    if (
                        fund_a["platform"] == fund_b["platform"]
                        and fund_a["tax_wrapper"] == fund_b["tax_wrapper"]
                    ):
                        continue

                    # Skip if already matched
                    pair = tuple(sorted([fund_a["fund_name"], fund_b["fund_name"]]))
                    if pair in existing_pairs:
                        continue

                    match = CrossReferenceMatch(
                        fund_a=fund_a["fund_name"],
                        fund_b=fund_b["fund_name"],
                        platform_a=fund_a["platform"],
                        platform_b=fund_b["platform"],
                        wrapper_a=fund_a["tax_wrapper"],
                        wrapper_b=fund_b["tax_wrapper"],
                        match_type="isin",
                        matched_identifier=isin,
                        confidence=0.92,
                        reason=f"Same ISIN: {isin}",
                    )
                    matches.append(match)
                    existing_pairs.add(pair)

        return matches

    def _find_same_wrapper_holdings(self, funds: list[dict]) -> list[CrossReferenceMatch]:
        """
        Find same fund held across different wrappers on same platform.

        This identifies when you hold the same fund in both ISA and SIPP.
        """
        matches = []
        seen_pairs = set()

        # Group by ticker (most reliable identifier)
        ticker_groups: dict[str, list[dict]] = defaultdict(list)
        for fund in funds:
            if fund["ticker"]:
                ticker_groups[fund["ticker"]].append(fund)

        for ticker, ticker_funds in ticker_groups.items():
            # Group by platform
            by_platform: dict[str, list[dict]] = defaultdict(list)
            for f in ticker_funds:
                by_platform[f["platform"]].append(f)

            for platform, platform_funds in by_platform.items():
                # Look for same fund in different wrappers
                wrappers = set(f["tax_wrapper"] for f in platform_funds)
                if len(wrappers) > 1:
                    # Found same fund in multiple wrappers
                    for i, fund_a in enumerate(platform_funds):
                        for fund_b in platform_funds[i + 1 :]:
                            if fund_a["tax_wrapper"] != fund_b["tax_wrapper"]:
                                pair = tuple(
                                    sorted(
                                        [
                                            (fund_a["fund_name"], fund_a["tax_wrapper"]),
                                            (fund_b["fund_name"], fund_b["tax_wrapper"]),
                                        ]
                                    )
                                )
                                if pair in seen_pairs:
                                    continue
                                seen_pairs.add(pair)

                                match = CrossReferenceMatch(
                                    fund_a=fund_a["fund_name"],
                                    fund_b=fund_b["fund_name"],
                                    platform_a=platform,
                                    platform_b=platform,
                                    wrapper_a=fund_a["tax_wrapper"],
                                    wrapper_b=fund_b["tax_wrapper"],
                                    match_type="same_platform_different_wrapper",
                                    matched_identifier=ticker,
                                    confidence=1.0,
                                    reason=f"Same fund ({ticker}) held in {fund_a['tax_wrapper']} and {fund_b['tax_wrapper']} on {platform}",
                                )
                                matches.append(match)

        return matches

    def analyze(self) -> tuple[list[CrossReferenceMatch], list[CrossReferenceMatch], list[str]]:
        """
        Run full cross-reference analysis.

        Returns:
            Tuple of (verified_matches, unsure_matches, funds_without_identifiers)
        """
        logger.info("Starting cross-reference analysis...")

        funds = self._get_fund_identifiers()
        logger.info(f"  Found {len(funds)} fund/platform/wrapper combinations")

        ticker_to_funds, sedol_to_funds, isin_to_funds, _ = self._build_lookup_tables(funds)

        logger.info(f"  {len(ticker_to_funds)} unique tickers")
        logger.info(f"  {len(sedol_to_funds)} unique SEDOLs")
        logger.info(f"  {len(isin_to_funds)} unique ISINs")

        all_matches: list[CrossReferenceMatch] = []
        existing_pairs: set = set()

        # Find ticker matches first (highest priority)
        ticker_matches = self._find_ticker_matches(ticker_to_funds)
        all_matches.extend(ticker_matches)
        for m in ticker_matches:
            existing_pairs.add(tuple(sorted([m.fund_a, m.fund_b])))

        # Find SEDOL matches
        sedol_matches = self._find_sedol_matches(sedol_to_funds, existing_pairs)
        all_matches.extend(sedol_matches)

        # Find ISIN matches
        isin_matches = self._find_isin_matches(isin_to_funds, existing_pairs)
        all_matches.extend(isin_matches)

        # Find same-platform different-wrapper holdings
        wrapper_matches = self._find_same_wrapper_holdings(funds)
        all_matches.extend(wrapper_matches)

        # Partition by confidence threshold
        verified = [m for m in all_matches if m.is_verified]
        unsure = [m for m in all_matches if not m.is_verified]

        # Find funds without any identifiers
        funds_without_ids = [
            f["fund_name"]
            for f in funds
            if not f["ticker"] and not f["tx_sedol"] and not f["map_sedol"] and not f["isin"]
        ]

        logger.info(f"  Found {len(verified)} verified matches (confidence >= 0.90)")
        logger.info(f"  Found {len(unsure)} unsure matches (confidence < 0.90)")
        logger.info(f"  {len(set(funds_without_ids))} funds without identifiers")

        return verified, unsure, list(set(funds_without_ids))

    def close(self) -> None:
        """Close database connection."""
        self.conn.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)-8s | %(message)s",
    )

    with CrossReferenceAnalyzer() as analyzer:
        verified, unsure, no_ids = analyzer.analyze()

        print("\n" + "=" * 60)
        print("CROSS-REFERENCE ANALYSIS")
        print("=" * 60)

        print(f"\nVerified Matches ({len(verified)}):")
        for m in verified:
            print(f"  [{m.confidence:.2f}] {m.match_type}")
            print(f"    {m.fund_a[:40]} ({m.platform_a}/{m.wrapper_a})")
            print(f"    {m.fund_b[:40]} ({m.platform_b}/{m.wrapper_b})")
            print(f"    Reason: {m.reason}")
            print()

        if unsure:
            print(f"\nUnsure Matches - Requires Review ({len(unsure)}):")
            for m in unsure:
                print(f"  [{m.confidence:.2f}] {m.match_type}")
                print(f"    {m.fund_a[:40]} ({m.platform_a}/{m.wrapper_a})")
                print(f"    {m.fund_b[:40]} ({m.platform_b}/{m.wrapper_b})")
                print(f"    Reason: {m.reason}")
                print()

        if no_ids:
            print(f"\nFunds Without Identifiers ({len(no_ids)}):")
            for fund in no_ids[:10]:
                print(f"  - {fund}")
            if len(no_ids) > 10:
                print(f"  ... and {len(no_ids) - 10} more")
