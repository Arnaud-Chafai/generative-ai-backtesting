"""
Test simple de ejemplo para verificar que el setup funciona correctamente.
"""

import pytest
from datetime import datetime


def test_suma_basica():
    """Test básico de suma para verificar que pytest funciona"""
    assert 2 + 2 == 4


def test_fixtures_basicas(sample_prices, initial_capital):
    """Test que usa fixtures del conftest.py"""
    # Verificar que las fixtures se cargan correctamente
    assert len(sample_prices) == 5
    assert sample_prices[0] == 50000.0
    assert initial_capital == 1000.0


def test_sample_ohlcv_data(sample_ohlcv_data):
    """Test que verifica los datos OHLCV generados"""
    # Verificar que el DataFrame tiene la estructura correcta
    assert len(sample_ohlcv_data) == 100
    assert 'Open' in sample_ohlcv_data.columns
    assert 'High' in sample_ohlcv_data.columns
    assert 'Low' in sample_ohlcv_data.columns
    assert 'Close' in sample_ohlcv_data.columns
    assert 'Volume' in sample_ohlcv_data.columns

    # Verificar que High >= Low en todas las velas
    assert (sample_ohlcv_data['High'] >= sample_ohlcv_data['Low']).all()


def test_sample_signals(sample_buy_signal, sample_sell_signal):
    """Test que verifica las señales de ejemplo"""
    # Verificar señal de compra
    assert sample_buy_signal.symbol == "BTCUSDT"
    assert sample_buy_signal.price == 50000.0
    assert sample_buy_signal.usdt_amount == 100.0

    # Verificar señal de venta
    assert sample_sell_signal.symbol == "BTCUSDT"
    assert sample_sell_signal.price == 51000.0
    assert sample_sell_signal.usdt_amount == 100.0

    # Verificar que la venta es después de la compra
    assert sample_sell_signal.timestamp > sample_buy_signal.timestamp


def test_backtest_engine_initialization(backtest_engine, initial_capital):
    """Test que verifica la inicialización del BacktestEngine"""
    assert backtest_engine.initial_capital == initial_capital
    assert backtest_engine.current_capital == initial_capital
    assert len(backtest_engine.completed_trades) == 0


def test_position_manager_initialization(position_manager):
    """Test que verifica la inicialización del PositionManager"""
    # Verificar que no hay posiciones abiertas al inicio
    assert not position_manager.has_position("BTCUSDT")
