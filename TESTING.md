# Unit Testing Guide and Coverage Report

## Overview

This document tracks the unit testing suite for the finance-analysis project. The project aims for **80%+ code coverage** with comprehensive unit tests for critical business logic, data transformations, and parsing functions.

- **Framework**: pytest 9.0.2+
- **Coverage Tool**: pytest-cov 7.0.0+
- **Target Coverage**: 80%
- **Current Coverage**: 15% (77 tests passing, need to fix test signatures for remaining modules)

## Running Tests

### Run all tests with coverage
```bash
pytest tests/ -v --cov
```

### Run with detailed coverage report
```bash
pytest tests/ -v --cov --cov-report=html --cov-report=term-missing
```

### Run specific test file
```bash
pytest tests/test_helpers.py -v
```

### Run specific test class or method
```bash
pytest tests/test_helpers.py::TestParseDate::test_parse_date_dd_mm_yyyy_format -v
```

### Run with markers
```bash
pytest tests/ -m unit  # Only unit tests
pytest tests/ -m integration  # Only integration tests
```

## Test Coverage by Module

| Module | Tests | Pass | Fail | Coverage | Status | Critical Functions |
|--------|-------|------|------|----------|--------|-------------------|
| `portfolio/utils/helpers.py` | 69 | ✅ 69 | ❌ 0 | 77% | ✅ Complete | 7/7 functions |
| `portfolio/core/database.py` | 29 | ⏳ 15 | ❌ 14 | 39% | 🔄 In Progress | 7/19 methods |
| `portfolio/utils/calculators.py` | 16 | ❌ 0 | ❌ 16 | 36% | 🔄 In Progress | 0/8 methods |
| `portfolio/loaders/` | 0 | - | - | ~25% | 📋 Pending | 0/8 methods |
| `app/data/queries.py` | 0 | - | - | 0% | 📋 Pending | 0/5 functions |
| `portfolio/core/models.py` | 0 | - | - | 70% | 📋 Pending | 0/4 properties |
| `scripts/update_prices.py` | 0 | - | - | 0% | 📋 Pending | 0/5 functions |
| `scripts/validate_database.py` | 0 | - | - | 0% | 📋 Pending | 0/4 functions |

**Overall**: 114 tests, 77 passing (67%), coverage 15%

## Test Organization

```
tests/
├── conftest.py                 # Shared fixtures
├── fixtures/
│   ├── test_data.py           # Test constants and data
│   └── sample_csvs/
│       ├── fidelity_sample.csv
│       ├── ii_sample.csv
│       └── ie_sample.csv
├── test_helpers.py            # ✅ 69 tests - PASSING
├── test_database.py           # 29 tests - 15 passing, 14 need signature fixes
├── test_calculators.py        # 16 tests - need signature fixes
├── test_models.py             # 📋 Pending
├── test_queries.py            # 📋 Pending
├── test_update_prices.py      # 📋 Pending
├── test_validate_database.py  # 📋 Pending
└── loaders/
    ├── test_fidelity_loader.py    # 📋 Pending
    ├── test_ii_loader.py          # 📋 Pending
    └── test_ie_loader.py          # 📋 Pending
```

## Test Categories

### Tier 1: Critical Business Logic (Must Have)

**Status**: 🔄 **In Progress** - 77/~50 tests complete

These tests ensure core functionality and data integrity:

1. **Data Parsing** ✅
   - Date parsing (6 formats) - 12 tests
   - Money parsing (symbols, negatives, commas) - 14 tests
   - Price parsing (pence vs pounds) - 12 tests
   - Quantity parsing - 11 tests
   - Fund name normalisation - 11 tests
   - Date arithmetic - 8 tests
   - CSV file discovery - 7 tests

2. **Database Operations** 🔄
   - Transaction insertion (single, batch, duplicates) - 5 tests passing
   - Fund-based queries (exact, partial, date range) - 5 tests passing
   - Price history management - 3 tests (need fixes)
   - Ticker mapping operations - 5 tests (need fixes)
   - Utility methods - 5 tests (need fixes)

3. **Financial Calculations** 🔄
   - Return calculations - 16 tests (need signature fixes)
   - MWRR/IRR computations - pending
   - Annualised returns - pending

### Tier 2: Important Functions

**Status**: 📋 Pending (~30 tests needed)

1. Price Update Logic
2. Fund Mapping Status
3. Transaction Aggregations
4. Database Validation

### Tier 3: Supporting Functions

**Status**: 📋 Pending (~15 tests needed)

1. Chart Data Preparation
2. Model Serialization
3. Display Formatting

## Fixtures

### Database Fixtures
- `in_memory_db`: Fresh SQLite database for each test
- `populated_db`: Pre-populated with sample transactions and prices

### Transaction Fixtures
- `sample_transaction`: Single transaction object
- `sample_transactions_list`: List of transaction objects

### CSV Fixtures
- `fidelity_csv_sample`: Sample Fidelity CSV data
- `ii_csv_sample`: Sample Interactive Investor CSV data
- `ie_csv_sample`: Sample InvestEngine CSV data

### API Mocks
- `mock_yfinance_ticker`: Mocked yfinance Ticker
- `mock_yfinance_forex`: Mocked forex pricing
- `patch_yfinance_ticker`: Patched yfinance.Ticker constructor

### Data Fixtures
- `sample_price_dataframe`: Sample OHLC price data
- `sample_holdings_dataframe`: Sample holdings data
- `sample_current_holdings_json`: Sample current holdings JSON

## Known Issues & Fixes Needed

### Issue 1: Transaction Class Signature Mismatch
**Status**: 🔴 Needs fixing
- **Problem**: Tests use `amount` and `mapped_fund_name` parameters that don't exist
- **Actual Fields**: `price_per_unit`, `value`, `currency`, `sedol`, `reference`
- **Files Affected**: `test_database.py`, `test_calculators.py`
- **Fix**: Update test fixtures to use correct Transaction initialization

### Issue 2: ReturnCalculator Signature Mismatch
**Status**: 🔴 Needs fixing
- **Problem**: Tests pass dict/summary instead of CashFlow list
- **Actual Signature**: `__init__(self, cash_flows: list[CashFlow], current_value: float)`
- **Files Affected**: `test_calculators.py`
- **Fix**: Create CashFlow objects or use portfolio.core.models.PortfolioSummary

### Issue 3: Database Price History Signature
**Status**: 🔴 Needs fixing
- **Problem**: Tests use `insert_price_history(ticker, date, price)`
- **Actual Method**: Likely requires different parameter order
- **Files Affected**: `test_database.py`
- **Fix**: Verify actual method signature and update tests

## Test Data

Test constants are defined in `tests/fixtures/test_data.py`:

```python
# Example test data
TEST_DATE_1 = date(2024, 1, 15)
TEST_FUND_NAME_1 = "Vanguard FTSE All-World Index Fund"
TEST_TICKER_1 = "VWRP.L"
TEST_AMOUNT_1 = Decimal("1000.00")
TEST_UNITS_1 = Decimal("100.00")
TEST_PRICE_1 = Decimal("10.50")
```

## Adding New Tests

### 1. Create Test File
```python
# tests/test_module_name.py
import pytest
from portfolio.module import function_to_test

class TestFunctionName:
    """Test function_to_test."""

    def test_basic_functionality(self):
        """Test basic case."""
        result = function_to_test(input)
        assert result == expected

    def test_edge_case(self):
        """Test edge case."""
        result = function_to_test(edge_input)
        assert result == expected
```

### 2. Use Fixtures
```python
def test_with_fixture(populated_db):
    """Test using database fixture."""
    transactions = populated_db.get_all_transactions()
    assert len(transactions) == 2
```

### 3. Mock External Dependencies
```python
def test_with_mock(mocker):
    """Test with mocked function."""
    mock_fn = mocker.patch('module.external_function')
    mock_fn.return_value = expected_value

    result = function_under_test()
    assert result == expected
```

### 4. Use Date Freezing
```python
from freezegun import freeze_time

@freeze_time("2024-01-15")
def test_with_frozen_date():
    """Test with fixed date."""
    current_date = date.today()
    assert current_date == date(2024, 1, 15)
```

## Coverage Report

### Recent Coverage Run
```
Name                              Stmts   Miss  Cover   Missing
portfolio/utils/helpers.py         111     25    77%    238-267
portfolio/core/database.py         168    102    39%    149-175, 187-197...
portfolio/utils/calculators.py     118     76    36%    37-54, 72-78...
portfolio/core/models.py           128     38    70%    20, 31, 47, 52...
portfolio/loaders/                  ~236   ~190   ~20%   Most loader methods
app/data/queries.py                197    197    0%     All (needs tests)
scripts/                           ~1100  ~1100  0%     All (needs tests)

TOTAL                              2735   2323   15%
```

### HTML Coverage Report
Generate detailed coverage report:
```bash
pytest --cov --cov-report=html
open htmlcov/index.html
```

## Performance

**Test Execution Time**: ~0.93 seconds (117 tests)

- Average per test: ~8ms
- Database tests: Fastest (in-memory SQLite)
- Parsing tests: Fast (pure functions)
- Mock tests: Fast (no I/O)

## Continuous Integration

### GitHub Actions (Optional - Not Configured)
Add `.github/workflows/tests.yml` to run tests on push/PR:

```yaml
name: Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
        with:
          python-version: '3.10'
      - run: pip install -e ".[dev]"
      - run: pytest --cov
```

## Troubleshooting

### Issue: Import errors when running tests
**Solution**: Ensure `portfolio` package is installed in editable mode:
```bash
uv pip install -e .
```

### Issue: `conftest.py` not being found
**Solution**: Ensure `conftest.py` is in the `tests/` directory (not a subdirectory)

### Issue: Fixtures not available in tests
**Solution**: Check that fixture names match exactly in test function parameters

### Issue: SQLite errors in database tests
**Solution**: Use in-memory database (`:memory:`) instead of file path

## Future Improvements

1. **Add parameterized tests**: Use `pytest.mark.parametrize` for testing multiple inputs
2. **Add performance tests**: Mark slow tests with `@pytest.mark.slow`
3. **Add integration tests**: Create `tests/integration/` for workflow tests
4. **Add CI/CD**: Set up GitHub Actions for automated testing
5. **Add pytest plugins**: Consider `pytest-xdist` for parallel test execution
6. **Increase coverage to 80%+**: Complete pending tests for all modules

## Links

- [pytest documentation](https://docs.pytest.org/)
- [pytest-cov documentation](https://pytest-cov.readthedocs.io/)
- [Coverage.py](https://coverage.readthedocs.io/)
- [freezegun documentation](https://github.com/spulec/freezegun)

---

**Last Updated**: 2026-01-12
**Coverage Status**: 15% (77 tests passing, target 80%)
**Next Steps**: Fix Transaction/ReturnCalculator test signatures, write remaining modules
