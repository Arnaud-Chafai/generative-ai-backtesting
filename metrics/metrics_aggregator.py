"""
Agregador de métricas de backtest.

Combina métricas de trade y portfolio en un solo lugar.
Maneja las conversiones de nombres de columnas automáticamente.
"""

import pandas as pd
from metrics.trade_metrics import TradeMetricsCalculator
from metrics.portfolio_metrics import BacktestMetrics


class MetricsAggregator:
    """
    Calcula y combina todas las métricas de un backtest.
    
    Uso:
        aggregator = MetricsAggregator(
            results=results,
            strategy=strategy
        )
        
        # Obtener DataFrames
        df_trade_metrics = aggregator.trade_metrics_df
        df_portfolio_summary = aggregator.portfolio_summary_df
        
        # Obtener diccionario completo
        all_metrics = aggregator.all_metrics
        
        # Mostrar resumen
        aggregator.print_summary()
    """
    
    def __init__(self, results: pd.DataFrame, strategy):
        """
        Inicializa el agregador con los resultados del backtest.
        
        Args:
            results: DataFrame del BacktestEngine
            strategy: Instancia de la estrategia (para acceder a market_data, timeframe, etc.)
        """
        self.results = results
        self.strategy = strategy
        
        # Calcular métricas automáticamente
        self._calculate_all_metrics()
    
    def _calculate_all_metrics(self):
        """Calcula todas las métricas (trade + portfolio)."""
        # 1. Adaptar resultados para TradeMetricsCalculator
        results_adapted = self._adapt_for_trade_metrics(self.results)
        
        # 2. Calcular métricas por trade
        metrics_calculator = TradeMetricsCalculator(
            initial_capital=self.strategy.initial_capital,
            market_data=self.strategy.market_data,
            timeframe=self.strategy.timeframe
        )
        
        self.trade_metrics_df = metrics_calculator.create_trade_metrics_df(results_adapted)
        
        # 3. Adaptar para BacktestMetrics
        df_for_portfolio = self._adapt_for_portfolio_metrics(self.trade_metrics_df)
        
        # 4. Calcular métricas de portfolio
        portfolio_metrics = BacktestMetrics(
            trade_data=df_for_portfolio,
            initial_capital=self.strategy.initial_capital
        )
        
        self.all_metrics = portfolio_metrics.compute_all_metrics()
        self.portfolio_metrics = portfolio_metrics
    
    def _adapt_for_trade_metrics(self, results: pd.DataFrame) -> pd.DataFrame:
        """Convierte resultados del motor al formato de TradeMetricsCalculator."""
        adapted = results.copy()
        adapted = adapted.rename(columns={
            'entry_time': 'entry_timestamp',
            'exit_time': 'exit_timestamp',
            'avg_entry_price': 'entry_price',
            'total_cost': 'usdt_amount',
            'net_pnl': 'net_profit_loss'
        })
        adapted['position_side'] = 'LONG'  # TODO: adaptar cuando tengamos SHORT
        return adapted
    
    def _adapt_for_portfolio_metrics(self, trade_metrics: pd.DataFrame) -> pd.DataFrame:
        """Convierte métricas de trade al formato de BacktestMetrics."""
        adapted = trade_metrics.copy()
        adapted = adapted.rename(columns={
            'net_profit_loss': 'net_pnl',
            'entry_timestamp': 'entry_time',
            'exit_timestamp': 'exit_time'
        })
        
        # Añadir slippage_cost si no existe
        if 'slippage_cost' not in adapted.columns:
            if 'total_slippage' in self.results.columns:
                # Usar slippage del motor si está disponible
                adapted['slippage_cost'] = self.results['total_slippage'].values
            else:
                adapted['slippage_cost'] = 0.0
        
        return adapted
    
    def print_summary(self, sections: list[str] = None):
        """
        Imprime un resumen de las métricas.
        
        Args:
            sections: Lista de secciones a mostrar. Si None, muestra todas.
                     Opciones: 'general', 'pnl', 'drawdown', 'ratios', 'time', 'costs'
        """
        if sections is None:
            sections = ['general', 'pnl', 'drawdown', 'ratios', 'time', 'costs']
        
        print("\n" + "="*60)
        print("📊 MÉTRICAS COMPLETAS DEL BACKTEST")
        print("="*60)
        
        if 'general' in sections:
            print("\n💰 RESUMEN GENERAL")
            print("-"*60)
            general = self.portfolio_metrics.compute_general_summary()
            for key, value in general.items():
                print(f"  {key:30s}: {value}")
        
        if 'pnl' in sections:
            print("\n📊 ANÁLISIS DE PROFIT/LOSS")
            print("-"*60)
            pnl = self.portfolio_metrics.compute_profit_loss_analysis()
            for key, value in pnl.items():
                print(f"  {key:30s}: {value}")
        
        if 'drawdown' in sections:
            print("\n📉 DRAWDOWN")
            print("-"*60)
            dd = self.portfolio_metrics.compute_drawdown_analysis()
            for key, value in dd.items():
                print(f"  {key:30s}: {value}")
        
        if 'ratios' in sections:
            print("\n📈 RATIOS DE PERFORMANCE")
            print("-"*60)
            ratios = self.portfolio_metrics.compute_performance_ratios()
            for key, value in ratios.items():
                print(f"  {key:30s}: {value}")
        
        if 'time' in sections:
            print("\n⏱️ ESTADÍSTICAS DE TIEMPO")
            print("-"*60)
            time_stats = self.portfolio_metrics.compute_time_statistics()
            # Mostrar solo las más importantes para no saturar
            important_time_keys = [
                'backtest_duration', 'time_in_market_pct', 'trades_per_day',
                'avg_winning_trade_duration_min', 'avg_losing_trade_duration_min'
            ]
            for key in important_time_keys:
                if key in time_stats:
                    print(f"  {key:30s}: {time_stats[key]}")
        
        if 'costs' in sections:
            print("\n💸 COSTOS OPERACIONALES")
            print("-"*60)
            costs = self.portfolio_metrics.compute_operational_costs()
            for key, value in costs.items():
                print(f"  {key:30s}: {value}")
        
        print("\n" + "="*60)
    
    @property
    def portfolio_summary_df(self) -> pd.DataFrame:
        """Convierte el diccionario de métricas en un DataFrame para análisis."""
        return pd.DataFrame([self.all_metrics])
    
    def save_results(self, output_dir: str = 'outputs'):
        """
        Guarda todos los resultados en archivos CSV.
        
        Args:
            output_dir: Directorio donde guardar los archivos
        """
        import os
        os.makedirs(output_dir, exist_ok=True)
        
        # Guardar métricas detalladas por trade
        self.trade_metrics_df.to_csv(f'{output_dir}/trade_metrics.csv', index=False)
        
        # Guardar resumen de portfolio
        self.portfolio_summary_df.to_csv(f'{output_dir}/portfolio_summary.csv', index=False)
        
        # Guardar resultados raw del motor
        self.results.to_csv(f'{output_dir}/engine_results.csv', index=False)
        
        print(f"\n✓ Resultados guardados en {output_dir}/")