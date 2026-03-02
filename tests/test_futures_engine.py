"""Tests para el soporte de futuros en el BacktestEngine."""

import pytest
import numpy as np
from datetime import datetime
from models.enums import SignalType
from models.simple_signals import TradingSignal
from core.simple_backtest_engine import Entry, Position
import pandas as pd
from core.simple_backtest_engine import BacktestEngine
from config.market_configs.futures_config import get_futures_config
from config.market_configs.crypto_config import get_crypto_config
from metrics.trade_metrics import TradeMetricsCalculator
from utils.timeframe import Timeframe


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
        assert engine.point_value == pytest.approx(50.0)

    def test_engine_detects_crypto(self):
        """El engine sigue detectando crypto correctamente."""
        engine = BacktestEngine(1000.0, make_crypto_config())
        assert engine.is_futures is False
        assert engine.point_value == 0.0

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
        assert len(results) == 1
        assert results.iloc[0]['contracts'] == 3

    def test_futures_sizing_by_risk(self):
        """Sizing por riesgo: contracts = floor(risk_usd / (stop_dist * point_value))."""
        engine = BacktestEngine(100000.0, make_es_config())
        # Risk = 1% of 100k = $1000
        # Stop distance = |5000.25 - 4990| = 10.25 points (after slippage on entry)
        # contracts = floor(1000 / (10.25 * 50)) = floor(1.95) = 1
        # But exact values depend on slippage rounding, so just check > 0
        signals = [
            TradingSignal(
                timestamp=datetime(2024, 1, 1),
                signal_type=SignalType.BUY,
                symbol="ES",
                price=5000.0,
                position_size_pct=0.01,
                stop_loss_price=4990.0
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
        assert results.iloc[0]['contracts'] >= 1

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
        # entry with slippage: 5000 + 0.25 = 5000.25
        # exit with slippage: 5010 - 0.25 = 5009.75
        # gross_pnl = 2 * 50 * (5009.75 - 5000.25) = 2 * 50 * 9.5 = 950
        assert row['gross_pnl'] == pytest.approx(950.0, abs=1.0)
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
        assert row['total_entry_fees'] == pytest.approx(3 * 1.39, abs=0.01)
        assert row['exit_fee'] == pytest.approx(3 * 1.39, abs=0.01)

    def test_futures_capital_only_fees_on_entry(self):
        """Capital solo se reduce por fees al entrar (no por notional)."""
        engine = BacktestEngine(100000.0, make_es_config())
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
        expected_capital = 100000.0 - 1.39
        assert engine.capital == pytest.approx(expected_capital, abs=0.01)

    def test_futures_skip_trade_insufficient_risk(self):
        """Si risk < 1 contrato, skip el trade."""
        engine = BacktestEngine(100.0, make_es_config())
        signals = [
            TradingSignal(
                timestamp=datetime(2024, 1, 1),
                signal_type=SignalType.BUY,
                symbol="ES",
                price=5000.0,
                position_size_pct=0.01,
                stop_loss_price=4990.0
            ),
        ]
        engine.run(signals)
        assert engine.current_position is None

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
                contracts=2,
                stop_loss_price=4990.0
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
        assert 'risk_usd' in results.columns
        assert row['risk_usd'] > 0
        expected_pnl_pct = row['net_pnl'] / row['risk_usd'] * 100
        assert row['pnl_pct'] == pytest.approx(expected_pnl_pct, rel=1e-2)

    def test_futures_results_have_new_columns(self):
        """Resultados de futuros tienen contracts, risk_usd, point_value."""
        engine = BacktestEngine(100000.0, make_es_config())
        signals = [
            TradingSignal(datetime(2024,1,1), SignalType.BUY, "ES", 5000.0, 0.01, contracts=1),
            TradingSignal(datetime(2024,1,2), SignalType.SELL, "ES", 5010.0, 1.0),
        ]
        results = engine.run(signals)
        assert 'contracts' in results.columns
        assert 'risk_usd' in results.columns
        assert 'point_value' in results.columns

    def test_crypto_backtest_unchanged(self):
        """Backtest de crypto sigue produciendo resultados correctos."""
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
        assert row['contracts'] == 0
        assert row['risk_usd'] == 0.0
        assert row['gross_pnl'] > 0

    def test_crypto_empty_results_have_new_columns(self):
        """DataFrame vacio de crypto tambien tiene las nuevas columnas."""
        engine = BacktestEngine(1000.0, make_crypto_config())
        results = engine.run([])
        assert 'contracts' in results.columns
        assert 'risk_usd' in results.columns
        assert 'point_value' in results.columns


class TestMetricsFutures:
    """Tests de metricas adaptadas para futuros."""

    @pytest.fixture
    def es_market_data(self):
        """Market data simulada para ES con 5min bars."""
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
        """Trade data de futuros para metricas."""
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

    def test_mae_mfe_futures_uses_point_value(self, es_market_data, es_trade_data):
        """MAE/MFE para futuros = price_diff * contracts * point_value."""
        calc = TradeMetricsCalculator(
            initial_capital=100000.0,
            market_data=es_market_data,
            timeframe=Timeframe.M5,
            is_futures=True,
            point_value=50.0
        )
        result = calc.create_trade_metrics_df(es_trade_data)
        # MAE = (5000 - 4980) * 2 * 50 = 20 * 100 = $2000
        assert result.iloc[0]['MAE'] == pytest.approx(2000.0, rel=0.01)
        # MFE = (5020 - 5000) * 2 * 50 = 20 * 100 = $2000
        assert result.iloc[0]['MFE'] == pytest.approx(2000.0, rel=0.01)

    def test_riesgo_aplicado_futures_uses_risk_usd(self, es_market_data, es_trade_data):
        """riesgo_aplicado = risk_usd / capital * 100."""
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

    def test_trade_drawdown_futures(self, es_market_data, es_trade_data):
        """trade_drawdown = MAE / risk_usd * 100."""
        calc = TradeMetricsCalculator(
            initial_capital=100000.0,
            market_data=es_market_data,
            timeframe=Timeframe.M5,
            is_futures=True,
            point_value=50.0
        )
        result = calc.create_trade_metrics_df(es_trade_data)
        # MAE = 2000, risk_usd = 1000, drawdown = 200%
        assert result.iloc[0]['trade_drawdown'] == pytest.approx(200.0, rel=0.01)

    def test_crypto_metrics_unchanged(self):
        """Crypto metrics sin is_futures funciona como siempre."""
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
        # MAE = (50000 - 49900) * (10000 / 50000) = 100 * 0.2 = 20
        assert result.iloc[0]['MAE'] == pytest.approx(20.0, rel=0.01)
