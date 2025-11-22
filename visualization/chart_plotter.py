# visualization/chart_plotter.py
import numpy as np
import pandas as pd
import mplfinance as mpf
import matplotlib.pyplot as plt
from typing import Optional

class BacktestVisualizer:
    """
    Visualizador de resultados de backtest.
    
    Uso:
        # Desde BacktestRunner
        runner.plot_trades()
        
        # O independiente
        viz = BacktestVisualizer(strategy, trade_metrics_df)
        viz.plot_trades(interval_hours=5, number_visualisation=10)
    """
    
    def __init__(self, strategy, trade_metrics_df: pd.DataFrame):
        """
        Args:
            strategy: Instancia de BaseStrategy
            trade_metrics_df: DataFrame con métricas de trades (de MetricsAggregator)
        """
        self.strategy = strategy
        self.df_trades = trade_metrics_df
        self.df_market = strategy.market_data.copy()
        
        # Estilo de gráfico
        self.custom_style = mpf.make_mpf_style(
            base_mpl_style="fast",
            marketcolors=mpf.make_marketcolors(
                up="white", down="black", edge="black", wick="black",
                volume={"up": "green", "down": "red"}
            ),
            gridcolor="lightgray", 
            figcolor="gainsboro", 
            facecolor="gainsboro"
        )
    
    def plot_trades(
        self, 
        interval_hours: int = 5, 
        number_visualisation: Optional[int] = None
    ):
        """
        Genera gráficos de los trades en intervalos de tiempo.
        
        Args:
            interval_hours: Horas por gráfico
            number_visualisation: Límite de gráficos (None = todos)
        """
        start_time = self.df_market.index.min()
        end_time = self.df_market.index.max()
        interval = pd.Timedelta(hours=interval_hours)
        current_time = start_time
        count = 0
        
        print(f"📊 Generando gráficos...")
        print(f"  - Intervalo: {interval_hours}h")
        print(f"  - Período: {start_time.date()} a {end_time.date()}")
        if number_visualisation:
            print(f"  - Límite: {number_visualisation} gráficos")
        print()

        while current_time < end_time:
            if number_visualisation and count >= number_visualisation:
                break
            
            next_time = current_time + interval
            df_subset = self.df_market.loc[current_time:next_time].copy()
            
            if df_subset.empty or len(df_subset) < 2:
                current_time = next_time
                continue
            
            # Extraer señales usando nombres nuevos
            signals_long_entry = pd.Series(np.nan, index=df_subset.index)
            signals_long_exit = pd.Series(np.nan, index=df_subset.index)
            
            has_operations = False
            
            for _, trade in self.df_trades.iterrows():
                entry_time = pd.to_datetime(trade["entry_timestamp"])
                exit_time = pd.to_datetime(trade["exit_timestamp"])
                
                if entry_time in df_subset.index:
                    signals_long_entry.loc[entry_time] = trade["entry_price"]
                    has_operations = True
                
                if exit_time in df_subset.index:
                    signals_long_exit.loc[exit_time] = trade["exit_price"]
                    has_operations = True
            
            if not has_operations:
                current_time = next_time
                continue
            
            # Preparar plots adicionales
            apds = []
            
            # Indicadores (si existen)
            if "EMA_20" in df_subset.columns:
                apds.append(
                    mpf.make_addplot(df_subset["EMA_20"], color="red", width=1.5)
                )
            
            # Señales de entrada (verde hacia arriba)
            if not signals_long_entry.isna().all():
                apds.append(
                    mpf.make_addplot(
                        signals_long_entry, 
                        type='scatter', 
                        marker='^', 
                        markersize=100, 
                        color='green'
                    )
                )
            
            # Señales de salida (rojo hacia abajo)
            if not signals_long_exit.isna().all():
                apds.append(
                    mpf.make_addplot(
                        signals_long_exit, 
                        type='scatter', 
                        marker='v', 
                        markersize=100, 
                        color='red'
                    )
                )
            
            # Graficar
            mpf.plot(
                df_subset,
                type='candle',
                title=f"{self.strategy.symbol} - {current_time.strftime('%Y-%m-%d %H:%M')} a {next_time.strftime('%H:%M')}",
                style=self.custom_style,
                volume=True,
                addplot=apds if apds else None,
                figsize=(20, 9),
                warn_too_much_data=10000
            )
            
            plt.show()
            plt.close("all")
            
            count += 1
            current_time = next_time
        
        print(f"✓ {count} gráficos generados")