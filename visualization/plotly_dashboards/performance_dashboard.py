"""
Dashboard de rendimiento interactivo con Plotly.

Layout unificado Performance + Drawdown (4 filas x 2 columnas):
  Row 1: Curva de Equity (colspan=2) — eje X temporal
  Row 2: Underwater Equity (colspan=2) — eje X temporal
  Row 3: Histograma P&L + P&L Scatter por operacion
  Row 4: Top 5 Drawdowns + Histograma duracion DD (tiempo real)
"""

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from visualization.plotly_theme import COLORS, PROFIT_LOSS_COLORSCALE


def calculate_backtest_metrics(df_trade_metrics, initial_capital):
    """Calcula metricas basicas del backtest."""
    metrics = {}
    metrics['total_trades'] = len(df_trade_metrics)
    metrics['winning_trades'] = sum(df_trade_metrics['net_profit_loss'] > 0)
    metrics['losing_trades'] = sum(df_trade_metrics['net_profit_loss'] <= 0)
    total = metrics['total_trades']
    metrics['percent_profitable'] = metrics['winning_trades'] / total * 100 if total > 0 else 0
    metrics['gross_profit'] = df_trade_metrics[df_trade_metrics['net_profit_loss'] > 0]['net_profit_loss'].sum()
    metrics['gross_loss'] = df_trade_metrics[df_trade_metrics['net_profit_loss'] <= 0]['net_profit_loss'].sum()
    metrics['net_profit'] = df_trade_metrics['net_profit_loss'].sum()
    metrics['ROI'] = (metrics['net_profit'] / initial_capital) * 100
    if metrics['gross_loss'] != 0:
        metrics['profit_factor'] = abs(metrics['gross_profit'] / metrics['gross_loss'])
    else:
        metrics['profit_factor'] = float('inf') if metrics['gross_profit'] > 0 else 0
    metrics['expectancy'] = metrics['net_profit'] / total if total > 0 else 0

    if 'cumulative_capital' in df_trade_metrics.columns:
        cumulative = df_trade_metrics['cumulative_capital'].values
        max_so_far = np.maximum.accumulate(cumulative)
        drawdown = (cumulative - max_so_far) / max_so_far * 100
        metrics['max_drawdown_pct'] = abs(np.min(drawdown)) if len(drawdown) > 0 else 0
    else:
        metrics['max_drawdown_pct'] = 0

    return metrics


def _format_duration(hours):
    """
    Formatea duracion en horas a texto legible con dos niveles de unidad.

    Ejemplos: '45m', '5h 30m', '3d 14h', '2m 15d', '1a 2m'
    (a=año, m=mes a escala mensual, d=dia, h=hora, m=minuto a escala horaria)
    """
    total_minutes = round(hours * 60)
    if total_minutes < 60:
        return f"{total_minutes}m"
    total_hours = hours
    if total_hours < 24:
        h = int(total_hours)
        m = round((total_hours - h) * 60)
        return f"{h}h {m}m" if m > 0 else f"{h}h"
    total_days = hours / 24
    if total_days < 30:
        d = int(total_days)
        h = round((total_days - d) * 24)
        return f"{d}d {h}h" if h > 0 else f"{d}d"
    if total_days < 365:
        mo = int(total_days / 30)
        d = round(total_days - mo * 30)
        return f"{mo}m {d}d" if d > 0 else f"{mo}m"
    years = int(total_days / 365)
    mo = round((total_days - years * 365) / 30)
    return f"{years}a {mo}m" if mo > 0 else f"{years}a"


def _choose_duration_unit(durations_hours):
    """
    Elige la unidad y factor de conversion optimos para un array de duraciones.

    Returns:
        tuple: (label, divisor) — ej: ('horas', 1), ('dias', 24), ('minutos', 1/60)
    """
    if len(durations_hours) == 0:
        return 'horas', 1.0
    median = np.median(durations_hours)
    if median < 1:
        return 'minutos', 1 / 60
    if median < 48:
        return 'horas', 1.0
    return 'dias', 24.0


def _compute_drawdown_data(equity, timestamps=None):
    """
    Calcula serie de drawdown y periodos individuales.

    Args:
        equity: Array de valores de equity acumulada
        timestamps: Array de timestamps (datetime). Si se provee, calcula
                    duraciones reales en calendario.

    Returns:
        tuple: (dd_pct, top5_records, all_records)
    """
    peak = np.maximum.accumulate(equity)
    dd_pct = (equity - peak) / peak * 100

    # Identify individual drawdown periods
    in_dd = dd_pct < 0
    periods = []
    start = None
    for i in range(len(in_dd)):
        if in_dd[i] and start is None:
            start = i
        elif not in_dd[i] and start is not None:
            periods.append((start, i - 1))
            start = None
    if start is not None:
        periods.append((start, len(in_dd) - 1))

    has_time = timestamps is not None and len(timestamps) == len(equity)

    # Build drawdown records
    dd_records = []
    for s, e in periods:
        worst_idx = s + np.argmin(dd_pct[s:e + 1])
        rec = {
            'start': s + 1, 'end': e + 1, 'trough': worst_idx + 1,
            'depth_pct': dd_pct[worst_idx],
            'depth_abs': peak[worst_idx] - equity[worst_idx],
            'duration_ops': e - s + 1,
            'recovery': 'Yes' if e < len(in_dd) - 1 else 'No',
        }
        if has_time:
            td = timestamps[e] - timestamps[s]
            rec['duration_hours'] = td.total_seconds() / 3600
            rec['start_time'] = timestamps[s]
            rec['end_time'] = timestamps[e]
            rec['trough_time'] = timestamps[worst_idx]
        dd_records.append(rec)

    dd_records.sort(key=lambda r: r['depth_pct'])
    top5 = dd_records[:5]

    return dd_pct, top5, dd_records


def visualize_performance(strategy, df_trade_metrics, save_path=None):
    """
    Dashboard unificado de rendimiento y drawdown con Plotly.

    Layout 4x2:
      Row 1 (colspan=2): Curva de Equity — eje X temporal
      Row 2 (colspan=2): Underwater Equity — eje X temporal
      Row 3: Histograma P&L + KDE  |  P&L Scatter por operacion
      Row 4: Top 5 DD barras horiz |  Histograma duracion DD (tiempo real)

    Args:
        strategy: Objeto de estrategia
        df_trade_metrics: DataFrame con metricas de trades
        save_path: Ruta para guardar HTML (opcional)

    Returns:
        go.Figure
    """
    strategy_name = getattr(strategy, 'strategy_name', 'Trading Strategy')
    symbol = getattr(strategy, 'symbol', '')
    timeframe = str(getattr(strategy, 'timeframe', '')).replace('Timeframe.', '')
    initial_capital = getattr(strategy, 'initial_capital', 10000)
    currency = 'USDT'

    backtest_metrics = calculate_backtest_metrics(df_trade_metrics, initial_capital)

    # ── Compute equity and drawdown ───────────────────────────────────────
    if 'cumulative_capital' in df_trade_metrics.columns:
        equity = df_trade_metrics['cumulative_capital'].values.astype(float)
    else:
        equity = initial_capital + df_trade_metrics['net_profit_loss'].cumsum().values

    # Temporal axis: prefer exit_timestamp, fallback to entry_timestamp, then Op #
    timestamps = None
    use_time_axis = False
    for col in ('exit_timestamp', 'entry_timestamp'):
        if col in df_trade_metrics.columns:
            ts = pd.to_datetime(df_trade_metrics[col], errors='coerce')
            if ts.notna().all():
                timestamps = ts.values
                use_time_axis = True
                break

    if use_time_axis:
        x_axis = pd.to_datetime(timestamps)
    else:
        x_axis = np.arange(1, len(equity) + 1)

    op_nums = np.arange(1, len(equity) + 1)

    dd_pct, top5, dd_records = _compute_drawdown_data(
        equity,
        timestamps=pd.to_datetime(timestamps) if use_time_axis else None,
    )

    has_time_dd = use_time_axis and dd_records and 'duration_hours' in dd_records[0]

    # ── Subplot grid 4x2 ─────────────────────────────────────────────────
    fig = make_subplots(
        rows=4, cols=2,
        specs=[
            [{'colspan': 2}, None],   # Equity curve
            [{'colspan': 2}, None],   # Underwater equity
            [{}, {}],                  # P&L histogram | P&L scatter
            [{}, {}],                  # Top DD bars | DD duration hist
        ],
        row_heights=[0.30, 0.22, 0.24, 0.24],
        subplot_titles=[
            f'Curva de Equity — {strategy_name} ({symbol} {timeframe})',
            'Underwater Equity',
            'Distribucion de P&L', 'P&L por Operacion',
            'Top Drawdowns', 'Duracion de Drawdowns',
        ],
        vertical_spacing=0.09,
        horizontal_spacing=0.08,
    )

    # ── Row 1: Equity Curve ───────────────────────────────────────────────
    baseline = [initial_capital] * len(x_axis)

    # Build hover text with Op # for time-axis mode
    if use_time_axis:
        equity_hover = [
            f'Op #{n}<br>{t:%Y-%m-%d %H:%M}<br>Capital: {eq:,.2f} {currency}'
            for n, t, eq in zip(op_nums, pd.to_datetime(timestamps), equity)
        ]
    else:
        equity_hover = None

    # Invisible baseline for green fill reference
    fig.add_trace(go.Scatter(
        x=x_axis, y=baseline, mode='lines', line=dict(width=0),
        showlegend=False, hoverinfo='skip',
    ), row=1, col=1)

    # Green fill: profit region
    fig.add_trace(go.Scatter(
        x=x_axis, y=np.maximum(equity, initial_capital),
        fill='tonexty', fillcolor='rgba(38,166,154,0.15)',
        line=dict(width=0), showlegend=False, hoverinfo='skip',
    ), row=1, col=1)

    # Invisible baseline for red fill reference
    fig.add_trace(go.Scatter(
        x=x_axis, y=baseline, mode='lines', line=dict(width=0),
        showlegend=False, hoverinfo='skip',
    ), row=1, col=1)

    # Red fill: loss region
    fig.add_trace(go.Scatter(
        x=x_axis, y=np.minimum(equity, initial_capital),
        fill='tonexty', fillcolor='rgba(239,83,80,0.15)',
        line=dict(width=0), showlegend=False, hoverinfo='skip',
    ), row=1, col=1)

    # Visible baseline
    fig.add_trace(go.Scatter(
        x=x_axis, y=baseline, mode='lines',
        line=dict(color=COLORS['text_secondary'], dash='dash', width=1),
        name=f'Capital Inicial: {initial_capital} {currency}',
        hoverinfo='skip',
    ), row=1, col=1)

    # Main equity line
    if use_time_axis:
        fig.add_trace(go.Scatter(
            x=x_axis, y=equity, mode='lines',
            line=dict(color=COLORS['highlight'], width=2.5),
            name='Equity', showlegend=False,
            text=equity_hover, hoverinfo='text',
        ), row=1, col=1)
    else:
        fig.add_trace(go.Scatter(
            x=x_axis, y=equity, mode='lines',
            line=dict(color=COLORS['highlight'], width=2.5),
            name='Equity', showlegend=False,
            hovertemplate=f'Op #%{{x}}<br>Capital: %{{y:,.2f}} {currency}<extra></extra>',
        ), row=1, col=1)

    # Equity annotations
    final_capital = equity[-1]
    roi = backtest_metrics['ROI']
    roi_color = COLORS['profit'] if roi >= 0 else COLORS['loss']
    fig.add_annotation(
        x=0.02, y=0.88, xref='x domain', yref='y domain',
        text=f"<b>Capital Final: {final_capital:,.2f} {currency}</b>",
        showarrow=False, font=dict(size=13, color=COLORS['text']),
        bgcolor=COLORS['axes_bg'], borderpad=4,
        row=1, col=1,
    )
    fig.add_annotation(
        x=0.02, y=0.76, xref='x domain', yref='y domain',
        text=f"<b>ROI: {roi:+.2f}%</b>",
        showarrow=False, font=dict(size=13, color=roi_color),
        bgcolor=COLORS['axes_bg'], borderpad=4,
        row=1, col=1,
    )

    # ── Row 2: Underwater Equity ──────────────────────────────────────────
    if use_time_axis:
        dd_hover = [
            f'Op #{n}<br>{t:%Y-%m-%d %H:%M}<br>DD: {dd:.2f}%'
            for n, t, dd in zip(op_nums, pd.to_datetime(timestamps), dd_pct)
        ]
        fig.add_trace(go.Scatter(
            x=x_axis, y=dd_pct,
            fill='tozeroy', fillcolor='rgba(239,83,80,0.25)',
            line=dict(color=COLORS['loss'], width=1.5),
            text=dd_hover, hoverinfo='text',
            showlegend=False,
        ), row=2, col=1)
    else:
        fig.add_trace(go.Scatter(
            x=x_axis, y=dd_pct,
            fill='tozeroy', fillcolor='rgba(239,83,80,0.25)',
            line=dict(color=COLORS['loss'], width=1.5),
            hovertemplate='Op #%{x}<br>Drawdown: %{y:.2f}%<extra></extra>',
            showlegend=False,
        ), row=2, col=1)

    fig.add_hline(y=0, line_color=COLORS['text_secondary'], line_dash='dash',
                  opacity=0.4, row=2, col=1)

    # Highlight top 5 drawdowns: shaded regions + dot markers at trough
    shade_colors = [
        'rgba(239,83,80,0.15)', 'rgba(239,83,80,0.12)',
        'rgba(239,83,80,0.09)', 'rgba(239,83,80,0.07)',
        'rgba(239,83,80,0.05)',
    ]
    if top5:
        marker_x = []
        marker_y = []
        marker_hover = []

        for i, rec in enumerate(top5):
            if use_time_axis and 'start_time' in rec:
                vrect_x0 = rec['start_time']
                vrect_x1 = rec['end_time']
                trough_x = rec['trough_time']
            else:
                vrect_x0 = rec['start']
                vrect_x1 = rec['end']
                trough_x = rec['trough']

            fig.add_vrect(
                x0=vrect_x0, x1=vrect_x1,
                fillcolor=shade_colors[i] if i < len(shade_colors) else shade_colors[-1],
                line_width=0, row=2, col=1,
            )

            marker_x.append(trough_x)
            marker_y.append(rec['depth_pct'])

            dur_label = _format_duration(rec['duration_hours']) if has_time_dd else f"{rec['duration_ops']} ops"
            marker_hover.append(
                f"<b>#{i+1}</b><br>"
                f"DD: {rec['depth_pct']:.2f}%<br>"
                f"Duracion: {dur_label}<br>"
                f"Ops: {rec['start']}-{rec['end']}<br>"
                f"Recuperado: {rec['recovery']}"
            )

        fig.add_trace(go.Scatter(
            x=marker_x, y=marker_y,
            mode='markers',
            marker=dict(
                size=9, color=COLORS['loss'], symbol='circle',
                line=dict(color=COLORS['text'], width=1.5),
            ),
            hovertext=marker_hover,
            hoverinfo='text',
            showlegend=False,
        ), row=2, col=1)

    # Max DD annotation
    if dd_records:
        worst = dd_records[0]
        dur_text = _format_duration(worst['duration_hours']) if has_time_dd else f"{worst['duration_ops']} ops"
        fig.add_annotation(
            x=0.98, y=0.05, xref='x2 domain', yref='y2 domain',
            text=(f"<b>Max DD: {worst['depth_pct']:.2f}%</b> "
                  f"({worst['depth_abs']:.2f} abs, {dur_text})"),
            showarrow=False,
            font=dict(size=12, color=COLORS['loss']),
            bgcolor=COLORS['axes_bg'], borderpad=5,
            xanchor='right',
            row=2, col=1,
        )

    # ── Row 3: P&L Histogram + P&L Scatter ───────────────────────────────
    pnl = df_trade_metrics['net_profit_loss']

    # P&L Histogram
    fig.add_trace(go.Histogram(
        x=pnl, nbinsx=25,
        marker=dict(color=COLORS['highlight'], line=dict(color=COLORS['border'], width=0.5)),
        opacity=0.8, name='P&L',
        hovertemplate='Rango: %{x}<br>Frecuencia: %{y}<extra></extra>',
    ), row=3, col=1)

    # KDE overlay
    try:
        from scipy.stats import gaussian_kde
        kde_x = np.linspace(pnl.min(), pnl.max(), 200)
        kde_y = gaussian_kde(pnl.dropna())(kde_x)
        bin_width = (pnl.max() - pnl.min()) / 25
        kde_y_scaled = kde_y * len(pnl) * bin_width
        fig.add_trace(go.Scatter(
            x=kde_x, y=kde_y_scaled,
            mode='lines', line=dict(color=COLORS['text'], width=2),
            showlegend=False, hoverinfo='skip',
        ), row=3, col=1)
    except ImportError:
        pass

    fig.add_vline(x=0, line_dash='dash', line_color=COLORS['text_secondary'],
                  opacity=0.5, row=3, col=1)

    # P&L Scatter (keeps Op # on X — sequential view)
    trade_colors = [COLORS['profit'] if v > 0 else COLORS['loss'] for v in pnl]
    fig.add_trace(go.Scatter(
        x=list(range(1, len(pnl) + 1)),
        y=pnl,
        mode='markers',
        marker=dict(size=7, color=trade_colors, opacity=0.8,
                    line=dict(color=COLORS['border'], width=0.5)),
        name='Trades',
        hovertemplate='Op #%{x}<br>P&L: %{y:,.2f}<extra></extra>',
    ), row=3, col=2)

    fig.add_hline(y=0, line_dash='dash', line_color=COLORS['text_secondary'],
                  opacity=0.5, row=3, col=2)

    # ── Row 4: Top DD Bars + DD Duration Histogram ────────────────────────
    if top5:
        labels = [f"#{i+1}" for i in range(len(top5))]
        depths = [abs(r['depth_pct']) for r in top5]

        # Inside bar: depth + duration (compact)
        if has_time_dd:
            bar_texts = [
                f"{abs(r['depth_pct']):.1f}% — {_format_duration(r['duration_hours'])}"
                for r in top5
            ]
        else:
            bar_texts = [
                f"{abs(r['depth_pct']):.1f}% — {r['duration_ops']} ops"
                for r in top5
            ]

        # Hover: full detail
        hover_texts = []
        for r in top5:
            dur = _format_duration(r['duration_hours']) if has_time_dd else f"{r['duration_ops']} ops"
            hover_texts.append(
                f"DD: {r['depth_pct']:.2f}%<br>"
                f"Duracion: {dur}<br>"
                f"Ops: {r['start']}-{r['end']}<br>"
                f"Recuperado: {r['recovery']}"
            )

        fig.add_trace(go.Bar(
            y=labels[::-1], x=depths[::-1],
            orientation='h',
            marker=dict(
                color=depths[::-1],
                colorscale=[[0, 'rgba(239,83,80,0.4)'], [1, COLORS['loss']]],
                line=dict(color=COLORS['border'], width=0.5),
            ),
            text=bar_texts[::-1],
            textposition='inside',
            textfont=dict(color=COLORS['text'], size=11),
            hovertext=hover_texts[::-1],
            hoverinfo='text',
            showlegend=False,
        ), row=4, col=1)

    if dd_records:
        if has_time_dd:
            durations_hours = [r['duration_hours'] for r in dd_records]
            dur_unit_label, dur_divisor = _choose_duration_unit(durations_hours)
            hist_values = [h / dur_divisor for h in durations_hours]
            dur_axis_label = f'Duracion ({dur_unit_label})'
        else:
            hist_values = [r['duration_ops'] for r in dd_records]
            dur_axis_label = 'Duracion (operaciones)'

        fig.add_trace(go.Histogram(
            x=hist_values,
            marker=dict(color=COLORS['loss'], line=dict(color=COLORS['border'], width=0.5)),
            opacity=0.8,
            hovertemplate=f'Duracion: %{{x:.1f}} {dur_unit_label if has_time_dd else "ops"}<br>Frecuencia: %{{y}}<extra></extra>',
            showlegend=False,
        ), row=4, col=2)

        avg_val = np.mean(hist_values)
        fig.add_vline(x=avg_val, line_dash='dash', line_color=COLORS['text'],
                      opacity=0.7, row=4, col=2)
        fig.add_annotation(
            x=avg_val, y=1, yref='y8 domain',
            text=f'Avg: {avg_val:.1f}', showarrow=False,
            font=dict(size=10, color=COLORS['text']),
            yshift=10, row=4, col=2,
        )

        fig.update_xaxes(title_text=dur_axis_label, row=4, col=2)

    # ── Layout ────────────────────────────────────────────────────────────
    fig.update_layout(
        height=1200,
        margin=dict(t=60),
        showlegend=False,
    )

    x_label = '' if use_time_axis else 'Operacion #'
    fig.update_xaxes(title_text=x_label, row=1, col=1)
    fig.update_yaxes(title_text=f'Capital ({currency})', row=1, col=1)
    fig.update_xaxes(title_text=x_label, row=2, col=1)
    fig.update_yaxes(title_text='Drawdown (%)', row=2, col=1)
    fig.update_xaxes(title_text=f'P&L ({currency})', row=3, col=1)
    fig.update_yaxes(title_text='Frecuencia', row=3, col=1)
    fig.update_xaxes(title_text='Operacion #', row=3, col=2)
    fig.update_yaxes(title_text=f'P&L ({currency})', row=3, col=2)
    fig.update_xaxes(title_text='Profundidad (%)', row=4, col=1)
    fig.update_yaxes(title_text='Frecuencia', row=4, col=2)

    if save_path:
        fig.write_html(save_path)

    return fig
