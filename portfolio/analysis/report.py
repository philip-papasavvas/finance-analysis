"""
Markdown report generator for transaction analysis.

Generates a professional analyst-quality report with all findings.
"""

from pathlib import Path

from portfolio.analysis.models import (
    AnalysisResult,
    HoldingPeriodCategory,
)


class ReportGenerator:
    """Generates markdown analysis reports."""

    def __init__(self, result: AnalysisResult):
        """Initialize with analysis result."""
        self.result = result

    def generate(self) -> str:
        """Generate the complete markdown report."""
        sections = [
            self._header(),
            self._executive_summary(),
            self._current_holdings_section(),  # New section for unrealized gains
            self._holding_period_section(),
            self._trading_frequency_section(),
            self._price_impact_section(),
            self._cross_reference_section(),
            self._data_quality_section(),
            self._methodology_section(),
        ]
        return "\n\n".join(sections)

    def _header(self) -> str:
        """Generate report header with table of contents."""
        return f"""# Portfolio Transaction Analysis Report

**Generated:** {self.result.generated_at}
**Data Range:** {self.result.data_start_date} to {self.result.data_end_date}
**Total Transactions Analyzed:** {self.result.total_transactions} ({self.result.buy_count} BUY, {self.result.sell_count} SELL)
**Overall Confidence:** {self.result.overall_confidence:.2f}

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Current Holdings (Unrealized Gains)](#current-holdings-unrealized-gains)
   - [Portfolio Summary](#portfolio-summary)
   - [By Tax Wrapper](#by-tax-wrapper)
   - [Verified Holdings by Platform](#verified-holdings-by-platform-confidence--08)
   - [Items Requiring Review](#items-requiring-review-confidence--08)
3. [Holding Period Analysis](#1-holding-period-analysis)
   - [Summary by Category](#summary-by-category)
   - [Quick Flips (<30 days)](#quick-flips-30-days---top-15)
4. [Trading Frequency Analysis](#2-trading-frequency-analysis)
   - [By Platform](#by-platform)
   - [By Tax Wrapper](#by-tax-wrapper-1)
   - [Top 10 Most Traded Funds](#top-10-most-traded-funds)
   - [Yearly Trading Pattern](#yearly-trading-pattern)
5. [Price Impact Analysis](#3-price-impact-analysis)
6. [Cross-Reference Matches](#4-cross-reference-matches)
7. [Appendix: Data Quality Notes](#appendix-data-quality-notes)
8. [Methodology](#methodology)

---"""

    def _executive_summary(self) -> str:
        """Generate executive summary."""
        hp_summary = self.result.holding_period_summary
        pi_summary = self.result.price_impact_summary

        quick_flips = hp_summary.get("quick_flips_count", 0)
        quick_flips_pct = hp_summary.get("quick_flips_pct", 0)
        avg_holding = hp_summary.get("avg_holding_days", 0)

        favorable_pct = pi_summary.get("favorable_pct", 0)
        net_impact = pi_summary.get("net_impact", 0)

        return f"""## Executive Summary

| Metric | Value | Confidence |
|--------|-------|------------|
| Average Holding Period | {avg_holding:.0f} days | 0.95 |
| Quick Flips (<30 days) | {quick_flips} trades ({quick_flips_pct:.1f}%) | 0.95 |
| Favorable Price Impact | {favorable_pct:.1f}% of trades | 0.85 |
| Net Price Impact | £{net_impact:,.2f} | 0.85 |
| Cross-Platform Matches | {len(self.result.verified_matches)} verified | 0.92 |
| Items Requiring Review | {len(self.result.unsure_matches)} | - |

### Key Findings

1. **Holding Periods**: {self._get_holding_insight()}
2. **Trading Frequency**: {self._get_frequency_insight()}
3. **Price Execution**: {self._get_price_insight()}"""

    def _get_holding_insight(self) -> str:
        """Generate insight about holding periods."""
        summary = self.result.holding_period_summary
        if not summary:
            return "Insufficient data for analysis"

        quick_pct = summary.get("quick_flips_pct", 0)
        if quick_pct > 20:
            return f"High short-term trading activity ({quick_pct:.1f}% of sales within 30 days)"
        elif quick_pct > 10:
            return f"Moderate short-term trading ({quick_pct:.1f}% of sales within 30 days)"
        else:
            return f"Generally long-term focused ({quick_pct:.1f}% quick flips)"

    def _get_frequency_insight(self) -> str:
        """Generate insight about trading frequency."""
        monthly = self.result.monthly_pattern
        if not monthly:
            return "Insufficient data for analysis"

        avg_per_month = monthly.get("avg_trades_per_month", 0)
        if avg_per_month > 10:
            return f"High trading activity (avg {avg_per_month:.1f} trades/month)"
        elif avg_per_month > 5:
            return f"Moderate trading activity (avg {avg_per_month:.1f} trades/month)"
        else:
            return f"Low trading frequency (avg {avg_per_month:.1f} trades/month)"

    def _get_price_insight(self) -> str:
        """Generate insight about price impact."""
        summary = self.result.price_impact_summary
        if not summary:
            return "Insufficient price data for analysis"

        favorable_pct = summary.get("favorable_pct", 0)
        if favorable_pct > 60:
            return f"Strong execution ({favorable_pct:.1f}% favorable trades)"
        elif favorable_pct > 40:
            return f"Mixed execution quality ({favorable_pct:.1f}% favorable trades)"
        else:
            return f"Execution timing could improve ({favorable_pct:.1f}% favorable trades)"

    def _current_holdings_section(self) -> str:
        """Generate current holdings (unrealized gains) section."""
        holdings = self.result.current_holdings
        summary = self.result.current_holdings_summary
        CONFIDENCE_THRESHOLD = 0.8

        if not holdings:
            return """## Current Holdings (Unrealized Gains)

*No current holdings data available. Ensure data/current_holdings.json exists.*

**Note:** This section analyzes still-held positions from the current_holdings.json file."""

        total_value = summary.get("total_current_value", 0)
        total_cost = summary.get("total_cost_basis", 0)
        total_gain = summary.get("total_unrealized_gain", 0)
        total_gain_pct = summary.get("total_unrealized_gain_pct", 0)

        # By wrapper table
        wrapper_rows = []
        for wrapper, data in summary.get("by_wrapper", {}).items():
            gain_pct = (data["gain"] / data["cost"] * 100) if data["cost"] > 0 else 0
            wrapper_rows.append(
                f"| {wrapper} | £{data['value']:,.2f} | £{data['cost']:,.2f} | "
                f"£{data['gain']:,.2f} | {gain_pct:+.1f}% |"
            )
        wrapper_table = "\n".join(wrapper_rows) if wrapper_rows else "| *No data* | - | - | - | - |"

        # Separate high and low confidence holdings
        high_conf = [
            h for h in holdings if h.confidence >= CONFIDENCE_THRESHOLD and h.current_value > 0
        ]
        low_conf = [
            h for h in holdings if h.confidence < CONFIDENCE_THRESHOLD and h.current_value > 0
        ]

        # Group high confidence holdings by platform
        by_platform = {}
        for h in high_conf:
            if h.platform not in by_platform:
                by_platform[h.platform] = []
            by_platform[h.platform].append(h)

        # Generate platform sections
        platform_sections = []
        for platform in sorted(by_platform.keys()):
            platform_holdings = sorted(
                by_platform[platform], key=lambda x: x.current_value, reverse=True
            )
            platform_total = sum(h.current_value for h in platform_holdings)
            platform_cost = sum(h.cost_basis for h in platform_holdings)
            platform_gain = sum(h.unrealized_gain for h in platform_holdings)
            platform_gain_pct = (platform_gain / platform_cost * 100) if platform_cost > 0 else 0

            rows = []
            for h in platform_holdings:
                # Format TWR/MWR
                twr_str = f"{h.twr:+.1f}%" if h.twr is not None else "N/A"
                mwr_str = f"{h.mwr:+.1f}%" if h.mwr is not None else "N/A"
                days_str = f"{h.holding_period_days}" if h.holding_period_days > 0 else "-"

                # Calculate alpha vs All-World benchmark
                alpha_str = "N/A"
                if h.twr is not None and h.benchmark_vwrl is not None:
                    alpha = h.twr - h.benchmark_vwrl
                    alpha_str = f"{alpha:+.1f}%"

                rows.append(
                    f"| {h.fund_name[:30]} | {h.ticker} | {h.tax_wrapper} | "
                    f"£{h.current_value:,.0f} | £{h.cost_basis:,.0f} | "
                    f"{twr_str} | {mwr_str} | {alpha_str} | {days_str} |"
                )

            platform_section = f"""#### {platform}

**Platform Total:** £{platform_total:,.2f} | **Cost:** £{platform_cost:,.2f} | **Gain:** £{platform_gain:,.2f} ({platform_gain_pct:+.1f}%)

| Fund | Ticker | Wrapper | Value | Cost | TWR | MWR | Alpha | Days |
|------|--------|---------|-------|------|-----|-----|-------|------|
{chr(10).join(rows)}"""
            platform_sections.append(platform_section)

        verified_section = (
            "\n\n".join(platform_sections)
            if platform_sections
            else "*No high-confidence holdings found.*"
        )

        # Generate low confidence section for review, grouped by broker and wrapper
        if low_conf:
            # Group by platform, then by wrapper
            by_platform_wrapper = {}
            for h in low_conf:
                key = (h.platform, h.tax_wrapper)
                if key not in by_platform_wrapper:
                    by_platform_wrapper[key] = []
                by_platform_wrapper[key].append(h)

            review_sections = []
            for platform, wrapper in sorted(by_platform_wrapper.keys()):
                holdings_list = sorted(
                    by_platform_wrapper[(platform, wrapper)],
                    key=lambda x: x.current_value,
                    reverse=True,
                )
                section_total = sum(h.current_value for h in holdings_list)

                rows = []
                for h in holdings_list:
                    rows.append(
                        f"| {h.fund_name[:40]} | {h.ticker} | "
                        f"{h.units:,.2f} | £{h.current_value:,.2f} | £{h.cost_basis:,.2f} | "
                        f"{h.confidence:.2f} |"
                    )

                review_sections.append(
                    f"""#### {platform} - {wrapper}

**Section Total:** £{section_total:,.2f}

| Fund | Ticker | Units | Value | Cost | Conf |
|------|--------|-------|-------|------|------|
{chr(10).join(rows)}"""
                )

            review_section = f"""### Items Requiring Review (Confidence < {CONFIDENCE_THRESHOLD})

The following holdings have incomplete cost basis data. Please provide historical buy transactions.

{chr(10).join(review_sections)}"""
        else:
            review_section = ""

        return f"""## Current Holdings (Unrealized Gains)

This section analyzes still-held positions from your current portfolio.

### Portfolio Summary

| Metric | Value |
|--------|-------|
| Total Current Value | £{total_value:,.2f} |
| Total Cost Basis | £{total_cost:,.2f} |
| **Unrealized Gain/Loss** | **£{total_gain:,.2f}** |
| **Unrealized Return** | **{total_gain_pct:+.2f}%** |

### By Tax Wrapper

| Wrapper | Current Value | Cost Basis | Unrealized Gain | Return |
|---------|---------------|------------|-----------------|--------|
{wrapper_table}

### Verified Holdings by Platform (Confidence ≥ {CONFIDENCE_THRESHOLD})

{verified_section}

{review_section}

**Note:** Cost basis calculated using FIFO from transaction history. Only holdings with confidence ≥ {CONFIDENCE_THRESHOLD} are shown in the verified section."""

    def _holding_period_section(self) -> str:
        """Generate holding period analysis section."""
        summary = self.result.holding_period_summary
        holdings = self.result.holding_periods

        if not holdings:
            return """## 1. Holding Period Analysis

*No holding period data available - no complete buy-sell cycles found.*

**Confidence Level:** N/A"""

        # Category breakdown table
        cat_rows = []
        for cat in HoldingPeriodCategory:
            cat_data = summary.get("by_category", {}).get(cat.value, {})
            if cat_data.get("count", 0) > 0:
                cat_rows.append(
                    f"| {cat_data['label']} | {cat_data['count']} | "
                    f"{cat_data['pct_of_total']:.1f}% | "
                    f"{cat_data['avg_gain_loss_pct']:+.2f}% | "
                    f"£{cat_data['total_gain_loss']:,.2f} | "
                    f"{cat_data['flag']} |"
                )

        category_table = "\n".join(cat_rows) if cat_rows else "| *No data* | - | - | - | - | - |"

        # Quick flips detail (deduplicate)
        quick_flips = [h for h in holdings if h.is_quick_flip]
        quick_flips_table = ""
        if quick_flips:
            seen_quick = set()
            quick_rows = []
            for h in sorted(quick_flips, key=lambda x: x.holding_days):
                key = (h.fund_name, h.platform, h.buy_date, h.sell_date, h.holding_days)
                if key not in seen_quick:
                    seen_quick.add(key)
                    quick_rows.append(
                        f"| {h.fund_name[:35]} | {h.platform} | {h.tax_wrapper} | "
                        f"{h.buy_date} | {h.sell_date} | {h.holding_days} | "
                        f"{h.gain_loss_pct:+.2f}% |"
                    )
                if len(quick_rows) >= 15:
                    break
            quick_flips_table = f"""
### Quick Flips (<30 days) - Top 15

| Fund | Platform | Wrapper | Buy Date | Sell Date | Days | Gain/Loss |
|------|----------|---------|----------|-----------|------|-----------|
{chr(10).join(quick_rows)}"""

        return f"""## 1. Holding Period Analysis

### Summary by Category

| Category | Count | % of Total | Avg Gain/Loss | Total Gain/Loss | Flag |
|----------|-------|------------|---------------|-----------------|------|
{category_table}

**Total Holdings Analyzed:** {summary.get('total_holdings_analyzed', 0)}
**Average Holding Period:** {summary.get('avg_holding_days', 0):.0f} days
**Total Realised Gain/Loss:** £{summary.get('total_gain_loss', 0):,.2f}
{quick_flips_table}

**Confidence Level:** 0.95
**Caveats:**
- FIFO (First-In-First-Out) methodology used for lot matching
- Transfers between platforms/wrappers not tracked as sales
- Partial sells consume oldest lots first"""

    def _trading_frequency_section(self) -> str:
        """Generate trading frequency section."""
        by_platform = self.result.frequency_by_platform
        by_wrapper = self.result.frequency_by_wrapper
        by_fund = self.result.frequency_by_fund
        monthly = self.result.monthly_pattern

        # Platform table
        platform_rows = []
        for m in by_platform:
            platform_rows.append(
                f"| {m.platform} | {m.total_trades} | {m.buy_count} | {m.sell_count} | "
                f"{m.first_trade_date} | {m.last_trade_date} |"
            )
        platform_table = (
            "\n".join(platform_rows) if platform_rows else "| *No data* | - | - | - | - | - |"
        )

        # Wrapper table
        wrapper_rows = []
        for m in by_wrapper:
            wrapper_rows.append(
                f"| {m.tax_wrapper} | {m.total_trades} | {m.buy_count} | {m.sell_count} |"
            )
        wrapper_table = "\n".join(wrapper_rows) if wrapper_rows else "| *No data* | - | - | - |"

        # Top funds table
        fund_rows = []
        for m in by_fund[:10]:
            fund_rows.append(
                f"| {m.fund_name[:40]} | {m.ticker or 'N/A'} | {m.total_trades} | "
                f"{m.avg_trades_per_month:.2f} |"
            )
        fund_table = "\n".join(fund_rows) if fund_rows else "| *No data* | - | - | - |"

        # Yearly breakdown
        yearly = monthly.get("yearly", {})
        yearly_rows = []
        for year in sorted(yearly.keys()):
            data = yearly[year]
            yearly_rows.append(f"| {year} | {data['trades']} | {data['buys']} | {data['sells']} |")
        yearly_table = "\n".join(yearly_rows) if yearly_rows else "| *No data* | - | - | - |"

        return f"""## 2. Trading Frequency Analysis

### By Platform

| Platform | Total Trades | Buys | Sells | First Trade | Last Trade |
|----------|--------------|------|-------|-------------|------------|
{platform_table}

### By Tax Wrapper

| Tax Wrapper | Total Trades | Buys | Sells |
|-------------|--------------|------|-------|
{wrapper_table}

### Top 10 Most Traded Funds

| Fund | Ticker | Total Trades | Trades/Month |
|------|--------|--------------|--------------|
{fund_table}

### Yearly Trading Pattern

| Year | Total Trades | Buys | Sells |
|------|--------------|------|-------|
{yearly_table}

**Peak Month:** {monthly.get('peak_month', 'N/A')} ({monthly.get('peak_month_trades', 0)} trades)
**Average Trades/Month:** {monthly.get('avg_trades_per_month', 0):.2f}

**Confidence Level:** 1.00 (direct database counts)"""

    def _price_impact_section(self) -> str:
        """Generate price impact section."""
        summary = self.result.price_impact_summary
        impacts = self.result.price_impacts

        if not impacts:
            return """## 3. Price Impact Analysis

*No price impact data available - transactions could not be matched to market prices.*

**Confidence Level:** N/A"""

        # Summary stats
        by_type = summary.get("by_type", {})
        buy_stats = by_type.get("BUY", {})
        sell_stats = by_type.get("SELL", {})

        return f"""## 3. Price Impact Analysis

### Summary

| Metric | Value |
|--------|-------|
| Transactions Analyzed | {summary.get('total_analyzed', 0)} |
| Missing Price Data | {summary.get('missing_prices', 0)} transactions |
| Average Deviation | {summary.get('avg_deviation_pct', 0):.2f}% |
| Net Impact | £{summary.get('net_impact', 0):,.2f} |

### Classification Breakdown

| Classification | Count | Percentage |
|----------------|-------|------------|
| Favorable | {summary.get('favorable_count', 0)} | {summary.get('favorable_pct', 0):.1f}% |
| Neutral (±0.5%) | {summary.get('neutral_count', 0)} | {summary.get('neutral_pct', 0):.1f}% |
| Unfavorable | {summary.get('unfavorable_count', 0)} | {summary.get('unfavorable_pct', 0):.1f}% |

### By Transaction Type

| Type | Total | Favorable | Unfavorable |
|------|-------|-----------|-------------|
| BUY | {buy_stats.get('count', 0)} | {buy_stats.get('favorable', 0)} | {buy_stats.get('unfavorable', 0)} |
| SELL | {sell_stats.get('count', 0)} | {sell_stats.get('favorable', 0)} | {sell_stats.get('unfavorable', 0)} |

**Confidence Level:** 0.85
**Caveats:**
- Market prices are daily closes; intraday execution prices will differ
- Positive deviation on BUY = paid above market (unfavorable)
- Positive deviation on SELL = sold above market (favorable)
- Currency conversion may affect USD/EUR-denominated funds"""

    def _cross_reference_section(self) -> str:
        """Generate cross-reference section."""
        verified = self.result.verified_matches
        unsure = self.result.unsure_matches

        # Verified matches table
        verified_rows = []
        for m in verified:
            verified_rows.append(
                f"| {m.fund_a[:30]} | {m.platform_a}/{m.wrapper_a} | "
                f"{m.fund_b[:30]} | {m.platform_b}/{m.wrapper_b} | "
                f"{m.match_type} | {m.confidence:.2f} |"
            )
        verified_table = (
            "\n".join(verified_rows)
            if verified_rows
            else "| *No verified matches found* | - | - | - | - | - |"
        )

        # Unsure matches table (requires user review)
        unsure_rows = []
        for m in unsure:
            unsure_rows.append(
                f"| {m.fund_a[:30]} | {m.platform_a}/{m.wrapper_a} | "
                f"{m.fund_b[:30]} | {m.platform_b}/{m.wrapper_b} | "
                f"{m.match_type} | {m.confidence:.2f} | {m.reason[:30]} |"
            )
        unsure_table = (
            "\n".join(unsure_rows)
            if unsure_rows
            else "| *No uncertain matches* | - | - | - | - | - | - |"
        )

        return f"""## 4. Cross-Reference Matches

### Verified Matches (Confidence ≥ 0.90)

These matches are high-confidence identifications of the same underlying fund held across different platforms or tax wrappers.

| Fund A | Location A | Fund B | Location B | Match Type | Confidence |
|--------|------------|--------|------------|------------|------------|
{verified_table}

### Requires Review (Confidence < 0.90)

**ACTION REQUIRED:** Please review these potential matches and confirm or reject.

| Fund A | Location A | Fund B | Location B | Match Type | Confidence | Reason |
|--------|------------|--------|------------|------------|------------|--------|
{unsure_table}

**Note:** Confidence threshold set to 0.90 (strict) as requested."""

    def _data_quality_section(self) -> str:
        """Generate data quality section."""
        notes = self.result.data_quality_notes
        no_ticker = self.result.funds_without_ticker
        missing_prices = self.result.transactions_missing_prices

        notes_text = "\n".join(f"- {note}" for note in notes) if notes else "- No issues detected"

        funds_text = ""
        if no_ticker:
            fund_list = "\n".join(f"  - {f}" for f in no_ticker[:20])
            more_text = f"\n  - ... and {len(no_ticker) - 20} more" if len(no_ticker) > 20 else ""
            funds_text = f"""
### Funds Without Ticker Mapping

These funds cannot be included in price impact analysis:

{fund_list}{more_text}"""

        return f"""## Appendix: Data Quality Notes

### Issues Detected

{notes_text}

### Missing Data

- **Funds without ticker mapping:** {len(no_ticker)}
- **Transactions missing price data:** {missing_prices}
{funds_text}"""

    def _methodology_section(self) -> str:
        """Generate methodology section."""
        return """## Methodology

### Holding Period Analysis
- **Method:** FIFO (First-In-First-Out) lot matching
- **Categories:**
  - Very short-term: <30 days
  - Short-term: 30-89 days
  - Medium-term: 90-364 days
  - Long-term: 365+ days
- **Gain/Loss:** Calculated as (sell_value - buy_value) / buy_value × 100

### Price Impact Analysis
- **Source:** Transaction execution price vs. daily market close
- **Classification:**
  - Favorable: Bought below market OR sold above market
  - Neutral: Within ±0.5% of market
  - Unfavorable: Bought above market OR sold below market

### Cross-Reference Matching
- **Confidence Levels:**
  - 1.00: Ticker + ISIN match
  - 0.98: SEDOL exact match
  - 0.95: Ticker match only
  - 0.92: ISIN match only
  - <0.90: Requires manual review

### Confidence Framework

| Level | Meaning |
|-------|---------|
| 1.00 | Direct database fact (counts, dates) |
| 0.95-0.99 | Strong identifier match |
| 0.90-0.94 | Good match, minor uncertainty |
| 0.85-0.89 | Needs review |
| <0.85 | Low confidence (flagged) |

---

*Report generated by Portfolio Transaction Analyzer*
*Analysis performed with principal analyst methodology*"""

    def save(self, output_path: str | Path) -> Path:
        """Save report to file."""
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        content = self.generate()
        output_path.write_text(content)

        return output_path
