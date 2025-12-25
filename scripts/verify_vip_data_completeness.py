#!/usr/bin/env python3
"""
VIP Holdings Data Completeness Verification Script

Audits VIP holdings for:
- Price history completeness
- Transaction record completeness
- Data gaps and missing dates
- Overall coverage percentage
"""

import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Tuple
import sys

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from portfolio.core.database import TransactionDatabase


class VIPDataVerifier:
    """Verifies data completeness for VIP holdings."""

    def __init__(self, db_path: str = "portfolio.db"):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row

    def close(self):
        """Close database connection."""
        self.conn.close()

    def get_vip_holdings(self) -> List[Dict]:
        """Get all VIP holdings with their metadata."""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT ticker, fund_name, vip
            FROM fund_ticker_mapping
            WHERE vip = 1
            ORDER BY ticker
        """)
        return [dict(row) for row in cursor.fetchall()]

    def get_price_coverage(self, ticker: str) -> Dict:
        """Get price history coverage for a ticker."""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT
                COUNT(DISTINCT date) as data_points,
                MIN(date) as earliest_price,
                MAX(date) as latest_price
            FROM price_history
            WHERE ticker = ?
        """, (ticker,))

        row = cursor.fetchone()
        if row and row['data_points'] > 0:
            earliest = datetime.strptime(row['earliest_price'], '%Y-%m-%d').date()
            latest = datetime.strptime(row['latest_price'], '%Y-%m-%d').date()

            # Calculate expected business days (rough estimate: 5/7 of total days)
            total_days = (latest - earliest).days + 1
            expected_business_days = int(total_days * 5 / 7)

            # Calculate completeness percentage
            completeness = min(100, (row['data_points'] / expected_business_days * 100)) if expected_business_days > 0 else 0

            return {
                'has_data': True,
                'data_points': row['data_points'],
                'earliest': row['earliest_price'],
                'latest': row['latest_price'],
                'expected_days': expected_business_days,
                'completeness_pct': round(completeness, 1)
            }
        else:
            return {
                'has_data': False,
                'data_points': 0,
                'earliest': None,
                'latest': None,
                'expected_days': 0,
                'completeness_pct': 0
            }

    def get_transaction_coverage(self, ticker: str, fund_name: str) -> Dict:
        """Get transaction coverage for a ticker/fund."""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT
                COUNT(DISTINCT id) as transaction_count,
                MIN(date) as earliest_transaction,
                MAX(date) as latest_transaction
            FROM transactions
            WHERE fund_name = ? OR mapped_fund_name = ?
        """, (fund_name, fund_name))

        row = cursor.fetchone()
        if row and row['transaction_count'] > 0:
            return {
                'has_data': True,
                'count': row['transaction_count'],
                'earliest': row['earliest_transaction'],
                'latest': row['latest_transaction']
            }
        else:
            return {
                'has_data': False,
                'count': 0,
                'earliest': None,
                'latest': None
            }

    def identify_price_gaps(self, ticker: str, threshold_days: int = 7) -> List[Tuple[str, str, int]]:
        """Identify gaps in price history larger than threshold_days."""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT date
            FROM price_history
            WHERE ticker = ?
            ORDER BY date
        """, (ticker,))

        dates = [datetime.strptime(row['date'], '%Y-%m-%d').date() for row in cursor.fetchall()]

        gaps = []
        for i in range(len(dates) - 1):
            current = dates[i]
            next_date = dates[i + 1]
            gap_days = (next_date - current).days

            # Only report gaps larger than threshold (accounting for weekends)
            if gap_days > threshold_days:
                gaps.append((current.strftime('%Y-%m-%d'), next_date.strftime('%Y-%m-%d'), gap_days))

        return gaps

    def generate_report(self) -> str:
        """Generate comprehensive data completeness report."""
        vip_holdings = self.get_vip_holdings()

        report_lines = []
        report_lines.append("=" * 100)
        report_lines.append("VIP HOLDINGS DATA COMPLETENESS REPORT")
        report_lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report_lines.append("=" * 100)
        report_lines.append("")

        # Summary statistics
        total_holdings = len(vip_holdings)
        holdings_with_prices = 0
        holdings_with_transactions = 0
        avg_price_completeness = 0

        detailed_results = []

        for holding in vip_holdings:
            ticker = holding['ticker']
            fund_name = holding['fund_name']

            price_data = self.get_price_coverage(ticker)
            transaction_data = self.get_transaction_coverage(ticker, fund_name)
            price_gaps = self.identify_price_gaps(ticker)

            if price_data['has_data']:
                holdings_with_prices += 1
                avg_price_completeness += price_data['completeness_pct']

            if transaction_data['has_data']:
                holdings_with_transactions += 1

            # Overall status
            if price_data['has_data'] and transaction_data['has_data'] and price_data['completeness_pct'] > 90:
                status = "✓ Complete"
            elif price_data['has_data'] and transaction_data['has_data']:
                status = "⚠ Partial"
            elif not transaction_data['has_data']:
                status = "⚠ No Transactions"
            else:
                status = "✗ Incomplete"

            detailed_results.append({
                'ticker': ticker,
                'fund_name': fund_name,
                'price_data': price_data,
                'transaction_data': transaction_data,
                'price_gaps': price_gaps,
                'status': status
            })

        # Calculate averages
        if holdings_with_prices > 0:
            avg_price_completeness = avg_price_completeness / holdings_with_prices

        # Summary section
        report_lines.append("SUMMARY")
        report_lines.append("-" * 100)
        report_lines.append(f"Total VIP Holdings: {total_holdings}")
        report_lines.append(f"Holdings with Price History: {holdings_with_prices}/{total_holdings} ({holdings_with_prices/total_holdings*100:.1f}%)")
        report_lines.append(f"Holdings with Transactions: {holdings_with_transactions}/{total_holdings} ({holdings_with_transactions/total_holdings*100:.1f}%)")
        report_lines.append(f"Average Price Completeness: {avg_price_completeness:.1f}%")
        report_lines.append("")

        # Detailed section
        report_lines.append("DETAILED HOLDINGS ANALYSIS")
        report_lines.append("-" * 100)
        report_lines.append("")

        for result in detailed_results:
            ticker = result['ticker']
            fund_name = result['fund_name']
            price_data = result['price_data']
            transaction_data = result['transaction_data']
            price_gaps = result['price_gaps']
            status = result['status']

            report_lines.append(f"{'─' * 100}")
            report_lines.append(f"Ticker: {ticker}")
            report_lines.append(f"Fund: {fund_name}")
            report_lines.append(f"Status: {status}")
            report_lines.append("")

            # Price history
            report_lines.append("  Price History:")
            if price_data['has_data']:
                report_lines.append(f"    ✓ Has Data: {price_data['data_points']} data points")
                report_lines.append(f"    ✓ Date Range: {price_data['earliest']} to {price_data['latest']}")
                report_lines.append(f"    ✓ Completeness: {price_data['completeness_pct']}% ({price_data['data_points']}/{price_data['expected_days']} expected business days)")

                if price_gaps:
                    report_lines.append(f"    ⚠ Price Gaps Found: {len(price_gaps)} gaps > 7 days")
                    for gap_start, gap_end, gap_days in price_gaps[:5]:  # Show first 5 gaps
                        report_lines.append(f"      • {gap_start} → {gap_end} ({gap_days} days)")
                    if len(price_gaps) > 5:
                        report_lines.append(f"      ... and {len(price_gaps) - 5} more gaps")
                else:
                    report_lines.append("    ✓ No significant gaps found")
            else:
                report_lines.append("    ✗ No price history data")

            report_lines.append("")

            # Transactions
            report_lines.append("  Transaction Records:")
            if transaction_data['has_data']:
                report_lines.append(f"    ✓ Has Data: {transaction_data['count']} transactions")
                report_lines.append(f"    ✓ Date Range: {transaction_data['earliest']} to {transaction_data['latest']}")
            else:
                report_lines.append("    ✗ No transaction records")

            report_lines.append("")

        # Issues summary
        report_lines.append("=" * 100)
        report_lines.append("ISSUES IDENTIFIED")
        report_lines.append("-" * 100)

        # Holdings without transactions
        no_transactions = [r for r in detailed_results if not r['transaction_data']['has_data']]
        if no_transactions:
            report_lines.append("")
            report_lines.append(f"⚠ {len(no_transactions)} VIP holdings have NO transaction records:")
            for r in no_transactions:
                report_lines.append(f"  • {r['ticker']} - {r['fund_name']}")

        # Holdings with low price completeness
        low_completeness = [r for r in detailed_results if r['price_data']['has_data'] and r['price_data']['completeness_pct'] < 80]
        if low_completeness:
            report_lines.append("")
            report_lines.append(f"⚠ {len(low_completeness)} VIP holdings have price completeness < 80%:")
            for r in low_completeness:
                pct = r['price_data']['completeness_pct']
                report_lines.append(f"  • {r['ticker']} - {r['fund_name']} ({pct}%)")

        # Holdings with significant price gaps
        significant_gaps = [r for r in detailed_results if len(r['price_gaps']) > 5]
        if significant_gaps:
            report_lines.append("")
            report_lines.append(f"⚠ {len(significant_gaps)} VIP holdings have significant price gaps (>5 gaps of 7+ days):")
            for r in significant_gaps:
                gap_count = len(r['price_gaps'])
                report_lines.append(f"  • {r['ticker']} - {r['fund_name']} ({gap_count} gaps)")

        if not no_transactions and not low_completeness and not significant_gaps:
            report_lines.append("")
            report_lines.append("✓ No major issues identified!")

        report_lines.append("")
        report_lines.append("=" * 100)
        report_lines.append("END OF REPORT")
        report_lines.append("=" * 100)

        return "\n".join(report_lines)


def main():
    """Main execution function."""
    print("VIP Holdings Data Completeness Verification")
    print("=" * 100)
    print()

    verifier = VIPDataVerifier()

    try:
        report = verifier.generate_report()
        print(report)

        # Also save to file
        report_path = Path("reports") / f"vip_data_completeness_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        report_path.parent.mkdir(exist_ok=True)
        report_path.write_text(report)

        print()
        print(f"Report saved to: {report_path}")

    finally:
        verifier.close()


if __name__ == "__main__":
    main()