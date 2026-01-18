#!/usr/bin/env python3
"""
Performance Analysis Script

Calculates Time-Weighted Return (TWR) and Money-Weighted Return (MWR/IRR)
for all current holdings.
"""

import argparse
import logging
import sys
from datetime import datetime
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from portfolio.analysis.performance import PerformanceAnalyzer  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def generate_report(results, wrapper_summary, output_path: Path):
    """Generate markdown performance report with benchmark comparisons."""

    lines = [
        "# Portfolio Performance Analysis",
        "",
        f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "",
        "## Summary by Tax Wrapper",
        "",
        "| Wrapper | Value | Invested | Withdrawn | TWR (Ann.) | MWR (Ann.) | Holdings |",
        "|---------|-------|----------|-----------|------------|------------|----------|",
    ]

    for wrapper in ["ISA", "GIA", "SIPP"]:
        if wrapper in wrapper_summary:
            ws = wrapper_summary[wrapper]
            twr_str = f"{ws.twr:+.1f}%" if ws.twr is not None else "N/A"
            mwr_str = f"{ws.mwr:+.1f}%" if ws.mwr is not None else "N/A"
            lines.append(
                f"| {wrapper} | £{ws.current_value:,.0f} | £{ws.total_invested:,.0f} | "
                f"£{ws.total_withdrawn:,.0f} | {twr_str} | {mwr_str} | {ws.num_holdings} |"
            )

    # Total row
    total_value = sum(ws.current_value for ws in wrapper_summary.values())
    total_invested = sum(ws.total_invested for ws in wrapper_summary.values())
    total_withdrawn = sum(ws.total_withdrawn for ws in wrapper_summary.values())

    # Weighted average returns
    valid_twr = [
        (ws.twr, ws.current_value) for ws in wrapper_summary.values() if ws.twr is not None
    ]
    valid_mwr = [
        (ws.mwr, ws.current_value) for ws in wrapper_summary.values() if ws.mwr is not None
    ]

    total_twr = None
    if valid_twr:
        weight_sum = sum(w for _, w in valid_twr)
        if weight_sum > 0:
            total_twr = sum(t * w for t, w in valid_twr) / weight_sum

    total_mwr = None
    if valid_mwr:
        weight_sum = sum(w for _, w in valid_mwr)
        if weight_sum > 0:
            total_mwr = sum(m * w for m, w in valid_mwr) / weight_sum

    twr_str = f"{total_twr:+.1f}%" if total_twr is not None else "N/A"
    mwr_str = f"{total_mwr:+.1f}%" if total_mwr is not None else "N/A"

    lines.append(
        f"| **TOTAL** | **£{total_value:,.0f}** | **£{total_invested:,.0f}** | "
        f"**£{total_withdrawn:,.0f}** | **{twr_str}** | **{mwr_str}** | **{len(results)}** |"
    )

    # Benchmark comparison section
    lines.extend(
        [
            "",
            "## Benchmark Comparison",
            "",
            "Performance vs benchmarks over the weighted-average holding period for each wrapper.",
            "",
            "| Wrapper | TWR | vs All-World | vs S&P 500 | vs EM | vs FTSE100 | vs Japan |",
            "|---------|-----|--------------|------------|-------|------------|----------|",
        ]
    )

    for wrapper in ["ISA", "GIA", "SIPP"]:
        if wrapper in wrapper_summary:
            ws = wrapper_summary[wrapper]
            twr_str = f"{ws.twr:+.1f}%" if ws.twr is not None else "N/A"

            # Get benchmark returns
            vwrl = ws.benchmarks.get("VWRL.L")
            vusa = ws.benchmarks.get("VUSA.L")
            vfem = ws.benchmarks.get("VFEM.L")
            vuke = ws.benchmarks.get("VUKE.L")
            ijpn = ws.benchmarks.get("IJPN.L")

            # Calculate alpha (excess return) vs each benchmark
            if ws.twr is not None:
                vwrl_alpha = (
                    f"{ws.twr - vwrl.return_pct:+.1f}%" if vwrl and vwrl.return_pct else "N/A"
                )
                vusa_alpha = (
                    f"{ws.twr - vusa.return_pct:+.1f}%" if vusa and vusa.return_pct else "N/A"
                )
                vfem_alpha = (
                    f"{ws.twr - vfem.return_pct:+.1f}%" if vfem and vfem.return_pct else "N/A"
                )
                vuke_alpha = (
                    f"{ws.twr - vuke.return_pct:+.1f}%" if vuke and vuke.return_pct else "N/A"
                )
                ijpn_alpha = (
                    f"{ws.twr - ijpn.return_pct:+.1f}%" if ijpn and ijpn.return_pct else "N/A"
                )
            else:
                vwrl_alpha = vusa_alpha = vfem_alpha = vuke_alpha = ijpn_alpha = "N/A"

            lines.append(
                f"| {wrapper} | {twr_str} | {vwrl_alpha} | {vusa_alpha} | {vfem_alpha} | {vuke_alpha} | {ijpn_alpha} |"
            )

    # Add total row for benchmarks
    if total_twr is not None:
        # Get any wrapper's benchmarks for the total comparison (use weighted average approach)
        # We'll use the first wrapper with benchmarks as reference
        sample_benchmarks = None
        for ws in wrapper_summary.values():
            if ws.benchmarks:
                sample_benchmarks = ws.benchmarks
                break

        if sample_benchmarks:
            vwrl = sample_benchmarks.get("VWRL.L")
            vusa = sample_benchmarks.get("VUSA.L")
            vfem = sample_benchmarks.get("VFEM.L")
            vuke = sample_benchmarks.get("VUKE.L")
            ijpn = sample_benchmarks.get("IJPN.L")

            vwrl_alpha = (
                f"{total_twr - vwrl.return_pct:+.1f}%" if vwrl and vwrl.return_pct else "N/A"
            )
            vusa_alpha = (
                f"{total_twr - vusa.return_pct:+.1f}%" if vusa and vusa.return_pct else "N/A"
            )
            vfem_alpha = (
                f"{total_twr - vfem.return_pct:+.1f}%" if vfem and vfem.return_pct else "N/A"
            )
            vuke_alpha = (
                f"{total_twr - vuke.return_pct:+.1f}%" if vuke and vuke.return_pct else "N/A"
            )
            ijpn_alpha = (
                f"{total_twr - ijpn.return_pct:+.1f}%" if ijpn and ijpn.return_pct else "N/A"
            )

            lines.append(
                f"| **TOTAL** | **{twr_str}** | **{vwrl_alpha}** | **{vusa_alpha}** | **{vfem_alpha}** | **{vuke_alpha}** | **{ijpn_alpha}** |"
            )

    lines.extend(
        [
            "",
            "*Positive alpha indicates outperformance vs benchmark. Benchmarks are annualized returns over the same period.*",
            "",
            "### Benchmark Returns (Reference)",
            "",
        ]
    )

    # Show actual benchmark returns for reference
    if wrapper_summary:
        # Use ISA as the reference period (typically longest)
        ref_wrapper = wrapper_summary.get("ISA") or list(wrapper_summary.values())[0]
        if ref_wrapper.benchmarks:
            lines.append("| Benchmark | Ticker | Ann. Return | Period |")
            lines.append("|-----------|--------|-------------|--------|")
            for ticker, bench in ref_wrapper.benchmarks.items():
                if bench.return_pct is not None:
                    lines.append(
                        f"| {bench.name} | {bench.ticker} | {bench.return_pct:+.1f}% | "
                        f"{bench.start_date} to {bench.end_date} |"
                    )

    lines.extend(
        [
            "",
            "## Definitions",
            "",
            "- **TWR (Time-Weighted Return)**: Measures compound growth rate, removing the impact of cash flows. "
            "Best for comparing manager performance against benchmarks.",
            "- **MWR (Money-Weighted Return)**: Internal rate of return accounting for timing and size of investments. "
            "Reflects your actual experience as an investor.",
            "- **Alpha**: Excess return vs benchmark (Portfolio TWR - Benchmark Return).",
            "",
            "---",
            "",
            "## Holdings Detail",
            "",
        ]
    )

    # Group by wrapper
    for wrapper in ["ISA", "GIA", "SIPP"]:
        wrapper_holdings = sorted(
            [r for r in results if r.tax_wrapper == wrapper],
            key=lambda x: x.current_value,
            reverse=True,
        )

        if not wrapper_holdings:
            continue

        lines.extend(
            [
                f"### {wrapper}",
                "",
                "| Fund | Platform | Value | Invested | TWR | MWR | Days Held |",
                "|------|----------|-------|----------|-----|-----|-----------|",
            ]
        )

        for h in wrapper_holdings:
            twr_str = f"{h.twr:+.1f}%" if h.twr is not None else "N/A"
            mwr_str = f"{h.mwr:+.1f}%" if h.mwr is not None else "N/A"
            lines.append(
                f"| {h.fund_name[:35]} | {h.platform[:15]} | £{h.current_value:,.0f} | "
                f"£{h.total_invested:,.0f} | {twr_str} | {mwr_str} | {h.holding_period_days} |"
            )

        lines.append("")

    # Top performers
    lines.extend(
        [
            "---",
            "",
            "## Top Performers (by MWR)",
            "",
            "| Rank | Fund | Wrapper | MWR (Ann.) | Value |",
            "|------|------|---------|------------|-------|",
        ]
    )

    sorted_by_mwr = sorted(
        [r for r in results if r.mwr is not None], key=lambda x: x.mwr, reverse=True
    )[:10]

    for i, h in enumerate(sorted_by_mwr, 1):
        lines.append(
            f"| {i} | {h.fund_name[:30]} | {h.tax_wrapper} | {h.mwr:+.1f}% | £{h.current_value:,.0f} |"
        )

    lines.extend(
        [
            "",
            "---",
            "",
            f"*Report generated {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*",
        ]
    )

    output_path.write_text("\n".join(lines))
    return output_path


def main():
    parser = argparse.ArgumentParser(description="Analyze portfolio performance (TWR/MWR)")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("reports/performance_analysis.md"),
        help="Output report path",
    )
    parser.add_argument(
        "--db",
        type=Path,
        default=Path("portfolio.db"),
        help="Database path",
    )
    args = parser.parse_args()

    logger.info("=" * 60)
    logger.info("PERFORMANCE ANALYSIS (TWR/MWR)")
    logger.info("=" * 60)

    with PerformanceAnalyzer(db_path=args.db) as analyzer:
        results, wrapper_summary = analyzer.analyze()

    logger.info(f"Analyzed {len(results)} holdings")

    # Print summary
    print("\n" + "=" * 60)
    print("PERFORMANCE SUMMARY")
    print("=" * 60)

    for wrapper in ["ISA", "GIA", "SIPP"]:
        if wrapper in wrapper_summary:
            ws = wrapper_summary[wrapper]
            twr_str = f"{ws.twr:+.1f}%" if ws.twr is not None else "N/A"
            mwr_str = f"{ws.mwr:+.1f}%" if ws.mwr is not None else "N/A"
            print(f"\n{wrapper}:")
            print(f"  Value: £{ws.current_value:,.0f}")
            print(f"  TWR (Annualized): {twr_str}")
            print(f"  MWR (Annualized): {mwr_str}")

    # Generate report
    args.output.parent.mkdir(parents=True, exist_ok=True)
    generate_report(results, wrapper_summary, args.output)
    logger.info(f"\nReport saved to: {args.output}")


if __name__ == "__main__":
    main()
