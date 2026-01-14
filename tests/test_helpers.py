"""Unit tests for portfolio/utils/helpers.py parsing functions."""

from datetime import date
from pathlib import Path

import pytest

from portfolio.utils.helpers import (
    calculate_years_between,
    find_csv_files,
    normalise_fund_name,
    parse_date,
    parse_money,
    parse_price,
    parse_quantity,
)


class TestParseDate:
    """Test date parsing function."""

    def test_parse_date_dd_mm_yyyy_format(self):
        """Test parsing date in DD/MM/YYYY format."""
        result = parse_date("15/01/2024")
        assert result == date(2024, 1, 15)

    def test_parse_date_dd_mon_yyyy_format(self):
        """Test parsing date in DD Mon YYYY format."""
        result = parse_date("15 Jan 2024")
        assert result == date(2024, 1, 15)

    def test_parse_date_yyyy_mm_dd_format(self):
        """Test parsing date in YYYY-MM-DD format."""
        result = parse_date("2024-01-15")
        assert result == date(2024, 1, 15)

    def test_parse_date_dd_mm_yy_format(self):
        """Test parsing date in DD/MM/YY format."""
        result = parse_date("15/01/24")
        assert result == date(2024, 1, 15)

    def test_parse_date_dd_mm_yyyy_with_timestamp(self):
        """Test parsing date with timestamp (InvestEngine format)."""
        result = parse_date("15/01/24 14:30:45")
        assert result == date(2024, 1, 15)

    def test_parse_date_dd_mm_yyyy_with_dashes(self):
        """Test parsing date with dashes DD-MM-YYYY format."""
        result = parse_date("15-01-2024")
        assert result == date(2024, 1, 15)

    def test_parse_date_with_empty_string(self):
        """Test parsing empty string returns None."""
        result = parse_date("")
        assert result is None

    def test_parse_date_with_none_value(self):
        """Test parsing None value returns None."""
        result = parse_date(None)
        assert result is None

    def test_parse_date_with_whitespace(self):
        """Test parsing date with leading/trailing whitespace."""
        result = parse_date("  15/01/2024  ")
        assert result == date(2024, 1, 15)

    def test_parse_date_with_invalid_format(self):
        """Test parsing invalid date format returns None."""
        result = parse_date("invalid-date-format")
        assert result is None

    def test_parse_date_with_custom_formats(self):
        """Test parsing with custom formats."""
        result = parse_date("01-15-2024", formats=["%m-%d-%Y"])
        assert result == date(2024, 1, 15)

    def test_parse_date_with_custom_format_failure(self):
        """Test custom format fails when format doesn't match."""
        result = parse_date("15/01/2024", formats=["%m-%d-%Y"])
        assert result is None


class TestParseMoney:
    """Test monetary value parsing function."""

    def test_parse_money_with_gbp_symbol(self):
        """Test parsing money with GBP symbol."""
        result = parse_money("£1000.00")
        assert result == 1000.0

    def test_parse_money_with_comma_separator(self):
        """Test parsing money with comma separator."""
        result = parse_money("£1,234.56")
        assert result == 1234.56

    def test_parse_money_with_negative_dash_prefix(self):
        """Test parsing negative money with dash prefix."""
        result = parse_money("-£500.00")
        assert result == -500.0

    def test_parse_money_with_negative_dash_suffix(self):
        """Test parsing negative money with dash suffix."""
        result = parse_money("£-500.00")
        assert result == -500.0

    def test_parse_money_with_float(self):
        """Test parsing float value."""
        result = parse_money(1000.0)
        assert result == 1000.0

    def test_parse_money_with_integer(self):
        """Test parsing integer value."""
        result = parse_money(1000)
        assert result == 1000.0

    def test_parse_money_with_string_no_symbol(self):
        """Test parsing plain numeric string."""
        result = parse_money("1000.00")
        assert result == 1000.0

    def test_parse_money_with_na_string(self):
        """Test parsing 'n/a' returns 0.0."""
        result = parse_money("n/a")
        assert result == 0.0

    def test_parse_money_with_empty_string(self):
        """Test parsing empty string returns 0.0."""
        result = parse_money("")
        assert result == 0.0

    def test_parse_money_with_none_value(self):
        """Test parsing None returns 0.0."""
        result = parse_money(None)
        assert result == 0.0

    def test_parse_money_with_euro_symbol(self):
        """Test parsing money with EUR symbol."""
        result = parse_money("€1000.00")
        assert result == 1000.0

    def test_parse_money_with_dollar_symbol(self):
        """Test parsing money with USD symbol."""
        result = parse_money("$1000.00")
        assert result == 1000.0

    def test_parse_money_with_whitespace(self):
        """Test parsing money with whitespace."""
        result = parse_money("  £1000.00  ")
        assert result == 1000.0

    def test_parse_money_with_invalid_format(self):
        """Test parsing invalid money format returns 0.0."""
        result = parse_money("invalid")
        assert result == 0.0


class TestParsePrice:
    """Test price parsing function."""

    def test_parse_price_pounds_format(self):
        """Test parsing price in pounds."""
        result = parse_price("£10.50")
        assert result == 10.50

    def test_parse_price_pence_format(self):
        """Test parsing price in pence (p suffix)."""
        result = parse_price("162p")
        assert pytest.approx(result, abs=0.01) == 1.62

    def test_parse_price_pence_uppercase_format(self):
        """Test parsing price in pence (uppercase P)."""
        result = parse_price("162P")
        assert pytest.approx(result, abs=0.01) == 1.62

    def test_parse_price_plain_float(self):
        """Test parsing plain float value."""
        result = parse_price(10.50)
        assert result == 10.50

    def test_parse_price_plain_string(self):
        """Test parsing plain numeric string."""
        result = parse_price("10.50")
        assert result == 10.50

    def test_parse_price_with_comma_separator(self):
        """Test parsing price with comma separator."""
        result = parse_price("1,234.56")
        assert result == 1234.56

    def test_parse_price_with_na_string(self):
        """Test parsing 'n/a' returns 0.0."""
        result = parse_price("n/a")
        assert result == 0.0

    def test_parse_price_with_empty_string(self):
        """Test parsing empty string returns 0.0."""
        result = parse_price("")
        assert result == 0.0

    def test_parse_price_with_none_value(self):
        """Test parsing None returns 0.0."""
        result = parse_price(None)
        assert result == 0.0

    def test_parse_price_with_whitespace(self):
        """Test parsing price with whitespace."""
        result = parse_price("  £10.50  ")
        assert result == 10.50

    def test_parse_price_with_invalid_format(self):
        """Test parsing invalid price format returns 0.0."""
        result = parse_price("invalid")
        assert result == 0.0

    def test_parse_price_large_pence_value(self):
        """Test parsing large pence value converts correctly."""
        result = parse_price("10000p")
        assert result == 100.0


class TestParseQuantity:
    """Test quantity/units parsing function."""

    def test_parse_quantity_plain_float(self):
        """Test parsing plain float quantity."""
        result = parse_quantity(100.0)
        assert result == 100.0

    def test_parse_quantity_plain_integer(self):
        """Test parsing plain integer quantity."""
        result = parse_quantity(100)
        assert result == 100.0

    def test_parse_quantity_string_number(self):
        """Test parsing string number."""
        result = parse_quantity("100.00")
        assert result == 100.0

    def test_parse_quantity_with_comma_separator(self):
        """Test parsing quantity with comma separator."""
        result = parse_quantity("1,234.56")
        assert result == 1234.56

    def test_parse_quantity_fractional(self):
        """Test parsing fractional quantity."""
        result = parse_quantity("33.333333")
        assert result == 33.333333

    def test_parse_quantity_with_na_string(self):
        """Test parsing 'n/a' returns 0.0."""
        result = parse_quantity("n/a")
        assert result == 0.0

    def test_parse_quantity_with_empty_string(self):
        """Test parsing empty string returns 0.0."""
        result = parse_quantity("")
        assert result == 0.0

    def test_parse_quantity_with_none_value(self):
        """Test parsing None returns 0.0."""
        result = parse_quantity(None)
        assert result == 0.0

    def test_parse_quantity_with_whitespace(self):
        """Test parsing quantity with whitespace."""
        result = parse_quantity("  100.00  ")
        assert result == 100.0

    def test_parse_quantity_with_invalid_format(self):
        """Test parsing invalid quantity format returns 0.0."""
        result = parse_quantity("invalid")
        assert result == 0.0

    def test_parse_quantity_zero(self):
        """Test parsing zero quantity."""
        result = parse_quantity("0.00")
        assert result == 0.0


class TestNormaliseFundName:
    """Test fund name normalisation function."""

    def test_normalise_fund_name_whitespace_collapse(self):
        """Test collapsing extra whitespace."""
        result = normalise_fund_name("Vanguard  FTSE   All-World")
        assert result == "Vanguard FTSE All-World"

    def test_normalise_fund_name_ws_blue_substitution(self):
        """Test WS BLUE substitution."""
        result = normalise_fund_name("WS BLUE WHALE GROWTH")
        assert result == "WS Blue Whale"

    def test_normalise_fund_name_fundsmith_substitution(self):
        """Test FDSMITH substitution."""
        result = normalise_fund_name("FDSMITH EQ I AC")
        assert result == "Fundsmith"

    def test_normalise_fund_name_scottish_mortgage_substitution(self):
        """Test Scottish Mortgage substitution."""
        result = normalise_fund_name("SCOH MORT")
        assert result == "Scottish Mortgage"

    def test_normalise_fund_name_scottish_mortgage_full_name(self):
        """Test full Scottish Mortgage name substitution."""
        result = normalise_fund_name("SCOTTISH MORTGAGE")
        assert result == "Scottish Mortgage"

    def test_normalise_fund_name_ishares_gold_substitution(self):
        """Test iShares Gold ETF substitution."""
        result = normalise_fund_name("ISHS PHYSETCMD")
        assert result == "iShares Physical Gold"

    def test_normalise_fund_name_polar_cap_tech_substitution(self):
        """Test Polar Capital Tech substitution."""
        result = normalise_fund_name("POLAR CAP TECH")
        assert result == "Polar Capital Technology"

    def test_normalise_fund_name_empty_string(self):
        """Test normalising empty string returns empty string."""
        result = normalise_fund_name("")
        assert result == ""

    def test_normalise_fund_name_no_substitution(self):
        """Test normalising name with no substitution rules."""
        result = normalise_fund_name("Some Random Fund Name")
        assert result == "Some Random Fund Name"

    def test_normalise_fund_name_case_insensitive(self):
        """Test substitution is case-insensitive."""
        result = normalise_fund_name("ws blue whale growth")
        assert result == "WS Blue Whale"

    def test_normalise_fund_name_leading_trailing_whitespace(self):
        """Test stripping leading and trailing whitespace."""
        result = normalise_fund_name("  Vanguard Fund  ")
        assert result == "Vanguard Fund"


class TestCalculateYearsBetween:
    """Test years between dates calculation."""

    def test_calculate_years_between_one_year(self):
        """Test calculation for exactly one year."""
        result = calculate_years_between(date(2023, 1, 1), date(2024, 1, 1))
        assert pytest.approx(result, abs=0.01) == 1.0

    def test_calculate_years_between_two_years(self):
        """Test calculation for two years."""
        result = calculate_years_between(date(2022, 1, 1), date(2024, 1, 1))
        assert pytest.approx(result, abs=0.01) == 2.0

    def test_calculate_years_between_half_year(self):
        """Test calculation for half a year."""
        result = calculate_years_between(date(2024, 1, 1), date(2024, 7, 2))
        assert pytest.approx(result, abs=0.01) == 0.5

    def test_calculate_years_between_three_months(self):
        """Test calculation for three months (quarter year)."""
        result = calculate_years_between(date(2024, 1, 1), date(2024, 4, 1))
        assert pytest.approx(result, abs=0.01) == 0.25

    def test_calculate_years_between_same_date(self):
        """Test calculation for same date returns zero."""
        result = calculate_years_between(date(2024, 1, 1), date(2024, 1, 1))
        assert result == 0.0

    def test_calculate_years_between_leap_year(self):
        """Test calculation across leap year."""
        result = calculate_years_between(date(2023, 1, 1), date(2024, 1, 1))
        assert pytest.approx(result, abs=0.01) == 1.0

    def test_calculate_years_between_one_day(self):
        """Test calculation for one day."""
        result = calculate_years_between(date(2024, 1, 1), date(2024, 1, 2))
        assert pytest.approx(result, abs=0.001) == 1.0 / 365.25

    def test_calculate_years_between_five_years(self):
        """Test calculation for five years."""
        result = calculate_years_between(date(2019, 1, 1), date(2024, 1, 1))
        assert pytest.approx(result, abs=0.01) == 5.0


class TestFindCsvFiles:
    """Test CSV file discovery function."""

    def test_find_csv_files_single_file(self, tmp_path):
        """Test finding single CSV file."""
        csv_file = tmp_path / "data.csv"
        csv_file.write_text("test")

        results = find_csv_files(tmp_path, "*.csv")
        assert len(results) == 1
        assert results[0].name == "data.csv"

    def test_find_csv_files_multiple_files(self, tmp_path):
        """Test finding multiple CSV files."""
        (tmp_path / "data1.csv").write_text("test")
        (tmp_path / "data2.csv").write_text("test")
        (tmp_path / "data3.csv").write_text("test")

        results = find_csv_files(tmp_path, "*.csv")
        assert len(results) == 3

    def test_find_csv_files_with_pattern(self, tmp_path):
        """Test finding files with specific pattern."""
        (tmp_path / "transactions.csv").write_text("test")
        (tmp_path / "data.csv").write_text("test")

        results = find_csv_files(tmp_path, "transaction*.csv")
        assert len(results) == 1
        assert results[0].name == "transactions.csv"

    def test_find_csv_files_empty_directory(self, tmp_path):
        """Test finding files in empty directory."""
        results = find_csv_files(tmp_path, "*.csv")
        assert len(results) == 0

    def test_find_csv_files_nonexistent_directory(self):
        """Test finding files in nonexistent directory."""
        nonexistent = Path("/nonexistent/directory/path")
        results = find_csv_files(nonexistent, "*.csv")
        assert len(results) == 0

    def test_find_csv_files_sorted_by_name(self, tmp_path):
        """Test results are sorted by name."""
        (tmp_path / "z_data.csv").write_text("test")
        (tmp_path / "a_data.csv").write_text("test")
        (tmp_path / "m_data.csv").write_text("test")

        results = find_csv_files(tmp_path, "*.csv")
        names = [f.name for f in results]
        assert names == ["a_data.csv", "m_data.csv", "z_data.csv"]

    def test_find_csv_files_ignores_non_matching_files(self, tmp_path):
        """Test non-matching files are ignored."""
        (tmp_path / "data.csv").write_text("test")
        (tmp_path / "data.txt").write_text("test")
        (tmp_path / "data.json").write_text("test")

        results = find_csv_files(tmp_path, "*.csv")
        assert len(results) == 1
        assert results[0].suffix == ".csv"
