"""
Tab unificado de analisis temporal con sub-tabs (Anual/Semanal/Mensual).

Combina heatmap + barras P&L en un layout side-by-side:
  - Col 1 (82%): Heatmap
  - Col 2 (18%): Barra P&L total alineada con cada fila del heatmap

3 vistas con botones Plotly (updatemenus) que REEMPLAZAN datos de 2 traces
(en vez de visibility toggling, que falla con ejes categoricos).
"""

import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from utils.timeframe import DAYS_ORDER, MONTHS_ORDER, MONTHS_ABBR
from visualization.plotly_theme import COLORS, PROFIT_LOSS_COLORSCALE


# ── Constantes ────────────────────────────────────────────────────────────────

_MONTH_TO_NUM = {name: i + 1 for i, name in enumerate(MONTHS_ORDER)}

_ACCENT_COLOR = COLORS['highlight']  # #2962FF — for avg trade bars


# ── Helpers privados ──────────────────────────────────────────────────────────

def _build_annual_heatmap_data(df, metric_column, initial_capital):
    """Build z/text/hover matrices for Year x Month heatmap with TOTAL column."""
    df = df.copy()
    df['month_num'] = df['month'].map(_MONTH_TO_NUM)

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

    z, text, hover = [], [], []
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

        # TOTAL column
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
            zr.append(None)
            tr.append('')
            hr.append('')

        z.append(zr)
        text.append(tr)
        hover.append(hr)

    col_labels = MONTHS_ABBR + ['TOTAL']
    y_labels = [str(y) for y in years]

    return z, text, hover, col_labels, y_labels


def _build_hourday_heatmap_data(df, metric_column):
    """Build z/text/hover matrices for Hour x Day of Week heatmap."""
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
    x_labels = [f'{int(h)}:00' for h in hours]
    y_labels = list(pivot_mean.index)

    mean_vals = pivot_mean.values
    sum_vals = pivot_sum.fillna(0).values
    count_vals = pivot_count.fillna(0).values
    wins_vals = pivot_wins.fillna(0).values

    z = np.where(count_vals > 0, mean_vals, np.nan)

    text = np.where(
        count_vals > 0,
        np.vectorize(lambda v: f'{v:+.1f}')(mean_vals),
        ''
    )

    hover = np.empty_like(z, dtype=object)
    for r in range(len(y_labels)):
        for c in range(len(hours)):
            cnt = int(count_vals[r, c])
            if cnt > 0:
                w = int(wins_vals[r, c])
                wr = w / cnt * 100
                hover[r, c] = (
                    f"<b>{y_labels[r]}, {x_labels[c]}</b><br>"
                    f"P&L Medio: {mean_vals[r, c]:+,.2f}<br>"
                    f"P&L Total: {sum_vals[r, c]:+,.2f}<br>"
                    f"Trades: {cnt}<br>"
                    f"Win Rate: {wr:.1f}%"
                )
            else:
                hover[r, c] = f"<b>{y_labels[r]}, {x_labels[c]}</b><br>Sin trades"

    return z.tolist(), text.tolist(), hover.tolist(), x_labels, y_labels


def _build_monthday_heatmap_data(df, metric_column):
    """Build z/text/hover matrices for Month x Day of Month heatmap."""
    pivot_mean = pd.pivot_table(df, values=metric_column, index='month',
                                columns='day', aggfunc='mean')
    pivot_sum = pd.pivot_table(df, values=metric_column, index='month',
                               columns='day', aggfunc='sum')
    pivot_count = pd.pivot_table(df, values=metric_column, index='month',
                                 columns='day', aggfunc='count')
    pivot_wins = pd.pivot_table(df, values=metric_column, index='month',
                                columns='day',
                                aggfunc=lambda x: (x > 0).sum())

    if pivot_mean.empty:
        return [], [], [], [], []

    month_cat = pd.CategoricalIndex(pivot_mean.index, categories=MONTHS_ORDER, ordered=True)
    order = month_cat.sort_values()
    pivot_mean = pivot_mean.reindex(order)
    pivot_sum = pivot_sum.reindex(order)
    pivot_count = pivot_count.reindex(order)
    pivot_wins = pivot_wins.reindex(order)

    x_labels = [str(int(d)) for d in pivot_mean.columns]
    y_labels = list(pivot_mean.index)

    mean_vals = pivot_mean.values
    sum_vals = pivot_sum.fillna(0).values
    cnt_vals = pivot_count.fillna(0).values
    wins_vals = pivot_wins.fillna(0).values

    z = np.where(cnt_vals > 0, mean_vals, np.nan)

    text = np.where(
        cnt_vals > 0,
        np.vectorize(lambda v: f'{v:+.1f}')(mean_vals),
        ''
    )

    hover = np.empty_like(z, dtype=object)
    for r in range(len(y_labels)):
        for c in range(len(x_labels)):
            cnt = int(cnt_vals[r, c])
            if cnt > 0:
                wr = int(wins_vals[r, c]) / cnt * 100
                hover[r, c] = (
                    f"<b>{y_labels[r]}, Dia {x_labels[c]}</b><br>"
                    f"P&L Medio: {mean_vals[r, c]:+,.2f}<br>"
                    f"P&L Total: {sum_vals[r, c]:+,.2f}<br>"
                    f"Trades: {cnt}<br>"
                    f"Win Rate: {wr:.1f}%"
                )
            else:
                hover[r, c] = f"<b>{y_labels[r]}, Dia {x_labels[c]}</b><br>Sin trades"

    return z.tolist(), text.tolist(), hover.tolist(), x_labels, y_labels


def _compute_period_stats(df, period_col, period_order=None):
    """Compute net result, avg trade, trade count, and win rate per period."""
    if period_order is None:
        period_order = sorted(df[period_col].unique())

    rows = []
    for p in period_order:
        sub = df[df[period_col] == p]
        n = len(sub)
        if n > 0:
            wins = (sub['net_profit_loss'] > 0).sum()
            total = sub['net_profit_loss'].sum()
            rows.append({
                'period': str(p) if not isinstance(p, str) else p,
                'net_result': total,
                'avg_trade': total / n,
                'trades': n,
                'win_rate': wins / n * 100,
            })
        else:
            rows.append({
                'period': str(p) if not isinstance(p, str) else p,
                'net_result': 0, 'avg_trade': 0, 'trades': 0, 'win_rate': 0,
            })
    return pd.DataFrame(rows)


def _build_stat_annotations(stats_df):
    """Build the 3 stat-strip annotations for a given view."""
    total_trades = int(stats_df['trades'].sum())
    total_wins = int(
        stats_df.apply(lambda r: r['win_rate'] * r['trades'] / 100, axis=1).sum()
    )
    global_wr = (total_wins / total_trades * 100) if total_trades > 0 else 0

    if len(stats_df) > 0 and stats_df['net_result'].abs().sum() > 0:
        best_idx = stats_df['net_result'].idxmax()
        worst_idx = stats_df['net_result'].idxmin()
        best = stats_df.loc[best_idx]
        worst = stats_df.loc[worst_idx]
        best_text = f"Mejor: {best['period']} {best['net_result']:+,.0f}"
        worst_text = f"Peor: {worst['period']} {worst['net_result']:+,.0f}"
    else:
        best_text = "Mejor: —"
        worst_text = "Peor: —"

    summary_text = f"{total_trades} trades  |  WR: {global_wr:.0f}%"

    return [
        dict(
            text=f"<b>{best_text}</b>",
            x=0.0, y=1.06, xref='paper', yref='paper',
            xanchor='left', yanchor='bottom',
            showarrow=False,
            font=dict(size=12, color=COLORS['profit']),
        ),
        dict(
            text=f"<b>{worst_text}</b>",
            x=0.38, y=1.06, xref='paper', yref='paper',
            xanchor='left', yanchor='bottom',
            showarrow=False,
            font=dict(size=12, color=COLORS['loss']),
        ),
        dict(
            text=f"<b>{summary_text}</b>",
            x=1.0, y=1.06, xref='paper', yref='paper',
            xanchor='right', yanchor='bottom',
            showarrow=False,
            font=dict(size=12, color=COLORS['text_secondary']),
        ),
    ]


# ── Funcion principal ─────────────────────────────────────────────────────────

def visualize_temporal_analysis(strategy, df_trade_metrics,
                                metric_column='net_profit_loss', save_path=None):
    """
    Tab unificado de analisis temporal con sub-tabs (Anual/Semanal/Mensual).

    Usa 3 traces fijos (1 Heatmap + 2 Bar) y botones updatemenus que REEMPLAZAN
    los datos de cada trace via restyle. Esto evita el problema de ejes categoricos
    compartidos que ocurre con el patron de 9 traces + visibility toggling.

    Args:
        strategy: Objeto de estrategia
        df_trade_metrics: DataFrame con metricas de trades
        metric_column: Columna a analizar (default: net_profit_loss)
        save_path: Ruta para guardar HTML (opcional)

    Returns:
        go.Figure
    """
    initial_capital = getattr(strategy, 'initial_capital', 10000)

    required_cols = ['day_of_week', 'month', 'hour', 'day', 'year', 'net_profit_loss']
    for col in required_cols:
        if col not in df_trade_metrics.columns:
            raise ValueError(f"Columna '{col}' no existe en el DataFrame.")

    df = df_trade_metrics.copy()

    # ══════════════════════════════════════════════════════════════════════════
    # COMPUTE DATA FOR ALL 3 VIEWS
    # ══════════════════════════════════════════════════════════════════════════

    z1, text1, hover1, xcols1, ycols1 = _build_annual_heatmap_data(
        df, metric_column, initial_capital
    )
    z1_arr = np.array(z1, dtype=float)
    abs_max1 = np.nanmax(np.abs(z1_arr)) if not np.all(np.isnan(z1_arr)) else 1
    year_stats = _compute_period_stats(df, 'year')

    z2, text2, hover2, xcols2, ycols2 = _build_hourday_heatmap_data(df, metric_column)
    z2_arr = np.array(z2, dtype=float)
    abs_max2 = np.nanmax(np.abs(z2_arr)) if not np.all(np.isnan(z2_arr)) else 1
    day_stats = _compute_period_stats(df, 'day_of_week', DAYS_ORDER)

    z3, text3, hover3, xcols3, ycols3 = _build_monthday_heatmap_data(df, metric_column)
    if z3:
        z3_arr = np.array(z3, dtype=float)
        abs_max3 = np.nanmax(np.abs(z3_arr)) if not np.all(np.isnan(z3_arr)) else 1
    else:
        abs_max3 = 1
        z3 = [[0]]
        text3 = [['']]
        hover3 = [['Sin datos']]
        xcols3 = ['1']
        ycols3 = ['—']

    month_stats = _compute_period_stats(df, 'month', MONTHS_ORDER)
    # ── Per-view data arrays ──────────────────────────────────────────────
    all_z = [z1, z2, z3]
    all_text = [text1, text2, text3]
    all_hover = [hover1, hover2, hover3]
    all_xcols = [xcols1, xcols2, xcols3]
    all_ycols = [ycols1, ycols2, ycols3]
    all_amax = [abs_max1, abs_max2, abs_max3]
    all_stats = [year_stats, day_stats, month_stats]

    # Cell text on all views — font size scales down for denser grids
    all_hm_texttemplate = ['%{text}', '%{text}', '%{text}']
    all_hm_ts = [11, 8, 7]
    all_xgap = [2, 1, 1]
    all_ygap = [2, 1, 1]
    # Hour labels angled for weekly view; flat for annual/monthly
    all_tickangle = [0, -45, 0]

    # ══════════════════════════════════════════════════════════════════════════
    # CREATE FIGURE WITH 2 TRACES (Heatmap + Bar, initial = Annual)
    # ══════════════════════════════════════════════════════════════════════════

    fig = make_subplots(
        rows=1, cols=2,
        column_widths=[0.82, 0.18],
        horizontal_spacing=0.03,
    )

    # --- Trace 0: Heatmap (row=1, col=1) ---
    fig.add_trace(go.Heatmap(
        z=z1, x=xcols1, y=ycols1,
        text=text1, texttemplate='%{text}',
        textfont=dict(size=11, color=COLORS['text']),
        hovertext=hover1, hovertemplate='%{hovertext}<extra></extra>',
        colorscale=PROFIT_LOSS_COLORSCALE,
        zmid=0, zmin=-abs_max1, zmax=abs_max1,
        xgap=2, ygap=2,
        showscale=False,
    ), row=1, col=1)

    # --- Trace 1: P&L total bars aligned with heatmap rows (row=1, col=2) ---
    bar_colors_0 = [COLORS['profit'] if v > 0 else COLORS['loss']
                    for v in year_stats['net_result']]
    fig.add_trace(go.Bar(
        y=list(year_stats['period']), x=list(year_stats['net_result']),
        orientation='h',
        marker=dict(color=bar_colors_0,
                    line=dict(color=COLORS['border'], width=0.5)),
        text=[f" {int(t)}" for t in year_stats['trades']],
        textposition='outside',
        textfont=dict(size=9, color=COLORS['text_secondary']),
        cliponaxis=False,
        customdata=np.stack([year_stats['win_rate'], year_stats['trades']], axis=-1),
        hovertemplate=(
            '%{y}<br>'
            'P&L Total: %{x:,.2f}<br>'
            'Win Rate: %{customdata[0]:.1f}%<br>'
            'Trades: %{customdata[1]:.0f}<extra></extra>'
        ),
        showlegend=False,
    ), row=1, col=2)

    # ══════════════════════════════════════════════════════════════════════════
    # BUILD UPDATEMENUS BUTTONS (data replacement for 2 traces)
    # ══════════════════════════════════════════════════════════════════════════

    view_labels = ['Anual', 'Semanal', 'Mensual']
    view_annotations = [_build_stat_annotations(s) for s in all_stats]

    total_separator = dict(
        type='line', x0=11.5, x1=11.5, y0=0, y1=1,
        xref='x', yref='y domain',
        line=dict(color=COLORS['highlight'], width=2, dash='solid'),
        opacity=0.6,
    )

    buttons = []
    for vi in range(3):
        stats = all_stats[vi]

        pnl_colors = [COLORS['profit'] if v > 0 else COLORS['loss']
                      for v in stats['net_result']]

        # ── Trace data replacement (restyle) ──────────────────────────────
        # Array len = 2 → per-trace;  len = 1 → broadcast to all
        trace_update = {
            # Per-trace (len=2)
            'x': [all_xcols[vi], list(stats['net_result'])],
            'y': [all_ycols[vi], list(stats['period'])],
            'text': [
                all_text[vi],
                [f" {int(t)}" for t in stats['trades']],
            ],
            'texttemplate': [all_hm_texttemplate[vi], '%{text}'],
            'textfont.size': [all_hm_ts[vi], 9],
            'marker.color': [None, pnl_colors],
            'customdata': [
                None,
                np.stack([stats['win_rate'], stats['trades']], axis=-1).tolist(),
            ],
            # Broadcast (len=1): Bar ignores heatmap-only props
            'z': [all_z[vi]],
            'hovertext': [all_hover[vi]],
            'zmin': [-all_amax[vi]],
            'zmax': [all_amax[vi]],
            'xgap': [all_xgap[vi]],
            'ygap': [all_ygap[vi]],
        }

        # ── Layout update (relayout) ─────────────────────────────────────
        y_reversed = 'reversed' if vi == 0 else True

        layout_update = {
            'annotations': view_annotations[vi],
            'xaxis.autorange': True,
            'xaxis.side': 'top' if vi == 0 else 'bottom',
            'xaxis.tickangle': all_tickangle[vi],
            'yaxis.autorange': y_reversed,
            'xaxis2.autorange': True,
            'yaxis2.autorange': y_reversed,
            'shapes': [total_separator] if vi == 0 else [],
        }

        buttons.append(dict(
            label=f'  {view_labels[vi]}  ',
            method='update',
            args=[trace_update, layout_update],
        ))

    # ══════════════════════════════════════════════════════════════════════════
    # LAYOUT
    # ══════════════════════════════════════════════════════════════════════════

    fig.update_layout(
        height=800,
        margin=dict(t=100, l=60, r=30, b=50),
        showlegend=False,
        updatemenus=[dict(
            type='buttons',
            direction='right',
            x=0.0, y=1.16,
            xanchor='left', yanchor='top',
            bgcolor=COLORS['axes_bg'],
            bordercolor=COLORS['border'],
            font=dict(color=COLORS['text'], size=12),
            buttons=buttons,
            active=0,
        )],
        annotations=view_annotations[0],
    )

    # Annual view defaults
    fig.update_xaxes(side='top', tickangle=0, row=1, col=1)
    fig.update_yaxes(autorange='reversed', row=1, col=1)
    fig.update_yaxes(autorange='reversed', showticklabels=False, row=1, col=2)

    # TOTAL separator for initial view
    fig.add_shape(**total_separator)

    # Bar chart config
    fig.update_xaxes(title_text='P&L Total', title_font=dict(size=10), row=1, col=2)
    fig.update_xaxes(zeroline=True, zerolinecolor=COLORS['text_secondary'],
                     zerolinewidth=0.5, row=1, col=2)

    # Automargin for all axes
    for c in [1, 2]:
        fig.update_yaxes(automargin=True, row=1, col=c)
        fig.update_xaxes(automargin=True, row=1, col=c)

    if save_path:
        fig.write_html(save_path)

    return fig
