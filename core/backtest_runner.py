"""
Orquestador completo de backtests.

Ejecuta el backtest y calcula todas las métricas en un solo paso.
"""

from typing import Any
import pandas as pd
from core.simple_backtest_engine import BacktestEngine
from metrics.metrics_aggregator import MetricsAggregator
from config.market_configs.crypto_config import get_crypto_config


class BacktestRunner:
    """
    Ejecuta un backtest completo y calcula todas las métricas.
    
    Uso simple:
        runner = BacktestRunner(strategy)
        runner.run()
        runner.print_summary()
        
        # Acceder a resultados
        df_trades = runner.metrics.trade_metrics_df
        all_metrics = runner.metrics.all_metrics
    """
    
    def __init__(self, strategy: Any):
        """
        Inicializa el runner con una estrategia.
        
        Args:
            strategy: Instancia de BaseStrategy o similar
        """
        self.strategy = strategy
        self.engine: BacktestEngine | None = None
        self.results: pd.DataFrame | None = None
        self.metrics: MetricsAggregator | None = None
    
    def run(self, verbose: bool = True) -> pd.DataFrame:
        """
        Ejecuta el backtest completo.
        
        Args:
            verbose: Si True, imprime progreso
            
        Returns:
            DataFrame con resultados del motor
        """
        if verbose:
            print("\n" + "="*60)
            print("🚀 EJECUTANDO BACKTEST")
            print("="*60)
        
        # 1. Generar señales
        if verbose:
            print("\n🔍 Generando señales...")
        
        signals = self.strategy.generate_simple_signals()
        
        if verbose:
            print(f"✓ {len(signals)} señales generadas")
            print(f"  - Trades esperados: ~{len(signals)//2}")
        
        # 2. Configurar motor
        market_config = get_crypto_config(
            exchange=self.strategy.exchange,
            symbol=self.strategy.symbol
        )
        
        self.engine = BacktestEngine(
            initial_capital=self.strategy.initial_capital,
            market_config=market_config
        )
        
        # 3. Ejecutar backtest
        if verbose:
            print("\n⚙️ Ejecutando motor de backtest...")
        
        self.results = self.engine.run(signals)
        
        if verbose:
            print(f"✓ Backtest completado: {len(self.results)} trades")
        
        # 4. Calcular métricas
        if verbose:
            print("\n📊 Calculando métricas...")
        
        self.metrics = MetricsAggregator(
            results=self.results,
            strategy=self.strategy
        )
        
        if verbose:
            print("✓ Métricas calculadas")
        
        return self.results
    
    def print_summary(self, sections: list[str] = None):
        """Imprime resumen de métricas."""
        if self.metrics is None:
            print("⚠️ Primero ejecuta run()")
            return
        
        self.metrics.print_summary(sections=sections)
    
    def save_results(self, output_dir: str = 'outputs'):
        """Guarda todos los resultados."""
        if self.metrics is None:
            print("⚠️ Primero ejecuta run()")
            return
        
        self.metrics.save_results(output_dir=output_dir)



    def get_visualizer(self, interactive: bool = True):
        """
        Obtiene el visualizador para uso avanzado.

        Args:
            interactive: True para chart interactivo (TradingView), False para estático (mplfinance)

        Returns:
            Visualizador configurado con los resultados
        """
        if self.metrics is None:
            raise ValueError("⚠️ Primero ejecuta run()")

        if interactive:
            from visualization.chart_plotter import BacktestVisualizerInteractive
            return BacktestVisualizerInteractive(
                strategy=self.strategy,
                trade_metrics_df=self.metrics.trade_metrics_df
            )
        else:
            from visualization.chart_plotter import BacktestVisualizerStatic
            return BacktestVisualizerStatic(
                strategy=self.strategy,
                trade_metrics_df=self.metrics.trade_metrics_df
            )

    def plot_trades(
        self,
        interactive: bool = True,
        interval_hours: int = 5,
        number_visualisation: int = None,
        start: str = None,
        end: str = None,
        last_days: int = None,
        indicators: list = None,
    ):
        """
        Genera gráficos de los trades.

        Args:
            interactive: True (default) abre chart interactivo estilo TradingView.
                         False genera gráficos estáticos con mplfinance.
            interval_hours: Horas por gráfico (solo modo estático)
            number_visualisation: Límite de gráficos (solo modo estático, None = todos)
            start: Fecha inicio 'YYYY-MM-DD' (solo interactivo)
            end: Fecha fin 'YYYY-MM-DD' (solo interactivo)
            last_days: Mostrar últimos N días (solo interactivo)
        """
        viz = self.get_visualizer(interactive=interactive)
        if interactive:
            viz.show(start=start, end=end, last_days=last_days, indicators=indicators)
        else:
            viz.plot_trades(
                interval_hours=interval_hours,
                number_visualisation=number_visualisation
            )

    def plot_dashboards(
        self,
        modules: list = None,
        output_folder: str = "dashboards",
        show: bool = True
    ):
        """
        Genera dashboards de análisis.

        Args:
            modules: Lista de módulos a incluir. Disponibles:
                - performance, time_chart, temporal, metrics_distribution,
                - metrics_boxplot, mae_scatter, mfe_scatter, risk_reward_scatter,
                - volatility_scatter, profit_efficiency_scatter
                Si es None, genera todos.
            output_folder: Carpeta donde guardar los dashboards
            show: Si True, muestra los gráficos

        Returns:
            dict: Diccionario con las figuras generadas
        """
        if self.metrics is None:
            raise ValueError("⚠️ Primero ejecuta run()")

        from visualization.dashboard_manager import create_dashboard

        return create_dashboard(
            strategy=self.strategy,
            df_trade_metrics=self.metrics.trade_metrics_df,
            modules=modules,
            output_folder=output_folder,
            show=show
        )