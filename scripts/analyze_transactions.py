#!/usr/bin/env python3
"""
Transaction analysis CLI script.

Performs comprehensive analysis of portfolio transactions including:
- Holding period analysis (FIFO)
- Trading frequency metrics
- Price impact analysis
- Cross-reference matching across platforms

Usage:
    python scripts/analyze_transactions.py
    python scripts/analyze_transactions.py --dry-run
    python scripts/analyze_transactions.py --output reports/my_analysis.md
"""

import argparse
import logging
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from portfolio.analysis.cross_reference import CrossReferenceAnalyzer  # noqa: E402
from portfolio.analysis.current_holdings import CurrentHoldingsAnalyzer  # noqa: E402
from portfolio.analysis.holding_period import HoldingPeriodAnalyzer  # noqa: E402
from portfolio.analysis.models import AnalysisResult  # noqa: E402
from portfolio.analysis.performance import PerformanceAnalyzer  # noqa: E402
from portfolio.analysis.price_impact import PriceImpactAnalyzer  # noqa: E402
from portfolio.analysis.report import ReportGenerator  # noqa: E402
from portfolio.analysis.trading_frequency import TradingFrequencyAnalyzer  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)-8s | %(message)s",
)

logger = logging.getLogger(__name__)


def get_transaction_stats(db_path: Path) -> dict:
    """Get basic transaction statistics."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT
            COUNT(*) as total,
            SUM(CASE WHEN transaction_type = 'BUY' THEN 1 ELSE 0 END) as buys,
            SUM(CASE WHEN transaction_type = 'SELL' THEN 1 ELSE 0 END) as sells,
            MIN(date) as first_date,
            MAX(date) as last_date
        FROM transactions
        WHERE excluded = 0
          AND transaction_type IN ('BUY', 'SELL')
    """
    )

    row = cursor.fetchone()
    conn.close()

    return {
        "total": row["total"],
        "buys": row["buys"],
        "sells": row["sells"],
        "first_date": row["first_date"],
        "last_date": row["last_date"],
    }


def run_analysis(db_path: Path, dry_run: bool = False) -> AnalysisResult:
    """Run complete transaction analysis."""
    logger.info("=" * 60)
    logger.info("TRANSACTION ANALYSIS")
    logger.info("=" * 60)
    logger.info(f"Database: {db_path}")
    logger.info("")

    # Get basic stats
    stats = get_transaction_stats(db_path)
    logger.info(
        f"Total transactions: {stats['total']} ({stats['buys']} BUY, {stats['sells']} SELL)"
    )
    logger.info(f"Date range: {stats['first_date']} to {stats['last_date']}")
    logger.info("")

    if dry_run:
        logger.info("DRY RUN - Analysis preview only")
        logger.info("")

    # Initialize result
    result = AnalysisResult(
        generated_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        data_start_date=stats["first_date"],
        data_end_date=stats["last_date"],
        total_transactions=stats["total"],
        buy_count=stats["buys"],
        sell_count=stats["sells"],
    )

    # 1. Holding Period Analysis
    logger.info("-" * 40)
    logger.info("1. HOLDING PERIOD ANALYSIS")
    logger.info("-" * 40)

    with HoldingPeriodAnalyzer(db_path) as analyzer:
        holdings, hp_summary, hp_issues = analyzer.analyze()
        result.holding_periods = holdings
        result.holding_period_summary = hp_summary
        result.data_quality_notes.extend(hp_issues)

        quick_flips = hp_summary.get("quick_flips_count", 0)
        quick_pct = hp_summary.get("quick_flips_pct", 0)
        logger.info(f"  Holdings analyzed: {len(holdings)}")
        logger.info(f"  Quick flips (<30d): {quick_flips} ({quick_pct:.1f}%)")
        logger.info(f"  Avg holding: {hp_summary.get('avg_holding_days', 0):.0f} days")

    logger.info("")

    # 2. Trading Frequency Analysis
    logger.info("-" * 40)
    logger.info("2. TRADING FREQUENCY ANALYSIS")
    logger.info("-" * 40)

    with TradingFrequencyAnalyzer(db_path) as analyzer:
        by_fund, by_platform, by_wrapper, monthly = analyzer.analyze()
        result.frequency_by_fund = by_fund
        result.frequency_by_platform = by_platform
        result.frequency_by_wrapper = by_wrapper
        result.monthly_pattern = monthly

        logger.info(f"  Unique funds: {len(by_fund)}")
        logger.info(
            f"  Peak month: {monthly.get('peak_month')} ({monthly.get('peak_month_trades')} trades)"
        )
        logger.info(f"  Avg trades/month: {monthly.get('avg_trades_per_month', 0):.2f}")

    logger.info("")

    # 3. Price Impact Analysis
    logger.info("-" * 40)
    logger.info("3. PRICE IMPACT ANALYSIS")
    logger.info("-" * 40)

    with PriceImpactAnalyzer(db_path) as analyzer:
        impacts, pi_summary, missing_prices = analyzer.analyze()
        result.price_impacts = impacts
        result.price_impact_summary = pi_summary
        result.transactions_missing_prices = missing_prices

        favorable_pct = pi_summary.get("favorable_pct", 0)
        net_impact = pi_summary.get("net_impact", 0)
        logger.info(f"  Transactions with prices: {len(impacts)}")
        logger.info(f"  Favorable trades: {favorable_pct:.1f}%")
        logger.info(f"  Net impact: £{net_impact:,.2f}")

    logger.info("")

    # 4. Cross-Reference Analysis
    logger.info("-" * 40)
    logger.info("4. CROSS-REFERENCE MATCHING")
    logger.info("-" * 40)

    with CrossReferenceAnalyzer(db_path) as analyzer:
        verified, unsure, no_ids = analyzer.analyze()
        result.verified_matches = verified
        result.unsure_matches = unsure
        result.funds_without_ticker = no_ids

        logger.info(f"  Verified matches: {len(verified)}")
        logger.info(f"  Unsure matches: {len(unsure)}")
        logger.info(f"  Funds without IDs: {len(no_ids)}")

    logger.info("")

    # 5. Current Holdings Analysis
    logger.info("-" * 40)
    logger.info("5. CURRENT HOLDINGS (UNREALIZED GAINS)")
    logger.info("-" * 40)

    with CurrentHoldingsAnalyzer(db_path) as analyzer:
        holdings, ch_summary = analyzer.analyze()
        result.current_holdings = holdings
        result.current_holdings_summary = ch_summary

        total_value = ch_summary.get("total_current_value", 0)
        total_gain = ch_summary.get("total_unrealized_gain", 0)
        total_gain_pct = ch_summary.get("total_unrealized_gain_pct", 0)
        logger.info(f"  Holdings analyzed: {len(holdings)}")
        logger.info(f"  Total value: £{total_value:,.2f}")
        logger.info(f"  Unrealized gain: £{total_gain:,.2f} ({total_gain_pct:+.1f}%)")

    logger.info("")

    # 6. Performance Analysis (TWR/MWR with Benchmarks)
    logger.info("-" * 40)
    logger.info("6. PERFORMANCE ANALYSIS (TWR/MWR)")
    logger.info("-" * 40)

    with PerformanceAnalyzer(db_path) as analyzer:
        perf_results, perf_summary = analyzer.analyze()

        # Merge performance data into current holdings
        perf_lookup = {}
        for pr in perf_results:
            key = (pr.ticker, pr.platform, pr.tax_wrapper)
            perf_lookup[key] = pr

        for h in result.current_holdings:
            key = (h.ticker, h.platform, h.tax_wrapper)
            if key in perf_lookup:
                pr = perf_lookup[key]
                h.twr = pr.twr
                h.mwr = pr.mwr
                h.holding_period_days = pr.holding_period_days
                # Add benchmark returns
                if "VWRL.L" in pr.benchmarks:
                    h.benchmark_vwrl = pr.benchmarks["VWRL.L"].return_pct
                if "VUSA.L" in pr.benchmarks:
                    h.benchmark_vusa = pr.benchmarks["VUSA.L"].return_pct
                if "VFEM.L" in pr.benchmarks:
                    h.benchmark_vfem = pr.benchmarks["VFEM.L"].return_pct
                if "VUKE.L" in pr.benchmarks:
                    h.benchmark_vuke = pr.benchmarks["VUKE.L"].return_pct
                if "IJPN.L" in pr.benchmarks:
                    h.benchmark_ijpn = pr.benchmarks["IJPN.L"].return_pct

        # Store performance summary for report
        result.performance_summary = perf_summary

        logger.info(
            f"  Holdings with TWR: {len([h for h in result.current_holdings if h.twr is not None])}"
        )
        logger.info(
            f"  Holdings with MWR: {len([h for h in result.current_holdings if h.mwr is not None])}"
        )

    logger.info("")

    # Calculate overall confidence
    result.calculate_overall_confidence()
    logger.info("-" * 40)
    logger.info(f"OVERALL CONFIDENCE: {result.overall_confidence:.2f}")
    logger.info("-" * 40)

    return result


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Analyze portfolio transactions",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python scripts/analyze_transactions.py
    python scripts/analyze_transactions.py --dry-run
    python scripts/analyze_transactions.py --output reports/analysis.md
        """,
    )
    parser.add_argument(
        "--db-path",
        default="portfolio.db",
        help="Path to SQLite database (default: portfolio.db)",
    )
    parser.add_argument(
        "--output",
        "-o",
        default=None,
        help="Output file path (default: reports/transaction_analysis_YYYYMMDD.md)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview analysis without generating report",
    )

    args = parser.parse_args()

    db_path = Path(args.db_path)
    if not db_path.exists():
        logger.error(f"Database not found: {db_path}")
        sys.exit(1)

    # Run analysis
    result = run_analysis(db_path, dry_run=args.dry_run)

    if args.dry_run:
        logger.info("")
        logger.info("Dry run complete. Use without --dry-run to generate report.")
        sys.exit(0)

    # Generate report
    output_path = args.output
    if output_path is None:
        date_str = datetime.now().strftime("%Y%m%d")
        output_path = f"reports/transaction_analysis_{date_str}.md"

    output_path = Path(output_path)

    logger.info("")
    logger.info("=" * 60)
    logger.info("GENERATING REPORT")
    logger.info("=" * 60)

    generator = ReportGenerator(result)
    saved_path = generator.save(output_path)

    logger.info(f"Report saved to: {saved_path}")
    logger.info("")
    logger.info("=" * 60)
    logger.info("ANALYSIS COMPLETE")
    logger.info("=" * 60)

    # Print summary
    print()
    print("Summary:")
    print(f"  - Holding periods analyzed: {len(result.holding_periods)}")
    print(
        f"  - Quick flips (<30 days): {result.holding_period_summary.get('quick_flips_count', 0)}"
    )
    print(f"  - Price impacts analyzed: {len(result.price_impacts)}")
    print(f"  - Verified cross-references: {len(result.verified_matches)}")
    print(f"  - Items needing review: {len(result.unsure_matches)}")
    print(f"  - Overall confidence: {result.overall_confidence:.2f}")
    print()
    print(f"Report: {saved_path}")


if __name__ == "__main__":
    main()
