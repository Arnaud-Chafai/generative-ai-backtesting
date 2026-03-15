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
