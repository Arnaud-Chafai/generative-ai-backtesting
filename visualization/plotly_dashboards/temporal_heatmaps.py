"""
Heatmaps temporales unificados con Plotly.

3 heatmaps en un solo tab:
  1. Monthly Returns (Year x Month) — retornos mensuales con columna TOTAL
  2. Hour x Day of Week — patrones intradiarios
  3. Month x Day of Month — patrones calendario

Estilo: celdas limpias con valor clave, detalles ricos en hover.
"""

import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from utils.timeframe import DAYS_ORDER, MONTHS_ORDER, MONTHS_ABBR
from visualization.plotly_theme import COLORS, PROFIT_LOSS_COLORSCALE


# ── Mapa de meses nombre → numero ───────────────────────────────────────────
_MONTH_TO_NUM = {name: i + 1 for i, name in enumerate(MONTHS_ORDER)}


def visualize_temporal_heatmap(strategy, df_trade_metrics,
                               metric_column='net_profit_loss', save_path=None):
    """
    3 heatmaps temporales en un solo tab.

    Args:
        strategy: Objeto de estrategia
        df_trade_metrics: DataFrame con metricas de trades
        metric_column: Columna a analizar (default: net_profit_loss)
        save_path: Ruta para guardar HTML (opcional)

    Returns:
        go.Figure
    """
    strategy_name = getattr(strategy, 'strategy_name', 'Trading Strategy')
    symbol = getattr(strategy, 'symbol', '')
    timeframe = str(getattr(strategy, 'timeframe', '')).replace('Timeframe.', '')
    initial_capital = getattr(strategy, 'initial_capital', 10000)

    required_cols = ['day_of_week', 'month', 'hour', 'day', 'year']
    for col in required_cols:
        if col not in df_trade_metrics.columns:
            raise ValueError(f"Columna '{col}' no existe en el DataFrame.")

    df = df_trade_metrics.copy()
    df['month_num'] = df['month'].map(_MONTH_TO_NUM)

    n_years = df['year'].nunique()

    fig = make_subplots(
        rows=3, cols=1,
        subplot_titles=[
            f'Retornos Mensuales — {strategy_name} ({symbol} {timeframe})',
            'P&L Medio por Hora y Dia de la Semana',
            'P&L Medio por Mes y Dia del Mes',
        ],
        vertical_spacing=0.10,
        row_heights=[0.28, 0.30, 0.42],
    )

    # ═══════════════════════════════════════════════════════════════════════
    # HEATMAP 1: Monthly Returns (Year x Month + columna TOTAL)
    # ═══════════════════════════════════════════════════════════════════════
    monthly = df.groupby(['year', 'month_num']).agg(
        total_pnl=(metric_column, 'sum'),
        trades=(metric_column, 'count'),
        wins=(metric_column, lambda x: (x > 0).sum()),
    ).reset_index()
    monthly['return_pct'] = (monthly['total_pnl'] / initial_capital * 100).round(2)
    monthly['win_rate'] = (monthly['wins'] / monthly['trades'] * 100).round(1)
    monthly['avg_trade'] = (monthly['total_pnl'] / monthly['trades']).round(2)

    years = sorted(monthly['year'].unique())
    months_range = list(range(1, 13))

    z1, text1, hover1 = [], [], []
    for year in years:
        zr, tr, hr = [], [], []
        for m in months_range:
            row = monthly[(monthly['year'] == year) & (monthly['month_num'] == m)]
            if len(row) > 0:
                r = row.iloc[0]
                zr.append(r['return_pct'])
                tr.append(f"{r['return_pct']:+.1f}%")
                hr.append(
                    f"<b>{year} {MONTHS_ABBR[m-1]}</b><br>"
                    f"Return: {r['return_pct']:+.2f}%<br>"
                    f"P&L: {r['total_pnl']:+,.2f}<br>"
                    f"Trades: {int(r['trades'])}<br>"
                    f"Win Rate: {r['win_rate']:.1f}%<br>"
                    f"Avg/Trade: {r['avg_trade']:+,.2f}"
                )
            else:
                zr.append(None)
                tr.append('')
                hr.append(f"<b>{year} {MONTHS_ABBR[m-1]}</b><br>Sin trades")
        # Columna TOTAL
        yr_data = monthly[monthly['year'] == year]
        if len(yr_data) > 0:
            t_ret = yr_data['return_pct'].sum()
            t_pnl = yr_data['total_pnl'].sum()
            t_trades = int(yr_data['trades'].sum())
            t_wins = int(yr_data['wins'].sum())
            t_wr = (t_wins / t_trades * 100) if t_trades > 0 else 0
            zr.append(t_ret)
            tr.append(f"{t_ret:+.1f}%")
            hr.append(
                f"<b>{year} TOTAL</b><br>"
                f"Return: {t_ret:+.2f}%<br>"
                f"P&L: {t_pnl:+,.2f}<br>"
                f"Trades: {t_trades}<br>"
                f"Win Rate: {t_wr:.1f}%"
            )
        else:
            zr.append(None); tr.append(''); hr.append('')

        z1.append(zr); text1.append(tr); hover1.append(hr)

    col_labels = MONTHS_ABBR + ['TOTAL']
    z1_arr = np.array(z1, dtype=float)
    abs_max1 = np.nanmax(np.abs(z1_arr)) if not np.all(np.isnan(z1_arr)) else 1

    fig.add_trace(go.Heatmap(
        z=z1_arr, x=col_labels, y=[str(y) for y in years],
        text=text1, texttemplate='%{text}',
        textfont=dict(size=11, color=COLORS['text']),
        hovertext=hover1, hovertemplate='%{hovertext}<extra></extra>',
        colorscale=PROFIT_LOSS_COLORSCALE,
        zmid=0, zmin=-abs_max1, zmax=abs_max1,
        colorbar=dict(title='Ret %', ticksuffix='%', len=0.25, y=0.88),
        xgap=2, ygap=2,
    ), row=1, col=1)

    # Separador antes de TOTAL
    fig.add_vline(x=11.5, line_color=COLORS['highlight'], line_width=2,
                  opacity=0.6, row=1, col=1)

    # ═══════════════════════════════════════════════════════════════════════
    # HEATMAP 2: Hour x Day of Week
    # ═══════════════════════════════════════════════════════════════════════
    pivot_mean = pd.pivot_table(df, values=metric_column, index='day_of_week',
                                columns='hour', aggfunc='mean').reindex(DAYS_ORDER)
    pivot_sum = pd.pivot_table(df, values=metric_column, index='day_of_week',
                               columns='hour', aggfunc='sum').reindex(DAYS_ORDER)
    pivot_count = pd.pivot_table(df, values=metric_column, index='day_of_week',
                                 columns='hour', aggfunc='count').reindex(DAYS_ORDER)
    pivot_wins = pd.pivot_table(df, values=metric_column, index='day_of_week',
                                columns='hour',
                                aggfunc=lambda x: (x > 0).sum()).reindex(DAYS_ORDER)

    hours = list(pivot_mean.columns)
    x_labels2 = [f'{int(h)}:00' for h in hours]
    days_labels = list(pivot_mean.index)

    mean_vals = pivot_mean.values
    sum_vals = pivot_sum.fillna(0).values
    count_vals = pivot_count.fillna(0).values
    wins_vals = pivot_wins.fillna(0).values

    z2 = np.where(count_vals > 0, mean_vals, np.nan)
    abs_max2 = np.nanmax(np.abs(z2)) if not np.all(np.isnan(z2)) else 1

    text2 = np.where(
        count_vals > 0,
        np.vectorize(lambda v: f'{v:+.1f}')(mean_vals),
        ''
    )

    hover2 = np.empty_like(z2, dtype=object)
    for r in range(len(days_labels)):
        for c in range(len(hours)):
            cnt = int(count_vals[r, c])
            if cnt > 0:
                w = int(wins_vals[r, c])
                wr = w / cnt * 100
                hover2[r, c] = (
                    f"<b>{days_labels[r]}, {x_labels2[c]}</b><br>"
                    f"P&L Medio: {mean_vals[r, c]:+,.2f}<br>"
                    f"P&L Total: {sum_vals[r, c]:+,.2f}<br>"
                    f"Trades: {cnt}<br>"
                    f"Win Rate: {wr:.1f}%"
                )
            else:
                hover2[r, c] = f"<b>{days_labels[r]}, {x_labels2[c]}</b><br>Sin trades"

    fig.add_trace(go.Heatmap(
        z=z2, x=x_labels2, y=days_labels,
        text=text2, texttemplate='%{text}',
        textfont=dict(size=9, color=COLORS['text']),
        hovertext=hover2, hovertemplate='%{hovertext}<extra></extra>',
        colorscale=PROFIT_LOSS_COLORSCALE,
        zmid=0, zmin=-abs_max2, zmax=abs_max2,
        colorbar=dict(title='Avg P&L', len=0.25, y=0.50),
        xgap=1, ygap=1,
    ), row=2, col=1)

    # ═══════════════════════════════════════════════════════════════════════
    # HEATMAP 3: Month x Day of Month
    # ═══════════════════════════════════════════════════════════════════════
    pivot_mean3 = pd.pivot_table(df, values=metric_column, index='month',
                                 columns='day', aggfunc='mean')
    pivot_sum3 = pd.pivot_table(df, values=metric_column, index='month',
                                columns='day', aggfunc='sum')
    pivot_count3 = pd.pivot_table(df, values=metric_column, index='month',
                                  columns='day', aggfunc='count')
    pivot_wins3 = pd.pivot_table(df, values=metric_column, index='month',
                                 columns='day',
                                 aggfunc=lambda x: (x > 0).sum())

    if not pivot_mean3.empty:
        month_cat = pd.CategoricalIndex(pivot_mean3.index, categories=MONTHS_ORDER, ordered=True)
        order = month_cat.sort_values()
        pivot_mean3 = pivot_mean3.reindex(order)
        pivot_sum3 = pivot_sum3.reindex(order)
        pivot_count3 = pivot_count3.reindex(order)
        pivot_wins3 = pivot_wins3.reindex(order)

        days_cols = [str(int(d)) for d in pivot_mean3.columns]
        months_labels = list(pivot_mean3.index)

        mean3 = pivot_mean3.values
        sum3 = pivot_sum3.fillna(0).values
        cnt3 = pivot_count3.fillna(0).values
        w3 = pivot_wins3.fillna(0).values

        z3 = np.where(cnt3 > 0, mean3, np.nan)
        abs_max3 = np.nanmax(np.abs(z3)) if not np.all(np.isnan(z3)) else 1

        text3 = np.where(
            cnt3 > 0,
            np.vectorize(lambda v: f'{v:+.1f}')(mean3),
            ''
        )

        hover3 = np.empty_like(z3, dtype=object)
        for r in range(len(months_labels)):
            for c in range(len(days_cols)):
                cnt_v = int(cnt3[r, c])
                if cnt_v > 0:
                    wr = int(w3[r, c]) / cnt_v * 100
                    hover3[r, c] = (
                        f"<b>{months_labels[r]}, Dia {days_cols[c]}</b><br>"
                        f"P&L Medio: {mean3[r, c]:+,.2f}<br>"
                        f"P&L Total: {sum3[r, c]:+,.2f}<br>"
                        f"Trades: {cnt_v}<br>"
                        f"Win Rate: {wr:.1f}%"
                    )
                else:
                    hover3[r, c] = f"<b>{months_labels[r]}, Dia {days_cols[c]}</b><br>Sin trades"

        fig.add_trace(go.Heatmap(
            z=z3, x=days_cols, y=months_labels,
            text=text3, texttemplate='%{text}',
            textfont=dict(size=9, color=COLORS['text']),
            hovertext=hover3, hovertemplate='%{hovertext}<extra></extra>',
            colorscale=PROFIT_LOSS_COLORSCALE,
            zmid=0, zmin=-abs_max3, zmax=abs_max3,
            colorbar=dict(title='Avg P&L', len=0.25, y=0.12),
            xgap=1, ygap=1,
        ), row=3, col=1)
    else:
        fig.add_annotation(
            text='No hay suficientes datos para el analisis por mes',
            xref='x3 domain', yref='y3 domain', x=0.5, y=0.5,
            showarrow=False, font=dict(size=14, color=COLORS['text']),
        )

    # ── Layout ───────────────────────────────────────────────────────────
    fig.update_layout(
        height=1100,
        margin=dict(t=90, l=80),
        showlegend=False,
    )

    # Heatmap 1: meses arriba, años invertidos (mas reciente arriba)
    fig.update_xaxes(side='top', dtick=1, row=1, col=1)
    fig.update_yaxes(autorange='reversed', dtick=1, row=1, col=1)

    # Automargin para que no se corten labels de ejes Y
    for i in range(1, 4):
        fig.update_yaxes(automargin=True, row=i, col=1)
        fig.update_xaxes(automargin=True, row=i, col=1)

    # ── Reposicionar titulo del primer heatmap ────────────────────────
    # subplot_titles se posicionan justo encima del dominio de cada subplot.
    # El primer heatmap tiene xaxis side='top', asi que su titulo colisiona
    # con los tick labels del eje X. Lo desplazamos hacia arriba.
    if fig.layout.annotations:
        first_title = fig.layout.annotations[0]
        fig.layout.annotations[0].update(y=first_title.y + 0.05)

    if save_path:
        fig.write_html(save_path)

    return fig
