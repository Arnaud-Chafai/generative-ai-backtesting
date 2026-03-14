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
