import numpy as np
import pandas as pd
import mplfinance as mpf
import matplotlib.pyplot as plt
from strategies.base_strategy import BaseStrategy
from typing import Any, List, Dict

class BacktestVisualizer:
    def __init__(self, strategy: BaseStrategy, backtest_results: List[Dict[str, Any]]):
        self.strategy = strategy
        self.df_trades = pd.DataFrame(backtest_results)
        
        # ✅ Usamos los datos de la estrategia en vez de recargarlos desde CSV
        self.df_market = strategy.market_data.copy()

        # 🔹 Definir estilo de gráfico
        self.custom_style = mpf.make_mpf_style(
            base_mpl_style="fast",
            marketcolors=mpf.make_marketcolors(
                up="white", down="black", edge="black", wick="black",
                volume={"up": "green", "down": "red"}
            ),
            gridcolor="lightgray", figcolor="gainsboro", facecolor="gainsboro"
        )

    def plot_trades(self, interval_hours=5, number_visualisation=None):
        """Genera gráficos de los trades en intervalos de tiempo con límite opcional."""
        start_time = self.df_market.index.min()
        end_time = self.df_market.index.max()
        interval = pd.Timedelta(hours=interval_hours)
        current_time = start_time
        count = 0  # Contador para limitar visualizaciones

        while current_time < end_time:
            if number_visualisation is not None and count >= number_visualisation:
                break  # Detener si alcanzamos el límite

            next_time = current_time + interval
            df_subset = self.df_market.loc[current_time:next_time].copy()

            if df_subset.empty or len(df_subset) < 2:
                current_time = next_time
                continue  # Saltamos intervalos vacíos

            # 🔹 Extraer señales de entrada/salida por tipo de posición
            signals_long_entry = pd.Series(np.nan, index=df_subset.index)
            signals_long_exit = pd.Series(np.nan, index=df_subset.index)
            signals_short_entry = pd.Series(np.nan, index=df_subset.index)
            signals_short_exit = pd.Series(np.nan, index=df_subset.index)

            has_operations = False

            for _, trade in self.df_trades.iterrows():
                entry_time = pd.to_datetime(trade["entry_timestamp"])
                exit_time = pd.to_datetime(trade["exit_timestamp"])
                side = str(trade.get("position_side", "LONG")).upper()

                if entry_time in df_subset.index:
                    if side == "LONG":
                        signals_long_entry.loc[entry_time] = trade["entry_price"]
                    elif side == "SHORT":
                        signals_short_entry.loc[entry_time] = trade["entry_price"]
                    has_operations = True

                if exit_time in df_subset.index:
                    if side == "LONG":
                        signals_long_exit.loc[exit_time] = trade["exit_price"]
                    elif side == "SHORT":
                        signals_short_exit.loc[exit_time] = trade["exit_price"]
                    has_operations = True

            if not has_operations:
                current_time = next_time
                continue

            # 🔹 Preparar plots adicionales (solo si hay datos)
            apds = []
            if "EMA_20" in df_subset.columns:
                apds.append(mpf.make_addplot(df_subset["EMA_9"], color="black", width=1.5))
            # 🔹 Línea horizontal discontinua morada para máximos asiáticos
            if "Min_asian_session" in df_subset.columns and not df_subset["Min_asian_session"].isna().all():
                apds.append(
                    mpf.make_addplot(df_subset["Min_asian_session"], color='purple', width=2, linestyle='--')
                )

            # 🔹 Línea con marcador 'o' morado para máximos europeos/americanos
            if "Min_european_session" in df_subset.columns and not df_subset["Min_european_session"].isna().all():
                apds.append(
                    mpf.make_addplot(df_subset["Min_european_session"], color='purple', width=2, linestyle='-')
                )


            if not signals_long_entry.isna().all():
                apds.append(mpf.make_addplot(signals_long_entry, type='scatter', marker='^', markersize=100, color='green'))

            if not signals_long_exit.isna().all():
                apds.append(mpf.make_addplot(signals_long_exit, type='scatter', marker='v', markersize=100, color='red'))

            if not signals_short_entry.isna().all():
                apds.append(mpf.make_addplot(signals_short_entry, type='scatter', marker='v', markersize=100, color='red'))

            if not signals_short_exit.isna().all():
                apds.append(mpf.make_addplot(signals_short_exit, type='scatter', marker='^', markersize=100, color='green'))

            # 🔹 Graficamos
            mpf.plot(df_subset,
                     type='candle',
                     title=f"{self.strategy.symbol} - {current_time.strftime('%Y-%m-%d %H:%M')} a {next_time.strftime('%H:%M')}",
                     style=self.custom_style,
                     volume=True,
                     addplot=apds if apds else None,
                     figsize=(20, 9),
                     warn_too_much_data=10000)

            plt.show()
            plt.close("all")

            count += 1
            current_time = next_time
