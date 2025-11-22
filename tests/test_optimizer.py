"""
Tests para el módulo de optimización.
"""

import pytest
import pandas as pd
from strategies.examples.breakout_simple import BreakoutSimple
from optimization.optimizer import ParameterOptimizer
from utils.timeframe import Timeframe
import os


@pytest.fixture
def sample_market_data():
    """Fixture que carga datos de muestra"""
    data_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'data/laboratory_data/BTC/Timeframe.M5.csv'
    )

    if not os.path.exists(data_path):
        pytest.skip(f"Datos no encontrados en {data_path}")

    df = pd.read_csv(data_path, index_col='Time', parse_dates=['Time'])
    # Retornar solo primeros 1000 candles para tests rápidos
    return df.iloc[:1000]


class TestParameterOptimizer:
    """Suite de tests para ParameterOptimizer"""

    def test_optimizer_init(self, sample_market_data):
        """Test: Crear optimizador correctamente"""
        optimizer = ParameterOptimizer(
            strategy_class=BreakoutSimple,
            market_data=sample_market_data,
            symbol='BTC',
            timeframe=Timeframe.M5,
            exchange='Binance',
            initial_capital=1000.0
        )

        assert optimizer.strategy_class == BreakoutSimple
        assert len(optimizer.market_data) == 1000
        assert optimizer.fixed_params['symbol'] == 'BTC'

    def test_optimizer_validates_invalid_params(self, sample_market_data):
        """Test: Rechaza parámetros inválidos"""
        optimizer = ParameterOptimizer(
            strategy_class=BreakoutSimple,
            market_data=sample_market_data,
            symbol='BTC',
            timeframe=Timeframe.M5,
        )

        # Este parámetro no existe en BreakoutSimple
        with pytest.raises(ValueError, match="Parámetros inválidos"):
            optimizer._validate_params({
                'invalid_nonexistent_param': [1, 2, 3]
            })

    def test_optimizer_generates_grid(self, sample_market_data):
        """Test: Genera todas las combinaciones de grid search"""
        optimizer = ParameterOptimizer(
            strategy_class=BreakoutSimple,
            market_data=sample_market_data,
            symbol='BTC',
            timeframe=Timeframe.M5,
        )

        param_ranges = {
            'lookback_period': [10, 20],
            'position_size_pct': [0.3, 0.4, 0.5]
        }

        combinations = optimizer._generate_grid(param_ranges, method='grid')

        # 2 * 3 = 6 combinaciones
        assert len(combinations) == 6

        # Verificar que contiene las combinaciones esperadas
        assert {'lookback_period': 10, 'position_size_pct': 0.3} in combinations
        assert {'lookback_period': 20, 'position_size_pct': 0.5} in combinations

    def test_optimizer_rejects_unsupported_method(self, sample_market_data):
        """Test: Rechaza métodos no soportados"""
        optimizer = ParameterOptimizer(
            strategy_class=BreakoutSimple,
            market_data=sample_market_data,
            symbol='BTC',
            timeframe=Timeframe.M5,
        )

        with pytest.raises(ValueError, match="Método"):
            optimizer._generate_grid(
                {'lookback_period': [10, 20]},
                method='bayesian'  # No soportado en v1
            )

    def test_optimizer_has_valid_strategy_method(self):
        """Test: Valida que la estrategia tenga generate_simple_signals"""
        # Crear una clase que no tiene el método
        class InvalidStrategy:
            pass

        with pytest.raises(ValueError, match="generate_simple_signals"):
            ParameterOptimizer(
                strategy_class=InvalidStrategy,
                market_data=pd.DataFrame(),
            )

    def test_optimizer_returns_dataframe(self, sample_market_data):
        """Test: optimize() retorna DataFrame válido"""
        optimizer = ParameterOptimizer(
            strategy_class=BreakoutSimple,
            market_data=sample_market_data,
            symbol='BTC',
            timeframe=Timeframe.M5,
            exchange='Binance',
            initial_capital=1000.0
        )

        param_ranges = {
            'lookback_period': [10, 15]  # Solo 2 para test rápido
        }

        results = optimizer.optimize(
            param_ranges=param_ranges,
            metric='roi',
            show_progress=False
        )

        # Verificar que es DataFrame
        assert isinstance(results, pd.DataFrame)

        # Verificar que contiene columnas esperadas
        assert 'lookback_period' in results.columns
        assert 'roi' in results.columns
        assert 'sharpe_ratio' in results.columns
        assert 'total_trades' in results.columns

    def test_optimizer_best_params_with_filter(self, sample_market_data):
        """Test: get_best_params() filtra por min_trades"""
        optimizer = ParameterOptimizer(
            strategy_class=BreakoutSimple,
            market_data=sample_market_data,
            symbol='BTC',
            timeframe=Timeframe.M5,
            exchange='Binance',
            initial_capital=1000.0
        )

        # Ejecutar optimización
        optimizer.optimize(
            param_ranges={'lookback_period': [10, 15]},
            metric='sharpe_ratio',
            show_progress=False
        )

        # Obtener mejores parámetros
        best = optimizer.get_best_params(min_trades=10)

        # Debe retornar un diccionario
        if best is not None:
            assert isinstance(best, dict)
            assert 'lookback_period' in best


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
