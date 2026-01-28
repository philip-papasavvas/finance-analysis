#!/usr/bin/env python3
"""
Data Quality Review and Fix Script.

Analyzes transaction data quality issues, fixes high-confidence issues,
and creates a review file for lower-confidence issues.
"""

import logging
import sqlite3
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)-8s | %(message)s",
)
logger = logging.getLogger(__name__)

# Confidence threshold for auto-fix
AUTO_FIX_THRESHOLD = 0.90


@dataclass
class DataQualityIssue:
    """Represents a data quality issue."""

    category: str
    description: str
    fund_name: str
    platform: str
    tax_wrapper: str
    confidence: float
    suggested_fix: str
    details: dict

    def to_dict(self) -> dict:
        return {
            "category": self.category,
            "description": self.description,
            "fund_name": self.fund_name,
            "platform": self.platform,
            "tax_wrapper": self.tax_wrapper,
            "confidence": self.confidence,
            "suggested_fix": self.suggested_fix,
            "details": self.details,
        }


# High-confidence ticker mappings that can be auto-fixed
# These are clear matches based on fund name patterns
TICKER_MAPPINGS_HIGH_CONFIDENCE = {
    # Fidelity full names → existing tickers
    "BERKSHIRE HATHAWAY INC, COM USD0.0033 CLASS'B' (BRK.B)": {
        "ticker": "BRK-B",
        "confidence": 0.99,
        "reason": "Ticker symbol in fund name matches BRK-B",
    },
    # InvestEngine simplified names → LSE tickers
    "Vanguard S&P 500": {
        "ticker": "VUAG.L",
        "confidence": 0.95,
        "reason": "InvestEngine S&P 500 fund maps to VUAG.L",
    },
    "Vanguard FTSE All-World": {
        "ticker": "VWRP.L",
        "confidence": 0.95,
        "reason": "InvestEngine All-World fund maps to VWRP.L",
    },
    "Vanguard FTSE Developed Europe Ex-UK": {
        "ticker": "VERG.L",
        "confidence": 0.95,
        "reason": "InvestEngine Europe ex-UK fund maps to VERG.L",
    },
    # Interactive Investor abbreviated names
    "Scottish Mortgage": {
        "ticker": "SMT.L",
        "confidence": 0.95,
        "reason": "Scottish Mortgage Investment Trust",
    },
    "Polar Capital Technology": {
        "ticker": "PCT.L",
        "confidence": 0.92,
        "reason": "Polar Capital Technology Trust PLC",
    },
    "Polar Capital Global Technology I GBP": {
        "ticker": "PCT.L",
        "confidence": 0.92,
        "reason": "Polar Capital Technology Trust PLC",
    },
    "iShares Physical Gold": {
        "ticker": "SGLN.L",
        "confidence": 0.92,
        "reason": "iShares Physical Gold ETC",
    },
    "Invesco Physical Gold": {
        "ticker": "SGLD.L",
        "confidence": 0.92,
        "reason": "Invesco Physical Gold ETC",
    },
    "Invesco Nasdaq 100": {
        "ticker": "EQQQ.L",
        "confidence": 0.92,
        "reason": "Invesco EQQQ Nasdaq-100 UCITS ETF",
    },
    "iShares Global Clean Energy": {
        "ticker": "INRG.L",
        "confidence": 0.92,
        "reason": "iShares Global Clean Energy UCITS ETF",
    },
    "Allianz Technology Trust": {
        "ticker": "ATT.L",
        "confidence": 0.95,
        "reason": "Allianz Technology Trust PLC",
    },
}

# Lower confidence mappings that need user review
TICKER_MAPPINGS_NEEDS_REVIEW = {
    "Vanguard": {
        "ticker": "UNKNOWN",
        "confidence": 0.30,
        "reason": "Abbreviated name - could be multiple Vanguard funds",
    },
    "Baillie Gifford": {
        "ticker": "UNKNOWN",
        "confidence": 0.30,
        "reason": "Abbreviated name - could be multiple Baillie Gifford funds",
    },
    "Fidelity Funds": {
        "ticker": "UNKNOWN",
        "confidence": 0.30,
        "reason": "Abbreviated name - could be multiple Fidelity funds",
    },
    "Fidelity Investment": {
        "ticker": "UNKNOWN",
        "confidence": 0.30,
        "reason": "Abbreviated name - could be multiple Fidelity funds",
    },
    "Legal & General": {
        "ticker": "UNKNOWN",
        "confidence": 0.30,
        "reason": "Abbreviated name - could be multiple L&G funds",
    },
    "M&G Securities": {
        "ticker": "UNKNOWN",
        "confidence": 0.30,
        "reason": "Abbreviated name - could be multiple M&G funds",
    },
    "GAM Star": {
        "ticker": "UNKNOWN",
        "confidence": 0.30,
        "reason": "Abbreviated name - could be multiple GAM funds",
    },
    "AXA Framlington": {
        "ticker": "UNKNOWN",
        "confidence": 0.30,
        "reason": "Abbreviated name - could be multiple AXA funds",
    },
}


class DataQualityAnalyzer:
    """Analyzes and fixes data quality issues."""

    def __init__(self, db_path: str | Path = "portfolio.db"):
        self.db_path = Path(db_path)
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self.issues: list[DataQualityIssue] = []
        self.fixes_applied: list[dict] = []

    def analyze_missing_ticker_mappings(self) -> list[DataQualityIssue]:
        """Find funds without ticker mappings."""
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT DISTINCT t.fund_name, t.platform, t.tax_wrapper, COUNT(*) as tx_count
            FROM transactions t
            LEFT JOIN fund_ticker_mapping ftm ON t.fund_name = ftm.fund_name
            WHERE ftm.fund_name IS NULL
              AND t.excluded = 0
              AND t.transaction_type IN ('BUY', 'SELL')
            GROUP BY t.fund_name, t.platform, t.tax_wrapper
            ORDER BY tx_count DESC
        """
        )

        issues = []
        for row in cursor.fetchall():
            fund_name = row["fund_name"]

            # Check if we have a high-confidence mapping
            if fund_name in TICKER_MAPPINGS_HIGH_CONFIDENCE:
                mapping = TICKER_MAPPINGS_HIGH_CONFIDENCE[fund_name]
                issues.append(
                    DataQualityIssue(
                        category="missing_ticker_mapping",
                        description=f"Fund '{fund_name}' has no ticker mapping",
                        fund_name=fund_name,
                        platform=row["platform"],
                        tax_wrapper=row["tax_wrapper"],
                        confidence=mapping["confidence"],
                        suggested_fix=f"Add mapping: {fund_name} → {mapping['ticker']}",
                        details={
                            "ticker": mapping["ticker"],
                            "reason": mapping["reason"],
                            "tx_count": row["tx_count"],
                        },
                    )
                )
            elif fund_name in TICKER_MAPPINGS_NEEDS_REVIEW:
                mapping = TICKER_MAPPINGS_NEEDS_REVIEW[fund_name]
                issues.append(
                    DataQualityIssue(
                        category="missing_ticker_mapping",
                        description=f"Fund '{fund_name}' needs ticker mapping review",
                        fund_name=fund_name,
                        platform=row["platform"],
                        tax_wrapper=row["tax_wrapper"],
                        confidence=mapping["confidence"],
                        suggested_fix=f"User to provide ticker for: {fund_name}",
                        details={
                            "reason": mapping["reason"],
                            "tx_count": row["tx_count"],
                        },
                    )
                )
            else:
                # Unknown fund - needs manual review
                issues.append(
                    DataQualityIssue(
                        category="missing_ticker_mapping",
                        description=f"Fund '{fund_name}' has no ticker mapping",
                        fund_name=fund_name,
                        platform=row["platform"],
                        tax_wrapper=row["tax_wrapper"],
                        confidence=0.0,
                        suggested_fix="Manual ticker lookup required",
                        details={"tx_count": row["tx_count"]},
                    )
                )

        return issues

    def analyze_unmatched_sells(self) -> list[DataQualityIssue]:
        """Find sells with no matching buys (pre-history purchases)."""
        cursor = self.conn.cursor()
        cursor.execute(
            """
            WITH fund_buys AS (
                SELECT fund_name, platform, tax_wrapper,
                       SUM(units) as total_bought,
                       MIN(date) as first_buy_date
                FROM transactions
                WHERE transaction_type = 'BUY' AND excluded = 0
                GROUP BY fund_name, platform, tax_wrapper
            ),
            fund_sells AS (
                SELECT fund_name, platform, tax_wrapper,
                       SUM(units) as total_sold,
                       MIN(date) as first_sell_date
                FROM transactions
                WHERE transaction_type = 'SELL' AND excluded = 0
                GROUP BY fund_name, platform, tax_wrapper
            )
            SELECT
                s.fund_name,
                s.platform,
                s.tax_wrapper,
                COALESCE(b.total_bought, 0) as bought,
                s.total_sold as sold,
                s.total_sold - COALESCE(b.total_bought, 0) as unmatched_units,
                COALESCE(b.first_buy_date, 'N/A') as first_buy,
                s.first_sell_date as first_sell
            FROM fund_sells s
            LEFT JOIN fund_buys b ON s.fund_name = b.fund_name
                AND s.platform = b.platform
                AND s.tax_wrapper = b.tax_wrapper
            WHERE s.total_sold > COALESCE(b.total_bought, 0) + 0.01
            ORDER BY unmatched_units DESC
        """
        )

        issues = []
        for row in cursor.fetchall():
            # This is a data limitation issue - purchases before history
            issues.append(
                DataQualityIssue(
                    category="unmatched_sells",
                    description=f"Sells exceed recorded buys for {row['fund_name']}",
                    fund_name=row["fund_name"],
                    platform=row["platform"],
                    tax_wrapper=row["tax_wrapper"],
                    confidence=0.85,  # High confidence this is pre-history issue
                    suggested_fix="User to provide historical buy transactions or confirm pre-history purchases",
                    details={
                        "bought": row["bought"],
                        "sold": row["sold"],
                        "unmatched_units": row["unmatched_units"],
                        "first_buy": row["first_buy"],
                        "first_sell": row["first_sell"],
                    },
                )
            )

        return issues

    def apply_high_confidence_fixes(self) -> list[dict]:
        """Apply fixes for issues with confidence > 0.90."""
        cursor = self.conn.cursor()
        fixes = []

        for issue in self.issues:
            if issue.confidence >= AUTO_FIX_THRESHOLD:
                if issue.category == "missing_ticker_mapping":
                    ticker = issue.details.get("ticker")
                    if ticker and ticker != "UNKNOWN":
                        # Check if mapping already exists
                        cursor.execute(
                            "SELECT id FROM fund_ticker_mapping WHERE fund_name = ?",
                            (issue.fund_name,),
                        )
                        if cursor.fetchone() is None:
                            # Add the mapping
                            cursor.execute(
                                """
                                INSERT INTO fund_ticker_mapping
                                (fund_name, ticker, is_auto_mapped)
                                VALUES (?, ?, 1)
                            """,
                                (issue.fund_name, ticker),
                            )
                            fixes.append(
                                {
                                    "action": "added_ticker_mapping",
                                    "fund_name": issue.fund_name,
                                    "ticker": ticker,
                                    "confidence": issue.confidence,
                                    "reason": issue.details.get("reason", ""),
                                }
                            )
                            logger.info(
                                f"  ✓ Added mapping: {issue.fund_name} → {ticker} "
                                f"(confidence: {issue.confidence:.2f})"
                            )

        self.conn.commit()
        self.fixes_applied = fixes
        return fixes

    def run_analysis(self) -> tuple[list[DataQualityIssue], list[dict]]:
        """Run full data quality analysis."""
        logger.info("=" * 60)
        logger.info("DATA QUALITY ANALYSIS")
        logger.info("=" * 60)

        # Collect all issues
        logger.info("\nAnalyzing missing ticker mappings...")
        ticker_issues = self.analyze_missing_ticker_mappings()
        self.issues.extend(ticker_issues)
        logger.info(f"  Found {len(ticker_issues)} funds without ticker mappings")

        logger.info("\nAnalyzing unmatched sells...")
        sell_issues = self.analyze_unmatched_sells()
        self.issues.extend(sell_issues)
        logger.info(f"  Found {len(sell_issues)} funds with sells exceeding buys")

        # Categorize by confidence
        high_conf = [i for i in self.issues if i.confidence >= AUTO_FIX_THRESHOLD]
        low_conf = [i for i in self.issues if i.confidence < AUTO_FIX_THRESHOLD]

        logger.info(f"\nTotal issues: {len(self.issues)}")
        logger.info(f"  High confidence (>= {AUTO_FIX_THRESHOLD}): {len(high_conf)}")
        logger.info(f"  Needs review (< {AUTO_FIX_THRESHOLD}): {len(low_conf)}")

        # Apply high-confidence fixes
        if high_conf:
            logger.info("\nApplying high-confidence fixes...")
            fixes = self.apply_high_confidence_fixes()
            logger.info(f"  Applied {len(fixes)} fixes")

        return self.issues, self.fixes_applied

    def generate_review_file(self, output_path: Path) -> None:
        """Generate a markdown file for user review of low-confidence issues."""
        low_conf = [i for i in self.issues if i.confidence < AUTO_FIX_THRESHOLD]

        if not low_conf:
            logger.info("No low-confidence issues to review.")
            return

        lines = [
            "# Data Quality Issues - User Review Required",
            "",
            f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"**Total Issues:** {len(low_conf)}",
            "",
            "Please review each issue below and provide corrections.",
            "",
            "---",
            "",
        ]

        # Group by category
        categories = {}
        for issue in low_conf:
            if issue.category not in categories:
                categories[issue.category] = []
            categories[issue.category].append(issue)

        for category, issues in categories.items():
            lines.append(f"## {category.replace('_', ' ').title()}")
            lines.append("")

            if category == "missing_ticker_mapping":
                lines.append("| Fund Name | Platform | Transactions | Suggested Action |")
                lines.append("|-----------|----------|--------------|------------------|")
                for issue in sorted(issues, key=lambda x: -issue.details.get("tx_count", 0)):
                    tx_count = issue.details.get("tx_count", "?")
                    lines.append(
                        f"| {issue.fund_name[:50]} | {issue.platform} | {tx_count} | {issue.suggested_fix} |"
                    )

            elif category == "unmatched_sells":
                lines.append(
                    "These funds have more sells than recorded buys, suggesting purchases before your transaction history started."
                )
                lines.append("")
                lines.append(
                    "| Fund | Platform | Wrapper | Bought | Sold | Unmatched | First Sell |"
                )
                lines.append(
                    "|------|----------|---------|--------|------|-----------|------------|"
                )
                for issue in issues:
                    d = issue.details
                    lines.append(
                        f"| {issue.fund_name[:30]} | {issue.platform} | {issue.tax_wrapper} | "
                        f"{d['bought']:.2f} | {d['sold']:.2f} | {d['unmatched_units']:.2f} | {d['first_sell']} |"
                    )

            lines.append("")

        # Add action items section
        lines.extend(
            [
                "---",
                "",
                "## How to Fix",
                "",
                "### Missing Ticker Mappings",
                "For each fund without a ticker, add a mapping to the database:",
                "```sql",
                "INSERT INTO fund_ticker_mapping (fund_name, ticker) VALUES ('Fund Name', 'TICKER');",
                "```",
                "",
                "### Unmatched Sells (Pre-History Purchases)",
                "Option 1: Add historical buy transactions manually",
                "Option 2: Mark as acknowledged (these will have lower holding period confidence)",
                "",
            ]
        )

        output_path.write_text("\n".join(lines))
        logger.info(f"Review file saved to: {output_path}")

    def close(self) -> None:
        self.conn.close()


def main():
    db_path = Path("portfolio.db")
    review_path = Path("reports/data_quality_review.md")

    if not db_path.exists():
        logger.error(f"Database not found: {db_path}")
        sys.exit(1)

    analyzer = DataQualityAnalyzer(db_path)
    issues, fixes = analyzer.run_analysis()

    # Generate review file
    review_path.parent.mkdir(parents=True, exist_ok=True)
    analyzer.generate_review_file(review_path)

    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Total issues found: {len(issues)}")
    print(f"Fixes applied: {len(fixes)}")
    print(f"Issues for review: {len([i for i in issues if i.confidence < AUTO_FIX_THRESHOLD])}")
    print(f"\nReview file: {review_path}")

    analyzer.close()


if __name__ == "__main__":
    main()
