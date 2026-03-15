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


import numpy as np
import pandas as pd
from core.backtest_runner import BacktestRunner
from models.enums import MarketType
from strategies.base_strategy import BaseStrategy
from utils.timeframe import Timeframe


def _create_synthetic_data(n_bars=200, seed=42):
    """Create synthetic OHLCV data for short metrics tests."""
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


class _DummyBase(BaseStrategy):
    """Minimal base for short metrics tests."""
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
        return self.simple_signals


class ShortDummyStrategy(_DummyBase):
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
        data = _create_synthetic_data(200, seed=42)
        strategy = ShortDummyStrategy(data=data)
        runner = BacktestRunner(strategy)
        runner.run(verbose=False)

        trade_df = runner.metrics.trade_metrics_df
        assert 'position_side' in trade_df.columns
        assert all(trade_df['position_side'] == 'SHORT')

    def test_all_metrics_computed_for_short(self):
        """all_metrics dict should be fully populated for SHORT trades."""
        data = _create_synthetic_data(200, seed=42)
        strategy = ShortDummyStrategy(data=data)
        runner = BacktestRunner(strategy)
        runner.run(verbose=False)

        metrics = runner.metrics.all_metrics
        assert 'sharpe_ratio' in metrics
        assert 'total_trades' in metrics
        assert metrics['total_trades'] > 0

    def test_mae_mfe_correct_for_short(self):
        """For SHORT: price going UP = MAE (adverse), DOWN = MFE (favorable)."""
        data = _create_synthetic_data(200, seed=42)
        strategy = ShortDummyStrategy(data=data)
        runner = BacktestRunner(strategy)
        runner.run(verbose=False)

        trade_df = runner.metrics.trade_metrics_df
        # MAE and MFE should be populated (not NaN)
        assert trade_df['MAE'].notna().any()
        assert trade_df['MFE'].notna().any()
