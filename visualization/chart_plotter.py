# visualization/chart_plotter.py
import json
import os
import tempfile
import webbrowser

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
    Visualizador interactivo estilo TradingView.

    Genera un archivo HTML autocontenido con TradingView Lightweight Charts JS v4.2.3
    (CDN) y lo abre en el navegador. Zero dependencias Python adicionales.

    Uso:
        viz = BacktestVisualizerInteractive(strategy, trade_metrics_df)
        viz.show(last_days=30, indicators=['EMA_20'])
    """

    INDICATOR_COLORS = ['#FF6D00', '#2962FF', '#AB47BC', '#FFD600', '#00E676']

    def __init__(self, strategy, trade_metrics_df: pd.DataFrame, summary_metrics: dict = None, quote_currency: str = ''):
        self.strategy = strategy
        self.df_trades = trade_metrics_df
        self.df_market = strategy.market_data.copy()
        self._summary_metrics = summary_metrics or {}
        self._quote_currency = quote_currency

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
        Genera HTML con chart interactivo y lo abre en el navegador.

        Args:
            width, height: Tamaño inicial del chart en píxeles
            block: Ignorado (mantenido por compatibilidad de API)
            start: Fecha inicio 'YYYY-MM-DD' (filtra velas y trades)
            end: Fecha fin 'YYYY-MM-DD'
            last_days: Mostrar solo los últimos N días (alternativa a start/end)
            indicators: Lista de indicadores a mostrar (ej: ['EMA_20']). None = ninguno.
        """
        self._apply_date_filter(start, end, last_days)

        html = self._build_html(width, height, indicators)

        tmp_dir = os.path.join(tempfile.gettempdir(), 'backtesting_charts')
        os.makedirs(tmp_dir, exist_ok=True)
        filepath = os.path.join(tmp_dir, f'{self.strategy.symbol}_chart.html')

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(html)

        print(f"📊 Chart interactivo: {self.strategy.symbol}")
        print(f"  - {len(self._filtered_market)} velas")
        print(f"  - {len(self._filtered_trades)} trades")
        print(f"  - Archivo: {filepath}")

        webbrowser.open(filepath)

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
        """Prepara datos OHLCV con columnas normalizadas y 'time' como columna."""
        df = self._filtered_market.copy()

        rename_map = {}
        for col in df.columns:
            col_lower = col.lower()
            if col_lower in ('open', 'high', 'low', 'close', 'volume'):
                rename_map[col] = col_lower

        df = df.rename(columns=rename_map)

        # El index (datetime) se convierte en columna 'time'
        df = df.reset_index()
        index_col = df.columns[0]
        df = df.rename(columns={index_col: 'time'})

        return df[['time', 'open', 'high', 'low', 'close', 'volume']]

    def _serialize_candle_data(self) -> str:
        """DataFrame → JSON [{time, open, high, low, close}]"""
        df = self._prepare_ohlcv_data()
        times = df['time'].astype(np.int64) // 10**9
        records = [
            {'time': int(t), 'open': float(o), 'high': float(h),
             'low': float(l), 'close': float(c)}
            for t, o, h, l, c in zip(
                times, df['open'], df['high'], df['low'], df['close']
            )
        ]
        return json.dumps(records)

    def _serialize_volume_data(self) -> str:
        """DataFrame → JSON [{time, value, color}]"""
        df = self._prepare_ohlcv_data()
        times = df['time'].astype(np.int64) // 10**9
        records = [
            {
                'time': int(t),
                'value': float(v),
                'color': 'rgba(38,166,154,0.4)' if c >= o else 'rgba(239,83,80,0.4)',
            }
            for t, v, o, c in zip(
                times, df['volume'], df['open'], df['close']
            )
        ]
        return json.dumps(records)

    def _serialize_markers(self) -> str:
        """Trades → JSON [{time, position, shape, color, text, size}] ORDENADOS por time."""
        trades = self._filtered_trades
        if trades.empty:
            return '[]'

        markers = []

        # BUY markers: usar señales individuales si disponibles (muestra cada entrada DCA)
        buy_signals = self._get_individual_buy_signals()
        if buy_signals:
            for sig in buy_signals:
                sig_time = pd.to_datetime(sig.timestamp)
                markers.append({
                    'time': int(sig_time.value // 10**9),
                    'position': 'belowBar',
                    'shape': 'arrowUp',
                    'color': '#00bfff',
                    'text': f'BUY {sig.price:.0f}',
                    'size': 2,
                })
        else:
            # Fallback: usar entry del DataFrame (1 marker por trade)
            for _, trade in trades.iterrows():
                entry_time = pd.to_datetime(trade['entry_timestamp'])
                entry_price = trade['entry_price']
                markers.append({
                    'time': int(entry_time.value // 10**9),
                    'position': 'belowBar',
                    'shape': 'arrowUp',
                    'color': '#00bfff',
                    'text': f'BUY {entry_price:.0f}',
                    'size': 2,
                })

        # SELL markers: siempre del DataFrame de trades (tiene P&L)
        for _, trade in trades.iterrows():
            exit_time = pd.to_datetime(trade['exit_timestamp'])
            exit_price = trade['exit_price']
            net_pnl = trade.get('net_profit_loss', 0)
            pnl_pct = trade.get('pnl_pct', 0)
            pnl_sign = '+' if net_pnl >= 0 else ''
            markers.append({
                'time': int(exit_time.value // 10**9),
                'position': 'aboveBar',
                'shape': 'arrowDown',
                'color': '#ffe000',
                'text': f'SELL {exit_price:.0f} | {pnl_sign}{pnl_pct:.1f}%',
                'size': 2,
            })

        # CRITICAL: markers MUST be sorted by time or they become invisible
        markers.sort(key=lambda m: m['time'])
        return json.dumps(markers)

    def _get_individual_buy_signals(self) -> list:
        """Obtiene señales BUY individuales de la estrategia (para DCA multi-entry)."""
        signals = getattr(self.strategy, 'simple_signals', None)
        if not signals:
            return []
        from models.enums import SignalType
        buy_signals = [s for s in signals if s.signal_type == SignalType.BUY]
        # Solo usar si hay más señales BUY que trades (indica DCA/multi-entry)
        trades = self._filtered_trades
        if len(buy_signals) <= len(trades):
            return []
        # Filtrar por rango temporal del chart
        t_start = self._filtered_market.index.min()
        t_end = self._filtered_market.index.max()
        return [s for s in buy_signals if t_start <= pd.to_datetime(s.timestamp) <= t_end]

    def _serialize_indicator_data(self, indicators) -> list:
        """Columnas de indicadores → lista de (nombre, color, json_data)."""
        if not indicators:
            return []

        df = self._prepare_ohlcv_data()
        market_df = self._filtered_market
        times = df['time'].astype(np.int64) // 10**9
        result = []

        for i, col in enumerate(indicators):
            if col not in market_df.columns:
                print(f"  ⚠️ Columna '{col}' no encontrada, omitiendo")
                continue

            color = self.INDICATOR_COLORS[i % len(self.INDICATOR_COLORS)]
            values = market_df[col].values
            records = [
                {'time': int(t), 'value': float(v)}
                for t, v in zip(times, values)
                if pd.notna(v)
            ]
            result.append((col, color, json.dumps(records)))

        return result

    def _serialize_trades_for_panel(self) -> str:
        """Trades → JSON para el panel de navegación con métricas detalladas."""
        trades = self._filtered_trades
        if trades.empty:
            return '[]'

        def sf(trade, key):
            """Safe float: handles NaN, Inf, missing keys."""
            try:
                v = float(trade.get(key, 0))
                return v if np.isfinite(v) else 0.0
            except (TypeError, ValueError):
                return 0.0

        result = []
        for _, trade in trades.iterrows():
            entry_time = pd.to_datetime(trade['entry_timestamp'])
            exit_time = pd.to_datetime(trade['exit_timestamp'])
            result.append({
                'et': int(entry_time.value // 10**9),
                'xt': int(exit_time.value // 10**9),
                'ep': float(trade['entry_price']),
                'xp': float(trade['exit_price']),
                'pnl': sf(trade, 'pnl_pct'),
                'amt': sf(trade, 'net_profit_loss'),
                'dur': int(sf(trade, 'duration_bars')),
                'mae': sf(trade, 'MAE'),
                'mfe': sf(trade, 'MFE'),
                'eff': sf(trade, 'profit_efficiency'),
                'dd': sf(trade, 'trade_drawdown'),
                'rr': sf(trade, 'risk_reward_ratio'),
                'bil': int(sf(trade, 'bars_in_loss')),
                'bip': int(sf(trade, 'bars_in_profit')),
                'vol': sf(trade, 'trade_volatility'),
                'fees': sf(trade, 'total_fees'),
                'slip': sf(trade, 'total_slippage'),
                'risk': sf(trade, 'riesgo_aplicado'),
            })
        return json.dumps(result)

    def _build_summary_html(self) -> str:
        """Genera HTML del resumen completo de métricas del backtest."""
        m = self._summary_metrics
        if not m:
            return '<div class="nt">Sin datos de resumen</div>'

        def fv(key, fmt='.2f', suffix='', color=None):
            val = m.get(key)
            if val is None or isinstance(val, str) or (isinstance(val, float) and not np.isfinite(val)):
                return '<span style="color:#475569">\u2014</span>'
            if fmt == 'd':
                text = str(int(val))
            elif fmt == 's':
                text = str(val)
            else:
                text = format(val, fmt)
            text += suffix
            if color == 'auto':
                c = '#22c55e' if float(val) >= 0 else '#ef4444'
            elif color:
                c = color
            else:
                c = '#cbd5e1'
            return f'<span style="color:{c}">{text}</span>'

        def cell(label, val_html):
            return f'<div class="dm"><div class="dm-l">{label}</div><div class="dm-v">{val_html}</div></div>'

        def section(title, cells):
            return f'<div class="sh">{title}</div><div class="sg">{"".join(cells)}</div>'

        q = f' {self._quote_currency}' if self._quote_currency else ''

        parts = [
            section('Resumen General', [
                cell('Net Profit', fv('net_profit', '.2f', q, 'auto')),
                cell('ROI', fv('ROI', '.2f', '%', 'auto')),
                cell('Total Trades', fv('total_trades', 'd')),
                cell('Win Rate', fv('percent_profitable', '.1f', '%')),
                cell('Profit Factor', fv('profit_factor', '.2f')),
                cell('Expectancy', fv('expectancy', '.2f', q, 'auto')),
                cell('Win/Loss', fv('win_loss_ratio', '.2f')),
                cell('Gross Profit', fv('gross_profit', '.2f', q, 'auto')),
            ]),
            section('P&L', [
                cell('Gross Profit', fv('total_gross_profit', '.2f', q, '#22c55e')),
                cell('Gross Loss', fv('total_gross_loss', '.2f', q, '#ef4444')),
                cell('Avg Win', fv('avg_winning_trade', '.2f', q, '#22c55e')),
                cell('Avg Loss', fv('avg_losing_trade', '.2f', q, '#ef4444')),
                cell('Avg Win %', fv('avg_winning_trade_pct', '.2f', '%', '#22c55e')),
                cell('Avg Loss %', fv('avg_losing_trade_pct', '.2f', '%', '#ef4444')),
                cell('Largest Win', fv('largest_winning_trade', '.2f', q, '#22c55e')),
                cell('Largest Loss', fv('largest_losing_trade', '.2f', q, '#ef4444')),
                cell('Max Consec W', fv('max_consecutive_wins', 'd', '', '#22c55e')),
                cell('Max Consec L', fv('max_consecutive_losses', 'd', '', '#ef4444')),
                cell('Std Profit', fv('std_profit', '.2f', q)),
                cell('Avg Net P&L', fv('avg_trade_net_profit', '.2f', q, 'auto')),
            ]),
            section('Drawdown', [
                cell('Max DD', fv('max_drawdown', '.2f', q, '#ef4444')),
                cell('Max DD %', fv('max_drawdown_pct', '.2f', '%', '#ef4444')),
                cell('DD Duration', fv('drawdown_duration', 'd', ' bars')),
                cell('Avg DD', fv('avg_drawdown', '.2f', q, '#ef4444')),
            ]),
            section('Ratios', [
                cell('Sharpe', fv('sharpe_ratio', '.2f')),
                cell('Sortino', fv('sortino_ratio', '.2f')),
                cell('Recovery', fv('recovery_factor', '.2f')),
            ]),
            section('Tiempo', [
                cell('Duraci\u00f3n', fv('backtest_duration', 's')),
                cell('En Mercado', fv('time_in_market_pct', '.1f', '%')),
                cell('Trades/D\u00eda', fv('trades_per_day', '.2f')),
                cell('Avg Win Dur', fv('avg_winning_trade_duration_min', '.0f', ' min')),
                cell('Avg Loss Dur', fv('avg_losing_trade_duration_min', '.0f', ' min')),
            ]),
            section('Costes', [
                cell('Total Fees', fv('total_fees', '.2f', q)),
                cell('Total Slippage', fv('total_slippage_cost', '.2f', q)),
                cell('Avg Fee/Trade', fv('avg_fee_per_trade', '.2f', q)),
                cell('Fees % Capital', fv('fees_pct_of_capital', '.2f', '%')),
                cell('Costs % Gross', fv('costs_as_pct_of_gross_profit', '.1f', '%')),
            ]),
        ]
        return '<div class="ss">' + ''.join(parts) + '</div>'

    def _build_html(self, width, height, indicators) -> str:
        """Genera HTML con chart + panel lateral de trades."""
        candle_json = self._serialize_candle_data()
        volume_json = self._serialize_volume_data()
        trades_json = self._serialize_trades_for_panel()
        indicator_lines = self._serialize_indicator_data(indicators)

        total_bars = len(self._filtered_market)
        symbol = self.strategy.symbol
        bar_hours = self.strategy.timeframe.hours
        trades_df = self._filtered_trades
        n_trades = len(trades_df)
        summary_html = self._build_summary_html()

        # Stats para el panel
        if n_trades > 0 and 'pnl_pct' in trades_df.columns:
            wins = int((trades_df['pnl_pct'] > 0).sum())
            win_rate = f"{wins / n_trades * 100:.0f}"
            avg_pnl = float(trades_df['pnl_pct'].mean())
            total_pnl = float(trades_df['pnl_pct'].sum())
        else:
            win_rate, avg_pnl, total_pnl = "—", 0.0, 0.0

        avg_c = '#22c55e' if avg_pnl >= 0 else '#ef4444'
        tot_c = '#22c55e' if total_pnl >= 0 else '#ef4444'
        avg_s = f"{'+'if avg_pnl>=0 else''}{avg_pnl:.1f}%"
        tot_s = f"{'+'if total_pnl>=0 else''}{total_pnl:.1f}%"

        # Indicator JS
        indicator_js = ''
        for name, color, data_json in indicator_lines:
            var_name = ''.join(c if c.isalnum() else '_' for c in name)
            indicator_js += (
                f"cs{var_name}=chart.addLineSeries({{color:'{color}',"
                f"lineWidth:2,title:'{name}'}});"
                f"cs{var_name}.setData({data_json});\n    "
            )

        return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>{symbol} — Backtest</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Chakra+Petch:wght@400;600;700&family=DM+Mono:wght@400;500&display=swap" rel="stylesheet">
<script src="https://unpkg.com/lightweight-charts@4.2.3/dist/lightweight-charts.standalone.production.js"></script>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{background:#0c0e15;color:#e2e8f0;font-family:'DM Mono',monospace;height:100vh;overflow:hidden}}
#app{{display:flex;height:100vh}}
#chart-area{{flex:1;position:relative;min-width:0;overflow:hidden}}
#chart{{width:100%;height:100%}}
#legend{{position:absolute;top:12px;left:16px;z-index:10;font-size:12px;color:#94a3b8;pointer-events:none}}
#panel{{width:340px;background:#111622;border-left:1px solid #1e2531;display:flex;flex-direction:column;flex-shrink:0}}
.ph{{padding:16px;border-bottom:1px solid #1e2531}}
.pt{{font-family:'Chakra Petch',sans-serif;font-weight:700;font-size:15px;letter-spacing:1px;text-transform:uppercase;color:#f8fafc}}
.ps{{display:grid;grid-template-columns:1fr 1fr;gap:6px;margin-top:12px}}
.st{{background:#161d2e;border-radius:6px;padding:8px 10px}}
.sl{{font-size:9px;color:#64748b;text-transform:uppercase;letter-spacing:.8px}}
.sv{{font-size:13px;font-weight:500;margin-top:2px}}
.tl{{flex:1;overflow-y:auto;padding:8px}}
.ti{{background:#161d2e;border-radius:6px;padding:10px 12px;margin-bottom:4px;cursor:pointer;border:1px solid transparent;transition:border-color .12s,background .12s}}
.ti:hover{{border-color:#3b82f6;background:#182040}}
.ti.active{{border-color:#3b82f6;box-shadow:0 0 12px rgba(59,130,246,.15)}}
.tr{{display:flex;justify-content:space-between;align-items:center}}
.td{{font-size:10px;color:#64748b}}
.tp{{font-size:11px;margin-top:4px;color:#94a3b8;display:flex;justify-content:space-between;align-items:center}}
.tpnl{{font-weight:600;font-size:13px}}
.w{{color:#22c55e}}.l{{color:#ef4444}}
.tl::-webkit-scrollbar{{width:5px}}
.tl::-webkit-scrollbar-track{{background:transparent}}
.tl::-webkit-scrollbar-thumb{{background:#1e2531;border-radius:3px}}
.nt{{padding:32px 16px;text-align:center;color:#475569;font-size:12px}}
.cm{{position:absolute;pointer-events:none;z-index:1;width:0;height:0}}
.cm-b{{border-left:10px solid transparent;border-right:10px solid transparent;border-bottom:18px solid #00bfff;filter:drop-shadow(0 0 6px rgba(0,191,255,.7))}}
.cm-s{{border-left:10px solid transparent;border-right:10px solid transparent;border-top:18px solid #ffe000;filter:drop-shadow(0 0 6px rgba(255,224,0,.7))}}
.nav{{display:flex;gap:4px;padding:8px 16px;border-bottom:1px solid #1e2531}}
.nav button{{flex:1;padding:6px;background:#161d2e;border:1px solid #1e2531;border-radius:4px;color:#94a3b8;font-family:inherit;font-size:10px;cursor:pointer;transition:all .12s}}
.nav button:hover{{background:#1e2540;border-color:#3b82f6;color:#e2e8f0}}
.fb{{display:flex;gap:3px;padding:6px 16px 8px;border-bottom:1px solid #1e2531;flex-wrap:wrap}}
.fc{{padding:3px 7px;background:#161d2e;border:1px solid #1e2531;border-radius:3px;color:#64748b;font-family:inherit;font-size:9px;cursor:pointer;transition:all .15s;letter-spacing:.5px;text-transform:uppercase}}
.fc:hover{{color:#94a3b8;border-color:#475569}}
.fc.an{{background:#1e2540;border-color:#3b82f6;color:#e2e8f0}}
.fc.aw{{background:#052e16;border-color:#22c55e;color:#4ade80}}
.fc.al{{background:#2a0a0a;border-color:#ef4444;color:#f87171}}
.tamt{{font-size:10px;font-weight:600}}
.tdd{{display:none;grid-template-columns:1fr 1fr;gap:4px;margin-top:8px;padding-top:8px;border-top:1px solid #1e2531}}
.ti.active .tdd{{display:grid}}
.dm{{padding:4px 6px;background:#0c0e15;border-radius:4px}}
.dm-l{{font-size:8px;color:#475569;text-transform:uppercase;letter-spacing:.5px;cursor:help}}
.dm-v{{font-size:11px;color:#cbd5e1;margin-top:1px}}
.tabs{{display:flex;border-bottom:1px solid #1e2531}}
.tab{{flex:1;padding:10px;text-align:center;font-family:'Chakra Petch',sans-serif;font-weight:600;font-size:11px;letter-spacing:1.2px;text-transform:uppercase;color:#475569;cursor:pointer;border-bottom:2px solid transparent;transition:all .15s}}
.tab:hover{{color:#94a3b8;background:#161d2e}}
.tab.active{{color:#3b82f6;border-bottom-color:#3b82f6}}
.tc{{display:none;flex-direction:column;flex:1;overflow:hidden}}.tc.active{{display:flex}}
.ss{{overflow-y:auto;padding:8px 12px;flex:1}}
.ss::-webkit-scrollbar{{width:5px}}.ss::-webkit-scrollbar-track{{background:transparent}}.ss::-webkit-scrollbar-thumb{{background:#1e2531;border-radius:3px}}
.sh{{font-family:'Chakra Petch',sans-serif;font-weight:600;font-size:10px;letter-spacing:1px;text-transform:uppercase;color:#64748b;padding:12px 0 6px;border-bottom:1px solid #1e2531;margin-bottom:6px}}
.sh:first-child{{padding-top:4px}}
.sg{{display:grid;grid-template-columns:1fr 1fr;gap:4px;margin-bottom:8px}}
</style></head><body>
<div id="app">
  <div id="chart-area"><div id="legend"></div><div id="chart"></div></div>
  <div id="panel">
    <div class="ph">
      <div class="pt">{symbol} Trades</div>
      <div class="ps">
        <div class="st"><div class="sl">Trades</div><div class="sv">{n_trades}</div></div>
        <div class="st"><div class="sl">Win Rate</div><div class="sv">{win_rate}%</div></div>
        <div class="st"><div class="sl">Avg P&amp;L</div><div class="sv" style="color:{avg_c}">{avg_s}</div></div>
        <div class="st"><div class="sl">Total P&amp;L</div><div class="sv" style="color:{tot_c}">{tot_s}</div></div>
      </div>
    </div>
    <div class="tabs">
      <div class="tab active" data-t="summary" onclick="sTab('summary')">SUMMARY</div>
      <div class="tab" data-t="trades" onclick="sTab('trades')">TRADES</div>
    </div>
    <div class="tc" id="tc-trades">
      <div class="nav">
        <button onclick="prevTrade()">&#9664; Prev</button>
        <button onclick="showAll()">Show All</button>
        <button onclick="nextTrade()">Next &#9654;</button>
      </div>
      <div class="fb">
        <button class="fc an" data-f="all" onclick="ftrade('all')">ALL</button>
        <button class="fc" data-f="w10" onclick="ftrade('w10')" title="Top 10 Winners">BEST 10</button>
        <button class="fc" data-f="l10" onclick="ftrade('l10')" title="Top 10 Losers">WORST 10</button>
      </div>
      <div class="tl" id="tl"></div>
    </div>
    <div class="tc active" id="tc-summary">
      {summary_html}
    </div>
  </div>
</div>
<script>
var tData={trades_json};
var curIdx=-1;
var barH={bar_hours};
var qCur='{self._quote_currency}';
function fmtT(b){{var h=b*barH;if(h<1)return Math.round(h*60)+'m';if(h<24)return(h%1===0?h:h.toFixed(1))+'h';var d=h/24;return(d%1===0?d:d.toFixed(1))+'d';}}

// Panel de trades
var tl=document.getElementById('tl');
var allIdx=tData.map(function(_,i){{return i;}});
function rTl(idxs){{
  tl.innerHTML='';
  if(idxs.length===0){{tl.innerHTML='<div class="nt">Sin trades</div>';return;}}
  idxs.forEach(function(i){{
    var t=tData[i];
    var cls=t.pnl>=0?'w':'l';
    var sign=t.pnl>=0?'+':'';
    var asign=t.amt>=0?'+':'';
    var d=new Date(t.et*1000);
    var ds=d.toLocaleDateString('es',{{month:'short',day:'numeric'}})+' '+d.toLocaleTimeString('es',{{hour:'2-digit',minute:'2-digit'}});
    var div=document.createElement('div');
    div.className='ti';
    div.id='t'+i;
    div.innerHTML='<div class="tr"><span class="td">#'+(i+1)+' \\u00b7 '+ds+'</span><span class="tpnl '+cls+'">'+sign+t.pnl.toFixed(1)+'%</span></div><div class="tp"><div><span style="color:#22c55e">\\u25b2 '+t.ep.toFixed(0)+'</span> <span style="color:#475569">\\u2192</span> <span style="color:#ef4444">\\u25bc '+t.xp.toFixed(0)+'</span></div><span class="tamt '+cls+'">'+asign+t.amt.toFixed(2)+' '+qCur+'</span></div><div class="tdd"><div class="dm"><div class="dm-l" title="Tiempo total del trade desde entrada hasta salida">Duration</div><div class="dm-v">'+fmtT(t.dur)+' <span style="color:#475569">('+t.dur+'b)</span></div></div><div class="dm"><div class="dm-l" title="Desviaci\\u00f3n est\\u00e1ndar del precio durante el trade">Volatility</div><div class="dm-v">'+t.vol.toFixed(1)+'%</div></div><div class="dm"><div class="dm-l" title="M\\u00e1xima excursi\\u00f3n adversa: peor precio alcanzado contra tu posici\\u00f3n">MAE</div><div class="dm-v" style="color:#ef4444">'+t.mae.toFixed(2)+'</div></div><div class="dm"><div class="dm-l" title="M\\u00e1xima excursi\\u00f3n favorable: mejor precio alcanzado a tu favor">MFE</div><div class="dm-v" style="color:#22c55e">'+t.mfe.toFixed(2)+'</div></div><div class="dm"><div class="dm-l" title="Porcentaje del MFE capturado como beneficio real (PnL/MFE)">Efficiency</div><div class="dm-v">'+t.eff.toFixed(1)+'%</div></div><div class="dm"><div class="dm-l" title="Ratio riesgo/recompensa: MFE dividido por MAE">R:R Ratio</div><div class="dm-v">'+t.rr.toFixed(2)+'</div></div><div class="dm"><div class="dm-l" title="M\\u00e1xima ca\\u00edda desde el mejor punto del trade">Drawdown</div><div class="dm-v" style="color:#ef4444">'+t.dd.toFixed(2)+'%</div></div><div class="dm"><div class="dm-l" title="Porcentaje del capital arriesgado en este trade">Risk</div><div class="dm-v">'+t.risk.toFixed(1)+'%</div></div><div class="dm"><div class="dm-l" title="Tiempo que el trade estuvo en p\\u00e9rdida">Time Loss</div><div class="dm-v" style="color:#ef4444">'+fmtT(t.bil)+'</div></div><div class="dm"><div class="dm-l" title="Tiempo que el trade estuvo en beneficio">Time Profit</div><div class="dm-v" style="color:#22c55e">'+fmtT(t.bip)+'</div></div><div class="dm"><div class="dm-l" title="Comisiones totales pagadas (entrada + salida)">Fees</div><div class="dm-v">'+t.fees.toFixed(2)+' '+qCur+'</div></div><div class="dm"><div class="dm-l" title="Coste de deslizamiento entre precio esperado y ejecutado">Slippage</div><div class="dm-v">'+t.slip.toFixed(2)+' '+qCur+'</div></div></div>';
    div.onclick=function(){{goToTrade(i);}};
    tl.appendChild(div);
  }});
}}
rTl(allIdx);
function ftrade(mode){{
  var idxs;
  if(mode==='all'){{idxs=allIdx;}}
  else{{
    var asc=mode[0]==='l';
    var sorted=allIdx.slice().sort(function(a,b){{return asc?tData[a].pnl-tData[b].pnl:tData[b].pnl-tData[a].pnl;}});
    var n=mode.indexOf('10')>-1?10:5;
    idxs=sorted.slice(0,Math.min(n,sorted.length));
  }}
  rTl(idxs);
  document.querySelectorAll('.fc').forEach(function(el){{el.className='fc';}});
  var btn=document.querySelector('[data-f="'+mode+'"]');
  if(btn)btn.classList.add(mode[0]==='w'?'aw':mode[0]==='l'?'al':'an');
}}

function goToTrade(i){{
  if(i<0||i>=tData.length)return;
  curIdx=i;
  var t=tData[i];
  var pad=Math.max((t.xt-t.et)*0.5,7200);
  chart.timeScale().setVisibleRange({{from:t.et-pad,to:t.xt+pad}});
  document.querySelectorAll('.ti').forEach(function(el){{el.classList.toggle('active',el.id==='t'+i);}});
  var el=document.getElementById('t'+i);
  if(el)el.scrollIntoView({{block:'nearest',behavior:'smooth'}});
}}
function prevTrade(){{goToTrade(Math.max(0,(curIdx<0?0:curIdx)-1));}}
function nextTrade(){{goToTrade(Math.min(tData.length-1,(curIdx<0?0:curIdx)+1));}}
function showAll(){{
  if(tData.length>0){{
    chart.timeScale().setVisibleRange({{from:tData[0].et-86400,to:tData[tData.length-1].xt+86400}});
  }}else{{chart.timeScale().fitContent();}}
  curIdx=-1;
  document.querySelectorAll('.ti').forEach(function(el){{el.classList.remove('active');}});
}}
function sTab(tab){{
  document.querySelectorAll('.tc').forEach(function(el){{el.classList.remove('active');}});
  document.querySelectorAll('.tab').forEach(function(el){{el.classList.remove('active');}});
  document.getElementById('tc-'+tab).classList.add('active');
  document.querySelector('.tab[data-t="'+tab+'"]').classList.add('active');
}}

// Chart
var chartArea=document.getElementById('chart-area');
var chart=LightweightCharts.createChart(document.getElementById('chart'),{{
  width:chartArea.clientWidth,height:chartArea.clientHeight,
  layout:{{background:{{type:'solid',color:'#0c0e15'}},textColor:'#64748b',fontSize:11}},
  grid:{{vertLines:{{visible:false}},horzLines:{{color:'#1e2531'}}}},
  crosshair:{{mode:LightweightCharts.CrosshairMode.Normal}},
  rightPriceScale:{{borderColor:'#1e2531'}},
  timeScale:{{borderColor:'#1e2531',timeVisible:true,secondsVisible:false,rightOffset:12,barSpacing:6}},
  watermark:{{text:'{symbol}',color:'rgba(100,116,139,0.08)',visible:true,fontSize:64,horzAlign:'center',vertAlign:'center'}},
}});

var cs=chart.addCandlestickSeries({{
  upColor:'#22c55e',downColor:'#ef4444',
  borderUpColor:'#22c55e',borderDownColor:'#ef4444',
  wickUpColor:'#22c55e',wickDownColor:'#ef4444',
}});
cs.priceScale().applyOptions({{scaleMargins:{{top:0.05,bottom:0.25}}}});
cs.setData({candle_json});

try{{
  var vs=chart.addHistogramSeries({{priceFormat:{{type:'volume'}},priceScaleId:'vol'}});
  chart.priceScale('vol').applyOptions({{scaleMargins:{{top:0.75,bottom:0}},drawTicks:false}});
  vs.setData({volume_json});
}}catch(e){{console.warn('Vol:',e);}}

try{{{indicator_js}}}catch(e){{console.warn('Ind:',e);}}

// Vista inicial: primer trade o últimas 200 barras
if(tData.length>0){{goToTrade(0);}}
else if({total_bars}>200){{chart.timeScale().setVisibleLogicalRange({{from:{total_bars-200},to:{total_bars+10}}});}}
else{{chart.timeScale().fitContent();}}

// Legend OHLC
var leg=document.getElementById('legend');
chart.subscribeCrosshairMove(function(p){{
  if(!p||!p.time){{leg.innerHTML='';return;}}
  var d=p.seriesData.get(cs);if(!d)return;
  var c=d.close>=d.open?'#22c55e':'#ef4444';
  leg.innerHTML='<span style="color:'+c+'">{symbol}</span> O:'+d.open.toFixed(2)+' H:'+d.high.toFixed(2)+' L:'+d.low.toFixed(2)+' C:'+d.close.toFixed(2);
}});

// Resize
new ResizeObserver(function(){{chart.resize(chartArea.clientWidth,chartArea.clientHeight);}}).observe(chartArea);

// Custom HTML markers: crear una vez, reposicionar en cada cambio de vista
var mkEls=[];
tData.forEach(function(t){{
  [{{t:t.et,p:t.ep,b:1}},{{t:t.xt,p:t.xp,b:0}}].forEach(function(m){{
    var d=document.createElement('div');
    d.className='cm '+(m.b?'cm-b':'cm-s');
    d.style.display='none';
    chartArea.appendChild(d);
    mkEls.push({{el:d,t:m.t,p:m.p,b:m.b}});
  }});
}});
function uMk(){{
  mkEls.forEach(function(m){{
    var x=chart.timeScale().timeToCoordinate(m.t);
    var y=cs.priceToCoordinate(m.p);
    if(x===null||y===null){{m.el.style.display='none';return;}}
    m.el.style.display='';
    m.el.style.left=(x-10)+'px';
    m.el.style.top=(m.b?y:(y-18))+'px';
  }});
}}
chart.timeScale().subscribeVisibleLogicalRangeChange(function(){{requestAnimationFrame(uMk);}});
setTimeout(uMk,400);

// Keyboard navigation
document.addEventListener('keydown',function(e){{
  if(e.key==='ArrowLeft')prevTrade();
  if(e.key==='ArrowRight')nextTrade();
}});
</script></body></html>"""


# Alias de compatibilidad: por defecto usa el interactivo
BacktestVisualizer = BacktestVisualizerInteractive
