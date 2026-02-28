"""
Drawdown analysis dashboard con Plotly.

- Underwater equity plot (% bajo el pico)
- Top 5 peores drawdowns con duracion
- Histograma de drawdown durations
"""

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from visualization.plotly_theme import COLORS


def visualize_drawdown(strategy, df_trade_metrics, save_path=None):
    """
    Dashboard de analisis de drawdown.

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

    # Compute equity and drawdown series
    if 'cumulative_capital' in df_trade_metrics.columns:
        equity = df_trade_metrics['cumulative_capital'].values.astype(float)
    else:
        equity = initial_capital + df_trade_metrics['net_profit_loss'].cumsum().values

    x = np.arange(1, len(equity) + 1)
    peak = np.maximum.accumulate(equity)
    dd_pct = (equity - peak) / peak * 100  # negative values = underwater

    # ── Identify individual drawdown periods ─────────────────────────────
    in_dd = dd_pct < 0
    periods = []
    start = None
    for i in range(len(in_dd)):
        if in_dd[i] and start is None:
            start = i
        elif not in_dd[i] and start is not None:
            periods.append((start, i - 1))
            start = None
    if start is not None:  # still in drawdown at end
        periods.append((start, len(in_dd) - 1))

    # Build top-N drawdown table
    dd_records = []
    for s, e in periods:
        worst_idx = s + np.argmin(dd_pct[s:e + 1])
        dd_records.append({
            'start': s + 1, 'end': e + 1, 'trough': worst_idx + 1,
            'depth_pct': dd_pct[worst_idx],
            'depth_abs': peak[worst_idx] - equity[worst_idx],
            'duration': e - s + 1,
            'recovery': 'Yes' if e < len(in_dd) - 1 else 'No',
        })
    dd_records.sort(key=lambda r: r['depth_pct'])
    top5 = dd_records[:5]

    fig = make_subplots(
        rows=3, cols=1,
        row_heights=[0.45, 0.25, 0.30],
        subplot_titles=[
            f'Underwater Equity — {strategy_name} ({symbol} {timeframe})',
            'Top Drawdowns',
            'Duracion de Drawdowns (barras)',
        ],
        vertical_spacing=0.10,
    )

    # ── Panel 1: Underwater equity plot ──────────────────────────────────
    fig.add_trace(go.Scatter(
        x=x, y=dd_pct,
        fill='tozeroy', fillcolor='rgba(239,83,80,0.25)',
        line=dict(color=COLORS['loss'], width=1.5),
        hovertemplate='Op #%{x}<br>Drawdown: %{y:.2f}%<extra></extra>',
        showlegend=False,
    ), row=1, col=1)

    fig.add_hline(y=0, line_color=COLORS['text_secondary'], line_dash='dash',
                  opacity=0.4, row=1, col=1)

    # Highlight top 5 drawdowns with shaded regions
    shade_colors = [
        'rgba(239,83,80,0.15)', 'rgba(239,83,80,0.12)',
        'rgba(239,83,80,0.09)', 'rgba(239,83,80,0.07)',
        'rgba(239,83,80,0.05)',
    ]
    for i, rec in enumerate(top5):
        fig.add_vrect(
            x0=rec['start'], x1=rec['end'],
            fillcolor=shade_colors[i] if i < len(shade_colors) else shade_colors[-1],
            line_width=0, row=1, col=1,
        )
        # Label at the trough
        fig.add_annotation(
            x=rec['trough'], y=rec['depth_pct'],
            text=f"#{i+1}: {rec['depth_pct']:.1f}%",
            showarrow=True, arrowhead=2, arrowcolor=COLORS['loss'],
            font=dict(size=10, color=COLORS['loss']),
            bgcolor=COLORS['axes_bg'], borderpad=3,
            row=1, col=1,
        )

    # Max DD annotation
    if dd_records:
        worst = dd_records[0]
        fig.add_annotation(
            x=0.98, y=0.05, xref='x domain', yref='y domain',
            text=(f"<b>Max DD: {worst['depth_pct']:.2f}%</b> "
                  f"({worst['depth_abs']:.2f} abs, {worst['duration']} ops)"),
            showarrow=False,
            font=dict(size=12, color=COLORS['loss']),
            bgcolor=COLORS['axes_bg'], borderpad=5,
            xanchor='right',
            row=1, col=1,
        )

    # ── Panel 2: Top Drawdowns table as horizontal bars ──────────────────
    if top5:
        labels = [f"#{i+1} (Op {r['start']}-{r['end']})" for i, r in enumerate(top5)]
        depths = [abs(r['depth_pct']) for r in top5]
        durations = [r['duration'] for r in top5]
        recoveries = [r['recovery'] for r in top5]

        fig.add_trace(go.Bar(
            y=labels[::-1], x=depths[::-1],
            orientation='h',
            marker=dict(
                color=depths[::-1],
                colorscale=[[0, 'rgba(239,83,80,0.4)'], [1, COLORS['loss']]],
                line=dict(color=COLORS['border'], width=0.5),
            ),
            text=[f"{d:.1f}% | {dur} ops | Rec: {rec}"
                  for d, dur, rec in zip(depths[::-1], durations[::-1], recoveries[::-1])],
            textposition='inside',
            textfont=dict(color=COLORS['text'], size=11),
            hovertemplate='Drawdown: %{x:.2f}%<extra></extra>',
            showlegend=False,
        ), row=2, col=1)

    # ── Panel 3: Drawdown duration histogram ─────────────────────────────
    if dd_records:
        all_durations = [r['duration'] for r in dd_records]
        fig.add_trace(go.Histogram(
            x=all_durations,
            marker=dict(color=COLORS['loss'], line=dict(color=COLORS['border'], width=0.5)),
            opacity=0.8,
            hovertemplate='Duracion: %{x} ops<br>Frecuencia: %{y}<extra></extra>',
            showlegend=False,
        ), row=3, col=1)

        avg_dur = np.mean(all_durations)
        fig.add_vline(x=avg_dur, line_dash='dash', line_color=COLORS['text'],
                      opacity=0.7, row=3, col=1)
        fig.add_annotation(
            x=avg_dur, y=1, yref='y3 domain',
            text=f'Avg: {avg_dur:.1f}', showarrow=False,
            font=dict(size=10, color=COLORS['text']),
            yshift=10, row=3, col=1,
        )

    # ── Layout ───────────────────────────────────────────────────────────
    fig.update_layout(
        height=850,
        margin=dict(t=60),
        showlegend=False,
    )
    fig.update_yaxes(title_text='Drawdown (%)', row=1, col=1)
    fig.update_xaxes(title_text='Operacion #', row=1, col=1)
    fig.update_xaxes(title_text='Profundidad (%)', row=2, col=1)
    fig.update_xaxes(title_text='Duracion (operaciones)', row=3, col=1)
    fig.update_yaxes(title_text='Frecuencia', row=3, col=1)

    if save_path:
        fig.write_html(save_path)

    return fig
