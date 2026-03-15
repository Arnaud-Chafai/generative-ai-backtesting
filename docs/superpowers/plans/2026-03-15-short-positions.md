# SHORT Position Support — Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add SHORT position support to the backtesting engine, using `position_side` field on signals to determine trade direction, with inverted P&L and slippage for SHORT trades.

**Architecture:** Extend `TradingSignal` with `position_side` (default LONG for backward compat). Refactor engine from `_handle_buy/_handle_sell` to `_open_position/_close_position` with signal routing based on `signal_type + position_side`. Propagate `position_side` through metrics pipeline. All existing strategies work unchanged.

**Tech Stack:** Python, pandas, pytest. Modifies existing: `models/`, `core/`, `metrics/`, `strategies/`.

**Spec:** `docs/superpowers/specs/2026-03-15-short-positions-design.md`

---

## File Structure

| File | Action | Responsibility |
|------|--------|---------------|
| `models/simple_signals.py` | Modify | Add `position_side` field to TradingSignal |
| `strategies/base_strategy.py` | Modify | Add `position_side` param to `create_simple_signal()` |
| `core/simple_backtest_engine.py` | Modify | Signal routing, P&L inversion, slippage direction |
| `metrics/metrics_aggregator.py` | Modify | Remove hardcoded `'LONG'`, propagate from engine |
| `metrics/trade_metrics.py` | Modify | Remove default `'LONG'` fallback |
| `tests/test_short_engine.py` | Create | SHORT-specific engine tests (crypto + futures) |
| `tests/test_short_integration.py` | Create | End-to-end SHORT tests via BacktestRunner |

## Dependency Graph

```
Task 1: TradingSignal + BaseStrategy (signal model)
   ↓
Task 2: BacktestEngine refactor (routing + P&L + slippage)
   ↓
Task 3: Metrics pipeline (aggregator + trade_metrics)
   ↓
Task 4: Integration tests + regression
```

All tasks are **sequential** — each depends on the previous.

---

## Chunk 1: Signal Model

### Task 1: TradingSignal + BaseStrategy

**Files:**
- Modify: `models/simple_signals.py`
- Modify: `strategies/base_strategy.py`
- Test: `tests/test_short_engine.py`

- [ ] **Step 1: Write failing test for TradingSignal with position_side**

Create `tests/test_short_engine.py`:

```python
"""Tests for SHORT position support."""
import pytest
from datetime import datetime
from models.enums import SignalType, SignalPositionSide
from models.simple_signals import TradingSignal


class TestTradingSignalPositionSide:
    def test_default_position_side_is_long(self):
        signal = TradingSignal(
            timestamp=datetime(2024, 1, 1),
            signal_type=SignalType.BUY,
            symbol='BTC',
            price=100.0,
            position_size_pct=0.5,
        )
        assert signal.position_side == SignalPositionSide.LONG

    def test_explicit_short_position_side(self):
        signal = TradingSignal(
            timestamp=datetime(2024, 1, 1),
            signal_type=SignalType.SELL,
            symbol='BTC',
            price=100.0,
            position_size_pct=0.5,
            position_side=SignalPositionSide.SHORT,
        )
        assert signal.position_side == SignalPositionSide.SHORT

    def test_repr_includes_position_side_when_short(self):
        signal = TradingSignal(
            timestamp=datetime(2024, 1, 1),
            signal_type=SignalType.SELL,
            symbol='BTC',
            price=100.0,
            position_size_pct=0.5,
            position_side=SignalPositionSide.SHORT,
        )
        assert 'SHORT' in repr(signal)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_short_engine.py::TestTradingSignalPositionSide -v`
Expected: FAIL — `TradingSignal.__init__() got an unexpected keyword argument 'position_side'`

- [ ] **Step 3: Add `position_side` to TradingSignal**

In `models/simple_signals.py`, add import and field:

```python
# Add to imports (line 13):
from models.enums import SignalType, SignalPositionSide

# Add field after position_size_pct (line 46), BEFORE stop_loss_price:
    position_side: SignalPositionSide = SignalPositionSide.LONG  # LONG or SHORT
```

Update `__repr__` to show position_side when SHORT:

```python
def __repr__(self):
    base = (
        f"TradingSignal({self.signal_type.value} {self.symbol} "
        f"@ {self.price:.2f} on {self.timestamp}, "
        f"size={self.position_size_pct*100:.1f}%"
    )
    if self.position_side == SignalPositionSide.SHORT:
        base += f", side=SHORT"
    if self.stop_loss_price is not None:
        base += f", SL={self.stop_loss_price:.2f}"
    if self.contracts is not None:
        base += f", contracts={self.contracts}"
    return base + ")"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_short_engine.py::TestTradingSignalPositionSide -v`
Expected: All 3 tests PASS.

- [ ] **Step 5: Add `position_side` to `create_simple_signal` in BaseStrategy**

In `strategies/base_strategy.py`:

Add import (update line 9):
```python
from models.enums import SignalType, OrderType, CurrencyType, ExchangeName, MarketType, SignalPositionSide
```

Add parameter to `create_simple_signal()` (after `position_size_pct`):
```python
def create_simple_signal(
    self,
    signal_type: SignalType,
    timestamp: datetime,
    price: float,
    position_size_pct: float,
    position_side: SignalPositionSide = SignalPositionSide.LONG,
    stop_loss_price: float = None,
    contracts: int = None
) -> TradingSignal:
```

Pass it to TradingSignal constructor (in the method body):
```python
signal = TradingSignal(
    timestamp=timestamp,
    signal_type=signal_type,
    symbol=self.symbol,
    price=price,
    position_size_pct=position_size_pct,
    position_side=position_side,
    stop_loss_price=stop_loss_price,
    contracts=contracts
)
```

- [ ] **Step 6: Run full test suite for regressions**

Run: `pytest tests/ -v`
Expected: All existing tests PASS (no regressions — default LONG maintains old behavior).

- [ ] **Step 7: Commit**

```bash
git add models/simple_signals.py strategies/base_strategy.py tests/test_short_engine.py
git commit -m "feat(short): add position_side field to TradingSignal and BaseStrategy"
```

---

## Chunk 2: Engine Refactor

### Task 2: BacktestEngine — Signal Routing + P&L + Slippage

**Files:**
- Modify: `core/simple_backtest_engine.py`
- Test: `tests/test_short_engine.py` (append)

This is the largest task. The engine needs:
1. `Position.position_side` field
2. `_is_entry()` / `_is_exit()` routing methods
3. Rename `_handle_buy` → `_open_position`, `_handle_sell` → `_close_position`
4. Direction-aware slippage
5. Direction-aware P&L
6. `position_side` in completed trades and empty DataFrame

- [ ] **Step 1: Write failing SHORT crypto test**

Append to `tests/test_short_engine.py`:

```python
import pandas as pd
import numpy as np
from core.simple_backtest_engine import BacktestEngine, Position
from config.market_configs.crypto_config import get_crypto_config


def _make_signal(signal_type, price, position_side=SignalPositionSide.LONG,
                 pct=1.0, ts=None, symbol='BTC', **kwargs):
    """Helper to create TradingSignal for tests."""
    if ts is None:
        ts = datetime(2024, 1, 1)
    return TradingSignal(
        timestamp=ts,
        signal_type=signal_type,
        symbol=symbol,
        price=price,
        position_size_pct=pct,
        position_side=position_side,
        **kwargs,
    )


class TestShortCryptoEngine:
    """SHORT positions on crypto market."""

    def _make_engine(self, capital=1000.0):
        config = get_crypto_config('BTC', 'Binance')
        return BacktestEngine(initial_capital=capital, market_config=config)

    def test_short_basic_profit(self):
        """SELL@100 to open SHORT, BUY@90 to close. Price dropped = profit."""
        engine = self._make_engine()
        signals = [
            _make_signal(SignalType.SELL, 100.0, SignalPositionSide.SHORT,
                        ts=datetime(2024, 1, 1)),
            _make_signal(SignalType.BUY, 90.0, SignalPositionSide.SHORT,
                        ts=datetime(2024, 1, 2)),
        ]
        df = engine.run(signals)
        assert len(df) == 1
        assert df['gross_pnl'].iloc[0] > 0  # Price dropped = profit for SHORT
        assert df['position_side'].iloc[0] == 'SHORT'

    def test_short_basic_loss(self):
        """SELL@100 to open SHORT, BUY@110 to close. Price rose = loss."""
        engine = self._make_engine()
        signals = [
            _make_signal(SignalType.SELL, 100.0, SignalPositionSide.SHORT,
                        ts=datetime(2024, 1, 1)),
            _make_signal(SignalType.BUY, 110.0, SignalPositionSide.SHORT,
                        ts=datetime(2024, 1, 2)),
        ]
        df = engine.run(signals)
        assert len(df) == 1
        assert df['gross_pnl'].iloc[0] < 0  # Price rose = loss for SHORT

    def test_short_pnl_math(self):
        """Verify exact P&L calculation for SHORT crypto (no fees/slippage)."""
        config = {
            'tick_size': 0.01,
            'exchange_fee': 0.0,
            'slippage': 0.0,
        }
        engine = BacktestEngine(initial_capital=1000.0, market_config=config)
        signals = [
            _make_signal(SignalType.SELL, 100.0, SignalPositionSide.SHORT,
                        ts=datetime(2024, 1, 1)),
            _make_signal(SignalType.BUY, 90.0, SignalPositionSide.SHORT,
                        ts=datetime(2024, 1, 2)),
        ]
        df = engine.run(signals)
        # Entry: 1000 * 1.0 = 1000 USDT committed, at price 100 = 10 units
        # Exit: 10 units * 90 = 900 USDT (exit_value)
        # SHORT gross_pnl = closed_cost - exit_value = 1000 - 900 = 100
        assert abs(df['gross_pnl'].iloc[0] - 100.0) < 0.01

    def test_short_position_side_in_output(self):
        """Output DataFrame must include position_side column."""
        config = {
            'tick_size': 0.01,
            'exchange_fee': 0.0,
            'slippage': 0.0,
        }
        engine = BacktestEngine(initial_capital=1000.0, market_config=config)
        signals = [
            _make_signal(SignalType.SELL, 100.0, SignalPositionSide.SHORT,
                        ts=datetime(2024, 1, 1)),
            _make_signal(SignalType.BUY, 90.0, SignalPositionSide.SHORT,
                        ts=datetime(2024, 1, 2)),
        ]
        df = engine.run(signals)
        assert 'position_side' in df.columns
        assert df['position_side'].iloc[0] == 'SHORT'

    def test_long_still_works(self):
        """LONG trades must produce same results as before (regression)."""
        config = {
            'tick_size': 0.01,
            'exchange_fee': 0.0,
            'slippage': 0.0,
        }
        engine = BacktestEngine(initial_capital=1000.0, market_config=config)
        signals = [
            _make_signal(SignalType.BUY, 100.0, SignalPositionSide.LONG,
                        ts=datetime(2024, 1, 1)),
            _make_signal(SignalType.SELL, 110.0, SignalPositionSide.LONG,
                        ts=datetime(2024, 1, 2)),
        ]
        df = engine.run(signals)
        assert len(df) == 1
        # LONG: gross_pnl = exit_value - entry_cost = 1100 - 1000 = 100
        assert abs(df['gross_pnl'].iloc[0] - 100.0) < 0.01
        assert df['position_side'].iloc[0] == 'LONG'

    def test_long_default_without_position_side(self):
        """Signals without explicit position_side default to LONG."""
        config = {
            'tick_size': 0.01,
            'exchange_fee': 0.0,
            'slippage': 0.0,
        }
        engine = BacktestEngine(initial_capital=1000.0, market_config=config)
        signals = [
            TradingSignal(
                timestamp=datetime(2024, 1, 1),
                signal_type=SignalType.BUY,
                symbol='BTC',
                price=100.0,
                position_size_pct=1.0,
                # NO position_side — should default to LONG
            ),
            TradingSignal(
                timestamp=datetime(2024, 1, 2),
                signal_type=SignalType.SELL,
                symbol='BTC',
                price=110.0,
                position_size_pct=1.0,
            ),
        ]
        df = engine.run(signals)
        assert len(df) == 1
        assert df['position_side'].iloc[0] == 'LONG'
        assert df['gross_pnl'].iloc[0] > 0

    def test_ignore_mismatched_exit(self):
        """BUY+LONG exit while SHORT is open → ignored."""
        config = {
            'tick_size': 0.01,
            'exchange_fee': 0.0,
            'slippage': 0.0,
        }
        engine = BacktestEngine(initial_capital=1000.0, market_config=config)
        signals = [
            _make_signal(SignalType.SELL, 100.0, SignalPositionSide.SHORT,
                        ts=datetime(2024, 1, 1)),
            # Wrong: SELL+LONG exit while SHORT is open
            _make_signal(SignalType.SELL, 95.0, SignalPositionSide.LONG,
                        ts=datetime(2024, 1, 2)),
            # Correct: BUY+SHORT to close
            _make_signal(SignalType.BUY, 90.0, SignalPositionSide.SHORT,
                        ts=datetime(2024, 1, 3)),
        ]
        df = engine.run(signals)
        assert len(df) == 1  # Only 1 trade completed

    def test_exit_short_without_position(self):
        """BUY+SHORT without open position → ignored, no crash."""
        config = {
            'tick_size': 0.01,
            'exchange_fee': 0.0,
            'slippage': 0.0,
        }
        engine = BacktestEngine(initial_capital=1000.0, market_config=config)
        signals = [
            _make_signal(SignalType.BUY, 90.0, SignalPositionSide.SHORT,
                        ts=datetime(2024, 1, 1)),
        ]
        df = engine.run(signals)
        assert len(df) == 0

    def test_short_dca(self):
        """Two SELL entries for SHORT (DCA), then BUY closes all."""
        config = {
            'tick_size': 0.01,
            'exchange_fee': 0.0,
            'slippage': 0.0,
        }
        engine = BacktestEngine(initial_capital=1000.0, market_config=config)
        signals = [
            _make_signal(SignalType.SELL, 100.0, SignalPositionSide.SHORT,
                        pct=0.5, ts=datetime(2024, 1, 1)),
            _make_signal(SignalType.SELL, 105.0, SignalPositionSide.SHORT,
                        pct=0.5, ts=datetime(2024, 1, 2)),
            _make_signal(SignalType.BUY, 90.0, SignalPositionSide.SHORT,
                        ts=datetime(2024, 1, 3)),
        ]
        df = engine.run(signals)
        assert len(df) == 1
        assert df['gross_pnl'].iloc[0] > 0  # Price dropped from ~102.5 avg to 90
        assert df['num_entries'].iloc[0] == 2

    def test_short_slippage_direction(self):
        """SHORT entry (SELL) gets worse price (lower), exit (BUY) gets worse price (higher)."""
        config = {
            'tick_size': 0.01,
            'exchange_fee': 0.0,
            'slippage': 0.01,  # 1% slippage
        }
        engine = BacktestEngine(initial_capital=1000.0, market_config=config)
        signals = [
            _make_signal(SignalType.SELL, 100.0, SignalPositionSide.SHORT,
                        ts=datetime(2024, 1, 1)),
            _make_signal(SignalType.BUY, 90.0, SignalPositionSide.SHORT,
                        ts=datetime(2024, 1, 2)),
        ]
        df = engine.run(signals)
        # Entry: SELL at 100, slippage DOWN → real_price < 100 (gets less)
        assert df['avg_entry_price'].iloc[0] < 100.0
        # Exit: BUY at 90, slippage UP → real_price > 90 (pays more)
        assert df['exit_price'].iloc[0] > 90.0

    def test_empty_dataframe_has_position_side(self):
        """Empty results DataFrame must include position_side column."""
        config = {
            'tick_size': 0.01,
            'exchange_fee': 0.0,
            'slippage': 0.0,
        }
        engine = BacktestEngine(initial_capital=1000.0, market_config=config)
        df = engine.run([])
        assert 'position_side' in df.columns

    def test_short_partial_close(self):
        """Close 50% of SHORT position, then close rest."""
        config = {
            'tick_size': 0.01,
            'exchange_fee': 0.0,
            'slippage': 0.0,
        }
        engine = BacktestEngine(initial_capital=1000.0, market_config=config)
        signals = [
            _make_signal(SignalType.SELL, 100.0, SignalPositionSide.SHORT,
                        ts=datetime(2024, 1, 1)),
            _make_signal(SignalType.BUY, 90.0, SignalPositionSide.SHORT,
                        pct=0.5, ts=datetime(2024, 1, 2)),
            _make_signal(SignalType.BUY, 80.0, SignalPositionSide.SHORT,
                        pct=1.0, ts=datetime(2024, 1, 3)),
        ]
        df = engine.run(signals)
        assert len(df) == 2
        assert all(df['position_side'] == 'SHORT')
        assert all(df['gross_pnl'] > 0)  # Both closings profitable
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_short_engine.py::TestShortCryptoEngine -v`
Expected: FAIL — engine doesn't understand SHORT signals yet.

- [ ] **Step 3: Implement engine changes**

Modify `core/simple_backtest_engine.py`:

**3a. Add import** (line 15):
```python
from models.enums import SignalType, SignalPositionSide
```

**3b. Add `position_side` to Position** (line 45-47):
```python
class Position:
    def __init__(self, symbol: str, entry_time: datetime):
        self.symbol = symbol
        self.entry_time = entry_time
        self.entries: list[Entry] = []
        self.position_side: SignalPositionSide = None  # Set on first entry
```

**3c. Add routing methods** to BacktestEngine (after `__init__`, before `run`):
```python
def _is_entry(self, signal: TradingSignal) -> bool:
    """BUY+LONG = entry, SELL+SHORT = entry."""
    return (
        (signal.position_side == SignalPositionSide.LONG and signal.signal_type == SignalType.BUY) or
        (signal.position_side == SignalPositionSide.SHORT and signal.signal_type == SignalType.SELL)
    )

def _is_exit(self, signal: TradingSignal) -> bool:
    """SELL+LONG = exit, BUY+SHORT = exit."""
    return (
        (signal.position_side == SignalPositionSide.LONG and signal.signal_type == SignalType.SELL) or
        (signal.position_side == SignalPositionSide.SHORT and signal.signal_type == SignalType.BUY)
    )
```

**3d. Replace routing in `run()`** (lines 248-252):
```python
for signal in signals:
    if self._is_entry(signal):
        self._open_position(signal)
    elif self._is_exit(signal):
        self._close_position(signal)
```

**3e. Rename `_handle_buy` → `_open_position`** and add position_side tracking:

At the start of `_open_position`, after computing `real_price`:
```python
def _open_position(self, signal: TradingSignal):
    """Open or add to a position (entry signal)."""
    real_price = self._apply_slippage(signal)
    slippage_per_unit = abs(real_price - signal.price)
```

When creating new Position, set position_side:
```python
if self.current_position is None:
    self.current_position = Position(
        symbol=signal.symbol,
        entry_time=signal.timestamp
    )
    self.current_position.position_side = signal.position_side
    self.current_position._risk_usd = 0.0
else:
    # DCA: verify same direction
    if self.current_position.position_side != signal.position_side:
        return  # Ignore entry for different direction
```

The rest of `_open_position` (crypto entry_size, futures contracts, etc.) stays the same. Capital is blocked symmetrically for both LONG and SHORT.

**3f. Rename `_handle_sell` → `_close_position`** and add direction validation + P&L inversion:

```python
def _close_position(self, signal: TradingSignal):
    """Close total or partial position (exit signal)."""
    if self.current_position is None:
        return
    # Validate direction matches
    if self.current_position.position_side != signal.position_side:
        return

    pos = self.current_position
    pct = signal.position_size_pct
    real_price = self._apply_slippage(signal)
    slippage_per_unit = abs(signal.price - real_price)
```

For **crypto P&L** (replace line 427):
```python
if pos.position_side == SignalPositionSide.LONG:
    gross_pnl = exit_value - closed_cost
else:
    gross_pnl = closed_cost - exit_value
```

For **crypto capital recovery** (replace line 430):
```python
if pos.position_side == SignalPositionSide.LONG:
    self.capital += (exit_value - exit_fee)
else:
    # SHORT: return committed capital + profit (or - loss)
    self.capital += (closed_cost + gross_pnl - exit_fee)
```

For **futures P&L** (replace line 375):
```python
if pos.position_side == SignalPositionSide.LONG:
    gross_pnl = closed_contracts * self.point_value * (real_price - avg_entry)
else:
    gross_pnl = closed_contracts * self.point_value * (avg_entry - real_price)
```

Add `position_side` to completed_trades dict in **BOTH** blocks:

**Futures block** (after `'symbol': pos.symbol,` around line 386):
```python
'symbol': pos.symbol,
'position_side': pos.position_side.value,  # 'LONG' or 'SHORT'
'entry_time': pos.entry_time,
```

**Crypto block** (after `'symbol': pos.symbol,` around line 435):
```python
'symbol': pos.symbol,
'position_side': pos.position_side.value,  # 'LONG' or 'SHORT'
'entry_time': pos.entry_time,
```

**CRITICAL:** Both blocks must include this line. Missing one means that market's trades won't have `position_side` in the output DataFrame.

**3g. Direction-aware slippage** — replace `_apply_slippage_to_price`:

```python
def _apply_slippage(self, signal: TradingSignal) -> float:
    """Apply slippage — always against the trader.

    Entry LONG or Exit SHORT → price goes UP (trader pays more)
    Entry SHORT or Exit LONG → price goes DOWN (trader receives less)
    """
    is_entry = self._is_entry(signal)

    # Slippage goes up when entering LONG or exiting SHORT
    price_goes_up = (
        (is_entry and signal.position_side == SignalPositionSide.LONG) or
        (not is_entry and signal.position_side == SignalPositionSide.SHORT)
    )

    price = signal.price
    if self.slippage_fixed > 0:
        real_price = price + self.slippage_fixed if price_goes_up else price - self.slippage_fixed
    elif price_goes_up:
        real_price = price * (1 + self.slippage_pct)
    else:
        real_price = price * (1 - self.slippage_pct)

    return round(real_price / self.tick_size) * self.tick_size
```

Update all callers of `_apply_slippage_to_price` to use `_apply_slippage(signal)` instead. There are 2 call sites:
- In `_open_position`: `real_price = self._apply_slippage(signal)`
- In `_close_position`: `real_price = self._apply_slippage(signal)`

**3h. Add `position_side` to empty DataFrame** (line 498):
```python
return pd.DataFrame(columns=[
    'symbol', 'position_side', 'entry_time', 'exit_time', 'num_entries',
    ...
])
```

- [ ] **Step 4: Run SHORT crypto tests**

Run: `pytest tests/test_short_engine.py -v`
Expected: All tests PASS.

- [ ] **Step 5: Run full test suite for regressions**

Run: `pytest tests/ -v`
Expected: All existing tests PASS. The `position_side` column is new in the output but existing tests don't check for it specifically.

**Note:** Existing tests may fail if they check exact column counts or don't expect `position_side`. Fix by adding `position_side` awareness to existing test assertions if needed.

- [ ] **Step 6: Write SHORT futures tests (TDD: write before verifying)**

Append to `tests/test_short_engine.py` (these were written in Step 1 conceptually but added here for file organization; they should already fail before engine changes since they're appended to the same file):

```python
class TestShortFuturesEngine:
    """SHORT positions on futures market."""

    def _make_engine(self, capital=10000.0):
        from config.market_configs.futures_config import get_futures_config
        config = get_futures_config('CL', 'CME')
        return BacktestEngine(initial_capital=capital, market_config=config)

    def test_short_futures_profit(self):
        """SHORT futures: entry@70, exit@65 = profit."""
        engine = self._make_engine()
        signals = [
            _make_signal(SignalType.SELL, 70.0, SignalPositionSide.SHORT,
                        ts=datetime(2024, 1, 1), symbol='CL',
                        contracts=1),
            _make_signal(SignalType.BUY, 65.0, SignalPositionSide.SHORT,
                        ts=datetime(2024, 1, 2), symbol='CL'),
        ]
        df = engine.run(signals)
        assert len(df) == 1
        assert df['gross_pnl'].iloc[0] > 0
        assert df['position_side'].iloc[0] == 'SHORT'

    def test_short_futures_loss(self):
        """SHORT futures: entry@70, exit@75 = loss."""
        engine = self._make_engine()
        signals = [
            _make_signal(SignalType.SELL, 70.0, SignalPositionSide.SHORT,
                        ts=datetime(2024, 1, 1), symbol='CL',
                        contracts=1),
            _make_signal(SignalType.BUY, 75.0, SignalPositionSide.SHORT,
                        ts=datetime(2024, 1, 2), symbol='CL'),
        ]
        df = engine.run(signals)
        assert len(df) == 1
        assert df['gross_pnl'].iloc[0] < 0

    def test_long_futures_regression(self):
        """LONG futures must still work correctly."""
        engine = self._make_engine()
        signals = [
            _make_signal(SignalType.BUY, 70.0, SignalPositionSide.LONG,
                        ts=datetime(2024, 1, 1), symbol='CL',
                        contracts=1),
            _make_signal(SignalType.SELL, 75.0, SignalPositionSide.LONG,
                        ts=datetime(2024, 1, 2), symbol='CL'),
        ]
        df = engine.run(signals)
        assert len(df) == 1
        assert df['gross_pnl'].iloc[0] > 0
        assert df['position_side'].iloc[0] == 'LONG'
```

- [ ] **Step 7: Run all SHORT tests**

Run: `pytest tests/test_short_engine.py -v`
Expected: All tests PASS.

- [ ] **Step 8: Commit**

```bash
git add core/simple_backtest_engine.py tests/test_short_engine.py
git commit -m "feat(short): refactor engine with signal routing and SHORT P&L support"
```

---

## Chunk 3: Metrics Pipeline

### Task 3: Metrics Propagation

**Files:**
- Modify: `metrics/metrics_aggregator.py`
- Modify: `metrics/trade_metrics.py`
- Test: `tests/test_short_engine.py` (append)

- [ ] **Step 1: Write failing test for metrics propagation**

Append to `tests/test_short_engine.py`:

```python
from core.backtest_runner import BacktestRunner
from conftest import DummyStrategy, create_synthetic_data
from models.enums import MarketType
from utils.timeframe import Timeframe


class ShortDummyStrategy(DummyStrategy):
    """DummyStrategy that opens SHORT positions instead of LONG."""
    def generate_simple_signals(self):
        df = self.market_data
        i = 0
        while i + self.hold_bars < len(df):
            # SHORT entry: SELL
            self.create_simple_signal(
                signal_type=SignalType.SELL,
                timestamp=df.index[i],
                price=df['Close'].iloc[i],
                position_size_pct=1.0,
                position_side=SignalPositionSide.SHORT,
            )
            # SHORT exit: BUY
            sell_i = i + self.hold_bars
            self.create_simple_signal(
                signal_type=SignalType.BUY,
                timestamp=df.index[sell_i],
                price=df['Close'].iloc[sell_i],
                position_size_pct=1.0,
                position_side=SignalPositionSide.SHORT,
            )
            i += self.buy_every
        return self.simple_signals


class TestShortMetricsPropagation:
    def test_position_side_in_trade_metrics_df(self):
        """position_side must propagate to trade_metrics_df."""
        data = create_synthetic_data(200, seed=42)
        strategy = ShortDummyStrategy(data=data)
        runner = BacktestRunner(strategy)
        runner.run(verbose=False)

        trade_df = runner.metrics.trade_metrics_df
        assert 'position_side' in trade_df.columns
        assert all(trade_df['position_side'] == 'SHORT')

    def test_all_metrics_computed_for_short(self):
        """all_metrics dict should be fully populated for SHORT trades."""
        data = create_synthetic_data(200, seed=42)
        strategy = ShortDummyStrategy(data=data)
        runner = BacktestRunner(strategy)
        runner.run(verbose=False)

        metrics = runner.metrics.all_metrics
        assert 'sharpe_ratio' in metrics
        assert 'total_trades' in metrics
        assert metrics['total_trades'] > 0

    def test_mae_mfe_correct_for_short(self):
        """For SHORT: price going UP = MAE (adverse), DOWN = MFE (favorable)."""
        data = create_synthetic_data(200, seed=42)
        strategy = ShortDummyStrategy(data=data)
        runner = BacktestRunner(strategy)
        runner.run(verbose=False)

        trade_df = runner.metrics.trade_metrics_df
        # MAE and MFE should be populated (not NaN)
        assert trade_df['MAE'].notna().any()
        assert trade_df['MFE'].notna().any()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_short_engine.py::TestShortMetricsPropagation -v`
Expected: FAIL — `metrics_aggregator.py` overwrites position_side with 'LONG'.

- [ ] **Step 3: Fix MetricsAggregator**

In `metrics/metrics_aggregator.py`, remove line 90:
```python
# DELETE THIS LINE:
adapted['position_side'] = 'LONG'  # TODO: adaptar cuando tengamos SHORT
```

The `position_side` column now comes from the engine's DataFrame and passes through untouched.

- [ ] **Step 4: Fix TradeMetricsCalculator default**

In `metrics/trade_metrics.py`, in `_prepare_data()`, find the `else` branch that defaults to LONG and replace:

```python
# BEFORE:
else:
    df["position_side"] = "LONG"

# AFTER:
else:
    raise ValueError(
        "trade_data must include 'position_side' column. "
        "Ensure BacktestEngine outputs position_side."
    )
```

- [ ] **Step 5: Run tests**

Run: `pytest tests/test_short_engine.py -v`
Expected: All tests PASS.

- [ ] **Step 6: Run full test suite**

Run: `pytest tests/ -v`
Expected: All tests PASS. Existing strategies output `position_side='LONG'` from the engine, so the metrics pipeline receives it correctly.

- [ ] **Step 7: Commit**

```bash
git add metrics/metrics_aggregator.py metrics/trade_metrics.py tests/test_short_engine.py
git commit -m "feat(short): propagate position_side through metrics pipeline"
```

---

## Chunk 4: Integration + Regression

### Task 4: End-to-end Integration Tests

**Files:**
- Create: `tests/test_short_integration.py`
- Modify: `core/CLAUDE.md` (update docs)

- [ ] **Step 1: Write integration tests**

Create `tests/test_short_integration.py`:

```python
"""End-to-end integration tests for SHORT position support."""
import pytest
from conftest import DummyStrategy, create_synthetic_data
from core.backtest_runner import BacktestRunner
from models.enums import SignalType, SignalPositionSide
from tests.test_short_engine import ShortDummyStrategy


class TestShortIntegrationCrypto:
    def test_full_pipeline_short(self):
        """SHORT strategy → runner → engine → metrics → all_metrics."""
        data = create_synthetic_data(500, seed=42)
        strategy = ShortDummyStrategy(data=data)
        runner = BacktestRunner(strategy)
        result = runner.run(verbose=False)

        # Engine output
        assert 'position_side' in result.columns
        assert all(result['position_side'] == 'SHORT')

        # Metrics
        metrics = runner.metrics.all_metrics
        assert metrics['total_trades'] > 0
        assert 'sharpe_ratio' in metrics
        assert 'max_drawdown' in metrics

    def test_long_regression(self):
        """LONG DummyStrategy must produce identical structure."""
        data = create_synthetic_data(500, seed=42)
        strategy = DummyStrategy(data=data)
        runner = BacktestRunner(strategy)
        result = runner.run(verbose=False)

        assert 'position_side' in result.columns
        assert all(result['position_side'] == 'LONG')
        assert runner.metrics.all_metrics['total_trades'] > 0

    def test_validation_module_works_with_short(self):
        """Validation module should work transparently with SHORT."""
        from validation import MonteCarloValidator
        data = create_synthetic_data(500, seed=42)
        strategy = ShortDummyStrategy(data=data)
        runner = BacktestRunner(strategy)
        runner.run(verbose=False)

        mc = MonteCarloValidator(
            trades_df=runner.metrics.trade_metrics_df,
            initial_capital=strategy.initial_capital,
        )
        result = mc.run(n_simulations=50, seed=42, verbose=False)
        assert result.p_value >= 0
```

- [ ] **Step 2: Run integration tests**

Run: `pytest tests/test_short_integration.py -v`
Expected: All tests PASS.

- [ ] **Step 3: Run complete test suite**

Run: `pytest tests/ -v`
Expected: All tests PASS.

- [ ] **Step 4: Update documentation**

Update `core/CLAUDE.md` — replace references to `_handle_buy/_handle_sell` with `_open_position/_close_position`. Add SHORT section:

Add after the BacktestEngine description:
```markdown
**Soporte SHORT:**
- `position_side` en TradingSignal determina la direccion (LONG o SHORT)
- Routing: BUY+LONG y SELL+SHORT = entrada, SELL+LONG y BUY+SHORT = salida
- P&L invertido para SHORT: `closed_cost - exit_value` (crypto), `avg_entry - exit_price` (futuros)
- Slippage siempre en contra del trader, independiente de la direccion
- Una posicion a la vez, cierre explicito
```

- [ ] **Step 5: Commit**

```bash
git add tests/test_short_integration.py core/CLAUDE.md
git commit -m "feat(short): add integration tests and update engine docs"
```

- [ ] **Step 6: Final full test suite run**

Run: `pytest tests/ -v`
Expected: ALL tests PASS. No regressions.

- [ ] **Step 7: Update root CLAUDE.md**

In `CLAUDE.md`, add to "Notas tecnicas":
```
- Soporta posiciones LONG y SHORT (una a la vez, cierre explicito)
```

Remove:
```
- Solo soporta posiciones LONG actualmente
```

- [ ] **Step 8: Final commit**

```bash
git add CLAUDE.md
git commit -m "docs: update project notes — SHORT support added"
```

---

## Known Limitation: Visualization

**`chart_plotter.py` is NOT modified in this plan.** If a SHORT strategy is plotted with `runner.plot_trades()`:
- SHORT entry (SELL) markers will appear as exit arrows (arrowDown, yellow)
- SHORT exit (BUY) markers will appear as entry arrows (arrowUp, green)

This is visually confusing but **all data and metrics are correct**. Fix in Phase 2 (future).
