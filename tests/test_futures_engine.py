"""Tests para el soporte de futuros en el BacktestEngine."""

import pytest
from datetime import datetime
from models.enums import SignalType
from models.simple_signals import TradingSignal
from core.simple_backtest_engine import Entry, Position


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
        """partial_close_futures reduce contratos con floor por entrada."""
        pos = Position(symbol="ES", entry_time=datetime(2024, 1, 1))
        pos.add_entry(datetime(2024, 1, 1), 5000.0, size_usdt=0.0, contracts=3, fee=4.17, slippage_cost=0.75)
        pos.add_entry(datetime(2024, 1, 2), 4950.0, size_usdt=0.0, contracts=2, fee=2.78, slippage_cost=0.5)
        # Total = 5 contracts. Close 50% = floor(3*0.5)=1 + floor(2*0.5)=1 = 2 contracts
        closed = pos.partial_close_futures(0.5)
        assert closed['total_contracts'] == 2
        assert pos.total_contracts() == 3  # 5 - 2 = 3

    def test_partial_close_futures_skip_zero(self):
        """Si floor da 0, se salta esa entrada."""
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
