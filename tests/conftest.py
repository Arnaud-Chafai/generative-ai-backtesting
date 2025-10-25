"""
Pytest configuration and shared fixtures for backtesting tests.

This file contains common fixtures used across all test modules.
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List

# Import models and enums
from models.enums import SignalType, OrderType, CurrencyType, ExchangeName, MarketType, SignalPositionSide
from models._deprecateds_ignals import StrategySignal
from models.trades.crypto_trade import CryptoTrade
from models.markets.crypto_market import CryptoMarketDefinition
from utils.timeframe import Timeframe

# Import core components
from core.backtest_engine import BacktestEngine
from core.position_manager import PositionManager


# ============================================================================
# BASIC DATA FIXTURES
# ============================================================================

@pytest.fixture
def sample_ohlcv_data() -> pd.DataFrame:
    """
    Creates sample OHLCV data for testing.

    Returns:
        DataFrame with columns: Time, Open, High, Low, Close, Volume
    """
    dates = pd.date_range(start='2024-01-01', periods=100, freq='1h')

    # Generate realistic-looking price data
    np.random.seed(42)
    base_price = 50000.0
    returns = np.random.randn(100) * 0.01  # 1% volatility
    close_prices = base_price * (1 + returns).cumprod()

    df = pd.DataFrame({
        'Time': dates,
        'Open': close_prices * (1 + np.random.randn(100) * 0.001),
        'High': close_prices * (1 + abs(np.random.randn(100)) * 0.002),
        'Low': close_prices * (1 - abs(np.random.randn(100)) * 0.002),
        'Close': close_prices,
        'Volume': np.random.randint(100, 1000, 100)
    })

    df.set_index('Time', inplace=True)
    return df


@pytest.fixture
def sample_prices() -> List[float]:
    """Returns a list of sample prices for testing."""
    return [50000.0, 51000.0, 49500.0, 52000.0, 50500.0]


@pytest.fixture
def sample_timestamps() -> List[datetime]:
    """Returns a list of sample timestamps for testing."""
    base = datetime(2024, 1, 1, 0, 0, 0)
    return [base + timedelta(hours=i) for i in range(10)]


# ============================================================================
# MARKET CONFIGURATION FIXTURES
# ============================================================================

@pytest.fixture
def crypto_market_config() -> CryptoMarketDefinition:
    """Creates a standard crypto market configuration."""
    return CryptoMarketDefinition(
        market=MarketType.CRYPTO.value,
        symbol="BTCUSDT",
        exchange="Binance"
    )


@pytest.fixture
def initial_capital() -> float:
    """Standard initial capital for testing."""
    return 1000.0


# ============================================================================
# SIGNAL FIXTURES
# ============================================================================

@pytest.fixture
def sample_buy_signal(sample_timestamps) -> StrategySignal:
    """Creates a sample BUY signal for testing."""
    return StrategySignal(
        id="test-signal-buy-001",
        market=MarketType.CRYPTO,
        exchange=ExchangeName.BINANCE,
        strategy_name="TestStrategy",
        symbol="BTCUSDT",
        currency=CurrencyType.USDT,
        timeframe=Timeframe.H1,
        signal_type=SignalType.BUY,
        order_type=OrderType.MARKET,
        usdt_amount=100.0,
        price=50000.0,
        slippage_pct=0.001,
        slippage_cost=0.05,
        timestamp=sample_timestamps[0],
        stop_loss=None,
        take_profit=None,
        fee=0.075,
        position_side=SignalPositionSide.LONG
    )


@pytest.fixture
def sample_sell_signal(sample_timestamps) -> StrategySignal:
    """Creates a sample SELL signal for testing."""
    return StrategySignal(
        id="test-signal-sell-001",
        market=MarketType.CRYPTO,
        exchange=ExchangeName.BINANCE,
        strategy_name="TestStrategy",
        symbol="BTCUSDT",
        currency=CurrencyType.USDT,
        timeframe=Timeframe.H1,
        signal_type=SignalType.SELL,
        order_type=OrderType.MARKET,
        usdt_amount=100.0,
        price=51000.0,
        slippage_pct=0.001,
        slippage_cost=0.051,
        timestamp=sample_timestamps[1],
        stop_loss=None,
        take_profit=None,
        fee=0.075,
        position_side=SignalPositionSide.LONG
    )


@pytest.fixture
def sample_signal_pair(sample_buy_signal, sample_sell_signal) -> List[StrategySignal]:
    """Creates a pair of BUY and SELL signals for testing complete trades."""
    return [sample_buy_signal, sample_sell_signal]


# ============================================================================
# TRADE FIXTURES
# ============================================================================

@pytest.fixture
def sample_crypto_trade(sample_timestamps) -> CryptoTrade:
    """Creates a sample crypto trade with entry."""
    trade = CryptoTrade(
        symbol="BTCUSDT",
        entry_time=sample_timestamps[0],
        exchange="Binance"
    )

    # Add entry
    trade.add_entry(
        timestamp=sample_timestamps[0],
        signal_type=SignalType.BUY,
        volume=0.002,  # 100 USDT / 50000 price
        price=50000.0
    )

    return trade


@pytest.fixture
def completed_crypto_trade(sample_crypto_trade, sample_timestamps) -> CryptoTrade:
    """Creates a completed crypto trade with entry and exit."""
    # Add exit to the trade
    sample_crypto_trade.add_exit(
        timestamp=sample_timestamps[1],
        signal_type=SignalType.SELL,
        volume=0.002,
        price=51000.0
    )

    # Calculate P&L
    sample_crypto_trade.calculate_pnl()

    return sample_crypto_trade


# ============================================================================
# ENGINE AND MANAGER FIXTURES
# ============================================================================

@pytest.fixture
def backtest_engine(initial_capital) -> BacktestEngine:
    """Creates a fresh backtest engine instance."""
    return BacktestEngine(initial_capital=initial_capital)


@pytest.fixture
def position_manager() -> PositionManager:
    """Creates a fresh position manager instance."""
    return PositionManager()


# ============================================================================
# PARAMETRIZATION HELPERS
# ============================================================================

@pytest.fixture(params=[100.0, 500.0, 1000.0, 5000.0])
def various_capitals(request) -> float:
    """Parametrized fixture for testing with various capital amounts."""
    return request.param


@pytest.fixture(params=[0.0, 0.001, 0.002])
def various_slippages(request) -> float:
    """Parametrized fixture for testing with various slippage percentages."""
    return request.param


@pytest.fixture(params=[0.0, 0.00075, 0.001])
def various_fees(request) -> float:
    """Parametrized fixture for testing with various fee percentages."""
    return request.param


# ============================================================================
# CLEANUP AND TEARDOWN
# ============================================================================

@pytest.fixture(autouse=True)
def reset_random_seed():
    """
    Automatically resets numpy random seed before each test.
    This ensures reproducible results in tests that use random data.
    """
    np.random.seed(42)
    yield
    # Teardown code here if needed


@pytest.fixture
def temp_test_data_dir(tmp_path):
    """
    Creates a temporary directory for test data files.
    Automatically cleaned up after test completion.
    """
    data_dir = tmp_path / "test_data"
    data_dir.mkdir()
    return data_dir
