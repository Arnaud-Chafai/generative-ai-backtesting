"""End-to-end integration tests for SHORT position support."""
import numpy as np
import pandas as pd
import pytest
from datetime import datetime

from core.backtest_runner import BacktestRunner
from models.enums import SignalType, SignalPositionSide, MarketType
from models.simple_signals import TradingSignal
from strategies.base_strategy import BaseStrategy
from utils.timeframe import Timeframe


def _create_synthetic_data(n_bars=500, seed=42):
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
        'Open': open_prices, 'High': high, 'Low': low,
        'Close': close, 'Volume': np.random.uniform(100, 1000, n_bars),
    }, index=dates)
    df.index.name = 'Time'
    return df


class _ShortStrategy(BaseStrategy):
    """SHORT strategy for integration tests."""
    def __init__(self, buy_every=20, hold_bars=10, **kwargs):
        super().__init__(
            market=MarketType.CRYPTO,
            symbol=kwargs.pop('symbol', 'BTC'),
            strategy_name='ShortIntegration',
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
                signal_type=SignalType.SELL,
                timestamp=df.index[i],
                price=df['Close'].iloc[i],
                position_size_pct=1.0,
                position_side=SignalPositionSide.SHORT,
            )
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


class _LongStrategy(BaseStrategy):
    """LONG strategy for regression tests."""
    def __init__(self, buy_every=20, hold_bars=10, **kwargs):
        super().__init__(
            market=MarketType.CRYPTO,
            symbol=kwargs.pop('symbol', 'BTC'),
            strategy_name='LongIntegration',
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


class TestShortIntegrationCrypto:
    def test_full_pipeline_short(self):
        """SHORT strategy -> runner -> engine -> metrics -> all_metrics."""
        data = _create_synthetic_data(500, seed=42)
        strategy = _ShortStrategy(data=data)
        runner = BacktestRunner(strategy)
        result = runner.run(verbose=False)

        assert 'position_side' in result.columns
        assert all(result['position_side'] == 'SHORT')

        metrics = runner.metrics.all_metrics
        assert metrics['total_trades'] > 0
        assert 'sharpe_ratio' in metrics
        assert 'max_drawdown' in metrics

    def test_long_regression(self):
        """LONG strategy must produce identical structure."""
        data = _create_synthetic_data(500, seed=42)
        strategy = _LongStrategy(data=data)
        runner = BacktestRunner(strategy)
        result = runner.run(verbose=False)

        assert 'position_side' in result.columns
        assert all(result['position_side'] == 'LONG')
        assert runner.metrics.all_metrics['total_trades'] > 0

    def test_validation_module_works_with_short(self):
        """Validation module should work transparently with SHORT."""
        from validation import MonteCarloValidator
        data = _create_synthetic_data(500, seed=42)
        strategy = _ShortStrategy(data=data)
        runner = BacktestRunner(strategy)
        runner.run(verbose=False)

        mc = MonteCarloValidator(
            trades_df=runner.metrics.trade_metrics_df,
            initial_capital=strategy.initial_capital,
        )
        result = mc.run(n_simulations=50, seed=42, verbose=False)
        assert result.p_value >= 0
