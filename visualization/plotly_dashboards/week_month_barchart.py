"""
Analisis temporal con barras horizontales en Plotly.

3 paneles: resultado por Año, Mes, Dia de la semana.
Hover con win rate y trade count (reemplaza legend panels de matplotlib).
"""

import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from utils.timeframe import DAYS_ORDER, MONTHS_ORDER
from visualization.plotly_theme import COLORS


def _compute_period_stats(df, period_col, period_order=None):
    """Compute net result, trade count, and win rate per period value."""
    if period_order is None:
        period_order = sorted(df[period_col].unique())

    rows = []
    for p in period_order:
        sub = df[df[period_col] == p]
        n = len(sub)
        if n > 0:
            wins = (sub['net_profit_loss'] > 0).sum()
            rows.append({
                'period': str(p) if not isinstance(p, str) else p,
                'net_result': sub['net_profit_loss'].sum(),
                'trades': n,
                'win_rate': wins / n * 100,
            })
        else:
            rows.append({
                'period': str(p) if not isinstance(p, str) else p,
                'net_result': 0, 'trades': 0, 'win_rate': 0,
            })
    return pd.DataFrame(rows)


def time_chart(df_trade_metrics, save_path=None):
    """
    Barchart horizontal de P&L por año, mes y dia de la semana.

    Args:
        df_trade_metrics: DataFrame con metricas de trades
        save_path: Ruta para guardar HTML (opcional)

    Returns:
        go.Figure
    """
    required_cols = ['day_of_week', 'month', 'year', 'net_profit_loss']
    for col in required_cols:
        if col not in df_trade_metrics.columns:
            raise ValueError(f"Columna '{col}' no existe en el DataFrame.")

    fig = make_subplots(
        rows=3, cols=1,
        subplot_titles=['Resultado por Año', 'Resultado por Mes', 'Resultado por Dia de la Semana'],
        vertical_spacing=0.08,
    )

    df = df_trade_metrics

    # ── Year Panel ───────────────────────────────────────────────────────
    year_df = _compute_period_stats(df, 'year')
    bar_colors = [COLORS['profit'] if v > 0 else COLORS['loss'] for v in year_df['net_result']]
    fig.add_trace(go.Bar(
        y=year_df['period'], x=year_df['net_result'],
        orientation='h',
        marker=dict(color=bar_colors, line=dict(color=COLORS['border'], width=0.5)),
        text=[f"  {int(t)} ops" for t in year_df['trades']],
        textposition='outside', textfont=dict(size=10, color=COLORS['text']),
        customdata=np.stack([year_df['win_rate'], year_df['trades']], axis=-1),
        hovertemplate='%{y}<br>Resultado: %{x:,.2f}<br>Win Rate: %{customdata[0]:.1f}%<br>Trades: %{customdata[1]:.0f}<extra></extra>',
        showlegend=False,
    ), row=1, col=1)
    fig.add_vline(x=0, line_color=COLORS['text_secondary'], opacity=0.3, row=1, col=1)

    # ── Month Panel ──────────────────────────────────────────────────────
    month_df = _compute_period_stats(df, 'month', MONTHS_ORDER)
    bar_colors_m = [COLORS['profit'] if v > 0 else COLORS['loss'] for v in month_df['net_result']]
    # Abbreviated labels
    month_labels = [p[:3] for p in month_df['period']]
    fig.add_trace(go.Bar(
        y=month_labels, x=month_df['net_result'],
        orientation='h',
        marker=dict(color=bar_colors_m, line=dict(color=COLORS['border'], width=0.5)),
        text=[f"  {int(t)} ops" for t in month_df['trades']],
        textposition='outside', textfont=dict(size=10, color=COLORS['text']),
        customdata=np.stack([month_df['win_rate'], month_df['trades']], axis=-1),
        hovertemplate='%{y}<br>Resultado: %{x:,.2f}<br>Win Rate: %{customdata[0]:.1f}%<br>Trades: %{customdata[1]:.0f}<extra></extra>',
        showlegend=False,
    ), row=2, col=1)
    fig.add_vline(x=0, line_color=COLORS['text_secondary'], opacity=0.3, row=2, col=1)

    # ── Day of Week Panel ────────────────────────────────────────────────
    day_df = _compute_period_stats(df, 'day_of_week', DAYS_ORDER)
    bar_colors_d = [COLORS['profit'] if v > 0 else COLORS['loss'] for v in day_df['net_result']]
    fig.add_trace(go.Bar(
        y=day_df['period'], x=day_df['net_result'],
        orientation='h',
        marker=dict(color=bar_colors_d, line=dict(color=COLORS['border'], width=0.5)),
        text=[f"  {int(t)} ops" for t in day_df['trades']],
        textposition='outside', textfont=dict(size=10, color=COLORS['text']),
        customdata=np.stack([day_df['win_rate'], day_df['trades']], axis=-1),
        hovertemplate='%{y}<br>Resultado: %{x:,.2f}<br>Win Rate: %{customdata[0]:.1f}%<br>Trades: %{customdata[1]:.0f}<extra></extra>',
        showlegend=False,
    ), row=3, col=1)
    fig.add_vline(x=0, line_color=COLORS['text_secondary'], opacity=0.3, row=3, col=1)

    # ── Layout ───────────────────────────────────────────────────────────
    fig.update_layout(
        height=900,
        margin=dict(t=60),
    )
    for i in range(1, 4):
        fig.update_xaxes(title_text='Resultado Neto', row=i, col=1)

    if save_path:
        fig.write_html(save_path)

    return fig
