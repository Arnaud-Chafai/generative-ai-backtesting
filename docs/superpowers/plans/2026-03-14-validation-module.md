# Validation Module Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement a `validation/` module with three statistical validators (OOS Split, Monte Carlo, Walk-Forward) plus a ValidationSuite orchestrator to detect overfitting in backtested trading strategies.

**Architecture:** Independent validator classes in `validation/`, each returning typed dataclasses from `results.py`. A `ValidationSuite` orchestrator runs all three sequentially. Validators use existing `BacktestRunner` and `ParameterOptimizer` internally.

**Tech Stack:** Python, numpy, pandas, pytest. Existing framework: `core.backtest_runner`, `optimization.optimizer`, `strategies.base_strategy`.

**Specs:** `docs/superpowers/specs/2026-03-14-validation-*-design.md` (5 files)

---

## File Structure

| File | Responsibility |
|------|---------------|
| `validation/__init__.py` | Public exports |
| `validation/results.py` | 5 dataclasses for all validator outputs |
| `validation/monte_carlo.py` | MonteCarloValidator — trade permutation |
| `validation/oos_split.py` | OOSSplitValidator — IS/OOS split |
| `validation/walk_forward.py` | WalkForwardValidator — rolling/anchored windows |
| `validation/validation_suite.py` | ValidationSuite — orchestrator |
| `tests/conftest.py` | DummyStrategy class + synthetic data fixtures |
| `tests/test_validation_results.py` | Tests for dataclasses |
| `tests/test_monte_carlo.py` | Tests for MonteCarloValidator |
| `tests/test_oos_split.py` | Tests for OOSSplitValidator |
| `tests/test_walk_forward.py` | Tests for WalkForwardValidator |
| `tests/test_validation_suite.py` | Tests for ValidationSuite |
| `validation/CLAUDE.md` | Module documentation |

## Dependency Graph

```
Task 1: Foundation (results.py + conftest.py + __init__.py)
   ↓
   ├─ Task 2: Monte Carlo      ─┐
   ├─ Task 3: OOS Split        ─┤ (parallel)
   └─ Task 4: Walk-Forward     ─┘
                                 ↓
                    Task 5: ValidationSuite + Docs
```

Tasks 2, 3, 4 are **independent** and can be executed in parallel after Task 1 completes.

**Parallel safety:** Task 1 pre-populates `validation/__init__.py` with ALL imports (guarded by try/except) so Tasks 2, 3, 4 do NOT need to modify it — avoiding merge conflicts.

---

## Chunk 1: Foundation

### Task 1: Result Dataclasses + Test Fixtures

**Files:**
- Create: `validation/__init__.py`
- Create: `validation/results.py`
- Create: `tests/conftest.py`
- Test: `tests/test_validation_results.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_validation_results.py`:

```python
"""Tests for validation result dataclasses."""
import numpy as np
import pandas as pd
import pytest

from validation.results import (
    OOSResult,
    MonteCarloResult,
    WalkForwardWindow,
    WalkForwardResult,
    ValidationReport,
)


class TestOOSResult:
    def test_instantiation(self):
        result = OOSResult(
            in_sample_metrics={'sharpe_ratio': 1.5, 'ROI': 10.0},
            out_of_sample_metrics={'sharpe_ratio': 0.8, 'ROI': 5.0},
            split_date=pd.Timestamp('2024-06-01'),
            is_size=700,
            oos_size=300,
            degradation={
                'sharpe_ratio': {'is': 1.5, 'oos': 0.8, 'pct_change': -46.7},
            },
        )
        assert result.is_size == 700
        assert result.oos_size == 300
        assert result.split_date == pd.Timestamp('2024-06-01')

    def test_degradation_values(self):
        result = OOSResult(
            in_sample_metrics={}, out_of_sample_metrics={},
            split_date=pd.Timestamp('2024-06-01'),
            is_size=700, oos_size=300,
            degradation={
                'sharpe_ratio': {'is': 2.0, 'oos': 1.0, 'pct_change': -50.0},
            },
        )
        assert result.degradation['sharpe_ratio']['pct_change'] == -50.0


class TestMonteCarloResult:
    def test_instantiation(self):
        n_sim, n_trades = 100, 20
        result = MonteCarloResult(
            original_final_equity=1200.0,
            simulated_equities=np.ones((n_sim, n_trades)) * 1200,
            percentiles={5: 1100, 25: 1150, 50: 1200, 75: 1250, 95: 1300},
            p_value=0.55,
            max_drawdowns=np.ones(n_sim) * 0.05,
            confidence_intervals={
                'final_equity': (1100, 1300),
                'max_drawdown': (0.03, 0.08),
            },
        )
        assert result.original_final_equity == 1200.0
        assert result.simulated_equities.shape == (n_sim, n_trades)
        assert result.p_value == 0.55


class TestWalkForwardResult:
    def test_instantiation(self):
        window = WalkForwardWindow(
            window_id=0,
            is_start=pd.Timestamp('2024-01-01'),
            is_end=pd.Timestamp('2024-04-01'),
            oos_start=pd.Timestamp('2024-04-01'),
            oos_end=pd.Timestamp('2024-06-01'),
            best_params={'lookback': 20},
            is_metrics={'sharpe_ratio': 1.5},
            oos_metrics={'sharpe_ratio': 1.0},
        )
        assert window.window_id == 0
        assert window.best_params == {'lookback': 20}

        result = WalkForwardResult(
            windows=[window],
            oos_combined_metrics={'sharpe_ratio': 1.0},
            efficiency_ratio=0.67,
            param_stability={'lookback': {'values': [20], 'mean': 20, 'std': 0, 'cv': 0}},
        )
        assert result.efficiency_ratio == 0.67
        assert len(result.windows) == 1


class TestValidationReport:
    def test_all_none(self):
        report = ValidationReport(
            oos=None,
            monte_carlo=None,
            walk_forward=None,
            summary={'is_robust': True, 'issues': [], 'scores': {}},
        )
        assert report.oos is None
        assert report.monte_carlo is None
        assert report.walk_forward is None
        assert report.summary['is_robust'] is True

    def test_with_results(self):
        oos = OOSResult(
            in_sample_metrics={}, out_of_sample_metrics={},
            split_date=pd.Timestamp('2024-06-01'),
            is_size=700, oos_size=300, degradation={},
        )
        report = ValidationReport(
            oos=oos, monte_carlo=None, walk_forward=None,
            summary={'is_robust': True, 'issues': [], 'scores': {}},
        )
        assert report.oos is not None
        assert report.monte_carlo is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_validation_results.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'validation'`

- [ ] **Step 3: Create validation directory**

Run: `mkdir validation`

- [ ] **Step 4: Write `validation/results.py`**

```python
"""Dataclasses for validation module results."""
from dataclasses import dataclass
import numpy as np
import pandas as pd


@dataclass
class OOSResult:
    """Results from out-of-sample split validation."""
    in_sample_metrics: dict
    out_of_sample_metrics: dict
    split_date: pd.Timestamp
    is_size: int
    oos_size: int
    degradation: dict  # {metric: {'is': float, 'oos': float, 'pct_change': float}}


@dataclass
class MonteCarloResult:
    """Results from Monte Carlo trade permutation."""
    original_final_equity: float
    simulated_equities: np.ndarray  # (n_simulations, n_trades)
    percentiles: dict  # {5: float, 25: float, 50: float, 75: float, 95: float}
    p_value: float
    max_drawdowns: np.ndarray  # (n_simulations,)
    confidence_intervals: dict  # {'final_equity': (lo, hi), 'max_drawdown': (lo, hi)}


@dataclass
class WalkForwardWindow:
    """Results from a single walk-forward window."""
    window_id: int
    is_start: pd.Timestamp
    is_end: pd.Timestamp
    oos_start: pd.Timestamp
    oos_end: pd.Timestamp
    best_params: dict | None
    is_metrics: dict
    oos_metrics: dict


@dataclass
class WalkForwardResult:
    """Aggregated results from walk-forward validation."""
    windows: list[WalkForwardWindow]
    oos_combined_metrics: dict
    efficiency_ratio: float
    param_stability: dict | None  # {param: {'values', 'mean', 'std', 'cv'}}


@dataclass
class ValidationReport:
    """Consolidated report from all validators."""
    oos: OOSResult | None
    monte_carlo: MonteCarloResult | None
    walk_forward: WalkForwardResult | None
    summary: dict  # {'is_robust': bool, 'issues': list[str], 'scores': dict}
```

- [ ] **Step 5: Write `validation/__init__.py` with ALL imports pre-populated**

This prevents merge conflicts when Tasks 2, 3, 4 run in parallel. Guarded imports so Task 1 can commit before the validators exist.

```python
"""Validation module for detecting overfitting in backtested strategies."""
from .results import (
    OOSResult,
    MonteCarloResult,
    WalkForwardWindow,
    WalkForwardResult,
    ValidationReport,
)

try:
    from .monte_carlo import MonteCarloValidator
except ImportError:
    pass

try:
    from .oos_split import OOSSplitValidator
except ImportError:
    pass

try:
    from .walk_forward import WalkForwardValidator
except ImportError:
    pass

try:
    from .validation_suite import ValidationSuite
except ImportError:
    pass
```

- [ ] **Step 6: Write `tests/conftest.py` with shared fixtures**

```python
"""Shared test fixtures for validation module tests."""
import numpy as np
import pandas as pd
import pytest

from models.enums import SignalType, MarketType
from strategies.base_strategy import BaseStrategy
from utils.timeframe import Timeframe


def create_synthetic_data(n_bars=500, seed=42):
    """Create synthetic OHLCV data with gentle uptrend."""
    np.random.seed(seed)
    dates = pd.date_range('2024-01-01', periods=n_bars, freq='5min')
    trend = np.linspace(100, 120, n_bars)
    noise = np.random.normal(0, 0.5, n_bars)
    close = trend + noise
    open_prices = close + np.random.normal(0, 0.2, n_bars)
    high = np.maximum(open_prices, close) + np.abs(np.random.normal(0, 0.3, n_bars))
    low = np.minimum(open_prices, close) - np.abs(np.random.normal(0, 0.3, n_bars))

    df = pd.DataFrame({
        'Open': open_prices,
        'High': high,
        'Low': low,
        'Close': close,
        'Volume': np.random.uniform(100, 1000, n_bars),
    }, index=dates)
    df.index.name = 'Time'
    return df


class DummyStrategy(BaseStrategy):
    """Test strategy: buys and sells at regular intervals.

    Generates deterministic trades regardless of market conditions.
    Used by validation module tests.

    Args:
        buy_every: bars between each buy signal (default 20)
        hold_bars: bars to hold before selling (default 10)
    """
    def __init__(self, buy_every=20, hold_bars=10, **kwargs):
        super().__init__(
            market=MarketType.CRYPTO,
            symbol=kwargs.pop('symbol', 'BTC'),
            strategy_name='DummyTest',
            timeframe=kwargs.pop('timeframe', Timeframe.M5),
            exchange=kwargs.pop('exchange', 'Binance'),
            initial_capital=kwargs.pop('initial_capital', 1000.0),
            data=kwargs.pop('data', None),
        )
        self.buy_every = buy_every
        self.hold_bars = hold_bars

    def generate_simple_signals(self):
        df = self.market_data
        i = 0
        while i + self.hold_bars < len(df):
            self.create_simple_signal(
                signal_type=SignalType.BUY,
                timestamp=df.index[i],
                price=df['Close'].iloc[i],
                position_size_pct=1.0,
            )
            sell_i = i + self.hold_bars
            self.create_simple_signal(
                signal_type=SignalType.SELL,
                timestamp=df.index[sell_i],
                price=df['Close'].iloc[sell_i],
                position_size_pct=1.0,
            )
            i += self.buy_every
        return self.simple_signals


@pytest.fixture
def synthetic_market_data():
    """500-bar synthetic OHLCV DataFrame with gentle uptrend."""
    return create_synthetic_data(500, seed=42)


@pytest.fixture
def small_market_data():
    """100-bar synthetic data for fast tests."""
    return create_synthetic_data(100, seed=42)


@pytest.fixture
def dummy_strategy_class():
    """Return DummyStrategy class (not instance) for validators."""
    return DummyStrategy


@pytest.fixture
def synthetic_trades_df():
    """DataFrame with known P&L values for Monte Carlo testing."""
    return pd.DataFrame({
        'net_pnl': [10, -5, 15, -3, 8, -7, 12, -4, 20, -6,
                    5, -8, 11, -2, 9, -10, 7, -1, 14, -3],
    })
```

- [ ] **Step 7: Run tests to verify they pass**

Run: `pytest tests/test_validation_results.py -v`
Expected: All 6 tests PASS.

- [ ] **Step 8: Commit**

```bash
git add validation/__init__.py validation/results.py tests/conftest.py tests/test_validation_results.py
git commit -m "feat(validation): add result dataclasses and test fixtures"
```

---

## Chunk 2: Monte Carlo

### Task 2: MonteCarloValidator

**Files:**
- Create: `validation/monte_carlo.py`
- Create: `tests/test_monte_carlo.py`
- Modify: `validation/__init__.py` (add import)

**Spec:** `docs/superpowers/specs/2026-03-14-validation-monte-carlo-design.md`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_monte_carlo.py`:

```python
"""Tests for MonteCarloValidator."""
import numpy as np
import pandas as pd
import pytest

from validation.monte_carlo import MonteCarloValidator


class TestMonteCarloInstantiation:
    def test_basic_creation(self, synthetic_trades_df):
        mc = MonteCarloValidator(synthetic_trades_df, initial_capital=1000.0)
        assert mc.initial_capital == 1000.0

    def test_rejects_empty_dataframe(self):
        with pytest.raises(ValueError, match="at least 2 trades"):
            MonteCarloValidator(pd.DataFrame({'net_pnl': []}))

    def test_rejects_single_trade(self):
        with pytest.raises(ValueError, match="at least 2 trades"):
            MonteCarloValidator(pd.DataFrame({'net_pnl': [10]}))

    def test_rejects_missing_pnl_column(self):
        with pytest.raises(ValueError, match="net_pnl.*net_profit_loss"):
            MonteCarloValidator(pd.DataFrame({'other_col': [1, 2, 3]}))

    def test_detects_net_profit_loss_column(self):
        df = pd.DataFrame({'net_profit_loss': [10, -5, 15]})
        mc = MonteCarloValidator(df, initial_capital=1000.0)
        assert mc.initial_capital == 1000.0


class TestMonteCarloRun:
    def test_deterministic_with_seed(self, synthetic_trades_df):
        mc = MonteCarloValidator(synthetic_trades_df)
        r1 = mc.run(n_simulations=100, seed=42, verbose=False)
        mc2 = MonteCarloValidator(synthetic_trades_df)
        r2 = mc2.run(n_simulations=100, seed=42, verbose=False)
        np.testing.assert_array_equal(r1.simulated_equities, r2.simulated_equities)

    def test_result_shapes(self, synthetic_trades_df):
        mc = MonteCarloValidator(synthetic_trades_df)
        result = mc.run(n_simulations=50, seed=42, verbose=False)
        assert result.simulated_equities.shape == (50, 20)
        assert result.max_drawdowns.shape == (50,)

    def test_percentile_ordering(self, synthetic_trades_df):
        mc = MonteCarloValidator(synthetic_trades_df)
        result = mc.run(n_simulations=500, seed=42, verbose=False)
        assert result.percentiles[5] <= result.percentiles[25]
        assert result.percentiles[25] <= result.percentiles[50]
        assert result.percentiles[50] <= result.percentiles[75]
        assert result.percentiles[75] <= result.percentiles[95]

    def test_p_value_range(self, synthetic_trades_df):
        mc = MonteCarloValidator(synthetic_trades_df)
        result = mc.run(n_simulations=100, seed=42, verbose=False)
        assert 0.0 <= result.p_value <= 1.0

    def test_confidence_intervals_structure(self, synthetic_trades_df):
        mc = MonteCarloValidator(synthetic_trades_df)
        result = mc.run(n_simulations=100, confidence_level=0.95, seed=42, verbose=False)
        assert 'final_equity' in result.confidence_intervals
        assert 'max_drawdown' in result.confidence_intervals
        lo, hi = result.confidence_intervals['final_equity']
        assert lo <= hi

    def test_uniform_trades_all_same_equity(self):
        """All trades +$10: every permutation produces identical equity curve."""
        df = pd.DataFrame({'net_pnl': [10.0] * 20})
        mc = MonteCarloValidator(df, initial_capital=1000.0)
        result = mc.run(n_simulations=100, seed=42, verbose=False)
        # All final equities should be 1000 + 20*10 = 1200
        expected = 1000.0 + 20 * 10.0
        np.testing.assert_allclose(
            result.simulated_equities[:, -1], expected, atol=1e-10
        )

    def test_original_final_equity(self, synthetic_trades_df):
        mc = MonteCarloValidator(synthetic_trades_df, initial_capital=1000.0)
        result = mc.run(n_simulations=50, seed=42, verbose=False)
        expected = 1000.0 + synthetic_trades_df['net_pnl'].sum()
        assert abs(result.original_final_equity - expected) < 1e-10

    def test_max_drawdowns_non_negative(self, synthetic_trades_df):
        mc = MonteCarloValidator(synthetic_trades_df)
        result = mc.run(n_simulations=100, seed=42, verbose=False)
        assert (result.max_drawdowns >= 0).all()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_monte_carlo.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'validation.monte_carlo'`

- [ ] **Step 3: Write `validation/monte_carlo.py`**

```python
"""Monte Carlo validator — tests equity curve robustness via trade permutation."""
import numpy as np
import pandas as pd

from validation.results import MonteCarloResult


class MonteCarloValidator:
    """Validate equity curve robustness by permuting trade order.

    Shuffles the P&L sequence N times to generate a distribution of
    equity curves. If the real result sits comfortably within the
    distribution, the strategy is robust to trade ordering.

    Args:
        trades_df: DataFrame with 'net_pnl' or 'net_profit_loss' column.
        initial_capital: Starting capital for equity curves.
    """

    def __init__(self, trades_df: pd.DataFrame, initial_capital: float = 1000.0):
        # Detect P&L column
        if 'net_pnl' in trades_df.columns:
            self._pnl_col = 'net_pnl'
        elif 'net_profit_loss' in trades_df.columns:
            self._pnl_col = 'net_profit_loss'
        else:
            raise ValueError(
                f"trades_df must have 'net_pnl' or 'net_profit_loss' column. "
                f"Found columns: {list(trades_df.columns)}"
            )

        if len(trades_df) < 2:
            raise ValueError(
                f"trades_df must have at least 2 trades for permutation. "
                f"Got {len(trades_df)}."
            )

        self.trades_df = trades_df
        self.initial_capital = initial_capital

    def run(
        self,
        n_simulations: int = 1000,
        confidence_level: float = 0.95,
        seed: int | None = None,
        verbose: bool = True,
    ) -> MonteCarloResult:
        """Run Monte Carlo permutation analysis.

        Args:
            n_simulations: Number of random permutations.
            confidence_level: For confidence intervals (e.g. 0.95 = 95%).
            seed: Random seed for reproducibility.
            verbose: Print results summary.

        Returns:
            MonteCarloResult with equity distributions and statistics.
        """
        pnl_series = self.trades_df[self._pnl_col].values.astype(float)
        n_trades = len(pnl_series)

        # Original equity curve
        original_equity = self.initial_capital + np.cumsum(pnl_series)
        original_final = float(original_equity[-1])

        # Generate permutations
        rng = np.random.default_rng(seed)
        simulated_equities = np.zeros((n_simulations, n_trades))
        max_drawdowns = np.zeros(n_simulations)

        for i in range(n_simulations):
            shuffled = rng.permutation(pnl_series)
            equity = self.initial_capital + np.cumsum(shuffled)
            simulated_equities[i] = equity

            running_max = np.maximum.accumulate(equity)
            drawdown_pct = np.where(
                running_max > 0,
                (running_max - equity) / running_max,
                0.0,
            )
            max_drawdowns[i] = float(drawdown_pct.max())

        # Statistics
        final_equities = simulated_equities[:, -1]
        percentiles = {
            p: float(np.percentile(final_equities, p))
            for p in [5, 25, 50, 75, 95]
        }

        p_value = float(np.mean(final_equities >= original_final))

        alpha = 1 - confidence_level
        lower_pct = (alpha / 2) * 100
        upper_pct = (1 - alpha / 2) * 100
        confidence_intervals = {
            'final_equity': (
                float(np.percentile(final_equities, lower_pct)),
                float(np.percentile(final_equities, upper_pct)),
            ),
            'max_drawdown': (
                float(np.percentile(max_drawdowns, lower_pct)),
                float(np.percentile(max_drawdowns, upper_pct)),
            ),
        }

        if verbose:
            print(f"\n=== Monte Carlo Validation ({n_simulations} simulations) ===")
            print(f"Original final equity: ${original_final:,.2f}")
            print(f"\nSimulated equity distribution:")
            print(f"  P5:  ${percentiles[5]:,.2f}  |  P25: ${percentiles[25]:,.2f}  |  "
                  f"P50: ${percentiles[50]:,.2f}  |  P75: ${percentiles[75]:,.2f}  |  "
                  f"P95: ${percentiles[95]:,.2f}")
            label = "ROBUST" if p_value > 0.4 else ("ACCEPTABLE" if p_value > 0.2 else "FRAGILE")
            print(f"\np-value: {p_value:.2f} ({label})")
            lo_eq, hi_eq = confidence_intervals['final_equity']
            lo_dd, hi_dd = confidence_intervals['max_drawdown']
            print(f"\n{confidence_level:.0%} Confidence Intervals:")
            print(f"  Final equity: [${lo_eq:,.2f}, ${hi_eq:,.2f}]")
            print(f"  Max drawdown: [{lo_dd:.1%}, {hi_dd:.1%}]")

        return MonteCarloResult(
            original_final_equity=original_final,
            simulated_equities=simulated_equities,
            percentiles=percentiles,
            p_value=p_value,
            max_drawdowns=max_drawdowns,
            confidence_intervals=confidence_intervals,
        )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_monte_carlo.py -v`
Expected: All 12 tests PASS.

- [ ] **Step 5: Run full test suite to check no regressions**

Run: `pytest tests/ -v`
Expected: All existing + new tests PASS.

- [ ] **Step 6: Commit**

```bash
git add validation/monte_carlo.py tests/test_monte_carlo.py
git commit -m "feat(validation): add MonteCarloValidator with trade permutation"
```

---

## Chunk 3: OOS Split

### Task 3: OOSSplitValidator

**Files:**
- Create: `validation/oos_split.py`
- Create: `tests/test_oos_split.py`
- Modify: `validation/__init__.py` (add import)

**Spec:** `docs/superpowers/specs/2026-03-14-validation-oos-split-design.md`

**Note:** This task runs BacktestRunner integration tests. BaseStrategy prints 2 stdout lines on data injection — this is expected noise from the existing framework.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_oos_split.py`:

```python
"""Tests for OOSSplitValidator."""
import pandas as pd
import pytest

from validation.oos_split import OOSSplitValidator


class TestOOSSplitInstantiation:
    def test_rejects_zero_ratio(self, dummy_strategy_class, synthetic_market_data):
        with pytest.raises(ValueError, match="oos_ratio"):
            OOSSplitValidator(
                strategy_class=dummy_strategy_class,
                market_data=synthetic_market_data,
                oos_ratio=0.0,
            )

    def test_rejects_ratio_one(self, dummy_strategy_class, synthetic_market_data):
        with pytest.raises(ValueError, match="oos_ratio"):
            OOSSplitValidator(
                strategy_class=dummy_strategy_class,
                market_data=synthetic_market_data,
                oos_ratio=1.0,
            )

    def test_rejects_insufficient_data(self, dummy_strategy_class):
        tiny_data = pd.DataFrame(
            {'Open': [1]*10, 'High': [2]*10, 'Low': [0.5]*10, 'Close': [1.5]*10, 'Volume': [100]*10},
            index=pd.date_range('2024-01-01', periods=10, freq='5min'),
        )
        tiny_data.index.name = 'Time'
        with pytest.raises(ValueError, match="at least 20"):
            OOSSplitValidator(
                strategy_class=dummy_strategy_class,
                market_data=tiny_data,
                oos_ratio=0.3,
            )


class TestOOSSplitRun:
    def test_split_sizes(self, dummy_strategy_class, synthetic_market_data):
        oos = OOSSplitValidator(
            strategy_class=dummy_strategy_class,
            market_data=synthetic_market_data,
            oos_ratio=0.3,
        )
        result = oos.run(verbose=False)
        assert result.is_size + result.oos_size == len(synthetic_market_data)
        assert result.is_size == int(len(synthetic_market_data) * 0.7)

    def test_split_date_in_range(self, dummy_strategy_class, synthetic_market_data):
        oos = OOSSplitValidator(
            strategy_class=dummy_strategy_class,
            market_data=synthetic_market_data,
            oos_ratio=0.3,
        )
        result = oos.run(verbose=False)
        assert result.split_date >= synthetic_market_data.index[0]
        assert result.split_date <= synthetic_market_data.index[-1]

    def test_metrics_populated(self, dummy_strategy_class, synthetic_market_data):
        oos = OOSSplitValidator(
            strategy_class=dummy_strategy_class,
            market_data=synthetic_market_data,
            oos_ratio=0.3,
        )
        result = oos.run(verbose=False)
        assert 'sharpe_ratio' in result.in_sample_metrics
        assert 'sharpe_ratio' in result.out_of_sample_metrics

    def test_degradation_has_key_metrics(self, dummy_strategy_class, synthetic_market_data):
        oos = OOSSplitValidator(
            strategy_class=dummy_strategy_class,
            market_data=synthetic_market_data,
            oos_ratio=0.3,
        )
        result = oos.run(verbose=False)
        expected_keys = {'sharpe_ratio', 'ROI', 'profit_factor', 'percent_profitable', 'max_drawdown_pct'}
        assert expected_keys.issubset(result.degradation.keys())

    def test_degradation_pct_change_calculation(self, dummy_strategy_class, synthetic_market_data):
        oos = OOSSplitValidator(
            strategy_class=dummy_strategy_class,
            market_data=synthetic_market_data,
            oos_ratio=0.3,
        )
        result = oos.run(verbose=False)
        for metric, vals in result.degradation.items():
            assert 'is' in vals
            assert 'oos' in vals
            assert 'pct_change' in vals
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_oos_split.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'validation.oos_split'`

- [ ] **Step 3: Write `validation/oos_split.py`**

```python
"""Out-of-sample split validator — detects overfitting via IS/OOS comparison."""
import contextlib
import io

import pandas as pd

from core.backtest_runner import BacktestRunner
from validation.results import OOSResult

METRICS_TO_COMPARE = [
    'sharpe_ratio',
    'ROI',
    'profit_factor',
    'percent_profitable',
    'max_drawdown_pct',
]


class OOSSplitValidator:
    """Split data into in-sample and out-of-sample periods.

    Runs independent backtests on each portion and measures degradation
    of key metrics to detect overfitting.

    Args:
        strategy_class: Strategy class (not instance) inheriting BaseStrategy.
        market_data: OHLCV DataFrame with DatetimeIndex.
        oos_ratio: Fraction of data for OOS (0.0-1.0 exclusive).
        **strategy_params: Fixed kwargs for strategy (symbol, timeframe, etc.)
    """

    def __init__(
        self,
        strategy_class: type,
        market_data: pd.DataFrame,
        oos_ratio: float = 0.3,
        **strategy_params,
    ):
        if oos_ratio <= 0.0 or oos_ratio >= 1.0:
            raise ValueError(f"oos_ratio must be in (0.0, 1.0), got {oos_ratio}")
        if len(market_data) < 20:
            raise ValueError(
                f"market_data must have at least 20 rows, got {len(market_data)}"
            )

        self.strategy_class = strategy_class
        self.market_data = market_data
        self.oos_ratio = oos_ratio
        self.strategy_params = strategy_params

    def run(self, verbose: bool = True) -> OOSResult:
        """Execute OOS split validation.

        Args:
            verbose: Print results summary.

        Returns:
            OOSResult with IS/OOS metrics and degradation analysis.
        """
        # Split data
        split_index = int(len(self.market_data) * (1 - self.oos_ratio))
        is_data = self.market_data.iloc[:split_index].copy()
        oos_data = self.market_data.iloc[split_index:].copy()
        split_date = oos_data.index[0]

        # Run IS backtest
        is_metrics = self._run_backtest(is_data)

        # Run OOS backtest
        oos_metrics = self._run_backtest(oos_data)

        # Calculate degradation
        degradation = {}
        for metric in METRICS_TO_COMPARE:
            is_val = is_metrics.get(metric, 0)
            oos_val = oos_metrics.get(metric, 0)
            if abs(is_val) > 1e-10:
                pct_change = (oos_val - is_val) / abs(is_val) * 100
            elif abs(oos_val) > 1e-10:
                pct_change = float('inf')
            else:
                pct_change = 0.0
            degradation[metric] = {
                'is': is_val,
                'oos': oos_val,
                'pct_change': pct_change,
            }

        if verbose:
            print(f"\n=== OOS Split Validation ===")
            print(f"Split date: {split_date}")
            print(f"In-Sample: {len(is_data)} bars | Out-of-Sample: {len(oos_data)} bars\n")
            print(f"{'Metric':<25} {'IS':>10} {'OOS':>10} {'Change':>10}")
            print("-" * 57)
            for metric, vals in degradation.items():
                pct = vals['pct_change']
                pct_str = f"{pct:+.1f}%" if pct != float('inf') else "inf"
                print(f"{metric:<25} {vals['is']:>10.3f} {vals['oos']:>10.3f} {pct_str:>10}")

        return OOSResult(
            in_sample_metrics=is_metrics,
            out_of_sample_metrics=oos_metrics,
            split_date=split_date,
            is_size=len(is_data),
            oos_size=len(oos_data),
            degradation=degradation,
        )

    def _run_backtest(self, data: pd.DataFrame) -> dict:
        """Run a single backtest and return all_metrics dict."""
        try:
            with contextlib.redirect_stdout(io.StringIO()):
                strategy = self.strategy_class(data=data, **self.strategy_params)
                runner = BacktestRunner(strategy)
                runner.run(verbose=False)
            return runner.metrics.all_metrics
        except Exception as e:
            if 'verbose' not in dir(self) or True:
                print(f"  Warning: backtest failed — {e}")
            return {'error': str(e)}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_oos_split.py -v`
Expected: All 8 tests PASS.

- [ ] **Step 5: Run full test suite**

Run: `pytest tests/ -v`
Expected: All tests PASS (no regressions).

- [ ] **Step 6: Commit**

```bash
git add validation/oos_split.py tests/test_oos_split.py
git commit -m "feat(validation): add OOSSplitValidator for IS/OOS comparison"
```

---

## Chunk 4: Walk-Forward

### Task 4: WalkForwardValidator

**Files:**
- Create: `validation/walk_forward.py`
- Create: `tests/test_walk_forward.py`
- Modify: `validation/__init__.py` (add import)

**Spec:** `docs/superpowers/specs/2026-03-14-validation-walk-forward-design.md`

**Important patterns:**
- Suppress stdout from `BaseStrategy.__init__` and `ParameterOptimizer.get_best_params()` using `contextlib.redirect_stdout`
- Valid optimization metrics: `'sharpe_ratio'`, `'roi'`, `'profit_factor'`, `'max_drawdown'`, `'sortino_ratio'`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_walk_forward.py`:

```python
"""Tests for WalkForwardValidator."""
import numpy as np
import pandas as pd
import pytest

from validation.walk_forward import WalkForwardValidator


@pytest.fixture
def tiny_market_data():
    """30-bar dataset too small for 5 windows."""
    np.random.seed(99)
    dates = pd.date_range('2024-01-01', periods=30, freq='5min')
    close = np.linspace(100, 105, 30)
    df = pd.DataFrame({
        'Open': close - 0.1, 'High': close + 0.3,
        'Low': close - 0.3, 'Close': close,
        'Volume': np.ones(30) * 100,
    }, index=dates)
    df.index.name = 'Time'
    return df


class TestWalkForwardInstantiation:
    def test_rejects_one_window(self, dummy_strategy_class, synthetic_market_data):
        with pytest.raises(ValueError, match="n_windows"):
            WalkForwardValidator(
                strategy_class=dummy_strategy_class,
                market_data=synthetic_market_data,
                n_windows=1,
            )

    def test_rejects_zero_windows(self, dummy_strategy_class, synthetic_market_data):
        with pytest.raises(ValueError, match="n_windows"):
            WalkForwardValidator(
                strategy_class=dummy_strategy_class,
                market_data=synthetic_market_data,
                n_windows=0,
            )

    def test_rejects_insufficient_data(self, dummy_strategy_class, tiny_market_data):
        with pytest.raises(ValueError, match="[Ii]nsufficient"):
            WalkForwardValidator(
                strategy_class=dummy_strategy_class,
                market_data=tiny_market_data,
                n_windows=5,
            )

    def test_rejects_invalid_optimization_metric(self, dummy_strategy_class, synthetic_market_data):
        wf = WalkForwardValidator(
            strategy_class=dummy_strategy_class,
            market_data=synthetic_market_data,
            n_windows=2,
        )
        with pytest.raises(ValueError, match="optimization_metric"):
            wf.run(
                param_ranges={'buy_every': [15, 20]},
                optimization_metric='invalid_metric',
                verbose=False,
            )


class TestWalkForwardRolling:
    def test_rolling_fixed_mode(self, dummy_strategy_class, synthetic_market_data):
        wf = WalkForwardValidator(
            strategy_class=dummy_strategy_class,
            market_data=synthetic_market_data,
            n_windows=3,
            oos_ratio=0.25,
            anchored=False,
        )
        result = wf.run(verbose=False)
        assert len(result.windows) == 3
        assert result.param_stability is None  # fixed mode

    def test_rolling_windows_cover_dataset(self, dummy_strategy_class, synthetic_market_data):
        wf = WalkForwardValidator(
            strategy_class=dummy_strategy_class,
            market_data=synthetic_market_data,
            n_windows=3,
            oos_ratio=0.25,
            anchored=False,
        )
        result = wf.run(verbose=False)
        # First window starts at first bar
        assert result.windows[0].is_start == synthetic_market_data.index[0]
        # Last window ends at last bar
        assert result.windows[-1].oos_end == synthetic_market_data.index[-1]
        # No gaps: each window's IS start == previous window's OOS end (next bar)
        for i in range(len(result.windows) - 1):
            curr_oos_end = result.windows[i].oos_end
            next_is_start = result.windows[i + 1].is_start
            # next window starts right after current window ends (1 bar gap max)
            gap = abs((next_is_start - curr_oos_end).total_seconds())
            assert gap <= 600, f"Gap between window {i} and {i+1}: {gap}s (max 600s for 5min bars)"

    def test_efficiency_ratio_calculated(self, dummy_strategy_class, synthetic_market_data):
        wf = WalkForwardValidator(
            strategy_class=dummy_strategy_class,
            market_data=synthetic_market_data,
            n_windows=3,
            oos_ratio=0.25,
        )
        result = wf.run(verbose=False)
        assert isinstance(result.efficiency_ratio, float)

    def test_oos_combined_metrics_populated(self, dummy_strategy_class, synthetic_market_data):
        wf = WalkForwardValidator(
            strategy_class=dummy_strategy_class,
            market_data=synthetic_market_data,
            n_windows=3,
        )
        result = wf.run(verbose=False)
        assert len(result.oos_combined_metrics) > 0


class TestWalkForwardAnchored:
    def test_anchored_is_always_starts_at_zero(self, dummy_strategy_class, synthetic_market_data):
        wf = WalkForwardValidator(
            strategy_class=dummy_strategy_class,
            market_data=synthetic_market_data,
            n_windows=3,
            oos_ratio=0.25,
            anchored=True,
        )
        result = wf.run(verbose=False)
        first_ts = synthetic_market_data.index[0]
        for w in result.windows:
            assert w.is_start == first_ts


class TestWalkForwardOptimization:
    def test_optimization_mode(self, dummy_strategy_class, small_market_data):
        """Test WF with re-optimization. Uses small data + tiny grid for speed."""
        wf = WalkForwardValidator(
            strategy_class=dummy_strategy_class,
            market_data=small_market_data,
            n_windows=2,
            oos_ratio=0.3,
        )
        result = wf.run(
            param_ranges={'buy_every': [15, 20]},
            optimization_metric='sharpe_ratio',
            min_trades=1,
            verbose=False,
        )
        assert len(result.windows) == 2
        # In optimization mode, best_params should be filled
        for w in result.windows:
            assert w.best_params is not None
        # param_stability should be calculated
        assert result.param_stability is not None
        assert 'buy_every' in result.param_stability

    def test_param_stability_has_cv(self, dummy_strategy_class, small_market_data):
        wf = WalkForwardValidator(
            strategy_class=dummy_strategy_class,
            market_data=small_market_data,
            n_windows=2,
            oos_ratio=0.3,
        )
        result = wf.run(
            param_ranges={'buy_every': [15, 20]},
            min_trades=1,
            verbose=False,
        )
        if result.param_stability:
            for param, stats in result.param_stability.items():
                assert 'values' in stats
                assert 'mean' in stats
                assert 'std' in stats
                assert 'cv' in stats
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_walk_forward.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'validation.walk_forward'`

- [ ] **Step 3: Write `validation/walk_forward.py`**

```python
"""Walk-forward validator — tests strategy robustness over rolling time windows."""
import contextlib
import io

import numpy as np
import pandas as pd

from core.backtest_runner import BacktestRunner
from validation.results import WalkForwardWindow, WalkForwardResult

# Note: 'roi' excluded — existing ParameterOptimizer has a key mismatch bug
# (optimizer uses 'roi' but BacktestMetrics returns 'ROI'). Use 'sharpe_ratio' as default.
VALID_OPT_METRICS = {'sharpe_ratio', 'profit_factor', 'max_drawdown', 'sortino_ratio'}


class WalkForwardValidator:
    """Divide data into rolling or anchored windows for IS/OOS validation.

    Supports two modes:
    - Fixed params: test if strategy degrades over time with constant params.
    - Re-optimization: optimize on IS, validate on OOS (classic walk-forward analysis).

    Args:
        strategy_class: Strategy class inheriting BaseStrategy.
        market_data: OHLCV DataFrame with DatetimeIndex.
        n_windows: Number of windows (>= 2).
        oos_ratio: Fraction of each window for OOS (0.0-1.0 exclusive).
        anchored: False=rolling (IS shifts), True=anchored (IS grows from start).
        **strategy_params: Fixed kwargs for strategy.
    """

    def __init__(
        self,
        strategy_class: type,
        market_data: pd.DataFrame,
        n_windows: int = 5,
        oos_ratio: float = 0.25,
        anchored: bool = False,
        **strategy_params,
    ):
        if n_windows < 2:
            raise ValueError(f"n_windows must be >= 2, got {n_windows}")
        if oos_ratio <= 0.0 or oos_ratio >= 1.0:
            raise ValueError(f"oos_ratio must be in (0.0, 1.0), got {oos_ratio}")
        if len(market_data) < n_windows * 20:
            raise ValueError(
                f"Insufficient data: {len(market_data)} bars for {n_windows} windows "
                f"(need at least {n_windows * 20})"
            )

        self.strategy_class = strategy_class
        self.market_data = market_data
        self.n_windows = n_windows
        self.oos_ratio = oos_ratio
        self.anchored = anchored
        self.strategy_params = strategy_params

    def run(
        self,
        param_ranges: dict | None = None,
        optimization_metric: str = 'sharpe_ratio',
        min_trades: int = 10,
        verbose: bool = True,
    ) -> WalkForwardResult:
        """Execute walk-forward validation.

        Args:
            param_ranges: If provided, re-optimize on each IS window.
                          If None, use fixed strategy_params.
            optimization_metric: Metric for optimizer and efficiency ratio.
            min_trades: Minimum trades for optimizer's get_best_params.
            verbose: Print per-window results.

        Returns:
            WalkForwardResult with per-window and aggregated metrics.
        """
        if param_ranges is not None and optimization_metric not in VALID_OPT_METRICS:
            raise ValueError(
                f"optimization_metric must be one of {VALID_OPT_METRICS}, "
                f"got '{optimization_metric}'"
            )

        windows_ranges = self._compute_windows()
        windows = []

        mode_label = "anchored" if self.anchored else "rolling"
        if verbose:
            opt_label = "optimization" if param_ranges else "fixed params"
            print(f"\n=== Walk-Forward Validation ({self.n_windows} windows, {mode_label}, {opt_label}) ===\n")

        for i, (is_start, is_end, oos_start, oos_end) in enumerate(windows_ranges):
            is_data = self.market_data.iloc[is_start:is_end].copy()
            oos_data = self.market_data.iloc[oos_start:oos_end].copy()

            if verbose:
                print(f"Window {i+1}/{self.n_windows}: "
                      f"IS [{is_data.index[0]} -> {is_data.index[-1]}] ({len(is_data)} bars) | "
                      f"OOS [{oos_data.index[0]} -> {oos_data.index[-1]}] ({len(oos_data)} bars)")

            # Determine params for this window
            if param_ranges is not None:
                best_params = self._optimize_window(is_data, param_ranges, optimization_metric, min_trades)
                full_params = {**self.strategy_params, **best_params}
            else:
                best_params = None
                full_params = self.strategy_params

            is_metrics = self._run_single_backtest(is_data, full_params)
            oos_metrics = self._run_single_backtest(oos_data, full_params)

            windows.append(WalkForwardWindow(
                window_id=i,
                is_start=is_data.index[0],
                is_end=is_data.index[-1],
                oos_start=oos_data.index[0],
                oos_end=oos_data.index[-1],
                best_params=best_params if param_ranges else None,
                is_metrics=is_metrics,
                oos_metrics=oos_metrics,
            ))

            if verbose:
                is_score = is_metrics.get(optimization_metric, 0)
                oos_score = oos_metrics.get(optimization_metric, 0)
                params_str = f"  params={best_params}" if best_params else ""
                print(f"  IS {optimization_metric}={is_score:.3f} | "
                      f"OOS {optimization_metric}={oos_score:.3f}{params_str}\n")

        # Aggregate
        valid_windows = [w for w in windows if 'error' not in w.oos_metrics]
        oos_combined_metrics = self._aggregate_oos_metrics(valid_windows)
        efficiency_ratio = self._compute_efficiency(valid_windows, optimization_metric)
        param_stability = self._compute_param_stability(valid_windows, param_ranges)

        if verbose:
            label = "ROBUST" if efficiency_ratio > 0.5 else ("MARGINAL" if efficiency_ratio > 0.3 else "OVERFITTING")
            print(f"Efficiency Ratio: {efficiency_ratio:.2f} ({label})")
            if param_stability:
                print("Param Stability:")
                for param, stats in param_stability.items():
                    cv_label = "STABLE" if stats['cv'] < 0.3 else ("MODERATE" if stats['cv'] < 0.5 else "UNSTABLE")
                    print(f"  {param}: mean={stats['mean']:.2f}, std={stats['std']:.2f}, cv={stats['cv']:.2f} ({cv_label})")

        return WalkForwardResult(
            windows=windows,
            oos_combined_metrics=oos_combined_metrics,
            efficiency_ratio=efficiency_ratio,
            param_stability=param_stability,
        )

    def _compute_windows(self) -> list[tuple[int, int, int, int]]:
        """Compute (is_start, is_end, oos_start, oos_end) index tuples."""
        total = len(self.market_data)
        ranges = []

        if not self.anchored:
            # Rolling: non-overlapping consecutive windows
            window_size = total // self.n_windows
            oos_size = int(window_size * self.oos_ratio)
            is_size = window_size - oos_size

            for i in range(self.n_windows):
                base = i * window_size
                is_start = base
                is_end = base + is_size
                oos_start = is_end
                oos_end = base + window_size
                if i == self.n_windows - 1:
                    oos_end = total  # absorb residue
                ranges.append((is_start, is_end, oos_start, oos_end))
        else:
            # Anchored: IS always starts at 0, grows each window
            oos_total = int(total * self.oos_ratio)
            is_base = total - oos_total
            oos_per_window = oos_total // self.n_windows

            for i in range(self.n_windows):
                is_start = 0
                is_end = is_base + i * oos_per_window
                oos_start = is_end
                oos_end = is_end + oos_per_window
                if i == self.n_windows - 1:
                    oos_end = total
                ranges.append((is_start, is_end, oos_start, oos_end))

        return ranges

    def _optimize_window(self, is_data, param_ranges, metric, min_trades) -> dict:
        """Run ParameterOptimizer on IS data, return best params."""
        from optimization.optimizer import ParameterOptimizer

        with contextlib.redirect_stdout(io.StringIO()):
            optimizer = ParameterOptimizer(
                strategy_class=self.strategy_class,
                market_data=is_data,
                **self.strategy_params,
            )
            optimizer.optimize(
                param_ranges=param_ranges,
                metric=metric,
                show_progress=False,
            )
            best = optimizer.get_best_params(min_trades=min_trades)

        return best if best else {}

    def _run_single_backtest(self, data: pd.DataFrame, params: dict) -> dict:
        """Run backtest, return all_metrics. Returns {'error': msg} on failure."""
        try:
            with contextlib.redirect_stdout(io.StringIO()):
                strategy = self.strategy_class(data=data, **params)
                runner = BacktestRunner(strategy)
                runner.run(verbose=False)
            return runner.metrics.all_metrics
        except Exception as e:
            return {'error': str(e)}

    @staticmethod
    def _aggregate_oos_metrics(valid_windows: list[WalkForwardWindow]) -> dict:
        """Average OOS metrics across valid windows."""
        if not valid_windows:
            return {}
        combined = {}
        keys = valid_windows[0].oos_metrics.keys()
        for key in keys:
            values = [
                w.oos_metrics[key] for w in valid_windows
                if isinstance(w.oos_metrics.get(key), (int, float))
            ]
            if values:
                combined[key] = sum(values) / len(values)
        return combined

    @staticmethod
    def _compute_efficiency(valid_windows: list[WalkForwardWindow], metric: str) -> float:
        """Compute OOS/IS efficiency ratio for target metric."""
        is_scores = [
            w.is_metrics[metric] for w in valid_windows
            if isinstance(w.is_metrics.get(metric), (int, float))
        ]
        oos_scores = [
            w.oos_metrics[metric] for w in valid_windows
            if isinstance(w.oos_metrics.get(metric), (int, float))
        ]
        if not is_scores or not oos_scores:
            return 0.0
        is_avg = sum(is_scores) / len(is_scores)
        oos_avg = sum(oos_scores) / len(oos_scores)
        return oos_avg / is_avg if abs(is_avg) > 1e-10 else 0.0

    @staticmethod
    def _compute_param_stability(
        valid_windows: list[WalkForwardWindow],
        param_ranges: dict | None,
    ) -> dict | None:
        """Compute coefficient of variation for each optimized parameter."""
        if param_ranges is None:
            return None
        windows_with_params = [w for w in valid_windows if w.best_params]
        if len(windows_with_params) < 2:
            return None

        stability = {}
        for param in windows_with_params[0].best_params:
            values = [
                w.best_params[param] for w in windows_with_params
                if param in w.best_params
            ]
            if values and all(isinstance(v, (int, float)) for v in values):
                mean = float(np.mean(values))
                std = float(np.std(values))
                cv = std / abs(mean) if abs(mean) > 1e-10 else float('inf')
                stability[param] = {
                    'values': values,
                    'mean': mean,
                    'std': std,
                    'cv': cv,
                }
        return stability if stability else None
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_walk_forward.py -v`
Expected: All 11 tests PASS.

- [ ] **Step 5: Run full test suite**

Run: `pytest tests/ -v`
Expected: All tests PASS.

- [ ] **Step 6: Commit**

```bash
git add validation/walk_forward.py tests/test_walk_forward.py
git commit -m "feat(validation): add WalkForwardValidator with rolling/anchored modes"
```

---

## Chunk 5: ValidationSuite + Documentation

### Task 5: ValidationSuite + CLAUDE.md

**Files:**
- Create: `validation/validation_suite.py`
- Create: `tests/test_validation_suite.py`
- Create: `validation/CLAUDE.md`
- Modify: `validation/__init__.py` (add import)

**Spec:** `docs/superpowers/specs/2026-03-14-validation-suite-design.md`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_validation_suite.py`:

```python
"""Tests for ValidationSuite orchestrator."""
import pytest

from validation.validation_suite import ValidationSuite


class TestValidationSuiteRunAll:
    def test_full_run(self, dummy_strategy_class, synthetic_market_data):
        suite = ValidationSuite(
            strategy_class=dummy_strategy_class,
            market_data=synthetic_market_data,
        )
        report = suite.run_all(
            oos_ratio=0.3,
            mc_simulations=50,
            mc_seed=42,
            wf_windows=2,
            wf_oos_ratio=0.25,
            verbose=False,
        )
        assert report.oos is not None
        assert report.monte_carlo is not None
        assert report.walk_forward is not None
        assert 'is_robust' in report.summary
        assert 'issues' in report.summary
        assert 'scores' in report.summary

    def test_skip_oos(self, dummy_strategy_class, synthetic_market_data):
        suite = ValidationSuite(
            strategy_class=dummy_strategy_class,
            market_data=synthetic_market_data,
        )
        report = suite.run_all(
            oos_ratio=0,  # skip
            mc_simulations=50,
            mc_seed=42,
            wf_windows=2,
            verbose=False,
        )
        assert report.oos is None
        assert report.monte_carlo is not None
        assert report.walk_forward is not None

    def test_skip_monte_carlo(self, dummy_strategy_class, synthetic_market_data):
        suite = ValidationSuite(
            strategy_class=dummy_strategy_class,
            market_data=synthetic_market_data,
        )
        report = suite.run_all(
            oos_ratio=0.3,
            mc_simulations=0,  # skip
            wf_windows=2,
            verbose=False,
        )
        assert report.monte_carlo is None
        assert report.oos is not None

    def test_skip_walk_forward(self, dummy_strategy_class, synthetic_market_data):
        suite = ValidationSuite(
            strategy_class=dummy_strategy_class,
            market_data=synthetic_market_data,
        )
        report = suite.run_all(
            oos_ratio=0.3,
            mc_simulations=50,
            mc_seed=42,
            wf_windows=0,  # skip
            verbose=False,
        )
        assert report.walk_forward is None
        assert report.oos is not None
        assert report.monte_carlo is not None

    def test_only_monte_carlo(self, dummy_strategy_class, synthetic_market_data):
        suite = ValidationSuite(
            strategy_class=dummy_strategy_class,
            market_data=synthetic_market_data,
        )
        report = suite.run_all(
            oos_ratio=0,
            mc_simulations=100,
            mc_seed=42,
            wf_windows=0,
            verbose=False,
        )
        assert report.oos is None
        assert report.monte_carlo is not None
        assert report.walk_forward is None


class TestValidationSuiteSummary:
    def test_summary_has_scores(self, dummy_strategy_class, synthetic_market_data):
        suite = ValidationSuite(
            strategy_class=dummy_strategy_class,
            market_data=synthetic_market_data,
        )
        report = suite.run_all(
            oos_ratio=0.3,
            mc_simulations=50,
            mc_seed=42,
            wf_windows=2,
            verbose=False,
        )
        scores = report.summary['scores']
        assert 'oos_degradation' in scores or report.oos is None
        assert 'mc_p_value' in scores or report.monte_carlo is None
        assert 'wf_efficiency' in scores or report.walk_forward is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_validation_suite.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'validation.validation_suite'`

- [ ] **Step 3: Write `validation/validation_suite.py`**

```python
"""ValidationSuite — orchestrator for all validation methods."""
import contextlib
import io

import pandas as pd

from core.backtest_runner import BacktestRunner
from validation.results import ValidationReport
from validation.oos_split import OOSSplitValidator
from validation.monte_carlo import MonteCarloValidator
from validation.walk_forward import WalkForwardValidator


class ValidationSuite:
    """Run OOS Split, Monte Carlo, and Walk-Forward validation in sequence.

    Each validator can be skipped by setting its control parameter to 0.

    Args:
        strategy_class: Strategy class inheriting BaseStrategy.
        market_data: OHLCV DataFrame with DatetimeIndex.
        **strategy_params: Fixed kwargs for strategy.
    """

    def __init__(
        self,
        strategy_class: type,
        market_data: pd.DataFrame,
        **strategy_params,
    ):
        self.strategy_class = strategy_class
        self.market_data = market_data
        self.strategy_params = strategy_params

    def run_all(
        self,
        # OOS params
        oos_ratio: float = 0.3,
        # Monte Carlo params
        mc_simulations: int = 1000,
        mc_seed: int | None = None,
        mc_confidence: float = 0.95,
        # Walk-Forward params
        wf_windows: int = 5,
        wf_oos_ratio: float = 0.25,
        wf_anchored: bool = False,
        # Walk-Forward optimization
        param_ranges: dict | None = None,
        optimization_metric: str = 'sharpe_ratio',
        wf_min_trades: int = 10,
        # General
        verbose: bool = True,
    ) -> ValidationReport:
        """Execute selected validators and produce consolidated report.

        Skip a validator by setting its control param to 0:
        - oos_ratio=0 → skip OOS
        - mc_simulations=0 → skip Monte Carlo
        - wf_windows=0 → skip Walk-Forward

        Args:
            See parameter docs above.

        Returns:
            ValidationReport with results from all executed validators.
        """
        oos_result = None
        mc_result = None
        wf_result = None

        # 1. OOS Split
        if oos_ratio > 0:
            if verbose:
                print("=" * 55)
                print("STEP 1/3: Out-of-Sample Split")
                print("=" * 55)
            oos_validator = OOSSplitValidator(
                strategy_class=self.strategy_class,
                market_data=self.market_data,
                oos_ratio=oos_ratio,
                **self.strategy_params,
            )
            oos_result = oos_validator.run(verbose=verbose)

        # 2. Monte Carlo (needs trades from full backtest)
        if mc_simulations > 0:
            if verbose:
                print("\n" + "=" * 55)
                print("STEP 2/3: Monte Carlo Simulation")
                print("=" * 55)
            # Run full backtest to get trades
            with contextlib.redirect_stdout(io.StringIO()):
                strategy_full = self.strategy_class(
                    data=self.market_data, **self.strategy_params
                )
                runner_full = BacktestRunner(strategy_full)
                runner_full.run(verbose=False)

            mc_validator = MonteCarloValidator(
                trades_df=runner_full.metrics.trade_metrics_df,
                initial_capital=strategy_full.initial_capital,
            )
            mc_result = mc_validator.run(
                n_simulations=mc_simulations,
                confidence_level=mc_confidence,
                seed=mc_seed,
                verbose=verbose,
            )

        # 3. Walk-Forward
        if wf_windows > 0:
            if verbose:
                print("\n" + "=" * 55)
                print("STEP 3/3: Walk-Forward Validation")
                print("=" * 55)
            wf_validator = WalkForwardValidator(
                strategy_class=self.strategy_class,
                market_data=self.market_data,
                n_windows=wf_windows,
                oos_ratio=wf_oos_ratio,
                anchored=wf_anchored,
                **self.strategy_params,
            )
            wf_result = wf_validator.run(
                param_ranges=param_ranges,
                optimization_metric=optimization_metric,
                min_trades=wf_min_trades,
                verbose=verbose,
            )

        # 4. Summary
        summary = self._generate_summary(oos_result, mc_result, wf_result)

        if verbose:
            print("\n" + "=" * 55)
            print("VALIDATION SUMMARY")
            print("=" * 55)
            if summary['is_robust']:
                print("Result: ROBUST — no significant issues detected")
            else:
                print("Result: ISSUES DETECTED")
                for issue in summary['issues']:
                    print(f"  ! {issue}")
            print(f"Scores: {summary['scores']}")

        return ValidationReport(
            oos=oos_result,
            monte_carlo=mc_result,
            walk_forward=wf_result,
            summary=summary,
        )

    @staticmethod
    def _generate_summary(oos, mc, wf) -> dict:
        """Analyze results and flag issues."""
        issues = []
        scores = {}

        if oos is not None:
            sharpe_deg = oos.degradation.get('sharpe_ratio', {})
            oos_degradation = sharpe_deg.get('pct_change', 0)
            scores['oos_degradation'] = oos_degradation
            if isinstance(oos_degradation, (int, float)) and oos_degradation < -50:
                issues.append(
                    f"OOS: sharpe_ratio degraded {oos_degradation:.1f}% vs in-sample"
                )

        if mc is not None:
            scores['mc_p_value'] = mc.p_value
            if mc.p_value < 0.2:
                issues.append(
                    f"MC: equity depends on trade order (p-value={mc.p_value:.2f})"
                )

        if wf is not None:
            scores['wf_efficiency'] = wf.efficiency_ratio
            if wf.efficiency_ratio < 0.3:
                issues.append(
                    f"WF: low efficiency ratio ({wf.efficiency_ratio:.2f}), "
                    f"possible overfitting"
                )
            if wf.param_stability:
                unstable = [
                    p for p, s in wf.param_stability.items()
                    if s['cv'] > 0.5
                ]
                if unstable:
                    issues.append(
                        f"WF: unstable parameters across windows: {unstable}"
                    )

        return {
            'is_robust': len(issues) == 0,
            'issues': issues,
            'scores': scores,
        }
```

- [ ] **Step 4: Update `validation/__init__.py` — replace try/except guards with clean imports**

All modules now exist, so remove the guards from Task 1:

```python
"""Validation module for detecting overfitting in backtested strategies."""
from .results import (
    OOSResult,
    MonteCarloResult,
    WalkForwardWindow,
    WalkForwardResult,
    ValidationReport,
)
from .monte_carlo import MonteCarloValidator
from .oos_split import OOSSplitValidator
from .walk_forward import WalkForwardValidator
from .validation_suite import ValidationSuite
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest tests/test_validation_suite.py -v`
Expected: All 6 tests PASS.

- [ ] **Step 6: Run full test suite**

Run: `pytest tests/ -v`
Expected: ALL tests PASS (no regressions).

- [ ] **Step 7: Write `validation/CLAUDE.md`**

```markdown
# Modulo: validation

Validacion estadistica de estrategias para detectar overfitting. Tres validadores independientes + un orquestador.

## Archivos

### results.py — Dataclasses de resultados
- `OOSResult` — Resultado de split IS/OOS
- `MonteCarloResult` — Resultado de permutacion de trades
- `WalkForwardWindow` / `WalkForwardResult` — Resultado de walk-forward
- `ValidationReport` — Reporte consolidado de los 3 validadores

### oos_split.py — `OOSSplitValidator`
Divide datos en in-sample (IS) y out-of-sample (OOS). Ejecuta backtests independientes y mide degradacion de metricas clave.

### monte_carlo.py — `MonteCarloValidator`
Permuta el orden de trades N veces para generar distribucion de equity curves. Calcula p-value e intervalos de confianza.

### walk_forward.py — `WalkForwardValidator`
Divide datos en N ventanas rodantes. Soporta modo fijo (params constantes) y modo optimizacion (re-optimiza en cada ventana IS).

### validation_suite.py — `ValidationSuite`
Orquestador que ejecuta los 3 validadores en secuencia y genera `ValidationReport` consolidado.

## Uso rapido

```python
from validation import ValidationSuite

suite = ValidationSuite(
    strategy_class=MiEstrategia,
    market_data=df,
    symbol='BTC', timeframe=Timeframe.M5, exchange='Binance',
    lookback_period=20,
)
report = suite.run_all(
    oos_ratio=0.3,
    mc_simulations=1000,
    wf_windows=5,
    param_ranges={'lookback_period': [10, 15, 20, 25, 30]},
)

if report.summary['is_robust']:
    print("Estrategia robusta!")
else:
    for issue in report.summary['issues']:
        print(f"Warning: {issue}")
```

## Uso individual

```python
from validation import MonteCarloValidator, OOSSplitValidator, WalkForwardValidator

# Monte Carlo (sobre trades existentes)
mc = MonteCarloValidator(runner.metrics.trade_metrics_df, initial_capital=1000)
result = mc.run(n_simulations=2000, seed=42)

# OOS Split
oos = OOSSplitValidator(strategy_class=MiEstrategia, market_data=df, oos_ratio=0.3, ...)
result = oos.run()

# Walk-Forward
wf = WalkForwardValidator(strategy_class=MiEstrategia, market_data=df, n_windows=5, ...)
result = wf.run(param_ranges={'lookback': [10, 20, 30]})
```

## Umbrales de robustez

| Validador | Metrica | Robusto | Marginal | Overfitting |
|-----------|---------|---------|----------|-------------|
| OOS | sharpe degradation | < 30% | 30-50% | > 50% |
| Monte Carlo | p-value | > 0.4 | 0.2-0.4 | < 0.2 |
| Walk-Forward | efficiency_ratio | > 0.5 | 0.3-0.5 | < 0.3 |
| Walk-Forward | param CV | < 0.3 | 0.3-0.5 | > 0.5 |

## Specs

Detalle completo en `docs/superpowers/specs/2026-03-14-validation-*-design.md`
```

- [ ] **Step 8: Commit**

```bash
git add validation/validation_suite.py validation/__init__.py validation/CLAUDE.md tests/test_validation_suite.py
git commit -m "feat(validation): add ValidationSuite orchestrator and module docs"
```

- [ ] **Step 9: Update root CLAUDE.md roadmap**

In `CLAUDE.md`, change the roadmap entry for Walk-Forward:

```
| 4c | Walk-Forward testing | Media |
```
to:
```
| 4c | ~~Walk-Forward testing~~ → validation/ module (OOS, MC, WF) | ✅ |
```

And add `validation/` to the architecture tree and module table.

- [ ] **Step 10: Final commit**

```bash
git add CLAUDE.md
git commit -m "docs: update roadmap — validation module complete"
```
