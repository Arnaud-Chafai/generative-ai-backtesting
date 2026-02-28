"""
Monthly returns grid con Plotly.

Heatmap clasico Year × Month mostrando retornos mensuales.
Herramienta esencial de analisis cuantitativo para detectar consistencia y estacionalidad.
"""

import pandas as pd
import numpy as np
import plotly.graph_objects as go
from visualization.plotly_theme import COLORS, PROFIT_LOSS_COLORSCALE
from utils.timeframe import MONTHS_ABBR


def visualize_monthly_returns(strategy, df_trade_metrics, save_path=None):
    """
    Heatmap de retornos mensuales (Year × Month).

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

    required = ['year', 'month', 'net_profit_loss']
    for col in required:
        if col not in df_trade_metrics.columns:
            raise ValueError(f"Columna '{col}' no existe en el DataFrame.")

    df = df_trade_metrics.copy()

    # Map month names to numbers for sorting
    month_to_num = {name: i + 1 for i, name in enumerate(
        ['January', 'February', 'March', 'April', 'May', 'June',
         'July', 'August', 'September', 'October', 'November', 'December']
    )}
    df['month_num'] = df['month'].map(month_to_num)

    # Aggregate P&L by year-month
    monthly = df.groupby(['year', 'month_num']).agg(
        net_pnl=('net_profit_loss', 'sum'),
        trades=('net_profit_loss', 'count'),
        wins=('net_profit_loss', lambda x: (x > 0).sum()),
    ).reset_index()
    monthly['win_rate'] = (monthly['wins'] / monthly['trades'] * 100).round(1)
    monthly['return_pct'] = (monthly['net_pnl'] / initial_capital * 100).round(2)

    # Build matrix Year (rows) × Month (cols)
    years = sorted(monthly['year'].unique())
    months = list(range(1, 13))

    z = []       # return values
    text = []    # cell text
    hover = []   # hover text
    for year in years:
        z_row, text_row, hover_row = [], [], []
        for m in months:
            row = monthly[(monthly['year'] == year) & (monthly['month_num'] == m)]
            if len(row) > 0:
                ret = row.iloc[0]['return_pct']
                pnl = row.iloc[0]['net_pnl']
                trades = int(row.iloc[0]['trades'])
                wr = row.iloc[0]['win_rate']
                z_row.append(ret)
                text_row.append(f'{ret:+.1f}%')
                hover_row.append(
                    f'{year} {MONTHS_ABBR[m-1]}<br>'
                    f'Return: {ret:+.2f}%<br>'
                    f'P&L: {pnl:+,.2f}<br>'
                    f'Trades: {trades}<br>'
                    f'Win Rate: {wr:.1f}%'
                )
            else:
                z_row.append(None)
                text_row.append('')
                hover_row.append(f'{year} {MONTHS_ABBR[m-1]}<br>No trades')
        z.append(z_row)
        text.append(text_row)
        hover.append(hover_row)

    # Yearly totals (rightmost column)
    yearly_totals = []
    yearly_text = []
    yearly_hover = []
    for year in years:
        yr_data = monthly[monthly['year'] == year]
        total_ret = yr_data['return_pct'].sum()
        total_pnl = yr_data['net_pnl'].sum()
        total_trades = int(yr_data['trades'].sum())
        total_wins = int(yr_data['wins'].sum())
        yr_wr = (total_wins / total_trades * 100) if total_trades > 0 else 0
        yearly_totals.append(total_ret)
        yearly_text.append(f'{total_ret:+.1f}%')
        yearly_hover.append(
            f'{year} TOTAL<br>'
            f'Return: {total_ret:+.2f}%<br>'
            f'P&L: {total_pnl:+,.2f}<br>'
            f'Trades: {total_trades}<br>'
            f'Win Rate: {yr_wr:.1f}%'
        )

    # Append yearly total as 13th column
    col_labels = MONTHS_ABBR + ['TOTAL']
    for i in range(len(years)):
        z[i].append(yearly_totals[i])
        text[i].append(yearly_text[i])
        hover[i].append(yearly_hover[i])

    z_arr = np.array(z, dtype=float)
    abs_max = np.nanmax(np.abs(z_arr)) if not np.all(np.isnan(z_arr)) else 1

    fig = go.Figure()

    fig.add_trace(go.Heatmap(
        z=z_arr,
        x=col_labels,
        y=[str(y) for y in years],
        text=text,
        texttemplate='%{text}',
        textfont=dict(size=12, color=COLORS['text']),
        hovertext=hover,
        hovertemplate='%{hovertext}<extra></extra>',
        colorscale=PROFIT_LOSS_COLORSCALE,
        zmid=0, zmin=-abs_max, zmax=abs_max,
        colorbar=dict(title='Return %', ticksuffix='%'),
        xgap=2, ygap=2,
    ))

    # Separator line before TOTAL column
    fig.add_vline(x=11.5, line_color=COLORS['highlight'], line_width=2, opacity=0.8)

    # Monthly aggregate row at bottom
    monthly_agg = []
    monthly_agg_text = []
    for m in months:
        m_data = monthly[monthly['month_num'] == m]
        avg_ret = m_data['return_pct'].mean() if len(m_data) > 0 else None
        monthly_agg.append(avg_ret)
        monthly_agg_text.append(f'{avg_ret:+.1f}%' if avg_ret is not None else '')

    fig.update_layout(
        title=dict(
            text=f'Monthly Returns | {strategy_name} ({symbol} {timeframe})',
            x=0.5,
        ),
        height=max(300, 80 * len(years) + 150),
        xaxis=dict(side='top', dtick=1),
        yaxis=dict(autorange='reversed', dtick=1),
    )

    # Add monthly average annotation below
    avg_text = ' | '.join(
        f'{MONTHS_ABBR[i]}: {monthly_agg[i]:+.1f}%' if monthly_agg[i] is not None else f'{MONTHS_ABBR[i]}: -'
        for i in range(12)
    )
    fig.add_annotation(
        x=0.5, y=-0.08, xref='paper', yref='paper',
        text=f'<b>Avg by month:</b> {avg_text}',
        showarrow=False,
        font=dict(size=10, color=COLORS['text_secondary']),
    )

    if save_path:
        fig.write_html(save_path)

    return fig
