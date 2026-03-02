"""Tests para el soporte de futuros en el BacktestEngine."""

import pytest
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
