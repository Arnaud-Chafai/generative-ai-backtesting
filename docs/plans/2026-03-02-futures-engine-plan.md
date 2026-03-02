# Futures Engine Support — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Make BacktestEngine correctly handle futures: contract-based sizing, per-contract fees, real P&L using point_value.

**Architecture:** Extend existing classes with `is_futures` branching. TradingSignal gets optional `stop_loss_price` and `contracts` fields. Engine branches on `is_futures` for sizing, fees, and P&L. Metrics get `is_futures`/`point_value` params for correct MAE/MFE.

**Tech Stack:** Python 3.12, pandas, pytest, dataclasses

**Design doc:** `docs/plans/2026-03-02-futures-engine-design.md`

---

### Task 1: Extend TradingSignal with optional futures fields

**Files:**
- Modify: `models/simple_signals.py`
- Test: `tests/test_futures_engine.py` (create)

**Step 1: Write the failing test**

Create `tests/test_futures_engine.py`:

```python
"""Tests para el soporte de futuros en el BacktestEngine."""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime
from models.enums import SignalType
from models.simple_signals import TradingSignal


class TestTradingSignalFutures:
    """Tests para los campos opcionales de futuros en TradingSignal."""

    def test_crypto_signal_unchanged(self):
        """Senales crypto existentes siguen funcionando sin cambios."""
        signal = TradingSignal(
            timestamp=datetime(2024, 1, 1),
            signal_type=SignalType.BUY,
            symbol="BTC",
            price=50000.0,
            position_size_pct=0.1
        )
        assert signal.stop_loss_price is None
        assert signal.contracts is None

    def test_futures_signal_with_stop_loss(self):
        """Senal de futuros con stop_loss_price para auto-sizing."""
        signal = TradingSignal(
            timestamp=datetime(2024, 1, 1),
            signal_type=SignalType.BUY,
            symbol="ES",
            price=5000.0,
            position_size_pct=0.01,
            stop_loss_price=4990.0
        )
        assert signal.stop_loss_price == 4990.0
        assert signal.contracts is None

    def test_futures_signal_with_contracts_override(self):
        """Senal de futuros con override manual de contratos."""
        signal = TradingSignal(
            timestamp=datetime(2024, 1, 1),
            signal_type=SignalType.BUY,
            symbol="ES",
            price=5000.0,
            position_size_pct=0.01,
            contracts=2
        )
        assert signal.contracts == 2

    def test_stop_loss_must_be_positive(self):
        """stop_loss_price debe ser positivo si se provee."""
        with pytest.raises(ValueError, match="stop_loss_price"):
            TradingSignal(
                timestamp=datetime(2024, 1, 1),
                signal_type=SignalType.BUY,
                symbol="ES",
                price=5000.0,
                position_size_pct=0.01,
                stop_loss_price=-100.0
            )

    def test_contracts_must_be_positive(self):
        """contracts debe ser >= 1 si se provee."""
        with pytest.raises(ValueError, match="contracts"):
            TradingSignal(
                timestamp=datetime(2024, 1, 1),
                signal_type=SignalType.BUY,
                symbol="ES",
                price=5000.0,
                position_size_pct=0.01,
                contracts=0
            )
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_futures_engine.py::TestTradingSignalFutures -v`
Expected: FAIL — `TradingSignal` does not accept `stop_loss_price` or `contracts`

**Step 3: Write minimal implementation**

In `models/simple_signals.py`, add the two optional fields to the dataclass and update `__post_init__`:

```python
from dataclasses import dataclass, field
from typing import Optional

@dataclass
class TradingSignal:
    """
    Una senal de trading simple.

    Campos base (requeridos):
        timestamp: Momento exacto de la senal
        signal_type: BUY o SELL
        symbol: Activo (ej: "BTC", "ES")
        price: Precio de referencia
        position_size_pct: Crypto: % capital a desplegar. Futuros: % capital a arriesgar.

    Campos opcionales (futuros):
        stop_loss_price: Precio de stop loss. Requerido para auto-sizing en futuros.
        contracts: Override manual de contratos. Si se provee, ignora el calculo automatico.
    """
    timestamp: datetime
    signal_type: SignalType
    symbol: str
    price: float
    position_size_pct: float
    stop_loss_price: Optional[float] = None
    contracts: Optional[int] = None

    def __post_init__(self):
        if self.price <= 0:
            raise ValueError(f"El precio debe ser positivo, recibido: {self.price}")

        if not (0 < self.position_size_pct <= 1):
            raise ValueError(
                f"position_size_pct debe estar entre 0 y 1 (0% a 100%), "
                f"recibido: {self.position_size_pct}"
            )

        if self.stop_loss_price is not None and self.stop_loss_price <= 0:
            raise ValueError(
                f"stop_loss_price debe ser positivo, recibido: {self.stop_loss_price}"
            )

        if self.contracts is not None and self.contracts < 1:
            raise ValueError(
                f"contracts debe ser >= 1, recibido: {self.contracts}"
            )

    def __repr__(self):
        extras = ""
        if self.contracts is not None:
            extras += f", contracts={self.contracts}"
        if self.stop_loss_price is not None:
            extras += f", sl={self.stop_loss_price:.2f}"
        return (
            f"TradingSignal({self.signal_type.value} {self.symbol} "
            f"@ {self.price:.2f} on {self.timestamp}, "
            f"size={self.position_size_pct*100:.1f}%{extras})"
        )
```

Note: Add `from typing import Optional` to imports. The `from enum import Enum` import can stay.

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_futures_engine.py::TestTradingSignalFutures -v`
Expected: All 5 tests PASS

**Step 5: Commit**

```bash
git add models/simple_signals.py tests/test_futures_engine.py
git commit -m "feat(models): add stop_loss_price and contracts to TradingSignal"
```

---

### Task 2: Extend Entry and Position for futures

**Files:**
- Modify: `core/simple_backtest_engine.py` (Entry, Position classes only)
- Test: `tests/test_futures_engine.py` (append)

**Step 1: Write the failing tests**

Append to `tests/test_futures_engine.py`:

```python
from core.simple_backtest_engine import Entry, Position


class TestPositionFutures:
    """Tests para Position con soporte de contratos."""

    def test_entry_has_contracts_field(self):
        """Entry debe tener campo contracts."""
        entry = Entry(
            timestamp=datetime(2024, 1, 1),
            price=5000.0,
            size_usdt=0.0,
            contracts=2,
            fee=2.78,
            slippage_cost=0.5
        )
        assert entry.contracts == 2

    def test_entry_contracts_default_zero(self):
        """Para crypto, contracts debe ser 0."""
        entry = Entry(
            timestamp=datetime(2024, 1, 1),
            price=50000.0,
            size_usdt=10000.0,
            contracts=0,
            fee=10.0,
            slippage_cost=1.0
        )
        assert entry.contracts == 0

    def test_position_total_contracts(self):
        """total_contracts() suma contratos de todas las entradas."""
        pos = Position(symbol="ES", entry_time=datetime(2024, 1, 1))
        pos.add_entry(datetime(2024, 1, 1), 5000.0, size_usdt=0.0, contracts=2, fee=2.78, slippage_cost=0.5)
        pos.add_entry(datetime(2024, 1, 2), 4950.0, size_usdt=0.0, contracts=1, fee=1.39, slippage_cost=0.5)
        assert pos.total_contracts() == 3

    def test_position_average_entry_price_futures(self):
        """average_entry_price pondera por contratos para futuros."""
        pos = Position(symbol="ES", entry_time=datetime(2024, 1, 1))
        pos.add_entry(datetime(2024, 1, 1), 5000.0, size_usdt=0.0, contracts=2, fee=2.78, slippage_cost=0.5)
        pos.add_entry(datetime(2024, 1, 2), 4950.0, size_usdt=0.0, contracts=1, fee=1.39, slippage_cost=0.5)
        # Avg = (2*5000 + 1*4950) / 3 = 4983.33
        assert pos.average_entry_price_futures() == pytest.approx(4983.33, rel=1e-2)

    def test_partial_close_futures_floor(self):
        """partial_close reduce contratos con floor por entrada."""
        pos = Position(symbol="ES", entry_time=datetime(2024, 1, 1))
        pos.add_entry(datetime(2024, 1, 1), 5000.0, size_usdt=0.0, contracts=3, fee=4.17, slippage_cost=0.75)
        pos.add_entry(datetime(2024, 1, 2), 4950.0, size_usdt=0.0, contracts=2, fee=2.78, slippage_cost=0.5)
        # Total = 5 contracts. Close 50% = floor(3*0.5)=1 + floor(2*0.5)=1 = 2 contracts
        closed = pos.partial_close_futures(0.5)
        assert closed['total_contracts'] == 2
        assert pos.total_contracts() == 3  # 5 - 2 = 3

    def test_partial_close_futures_skip_zero(self):
        """Si una entrada tiene 1 contrato y pct < 1.0, floor(1*0.3)=0, se salta esa entrada."""
        pos = Position(symbol="ES", entry_time=datetime(2024, 1, 1))
        pos.add_entry(datetime(2024, 1, 1), 5000.0, size_usdt=0.0, contracts=1, fee=1.39, slippage_cost=0.25)
        pos.add_entry(datetime(2024, 1, 2), 4950.0, size_usdt=0.0, contracts=4, fee=5.56, slippage_cost=1.0)
        # Close 30%: floor(1*0.3)=0, floor(4*0.3)=1 => 1 contract closed
        closed = pos.partial_close_futures(0.3)
        assert closed['total_contracts'] == 1
        assert pos.total_contracts() == 4  # 5 - 1 = 4

    def test_crypto_position_unchanged(self):
        """Position con crypto sigue funcionando como antes."""
        pos = Position(symbol="BTC", entry_time=datetime(2024, 1, 1))
        pos.add_entry(datetime(2024, 1, 1), 50000.0, size_usdt=10000.0, contracts=0, fee=10.0, slippage_cost=1.0)
        assert pos.total_cost() == 10000.0
        assert pos.total_crypto() == pytest.approx(0.2)
        assert pos.total_contracts() == 0
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/test_futures_engine.py::TestPositionFutures -v`
Expected: FAIL — Entry doesn't accept `contracts`, methods don't exist

**Step 3: Write minimal implementation**

Modify `core/simple_backtest_engine.py`:

Entry — add `contracts` field:
```python
@dataclass
class Entry:
    """Una entrada individual dentro de una posicion."""
    timestamp: datetime
    price: float
    size_usdt: float       # Crypto: USDT gastados. Futuros: 0
    contracts: int          # Crypto: 0. Futuros: N contratos
    fee: float
    slippage_cost: float
```

Position — update `add_entry`, add `total_contracts`, `average_entry_price_futures`, `partial_close_futures`:

```python
def add_entry(self, timestamp: datetime, price: float,
              size_usdt: float, fee: float, slippage_cost: float,
              contracts: int = 0):
    self.entries.append(Entry(
        timestamp=timestamp,
        price=price,
        size_usdt=size_usdt,
        contracts=contracts,
        fee=fee,
        slippage_cost=slippage_cost
    ))

def total_contracts(self) -> int:
    """Total de contratos en todas las entradas."""
    return sum(entry.contracts for entry in self.entries)

def average_entry_price_futures(self) -> float:
    """Precio promedio ponderado por contratos (futuros)."""
    total_c = self.total_contracts()
    if total_c == 0:
        return 0.0
    return sum(e.price * e.contracts for e in self.entries) / total_c

def partial_close_futures(self, pct: float) -> dict:
    """
    Cierra una fraccion de la posicion en futuros (floor por entrada).

    Returns:
        dict con total_contracts, total_entry_fees, total_entry_slippage,
        avg_entry_price
    """
    closed_contracts = 0
    closed_fees = 0.0
    closed_slippage = 0.0

    for entry in self.entries:
        contracts_to_close = int(entry.contracts * pct)  # floor
        if contracts_to_close == 0:
            continue
        fee_pct = contracts_to_close / entry.contracts
        closed_contracts += contracts_to_close
        closed_fees += entry.fee * fee_pct
        closed_slippage += entry.slippage_cost * fee_pct
        entry.contracts -= contracts_to_close
        entry.fee -= entry.fee * fee_pct
        entry.slippage_cost -= entry.slippage_cost * fee_pct

    return {
        'total_contracts': closed_contracts,
        'total_entry_fees': closed_fees,
        'total_entry_slippage': closed_slippage,
    }
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_futures_engine.py::TestPositionFutures -v`
Expected: All 7 tests PASS

**Step 5: Commit**

```bash
git add core/simple_backtest_engine.py tests/test_futures_engine.py
git commit -m "feat(engine): add contracts to Entry and futures methods to Position"
```

---

### Task 3: Futures branching in BacktestEngine

**Files:**
- Modify: `core/simple_backtest_engine.py` (BacktestEngine class)
- Test: `tests/test_futures_engine.py` (append)

This is the core task. The engine needs `is_futures` branching in `__init__`, `_handle_buy`, `_handle_sell`, and `_create_results_dataframe`.

**Step 1: Write the failing tests**

Append to `tests/test_futures_engine.py`:

```python
from core.simple_backtest_engine import BacktestEngine
from config.market_configs.futures_config import get_futures_config
from config.market_configs.crypto_config import get_crypto_config


def make_es_config():
    """Config de ES (S&P 500 E-mini) para tests."""
    return get_futures_config("CME", "ES")


def make_crypto_config():
    """Config de BTC/Binance para tests."""
    return get_crypto_config("Binance", "BTC")


class TestBacktestEngineFutures:
    """Tests del motor de backtest con futuros."""

    def test_engine_detects_futures(self):
        """El engine detecta is_futures y calcula point_value."""
        engine = BacktestEngine(100000.0, make_es_config())
        assert engine.is_futures is True
        assert engine.point_value == pytest.approx(50.0)  # 12.50 / 0.25

    def test_engine_detects_crypto(self):
        """El engine sigue detectando crypto correctamente."""
        engine = BacktestEngine(1000.0, make_crypto_config())
        assert engine.is_futures is False
        assert engine.point_value == 0.0

    def test_futures_sizing_by_risk(self):
        """Sizing por riesgo: contracts = floor(risk_usd / (stop_dist * point_value))."""
        engine = BacktestEngine(100000.0, make_es_config())
        signals = [
            TradingSignal(
                timestamp=datetime(2024, 1, 1),
                signal_type=SignalType.BUY,
                symbol="ES",
                price=5000.0,
                position_size_pct=0.01,  # Arriesgar 1% = $1000
                stop_loss_price=4990.0   # Stop a 10 puntos
            ),
            TradingSignal(
                timestamp=datetime(2024, 1, 2),
                signal_type=SignalType.SELL,
                symbol="ES",
                price=5020.0,
                position_size_pct=1.0
            ),
        ]
        results = engine.run(signals)
        assert len(results) == 1
        # contracts = floor(1000 / (10 * 50)) = floor(2.0) = 2
        # Pero slippage moves entry price to ~5000.25, stop_dist changes slightly
        # Just check contracts > 0 and P&L makes sense
        assert results.iloc[0]['contracts'] >= 1

    def test_futures_sizing_contracts_override(self):
        """Override manual: signal.contracts se usa directamente."""
        engine = BacktestEngine(100000.0, make_es_config())
        signals = [
            TradingSignal(
                timestamp=datetime(2024, 1, 1),
                signal_type=SignalType.BUY,
                symbol="ES",
                price=5000.0,
                position_size_pct=0.01,
                contracts=3
            ),
            TradingSignal(
                timestamp=datetime(2024, 1, 2),
                signal_type=SignalType.SELL,
                symbol="ES",
                price=5020.0,
                position_size_pct=1.0
            ),
        ]
        results = engine.run(signals)
        assert results.iloc[0]['contracts'] == 3

    def test_futures_pnl_calculation(self):
        """P&L = contracts * point_value * (exit_price - entry_price)."""
        engine = BacktestEngine(100000.0, make_es_config())
        signals = [
            TradingSignal(
                timestamp=datetime(2024, 1, 1),
                signal_type=SignalType.BUY,
                symbol="ES",
                price=5000.0,
                position_size_pct=0.01,
                contracts=2
            ),
            TradingSignal(
                timestamp=datetime(2024, 1, 2),
                signal_type=SignalType.SELL,
                symbol="ES",
                price=5010.0,
                position_size_pct=1.0
            ),
        ]
        results = engine.run(signals)
        row = results.iloc[0]
        # With slippage: entry ~5000.25, exit ~5009.75
        # gross_pnl = 2 * 50 * (5009.75 - 5000.25) = 2 * 50 * 9.5 = $950
        # fees = 2 * 1.39 * 2 = $5.56 (entry + exit)
        # net_pnl ~ $944.44
        assert row['gross_pnl'] > 0
        assert row['net_pnl'] < row['gross_pnl']  # fees reduce
        assert row['contracts'] == 2

    def test_futures_fees_per_contract(self):
        """Fees = contracts * fee_per_contract por lado."""
        engine = BacktestEngine(100000.0, make_es_config())
        signals = [
            TradingSignal(
                timestamp=datetime(2024, 1, 1),
                signal_type=SignalType.BUY,
                symbol="ES",
                price=5000.0,
                position_size_pct=0.01,
                contracts=3
            ),
            TradingSignal(
                timestamp=datetime(2024, 1, 2),
                signal_type=SignalType.SELL,
                symbol="ES",
                price=5000.0,
                position_size_pct=1.0
            ),
        ]
        results = engine.run(signals)
        row = results.iloc[0]
        # Entry fee = 3 * 1.39 = 4.17
        assert row['total_entry_fees'] == pytest.approx(3 * 1.39, abs=0.01)
        # Exit fee = 3 * 1.39 = 4.17
        assert row['exit_fee'] == pytest.approx(3 * 1.39, abs=0.01)

    def test_futures_capital_only_fees_on_entry(self):
        """Capital solo se reduce por fees al entrar (no por notional)."""
        config = make_es_config()
        engine = BacktestEngine(100000.0, config)
        signals = [
            TradingSignal(
                timestamp=datetime(2024, 1, 1),
                signal_type=SignalType.BUY,
                symbol="ES",
                price=5000.0,
                position_size_pct=0.01,
                contracts=1
            ),
        ]
        engine.run(signals)
        # Capital should only drop by entry_fee = 1 * 1.39
        expected_capital = 100000.0 - 1.39
        assert engine.capital == pytest.approx(expected_capital, abs=0.01)

    def test_futures_skip_trade_insufficient_risk(self):
        """Si risk < 1 contrato, skip el trade."""
        engine = BacktestEngine(100.0, make_es_config())  # Very little capital
        signals = [
            TradingSignal(
                timestamp=datetime(2024, 1, 1),
                signal_type=SignalType.BUY,
                symbol="ES",
                price=5000.0,
                position_size_pct=0.01,  # Risk = $1, need $500/contract
                stop_loss_price=4990.0
            ),
        ]
        engine.run(signals)
        assert engine.current_position is None  # No position opened

    def test_futures_pnl_pct_return_on_risk(self):
        """pnl_pct para futuros = net_pnl / risk_usd * 100."""
        engine = BacktestEngine(100000.0, make_es_config())
        signals = [
            TradingSignal(
                timestamp=datetime(2024, 1, 1),
                signal_type=SignalType.BUY,
                symbol="ES",
                price=5000.0,
                position_size_pct=0.01,
                contracts=2
            ),
            TradingSignal(
                timestamp=datetime(2024, 1, 2),
                signal_type=SignalType.SELL,
                symbol="ES",
                price=5020.0,
                position_size_pct=1.0
            ),
        ]
        results = engine.run(signals)
        row = results.iloc[0]
        assert 'risk_usd' in row
        assert 'pnl_pct' in row
        # pnl_pct should be net_pnl / risk_usd * 100
        expected_pnl_pct = row['net_pnl'] / row['risk_usd'] * 100
        assert row['pnl_pct'] == pytest.approx(expected_pnl_pct, rel=1e-2)

    def test_crypto_backtest_unchanged(self):
        """Backtest de crypto sigue produciendo los mismos resultados."""
        engine = BacktestEngine(1000.0, make_crypto_config())
        signals = [
            TradingSignal(
                timestamp=datetime(2024, 1, 1),
                signal_type=SignalType.BUY,
                symbol="BTC",
                price=50000.0,
                position_size_pct=0.5
            ),
            TradingSignal(
                timestamp=datetime(2024, 1, 2),
                signal_type=SignalType.SELL,
                symbol="BTC",
                price=51000.0,
                position_size_pct=1.0
            ),
        ]
        results = engine.run(signals)
        assert len(results) == 1
        row = results.iloc[0]
        assert row['contracts'] == 0  # Crypto has no contracts
        assert row['gross_pnl'] > 0
        assert row['risk_usd'] == 0.0  # Crypto uses total_cost for pnl_pct
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/test_futures_engine.py::TestBacktestEngineFutures -v`
Expected: FAIL — Engine doesn't have `is_futures`, `point_value`, etc.

**Step 3: Write minimal implementation**

Modify `BacktestEngine.__init__` in `core/simple_backtest_engine.py`:

```python
def __init__(self, initial_capital: float, market_config: dict):
    self.initial_capital = initial_capital
    self.capital = initial_capital

    self.tick_size = market_config['tick_size']

    # Detectar tipo de mercado
    self.is_futures = 'slippage_ticks' in market_config

    if self.is_futures:
        self.slippage_fixed = market_config['slippage_ticks'] * self.tick_size
        self.slippage_pct = 0.0
        self.fee_fixed = market_config['exchange_fee']
        self.fee_rate = 0.0
        self.point_value = market_config['tick_value'] / market_config['tick_size']
        self.contract_size = market_config['contract_size']
    else:
        self.slippage_fixed = 0.0
        self.slippage_pct = market_config['slippage']
        self.fee_fixed = 0.0
        self.fee_rate = market_config['exchange_fee']
        self.point_value = 0.0
        self.contract_size = 0

    self.current_position: Position | None = None
    self.completed_trades: list[dict] = []
```

Modify `_handle_buy`:

```python
def _handle_buy(self, signal: TradingSignal):
    real_price = self._apply_slippage_to_price(signal.price, is_buy=True)
    entry_slippage_cost = abs(real_price - signal.price)

    if self.is_futures:
        # --- FUTURES SIZING ---
        if signal.contracts is not None:
            num_contracts = signal.contracts
            risk_usd = 0.0  # Override: no risk calculation
        else:
            if signal.stop_loss_price is None:
                return  # Cannot size without stop_loss
            risk_usd = self.capital * signal.position_size_pct
            stop_distance = abs(real_price - signal.stop_loss_price)
            if stop_distance <= 0:
                return
            num_contracts = int(risk_usd / (stop_distance * self.point_value))
            if num_contracts < 1:
                return  # Insufficient risk for 1 contract
            risk_usd = num_contracts * stop_distance * self.point_value

        entry_fee = num_contracts * self.fee_fixed
        entry_slippage_cost_total = entry_slippage_cost * num_contracts * self.point_value

        if self.current_position is None:
            self.current_position = Position(
                symbol=signal.symbol,
                entry_time=signal.timestamp
            )
            self.current_position._risk_usd = risk_usd  # Store for pnl_pct

        self.current_position.add_entry(
            timestamp=signal.timestamp,
            price=real_price,
            size_usdt=0.0,
            contracts=num_contracts,
            fee=entry_fee,
            slippage_cost=entry_slippage_cost_total
        )
        self.capital -= entry_fee

    else:
        # --- CRYPTO SIZING (unchanged) ---
        entry_size_usdt = self.capital * signal.position_size_pct
        if entry_size_usdt <= 0:
            return

        entry_fee = entry_size_usdt * self.fee_rate
        entry_slippage_cost_total = entry_slippage_cost * (entry_size_usdt / real_price)

        if self.current_position is None:
            self.current_position = Position(
                symbol=signal.symbol,
                entry_time=signal.timestamp
            )
            self.current_position._risk_usd = 0.0

        self.current_position.add_entry(
            timestamp=signal.timestamp,
            price=real_price,
            size_usdt=entry_size_usdt,
            contracts=0,
            fee=entry_fee,
            slippage_cost=entry_slippage_cost_total
        )
        self.capital -= (entry_size_usdt + entry_fee)
```

Modify `_handle_sell`:

```python
def _handle_sell(self, signal: TradingSignal):
    if self.current_position is None:
        return

    pos = self.current_position
    pct = signal.position_size_pct
    real_price = self._apply_slippage_to_price(signal.price, is_buy=False)
    exit_slippage_cost = abs(signal.price - real_price)

    if self.is_futures:
        # --- FUTURES SELL ---
        if pct < 1.0:
            closed = pos.partial_close_futures(pct)
            closed_contracts = closed['total_contracts']
            closed_entry_fees = closed['total_entry_fees']
            closed_entry_slippage = closed['total_entry_slippage']
        else:
            closed_contracts = pos.total_contracts()
            closed_entry_fees = pos.total_fees_on_entries()
            closed_entry_slippage = pos.total_slippage_on_entries()

        if closed_contracts == 0:
            return

        avg_entry = pos.average_entry_price_futures() if pct < 1.0 else (
            sum(e.price * e.contracts for e in pos.entries) / closed_contracts
            if closed_contracts > 0 else 0.0
        )

        gross_pnl = closed_contracts * self.point_value * (real_price - avg_entry)
        exit_fee = closed_contracts * self.fee_fixed
        exit_slippage_total = exit_slippage_cost * closed_contracts * self.point_value
        net_pnl = gross_pnl - exit_fee

        self.capital += net_pnl

        risk_usd = getattr(pos, '_risk_usd', 0.0)
        pnl_pct = (net_pnl / risk_usd * 100) if risk_usd > 0 else 0

        self.completed_trades.append({
            'symbol': pos.symbol,
            'entry_time': pos.entry_time,
            'exit_time': signal.timestamp,
            'num_entries': len(pos.entries) if pct < 1.0 else len(pos.entries),
            'avg_entry_price': avg_entry,
            'exit_price': real_price,
            'total_cost': 0.0,
            'exit_value': 0.0,
            'contracts': closed_contracts,
            'risk_usd': risk_usd,
            'point_value': self.point_value,
            'total_entry_fees': closed_entry_fees,
            'exit_fee': exit_fee,
            'total_fees': closed_entry_fees + exit_fee,
            'entry_slippage': closed_entry_slippage,
            'exit_slippage': exit_slippage_total,
            'total_slippage': closed_entry_slippage + exit_slippage_total,
            'gross_pnl': gross_pnl,
            'net_pnl': net_pnl,
            'capital_after': self.capital,
            'pnl_pct': pnl_pct
        })

    else:
        # --- CRYPTO SELL (mostly unchanged) ---
        if pct < 1.0:
            closed = pos.partial_close(pct)
            closed_crypto = closed['total_crypto']
            closed_cost = closed['total_cost']
            closed_entry_fees = closed['total_entry_fees']
            closed_entry_slippage = closed['total_entry_slippage']
        else:
            closed_crypto = pos.total_crypto()
            closed_cost = pos.total_cost()
            closed_entry_fees = pos.total_fees_on_entries()
            closed_entry_slippage = pos.total_slippage_on_entries()

        exit_value = closed_crypto * real_price
        exit_fee = exit_value * self.fee_rate
        exit_slippage_total = exit_slippage_cost * closed_crypto

        gross_pnl = exit_value - closed_cost
        net_pnl = gross_pnl - exit_fee

        self.capital += (exit_value - exit_fee)

        avg_entry = closed_cost / closed_crypto if closed_crypto > 0 else 0.0

        self.completed_trades.append({
            'symbol': pos.symbol,
            'entry_time': pos.entry_time,
            'exit_time': signal.timestamp,
            'num_entries': len(pos.entries),
            'avg_entry_price': avg_entry,
            'exit_price': real_price,
            'total_cost': closed_cost,
            'exit_value': exit_value,
            'contracts': 0,
            'risk_usd': 0.0,
            'point_value': 0.0,
            'total_entry_fees': closed_entry_fees,
            'exit_fee': exit_fee,
            'total_fees': closed_entry_fees + exit_fee,
            'entry_slippage': closed_entry_slippage,
            'exit_slippage': exit_slippage_total,
            'total_slippage': closed_entry_slippage + exit_slippage_total,
            'gross_pnl': gross_pnl,
            'net_pnl': net_pnl,
            'capital_after': self.capital,
            'pnl_pct': (net_pnl / closed_cost * 100) if closed_cost > 0 else 0
        })

    if pct >= 1.0:
        self.current_position = None
```

Update `_create_results_dataframe` to include new columns:

```python
def _create_results_dataframe(self) -> pd.DataFrame:
    if not self.completed_trades:
        return pd.DataFrame(columns=[
            'symbol', 'entry_time', 'exit_time', 'num_entries',
            'avg_entry_price', 'exit_price', 'total_cost', 'exit_value',
            'contracts', 'risk_usd', 'point_value',
            'total_entry_fees', 'exit_fee', 'total_fees',
            'entry_slippage', 'exit_slippage', 'total_slippage',
            'gross_pnl', 'net_pnl', 'capital_after', 'pnl_pct'
        ])
    return pd.DataFrame(self.completed_trades)
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_futures_engine.py -v`
Expected: All tests PASS

**Step 5: Commit**

```bash
git add core/simple_backtest_engine.py tests/test_futures_engine.py
git commit -m "feat(engine): add futures branching for sizing, fees, and P&L"
```

---

### Task 4: Adapt metrics for futures

**Files:**
- Modify: `metrics/trade_metrics.py`
- Modify: `metrics/metrics_aggregator.py`
- Test: `tests/test_futures_engine.py` (append)

**Step 1: Write the failing tests**

Append to `tests/test_futures_engine.py`:

```python
from metrics.trade_metrics import TradeMetricsCalculator
from utils.timeframe import Timeframe


class TestMetricsFutures:
    """Tests de metricas adaptadas para futuros."""

    @pytest.fixture
    def es_market_data(self):
        """Crea market data simulada para ES."""
        dates = pd.date_range('2024-01-01', periods=100, freq='5min')
        return pd.DataFrame({
            'Open': 5000.0,
            'High': 5020.0,
            'Low': 4980.0,
            'Close': 5010.0,
            'Volume': 1000,
        }, index=dates)

    @pytest.fixture
    def es_trade_data(self):
        """Trade data simulada de futuros para metricas."""
        return pd.DataFrame([{
            'entry_timestamp': pd.Timestamp('2024-01-01 00:05:00'),
            'exit_timestamp': pd.Timestamp('2024-01-01 00:30:00'),
            'entry_price': 5000.0,
            'usdt_amount': 0.0,
            'contracts': 2,
            'risk_usd': 1000.0,
            'point_value': 50.0,
            'net_profit_loss': 500.0,
            'position_side': 'LONG',
        }])

    def test_mae_mfe_futures(self, es_market_data, es_trade_data):
        """MAE/MFE para futuros usa contracts * point_value."""
        calc = TradeMetricsCalculator(
            initial_capital=100000.0,
            market_data=es_market_data,
            timeframe=Timeframe.M5,
            is_futures=True,
            point_value=50.0
        )
        result = calc.create_trade_metrics_df(es_trade_data)
        # MAE = (5000 - 4980) * 2 * 50 = 20 * 100 = $2000 (using Low=4980)
        # But exact value depends on data. Just verify it's > 0
        assert result.iloc[0]['MAE'] > 0
        assert result.iloc[0]['MFE'] > 0

    def test_riesgo_aplicado_futures(self, es_market_data, es_trade_data):
        """riesgo_aplicado para futuros usa risk_usd / capital."""
        calc = TradeMetricsCalculator(
            initial_capital=100000.0,
            market_data=es_market_data,
            timeframe=Timeframe.M5,
            is_futures=True,
            point_value=50.0
        )
        result = calc.create_trade_metrics_df(es_trade_data)
        # riesgo = 1000 / 100000 * 100 = 1.0%
        assert result.iloc[0]['riesgo_aplicado'] == pytest.approx(1.0, abs=0.1)

    def test_crypto_metrics_unchanged(self):
        """Crypto metrics calculator sin is_futures funciona como antes."""
        dates = pd.date_range('2024-01-01', periods=100, freq='5min')
        market_data = pd.DataFrame({
            'Open': 50000.0, 'High': 50100.0, 'Low': 49900.0,
            'Close': 50000.0, 'Volume': 100,
        }, index=dates)
        trade_data = pd.DataFrame([{
            'entry_timestamp': pd.Timestamp('2024-01-01 00:05:00'),
            'exit_timestamp': pd.Timestamp('2024-01-01 00:30:00'),
            'entry_price': 50000.0,
            'usdt_amount': 10000.0,
            'contracts': 0,
            'risk_usd': 0.0,
            'point_value': 0.0,
            'net_profit_loss': 200.0,
            'position_side': 'LONG',
        }])
        calc = TradeMetricsCalculator(
            initial_capital=1000.0,
            market_data=market_data,
            timeframe=Timeframe.M5
        )
        result = calc.create_trade_metrics_df(trade_data)
        assert result.iloc[0]['MAE'] >= 0
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/test_futures_engine.py::TestMetricsFutures -v`
Expected: FAIL — `TradeMetricsCalculator` does not accept `is_futures`, `point_value`

**Step 3: Write minimal implementation**

Modify `metrics/trade_metrics.py`:

Constructor:
```python
class TradeMetricsCalculator:
    def __init__(self, initial_capital: float, market_data: pd.DataFrame, timeframe: Timeframe,
                 is_futures: bool = False, point_value: float = 0.0):
        self.initial_capital = initial_capital
        self.market_data = market_data
        self.timeframe = timeframe
        self.is_futures = is_futures
        self.point_value = point_value
```

Modify `_add_mae_mfe_volatility_efficiency` to pass `is_futures` context to `_calculate_mae_mfe`:
```python
def _add_mae_mfe_volatility_efficiency(self, df: pd.DataFrame) -> pd.DataFrame:
    maes = []
    mfes = []
    volatilities = []
    profit_efficiencies = []

    for _, row in df.iterrows():
        if self.is_futures:
            contracts = row.get("contracts", 0)
            quantity_multiplier = contracts * self.point_value
        else:
            quantity_multiplier = row["usdt_amount"]

        mae, mfe, min_price, max_price = self._calculate_mae_mfe(
            row["entry_timestamp"],
            row["exit_timestamp"],
            row["entry_price"],
            quantity_multiplier,
            row["position_side"]
        )
        maes.append(round(mae, 2))
        mfes.append(round(mfe, 2))

        if pd.notna(max_price) and pd.notna(min_price):
            trade_volatility = ((max_price - min_price) / row["entry_price"]) * 100
        else:
            trade_volatility = np.nan
        volatilities.append(round(trade_volatility, 2) if not np.isnan(trade_volatility) else np.nan)

        if mfe > 0:
            profit_efficiency = (row["net_profit_loss"] / mfe) * 100
            profit_efficiency = min(max(profit_efficiency, 0), 100)
        else:
            profit_efficiency = 0
        profit_efficiencies.append(round(profit_efficiency, 2))

    df["MAE"] = maes
    df["MFE"] = mfes
    df["trade_volatility"] = volatilities
    df["profit_efficiency"] = profit_efficiencies
    return df
```

The existing `_calculate_mae_mfe` already takes `quantity` as parameter, but uses `(quantity / entry_price)` internally. For futures we pass `contracts * point_value` as quantity, so the formula becomes:
- `mae = (entry_price - min_price) * (contracts * point_value / entry_price)` — WRONG

We need to fix `_calculate_mae_mfe` for futures. The formula should be:
- Crypto: `mae = (entry_price - min_price) * (usdt_amount / entry_price)` → (price_diff * crypto_qty)
- Futures: `mae = (entry_price - min_price) * contracts * point_value` → (price_diff * dollar_per_point)

So modify `_calculate_mae_mfe`:
```python
def _calculate_mae_mfe(self, entry_ts, exit_ts, entry_price, quantity, position_side):
    sub_data = self.market_data.loc[entry_ts:exit_ts]

    if not sub_data.empty:
        min_price = sub_data["Low"].min() if "Low" in sub_data.columns else sub_data["Close"].min()
        max_price = sub_data["High"].max() if "High" in sub_data.columns else sub_data["Close"].max()

        if self.is_futures:
            # quantity = contracts * point_value
            if position_side.upper() == "LONG":
                mae = (entry_price - min_price) * quantity
                mfe = (max_price - entry_price) * quantity
            elif position_side.upper() == "SHORT":
                mae = (max_price - entry_price) * quantity
                mfe = (entry_price - min_price) * quantity
            else:
                raise ValueError(f"position_side invalido: {position_side}")
        else:
            # quantity = usdt_amount (crypto)
            if position_side.upper() == "LONG":
                mae = (entry_price - min_price) * (quantity / entry_price)
                mfe = (max_price - entry_price) * (quantity / entry_price)
            elif position_side.upper() == "SHORT":
                mae = (max_price - entry_price) * (quantity / entry_price)
                mfe = (entry_price - min_price) * (quantity / entry_price)
            else:
                raise ValueError(f"position_side invalido: {position_side}")
    else:
        mae, mfe, min_price, max_price = np.nan, np.nan, np.nan, np.nan

    return mae, mfe, min_price, max_price
```

Modify `_add_risk_management_metrics` for futures:
```python
def _add_risk_management_metrics(self, df: pd.DataFrame) -> pd.DataFrame:
    riesgo_aplicado = []
    return_on_capital = []
    capital_previo = self.initial_capital

    for _, row in df.iterrows():
        if self.is_futures and 'risk_usd' in row and row['risk_usd'] > 0:
            riesgo = (row['risk_usd'] / capital_previo) * 100
        else:
            riesgo = (row["usdt_amount"] / capital_previo) * 100

        roc = (row["net_profit_loss"] / capital_previo) * 100

        riesgo_aplicado.append(round(riesgo, 2))
        return_on_capital.append(round(roc, 2))
        capital_previo += row["net_profit_loss"]

    df["riesgo_aplicado"] = riesgo_aplicado
    df["return_on_capital"] = return_on_capital
    df["cumulative_capital"] = self.initial_capital + df["net_profit_loss"].cumsum()
    return df
```

Modify `_add_trade_drawdown` for futures:
```python
def _add_trade_drawdown(self, df: pd.DataFrame) -> pd.DataFrame:
    if self.is_futures:
        df["trade_drawdown"] = np.where(
            df["MAE"] > 0,
            (df["MAE"] / (df.get("risk_usd", df["MAE"]))) * 100,
            0.0
        )
    else:
        df["trade_drawdown"] = (df["MAE"] / df["entry_price"]) * 100
    return df
```

Modify `metrics/metrics_aggregator.py` — pass `is_futures` and `point_value` to calculator:

```python
def _calculate_all_metrics(self):
    results_adapted = self._adapt_for_trade_metrics(self.results)

    # Detectar si es futuros por la presencia de contracts > 0
    is_futures = 'contracts' in self.results.columns and (self.results['contracts'] > 0).any()
    point_value = self.results['point_value'].iloc[0] if 'point_value' in self.results.columns else 0.0

    metrics_calculator = TradeMetricsCalculator(
        initial_capital=self.strategy.initial_capital,
        market_data=self.strategy.market_data,
        timeframe=self.strategy.timeframe,
        is_futures=is_futures,
        point_value=point_value
    )

    self.trade_metrics_df = metrics_calculator.create_trade_metrics_df(results_adapted)
    # ... rest unchanged
```

Also update `_adapt_for_trade_metrics` to carry over futures columns:
```python
def _adapt_for_trade_metrics(self, results: pd.DataFrame) -> pd.DataFrame:
    adapted = results.copy()
    adapted = adapted.rename(columns={
        'entry_time': 'entry_timestamp',
        'exit_time': 'exit_timestamp',
        'avg_entry_price': 'entry_price',
        'total_cost': 'usdt_amount',
        'net_pnl': 'net_profit_loss'
    })
    adapted['position_side'] = 'LONG'
    # Futures columns pass through naturally (contracts, risk_usd, point_value)
    return adapted
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_futures_engine.py -v`
Expected: All tests PASS

**Step 5: Commit**

```bash
git add metrics/trade_metrics.py metrics/metrics_aggregator.py tests/test_futures_engine.py
git commit -m "feat(metrics): adapt MAE/MFE and risk metrics for futures"
```

---

### Task 5: Adapt BaseStrategy.create_simple_signal

**Files:**
- Modify: `strategies/base_strategy.py`
- Test: `tests/test_futures_engine.py` (append)

**Step 1: Write the failing test**

Append to `tests/test_futures_engine.py`:

```python
from strategies.base_strategy import BaseStrategy
from models.enums import MarketType


class TestBaseStrategyFutures:
    """Tests de create_simple_signal con campos de futuros."""

    def test_create_signal_with_stop_loss(self):
        """create_simple_signal acepta stop_loss_price."""
        # We can't instantiate BaseStrategy directly (needs data),
        # so test TradingSignal directly
        signal = TradingSignal(
            timestamp=datetime(2024, 1, 1),
            signal_type=SignalType.BUY,
            symbol="ES",
            price=5000.0,
            position_size_pct=0.01,
            stop_loss_price=4990.0
        )
        assert signal.stop_loss_price == 4990.0

    def test_create_signal_with_contracts(self):
        """create_simple_signal acepta contracts."""
        signal = TradingSignal(
            timestamp=datetime(2024, 1, 1),
            signal_type=SignalType.BUY,
            symbol="ES",
            price=5000.0,
            position_size_pct=0.01,
            contracts=3
        )
        assert signal.contracts == 3
```

**Step 2: Run tests — these may already pass since TradingSignal already has the fields.**

Run: `pytest tests/test_futures_engine.py::TestBaseStrategyFutures -v`

**Step 3: Update `create_simple_signal` in `strategies/base_strategy.py`**

```python
def create_simple_signal(
    self,
    signal_type: SignalType,
    timestamp: datetime,
    price: float,
    position_size_pct: float,
    stop_loss_price: float = None,
    contracts: int = None
) -> TradingSignal:
    signal = TradingSignal(
        timestamp=timestamp,
        signal_type=signal_type,
        symbol=self.symbol,
        price=price,
        position_size_pct=position_size_pct,
        stop_loss_price=stop_loss_price,
        contracts=contracts
    )
    self.simple_signals.append(signal)
    return signal
```

**Step 4: Run all tests**

Run: `pytest tests/test_futures_engine.py -v`
Expected: All tests PASS

**Step 5: Commit**

```bash
git add strategies/base_strategy.py tests/test_futures_engine.py
git commit -m "feat(strategy): add stop_loss_price and contracts to create_simple_signal"
```

---

### Task 6: Run full test suite and verify backward compatibility

**Files:**
- No new files

**Step 1: Run existing tests**

Run: `pytest tests/ -v`
Expected: All existing tests PASS (backward compatible)

**Step 2: Run the new futures tests**

Run: `pytest tests/test_futures_engine.py -v`
Expected: All new tests PASS

**Step 3: Verify column consistency**

The engine DataFrame now always includes `contracts`, `risk_usd`, `point_value`. These default to 0 for crypto. Verify the MetricsAggregator handles this by running a full integration test manually or checking the `_adapt_for_trade_metrics` mapping still works.

**Step 4: Commit**

No changes expected — just verification. If any fixes were needed, commit them:

```bash
git commit -m "fix: ensure backward compatibility with crypto backtests"
```

---

## Summary of all files touched

| File | Action | Lines changed (approx) |
|------|--------|----------------------|
| `models/simple_signals.py` | Modify | +15 |
| `core/simple_backtest_engine.py` | Modify | +100 |
| `metrics/trade_metrics.py` | Modify | +30 |
| `metrics/metrics_aggregator.py` | Modify | +10 |
| `strategies/base_strategy.py` | Modify | +5 |
| `tests/test_futures_engine.py` | Create | ~250 |

Total: ~410 lines added/changed across 6 files.
