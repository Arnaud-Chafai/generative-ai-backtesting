"""
Parameter Optimizer - Busca automáticamente la mejor combinación de parámetros.

Usa Grid Search para probar todas las combinaciones de parámetros especificadas
y retorna la mejor según la métrica elegida.
"""

import inspect
import time
from typing import Any, Dict, List, Optional

import pandas as pd
from tqdm import tqdm

from core.backtest_runner import BacktestRunner
from .results import OptimizationResult


class ParameterOptimizer:
    """
    Optimizador de parámetros usando Grid Search.

    Evalúa múltiples combinaciones de parámetros de estrategia de trading
    para encontrar la mejor según una métrica especificada.

    Attributes:
        strategy_class: Clase de estrategia a optimizar
        market_data: DataFrame con datos OHLCV inyectados
        fixed_params: Parámetros que NO se optimizan (símbolo, timeframe, etc.)
        results: Lista de OptimizationResult de todas las iteraciones
    """

    def __init__(
        self,
        strategy_class: type,
        market_data: pd.DataFrame,
        **fixed_params
    ):
        """
        Inicializa el optimizador.

        Args:
            strategy_class: Clase que hereda de BaseStrategy
            market_data: DataFrame con columnas [open, high, low, close, volume]
            **fixed_params: Parámetros que NO varían (ej: symbol='BTC', timeframe=Timeframe.M5)
        """
        self.strategy_class = strategy_class
        self.market_data = market_data
        self.fixed_params = fixed_params
        self.results: List[OptimizationResult] = []
        self.best_params: Optional[Dict[str, Any]] = None
        self.best_score: float = -float('inf')
        self.target_metric: str = 'sharpe_ratio'

        # Validar que la estrategia es válida
        self._validate_strategy()

    def _validate_strategy(self) -> None:
        """Verifica que la estrategia tenga el método generate_simple_signals"""
        if not hasattr(self.strategy_class, 'generate_simple_signals'):
            raise ValueError(
                f"❌ Estrategia {self.strategy_class.__name__} debe implementar "
                f"generate_simple_signals() para funcionar con el optimizador"
            )

    def _validate_params(self, param_ranges: Dict[str, List[Any]]) -> None:
        """
        Valida que los parámetros en param_ranges existan en el __init__ de la estrategia.

        Args:
            param_ranges: Diccionario con parámetros a optimizar

        Raises:
            ValueError: Si hay parámetros inválidos
        """
        # Obtener parámetros válidos del __init__
        sig = inspect.signature(self.strategy_class.__init__)
        valid_params = set(sig.parameters.keys()) - {'self'}

        # Detectar parámetros inválidos
        invalid = set(param_ranges.keys()) - valid_params

        if invalid:
            raise ValueError(
                f"❌ Parámetros inválidos: {sorted(invalid)}\n"
                f"✅ Parámetros válidos: {sorted(valid_params)}"
            )

    def _generate_grid(
        self,
        param_ranges: Dict[str, List[Any]],
        method: str = 'grid'
    ) -> List[Dict[str, Any]]:
        """
        Genera todas las combinaciones de parámetros.

        Args:
            param_ranges: Diccionario donde cada clave es un parámetro y valor es lista de valores
            method: 'grid' para grid search (único soportado en v1)

        Returns:
            Lista de diccionarios, cada uno una combinación de parámetros

        Example:
            param_ranges = {
                'lookback_period': [10, 20],
                'position_size_pct': [0.3, 0.4]
            }
            # Retorna:
            # [
            #   {'lookback_period': 10, 'position_size_pct': 0.3},
            #   {'lookback_period': 10, 'position_size_pct': 0.4},
            #   {'lookback_period': 20, 'position_size_pct': 0.3},
            #   {'lookback_period': 20, 'position_size_pct': 0.4},
            # ]
        """
        if method != 'grid':
            raise ValueError(f"❌ Método '{method}' no soportado (solo 'grid' en v1)")

        import itertools

        keys = param_ranges.keys()
        values = param_ranges.values()

        # itertools.product genera todas las combinaciones
        combinations = [
            dict(zip(keys, combo))
            for combo in itertools.product(*values)
        ]

        return combinations

    def optimize(
        self,
        param_ranges: Dict[str, List[Any]],
        metric: str = 'sharpe_ratio',
        method: str = 'grid',
        show_progress: bool = True
    ) -> pd.DataFrame:
        """
        Ejecuta la optimización de parámetros.

        Args:
            param_ranges: Diccionario con parámetros a probar y sus valores
            metric: Métrica para evaluar (sharpe_ratio, roi, profit_factor, etc.)
            method: Método de búsqueda ('grid' en v1)
            show_progress: Mostrar barra de progreso

        Returns:
            DataFrame con todos los resultados ordenados por la métrica

        Raises:
            ValueError: Si los parámetros son inválidos
        """
        # Validaciones
        self._validate_params(param_ranges)
        if metric not in ['sharpe_ratio', 'roi', 'profit_factor', 'max_drawdown', 'sortino_ratio']:
            raise ValueError(f"❌ Métrica desconocida: {metric}")

        self.target_metric = metric

        # Generar combinaciones
        combinations = self._generate_grid(param_ranges, method)
        total = len(combinations)

        print(f"\n{'='*70}")
        print(f"🎯 OPTIMIZACIÓN DE PARÁMETROS - Grid Search")
        print(f"{'='*70}")
        print(f"Estrategia: {self.strategy_class.__name__}")
        print(f"Total de combinaciones: {total}")
        print(f"Parámetros fijos: {self.fixed_params}")
        print(f"Métrica objetivo: {metric}")
        print(f"{'='*70}\n")

        # Bucle de optimización con barra de progreso
        iterator = tqdm(
            combinations,
            desc="Optimizing",
            unit="combo",
            disable=not show_progress
        ) if show_progress else combinations

        for params in iterator:
            start_time = time.time()

            try:
                # Combinar parámetros fijos + variables
                full_params = {**self.fixed_params, **params}

                # ✅ INYECCIÓN DE DATOS: Pasar market_data a la estrategia
                strategy = self.strategy_class(data=self.market_data, **full_params)

                # Ejecutar backtest
                runner = BacktestRunner(strategy)
                runner.run(verbose=False)

                # Extraer métricas
                all_metrics = runner.metrics.all_metrics

                # Crear resultado
                execution_time = time.time() - start_time
                result = OptimizationResult(
                    params=params,
                    metrics=all_metrics,
                    execution_time=execution_time
                )
                self.results.append(result)

                # Actualizar mejor si es necesario
                score = all_metrics[metric]
                if score > self.best_score:
                    self.best_score = score
                    self.best_params = params

            except Exception as e:
                # Registrar errores pero continuar
                import traceback
                print(f"\n⚠️ Error en {params}: {str(e)}")
                # Descomentar la siguiente línea para debugging detallado:
                # traceback.print_exc()
                continue

        print(f"\n✅ Optimización completada: {len(self.results)} resultados\n")

        return self.get_summary()

    def get_summary(self) -> pd.DataFrame:
        """
        Convierte los resultados a un DataFrame de pandas.

        Returns:
            DataFrame con columnas: [parámetros + métricas clave + execution_time]
        """
        data = []

        for result in self.results:
            row = {**result.params}  # Primero los parámetros

            # Agregar métricas principales
            # Nota: Usar 'ROI' (mayúsculas) porque así se retorna de portfolio_metrics
            row.update({
                'sharpe_ratio': result.metrics.get('sharpe_ratio', None),
                'roi': result.metrics.get('ROI', None),  # ✅ Corrección: ROI está en mayúsculas
                'max_drawdown': result.metrics.get('max_drawdown', None),
                'profit_factor': result.metrics.get('profit_factor', None),
                'total_trades': result.metrics.get('total_trades', None),
                'execution_time': result.execution_time,
            })

            data.append(row)

        df = pd.DataFrame(data)

        # Validar que hay datos y que la métrica existe
        if df.empty:
            print("⚠️ No hay resultados válidos. El DataFrame está vacío.")
            return df

        # Ordenar por métrica objetivo (descendente para sharpe/roi, ascendente para drawdown)
        if self.target_metric in df.columns:
            ascending = self.target_metric == 'max_drawdown'
            df = df.sort_values(self.target_metric, ascending=ascending, na_position='last')
        else:
            print(f"⚠️ Métrica '{self.target_metric}' no encontrada en resultados")
            print(f"   Columnas disponibles: {list(df.columns)}")

        return df

    def get_best_params(
        self,
        metric: Optional[str] = None,
        min_trades: int = 20
    ) -> Optional[Dict[str, Any]]:
        """
        Retorna los mejores parámetros encontrados.

        Filtra resultados con pocos trades (menos de min_trades) para evitar
        resultados basados en estadísticas insuficientes (overfitting fantasma).

        Args:
            metric: Métrica a usar (si None, usa la del optimize())
            min_trades: Número mínimo de trades requeridos para considerar válido

        Returns:
            Diccionario con los mejores parámetros, o None si no hay resultados válidos
        """
        if not self.results:
            print("⚠️ No hay resultados de optimización todavía")
            return None

        metric = metric or self.target_metric
        df = self.get_summary()

        # ✅ FILTRO ANTI-FANTASMA: Eliminar resultados con pocos trades
        valid_results = df[df['total_trades'] >= min_trades]

        if valid_results.empty:
            print(
                f"⚠️ Ningún resultado tiene ≥{min_trades} trades. "
                f"Usa min_trades={min_trades-10} o baja el threshold."
            )
            return None

        # Ordenar y obtener el mejor
        ascending = metric == 'max_drawdown'
        best_row = valid_results.sort_values(metric, ascending=ascending).iloc[0]

        print(f"\n{'='*70}")
        print(f"🏆 MEJORES PARÁMETROS ENCONTRADOS")
        print(f"{'='*70}")
        for param_name, param_value in best_row.items():
            if param_name not in ['sharpe_ratio', 'roi', 'max_drawdown', 'profit_factor', 'total_trades', 'execution_time']:
                print(f"  {param_name}: {param_value}")

        # Formatear métricas de forma robusta ante valores None
        metric_value = best_row[metric]
        metric_str = f"{metric_value:.4f}" if metric_value is not None else "N/A"
        roi_value = best_row['roi']
        roi_str = f"{roi_value:.2f}%" if roi_value is not None else "N/A"
        sharpe_value = best_row['sharpe_ratio']
        sharpe_str = f"{sharpe_value:.2f}" if sharpe_value is not None else "N/A"

        print(f"\n  Métrica: {metric} = {metric_str}")
        print(f"  Total trades: {best_row['total_trades']}")
        print(f"  ROI: {roi_str}")
        print(f"  Sharpe: {sharpe_str}")
        print(f"{'='*70}\n")

        # Retornar como diccionario
        best_dict = best_row.drop(['sharpe_ratio', 'roi', 'max_drawdown', 'profit_factor', 'total_trades', 'execution_time']).to_dict()

        return best_dict

    def export_results(self, filename: str = 'optimization_results.csv') -> None:
        """
        Exporta todos los resultados a un archivo CSV.

        Args:
            filename: Nombre del archivo de salida
        """
        if not self.results:
            print("⚠️ No hay resultados para exportar")
            return

        df = self.get_summary()
        df.to_csv(filename, index=False)
        print(f"✅ Resultados exportados a {filename}")
