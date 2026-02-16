# visualization/chart_plotter.py
import numpy as np
import pandas as pd
import mplfinance as mpf
import matplotlib.pyplot as plt
from typing import Optional


class BacktestVisualizerStatic:
    """
    Visualizador estático de resultados de backtest (mplfinance).

    Uso:
        viz = BacktestVisualizerStatic(strategy, trade_metrics_df)
        viz.plot_trades(interval_hours=5, number_visualisation=10)
    """

    def __init__(self, strategy, trade_metrics_df: pd.DataFrame):
        self.strategy = strategy
        self.df_trades = trade_metrics_df
        self.df_market = strategy.market_data.copy()

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

            apds = []

            if "EMA_20" in df_subset.columns:
                apds.append(
                    mpf.make_addplot(df_subset["EMA_20"], color="red", width=1.5)
                )

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


class BacktestVisualizerInteractive:
    """
    Visualizador interactivo estilo TradingView usando lightweight-charts.

    Abre una ventana standalone con zoom, pan, crosshair y marcadores de trades.

    Uso:
        viz = BacktestVisualizerInteractive(strategy, trade_metrics_df)
        viz.show()
    """

    MAX_TRADE_LINES = 200  # Límite de líneas entry→exit para no sobrecargar el chart

    def __init__(self, strategy, trade_metrics_df: pd.DataFrame):
        self.strategy = strategy
        self.df_trades = trade_metrics_df
        self.df_market = strategy.market_data.copy()

    def show(
        self,
        width: int = 1400,
        height: int = 800,
        block: bool = True,
        start: Optional[str] = None,
        end: Optional[str] = None,
        last_days: Optional[int] = None,
        indicators: Optional[list] = None,
    ):
        """
        Abre el chart interactivo en una ventana standalone.

        Args:
            width, height: Tamaño de la ventana
            block: Si True, bloquea hasta cerrar la ventana
            start: Fecha inicio 'YYYY-MM-DD' (filtra velas y trades)
            end: Fecha fin 'YYYY-MM-DD'
            last_days: Mostrar solo los últimos N días (alternativa a start/end)
            indicators: Lista de indicadores a mostrar (ej: ['EMA_20']). None = ninguno.
        """
        from lightweight_charts import Chart

        # Permitir asyncio.run() dentro de Jupyter (que ya tiene event loop)
        try:
            import nest_asyncio
            nest_asyncio.apply()
        except ImportError:
            pass

        # Filtrar rango de fechas
        self._apply_date_filter(start, end, last_days)

        chart = Chart(width=width, height=height)

        self._configure_chart_style(chart)
        self._add_volume(chart)
        self._add_candlesticks(chart)
        self._add_indicators(chart, indicators=indicators)
        self._add_trade_markers(chart)

        print(f"📊 Abriendo chart interactivo: {self.strategy.symbol}")
        print(f"  - {len(self._filtered_market)} velas")
        print(f"  - {len(self._filtered_trades)} trades")

        chart.show(block=block)

    def _apply_date_filter(self, start, end, last_days):
        """Filtra market data y trades al rango especificado."""
        df = self.df_market
        trades = self.df_trades

        if last_days is not None:
            start_dt = df.index.max() - pd.Timedelta(days=last_days)
            df = df.loc[start_dt:]
        else:
            if start:
                df = df.loc[start:]
            if end:
                df = df.loc[:end]

        self._filtered_market = df

        # Filtrar trades dentro del rango visible
        t_start = df.index.min()
        t_end = df.index.max()
        mask = (
            (pd.to_datetime(trades['entry_timestamp']) >= t_start) &
            (pd.to_datetime(trades['exit_timestamp']) <= t_end)
        )
        self._filtered_trades = trades.loc[mask]

    def _prepare_ohlcv_data(self) -> pd.DataFrame:
        """Prepara datos OHLCV con formato requerido por lightweight-charts."""
        df = self._filtered_market.copy()

        # lightweight-charts espera columnas en minúsculas y 'time' como columna
        rename_map = {}
        for col in df.columns:
            col_lower = col.lower()
            if col_lower in ('open', 'high', 'low', 'close', 'volume'):
                rename_map[col] = col_lower

        df = df.rename(columns=rename_map)

        # El index (datetime) se convierte en columna 'time'
        df = df.reset_index()
        index_col = df.columns[0]  # primera columna tras reset
        df = df.rename(columns={index_col: 'time'})

        return df[['time', 'open', 'high', 'low', 'close', 'volume']]

    def _configure_chart_style(self, chart):
        """Aplica tema oscuro estilo TradingView."""
        chart.layout(
            background_color='#B0B0B0',
            text_color='#333333',
            font_size=12,
            font_family='Trebuchet MS'
        )
        chart.grid(vert_enabled=False, horz_enabled=False)
        chart.crosshair(mode='normal')
        chart.watermark(self.strategy.symbol, color='rgba(180, 180, 200, 0.15)')
        chart.legend(visible=True, ohlc=True, percent=True, lines=True, color='#333333')

    def _add_candlesticks(self, chart):
        """Agrega velas con estilo TradingView."""
        df = self._prepare_ohlcv_data()
        chart.set(df)
        chart.candle_style(
            up_color='#FFFFFF',
            down_color='#000000',
            border_up_color='#000000',
            border_down_color='#000000',
            wick_up_color='#000000',
            wick_down_color='#000000'
        )

    def _add_volume(self, chart):
        """Agrega barras de volumen en panel inferior."""
        chart.volume_config(
            up_color='rgba(38, 166, 154, 0.3)',
            down_color='rgba(239, 83, 80, 0.3)'
        )

    def _add_indicators(self, chart, indicators: Optional[list] = None):
        """
        Agrega indicadores al chart.

        Args:
            indicators: Lista de nombres de columnas a mostrar (ej: ['EMA_20', 'VWAP']).
                        Si es None, no agrega ninguno (para evitar saturar el chart).
        """
        if not indicators:
            return

        df = self._prepare_ohlcv_data()
        market_df = self._filtered_market

        colors = ['#FF6D00', '#2962FF', '#AB47BC', '#FFD600', '#00E676']
        color_idx = 0

        for col in indicators:
            if col not in market_df.columns:
                print(f"  ⚠️ Columna '{col}' no encontrada, omitiendo")
                continue

            line = chart.create_line(name=col, color=colors[color_idx % len(colors)], width=2)

            indicator_df = pd.DataFrame({
                'time': df['time'],
                col: market_df[col].values
            }).dropna()

            line.set(indicator_df)
            color_idx += 1

    def _add_trade_markers(self, chart):
        """Marca entradas/salidas con trend_line + markers JS con size grande."""
        import json

        MAX_TRADES = 200
        trades = self._filtered_trades
        if len(trades) > MAX_TRADES:
            print(f"  ⚠️ {len(trades)} trades > {MAX_TRADES}, omitiendo marcadores")
            return

        # Construir markers JS con size (la API Python no soporta size)
        js_markers = []

        for _, trade in trades.iterrows():
            entry_time = pd.to_datetime(trade['entry_timestamp'])
            exit_time = pd.to_datetime(trade['exit_timestamp'])
            entry_price = trade['entry_price']
            exit_price = trade['exit_price']
            net_pnl = trade.get('net_profit_loss', 0)
            pnl_pct = trade.get('pnl_pct', 0)
            pnl_sign = '+' if net_pnl >= 0 else ''
            trade_color = '#00FF00' if net_pnl >= 0 else '#CC0000'

            # Trend line entry→exit
            chart.trend_line(
                start_time=entry_time,
                start_value=entry_price,
                end_time=exit_time,
                end_value=exit_price,
                line_color=trade_color,
                width=2,
                style='dashed'
            )

            # Entry marker (unix timestamp int)
            entry_unix = int(entry_time.timestamp())
            exit_unix = int(exit_time.timestamp())

            js_markers.append({
                'time': entry_unix,
                'position': 'belowBar',
                'shape': 'arrowUp',
                'color': '#00FF00',
                'text': f'BUY {entry_price:.0f}',
                'size': 2
            })
            js_markers.append({
                'time': exit_unix,
                'position': 'aboveBar',
                'shape': 'arrowDown',
                'color': '#CC0000',
                'text': f'SELL {exit_price:.0f} | {pnl_sign}{pnl_pct:.1f}%',
                'size': 2
            })

        # Ordenar por tiempo e inyectar directo al JS
        js_markers.sort(key=lambda m: m['time'])
        if js_markers:
            chart.run_script(
                f'{chart.id}.series.setMarkers({json.dumps(js_markers)})'
            )

    def _add_trade_lines(self, chart):
        """Agrega líneas entry→exit coloreadas por profitabilidad."""
        trades = self._filtered_trades
        if len(trades) > self.MAX_TRADE_LINES:
            print(f"  ⚠️ {len(trades)} trades > límite ({self.MAX_TRADE_LINES}), omitiendo líneas entry→exit")
            return

        for _, trade in trades.iterrows():
            entry_time = pd.to_datetime(trade['entry_timestamp'])
            exit_time = pd.to_datetime(trade['exit_timestamp'])
            entry_price = trade['entry_price']
            exit_price = trade['exit_price']
            net_pnl = trade.get('net_pnl', 0)

            color = '#26A69A' if net_pnl >= 0 else '#EF5350'

            line = chart.create_line(
                name=f'trade_{_}',
                color=color,
                width=1,
                style='dotted',
                price_line=False,
                price_label=False
            )

            line_df = pd.DataFrame({
                'time': [entry_time, exit_time],
                f'trade_{_}': [entry_price, exit_price]
            })
            line.set(line_df)


# Alias de compatibilidad: por defecto usa el interactivo
BacktestVisualizer = BacktestVisualizerInteractive
