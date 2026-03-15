"""Tests for SHORT position support."""
import pytest
from datetime import datetime
from models.enums import SignalType, SignalPositionSide
from models.simple_signals import TradingSignal
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


class TestShortCryptoEngine:
    def _make_engine(self, capital=1000.0):
        config = get_crypto_config('Binance', 'BTC')
        return BacktestEngine(initial_capital=capital, market_config=config)

    def test_short_basic_profit(self):
        engine = self._make_engine()
        signals = [
            _make_signal(SignalType.SELL, 100.0, SignalPositionSide.SHORT, ts=datetime(2024, 1, 1)),
            _make_signal(SignalType.BUY, 90.0, SignalPositionSide.SHORT, ts=datetime(2024, 1, 2)),
        ]
        df = engine.run(signals)
        assert len(df) == 1
        assert df['gross_pnl'].iloc[0] > 0
        assert df['position_side'].iloc[0] == 'SHORT'

    def test_short_basic_loss(self):
        engine = self._make_engine()
        signals = [
            _make_signal(SignalType.SELL, 100.0, SignalPositionSide.SHORT, ts=datetime(2024, 1, 1)),
            _make_signal(SignalType.BUY, 110.0, SignalPositionSide.SHORT, ts=datetime(2024, 1, 2)),
        ]
        df = engine.run(signals)
        assert len(df) == 1
        assert df['gross_pnl'].iloc[0] < 0

    def test_short_pnl_math(self):
        config = {'tick_size': 0.01, 'exchange_fee': 0.0, 'slippage': 0.0}
        engine = BacktestEngine(initial_capital=1000.0, market_config=config)
        signals = [
            _make_signal(SignalType.SELL, 100.0, SignalPositionSide.SHORT, ts=datetime(2024, 1, 1)),
            _make_signal(SignalType.BUY, 90.0, SignalPositionSide.SHORT, ts=datetime(2024, 1, 2)),
        ]
        df = engine.run(signals)
        assert abs(df['gross_pnl'].iloc[0] - 100.0) < 0.01

    def test_short_position_side_in_output(self):
        config = {'tick_size': 0.01, 'exchange_fee': 0.0, 'slippage': 0.0}
        engine = BacktestEngine(initial_capital=1000.0, market_config=config)
        signals = [
            _make_signal(SignalType.SELL, 100.0, SignalPositionSide.SHORT, ts=datetime(2024, 1, 1)),
            _make_signal(SignalType.BUY, 90.0, SignalPositionSide.SHORT, ts=datetime(2024, 1, 2)),
        ]
        df = engine.run(signals)
        assert 'position_side' in df.columns
        assert df['position_side'].iloc[0] == 'SHORT'

    def test_long_still_works(self):
        config = {'tick_size': 0.01, 'exchange_fee': 0.0, 'slippage': 0.0}
        engine = BacktestEngine(initial_capital=1000.0, market_config=config)
        signals = [
            _make_signal(SignalType.BUY, 100.0, SignalPositionSide.LONG, ts=datetime(2024, 1, 1)),
            _make_signal(SignalType.SELL, 110.0, SignalPositionSide.LONG, ts=datetime(2024, 1, 2)),
        ]
        df = engine.run(signals)
        assert len(df) == 1
        assert abs(df['gross_pnl'].iloc[0] - 100.0) < 0.01
        assert df['position_side'].iloc[0] == 'LONG'

    def test_long_default_without_position_side(self):
        config = {'tick_size': 0.01, 'exchange_fee': 0.0, 'slippage': 0.0}
        engine = BacktestEngine(initial_capital=1000.0, market_config=config)
        signals = [
            TradingSignal(timestamp=datetime(2024, 1, 1), signal_type=SignalType.BUY,
                         symbol='BTC', price=100.0, position_size_pct=1.0),
            TradingSignal(timestamp=datetime(2024, 1, 2), signal_type=SignalType.SELL,
                         symbol='BTC', price=110.0, position_size_pct=1.0),
        ]
        df = engine.run(signals)
        assert len(df) == 1
        assert df['position_side'].iloc[0] == 'LONG'
        assert df['gross_pnl'].iloc[0] > 0

    def test_ignore_mismatched_exit(self):
        config = {'tick_size': 0.01, 'exchange_fee': 0.0, 'slippage': 0.0}
        engine = BacktestEngine(initial_capital=1000.0, market_config=config)
        signals = [
            _make_signal(SignalType.SELL, 100.0, SignalPositionSide.SHORT, ts=datetime(2024, 1, 1)),
            _make_signal(SignalType.SELL, 95.0, SignalPositionSide.LONG, ts=datetime(2024, 1, 2)),
            _make_signal(SignalType.BUY, 90.0, SignalPositionSide.SHORT, ts=datetime(2024, 1, 3)),
        ]
        df = engine.run(signals)
        assert len(df) == 1

    def test_exit_short_without_position(self):
        config = {'tick_size': 0.01, 'exchange_fee': 0.0, 'slippage': 0.0}
        engine = BacktestEngine(initial_capital=1000.0, market_config=config)
        signals = [
            _make_signal(SignalType.BUY, 90.0, SignalPositionSide.SHORT, ts=datetime(2024, 1, 1)),
        ]
        df = engine.run(signals)
        assert len(df) == 0

    def test_short_dca(self):
        config = {'tick_size': 0.01, 'exchange_fee': 0.0, 'slippage': 0.0}
        engine = BacktestEngine(initial_capital=1000.0, market_config=config)
        signals = [
            _make_signal(SignalType.SELL, 100.0, SignalPositionSide.SHORT, pct=0.5, ts=datetime(2024, 1, 1)),
            _make_signal(SignalType.SELL, 105.0, SignalPositionSide.SHORT, pct=0.5, ts=datetime(2024, 1, 2)),
            _make_signal(SignalType.BUY, 90.0, SignalPositionSide.SHORT, ts=datetime(2024, 1, 3)),
        ]
        df = engine.run(signals)
        assert len(df) == 1
        assert df['gross_pnl'].iloc[0] > 0
        assert df['num_entries'].iloc[0] == 2

    def test_short_slippage_direction(self):
        config = {'tick_size': 0.01, 'exchange_fee': 0.0, 'slippage': 0.01}
        engine = BacktestEngine(initial_capital=1000.0, market_config=config)
        signals = [
            _make_signal(SignalType.SELL, 100.0, SignalPositionSide.SHORT, ts=datetime(2024, 1, 1)),
            _make_signal(SignalType.BUY, 90.0, SignalPositionSide.SHORT, ts=datetime(2024, 1, 2)),
        ]
        df = engine.run(signals)
        assert df['avg_entry_price'].iloc[0] < 100.0
        assert df['exit_price'].iloc[0] > 90.0

    def test_empty_dataframe_has_position_side(self):
        config = {'tick_size': 0.01, 'exchange_fee': 0.0, 'slippage': 0.0}
        engine = BacktestEngine(initial_capital=1000.0, market_config=config)
        df = engine.run([])
        assert 'position_side' in df.columns

    def test_short_partial_close(self):
        config = {'tick_size': 0.01, 'exchange_fee': 0.0, 'slippage': 0.0}
        engine = BacktestEngine(initial_capital=1000.0, market_config=config)
        signals = [
            _make_signal(SignalType.SELL, 100.0, SignalPositionSide.SHORT, ts=datetime(2024, 1, 1)),
            _make_signal(SignalType.BUY, 90.0, SignalPositionSide.SHORT, pct=0.5, ts=datetime(2024, 1, 2)),
            _make_signal(SignalType.BUY, 80.0, SignalPositionSide.SHORT, pct=1.0, ts=datetime(2024, 1, 3)),
        ]
        df = engine.run(signals)
        assert len(df) == 2
        assert all(df['position_side'] == 'SHORT')
        assert all(df['gross_pnl'] > 0)


class TestShortFuturesEngine:
    def _make_engine(self, capital=10000.0):
        from config.market_configs.futures_config import get_futures_config
        config = get_futures_config('CME', 'CL')
        return BacktestEngine(initial_capital=capital, market_config=config)

    def test_short_futures_profit(self):
        engine = self._make_engine()
        signals = [
            _make_signal(SignalType.SELL, 70.0, SignalPositionSide.SHORT,
                        ts=datetime(2024, 1, 1), symbol='CL', contracts=1),
            _make_signal(SignalType.BUY, 65.0, SignalPositionSide.SHORT,
                        ts=datetime(2024, 1, 2), symbol='CL'),
        ]
        df = engine.run(signals)
        assert len(df) == 1
        assert df['gross_pnl'].iloc[0] > 0
        assert df['position_side'].iloc[0] == 'SHORT'

    def test_short_futures_loss(self):
        engine = self._make_engine()
        signals = [
            _make_signal(SignalType.SELL, 70.0, SignalPositionSide.SHORT,
                        ts=datetime(2024, 1, 1), symbol='CL', contracts=1),
            _make_signal(SignalType.BUY, 75.0, SignalPositionSide.SHORT,
                        ts=datetime(2024, 1, 2), symbol='CL'),
        ]
        df = engine.run(signals)
        assert len(df) == 1
        assert df['gross_pnl'].iloc[0] < 0

    def test_long_futures_regression(self):
        engine = self._make_engine()
        signals = [
            _make_signal(SignalType.BUY, 70.0, SignalPositionSide.LONG,
                        ts=datetime(2024, 1, 1), symbol='CL', contracts=1),
            _make_signal(SignalType.SELL, 75.0, SignalPositionSide.LONG,
                        ts=datetime(2024, 1, 2), symbol='CL'),
        ]
        df = engine.run(signals)
        assert len(df) == 1
        assert df['gross_pnl'].iloc[0] > 0
        assert df['position_side'].iloc[0] == 'LONG'
