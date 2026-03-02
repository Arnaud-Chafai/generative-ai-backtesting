"""
Trade Metrics dashboard — Scatter unificado con Plotly.

Scatter principal (metrica vs P&L) + 4 cross-scatters (metrica vs las otras 4),
con 5 botones para cambiar la metrica seleccionada. Regresion y correlacion en
cada subplot. Reemplaza los tabs Trade Metrics y Scatter Analysis anteriores.
"""

import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from visualization.plotly_theme import COLORS, SCATTER_COLORSCALE


# ── Metric definitions ──────────────────────────────────────────────────────

_METRICS = ['MAE', 'MFE', 'profit_efficiency', 'risk_reward_ratio',
            'trade_volatility']

_FRIENDLY = {
    'MAE': 'MAE',
    'MFE': 'MFE',
    'profit_efficiency': 'Efficiency',
    'risk_reward_ratio': 'R/R',
    'trade_volatility': 'Volatility',
}

_BUTTON_LABELS = {
    'MAE': 'MAE',
    'MFE': 'MFE',
    'profit_efficiency': 'Effic.',
    'risk_reward_ratio': 'R/R',
    'trade_volatility': 'Vol',
}

# For each selected metric, the 4 others for the cross-scatter grid
_CROSS_MAP = {m: [y for y in _METRICS if y != m] for m in _METRICS}


# ── Helpers ──────────────────────────────────────────────────────────────────

def _compute_regression(x, y):
    """Compute regression line endpoints. Returns (x0, y0, x1, y1) or None."""
    try:
        mask = ~(np.isnan(x) | np.isnan(y))
        xc, yc = x[mask], y[mask]
        if len(xc) < 3:
            return None
        coeffs = np.polyfit(xc, yc, 1)
        x0, x1 = float(xc.min()), float(xc.max())
        y0, y1 = float(np.polyval(coeffs, x0)), float(np.polyval(coeffs, x1))
        return (x0, y0, x1, y1)
    except (np.linalg.LinAlgError, ValueError):
        return None


def _compute_correlation(x, y):
    """Pearson correlation, handling NaN."""
    try:
        mask = ~(np.isnan(x) | np.isnan(y))
        xc, yc = x[mask], y[mask]
        if len(xc) < 3:
            return 0.0
        return float(np.corrcoef(xc, yc)[0, 1])
    except (ValueError, IndexError):
        return 0.0


def _make_regression_shape(x, y, xref, yref):
    """Build a regression shape dict for the given data and axis refs."""
    reg = _compute_regression(x, y)
    if reg is None:
        return None
    x0, y0, x1, y1 = reg
    return dict(
        type='line', x0=x0, y0=y0, x1=x1, y1=y1,
        xref=xref, yref=yref,
        line=dict(color=COLORS['text_secondary'], width=2, dash='dot'),
        opacity=0.7,
    )


def _build_stats_text(winners, losers, n_trades, r_corr):
    """Build summary stats string for the main annotation."""
    n_w = len(winners)
    n_l = len(losers)
    wr = (n_w / n_trades * 100) if n_trades > 0 else 0
    avg_w = winners['net_profit_loss'].mean() if n_w > 0 else 0
    avg_l = losers['net_profit_loss'].mean() if n_l > 0 else 0

    return (
        f"<b>{n_trades}</b> trades  |  "
        f"<span style='color:{COLORS['profit']}'>W: {n_w} (avg {avg_w:+.2f})</span>  |  "
        f"<span style='color:{COLORS['loss']}'>L: {n_l} (avg {avg_l:+.2f})</span>  |  "
        f"WR: {wr:.0f}%  |  r = {r_corr:.2f}"
    )


# ── Main function ────────────────────────────────────────────────────────────

def visualize_trade_metrics(strategy, df_trade_metrics, save_path=None):
    """
    Trade Metrics unificado: scatter principal + 4 cross-scatters.

    Layout:
        Row 1 (colspan 2): metrica seleccionada vs P&L (scatter grande)
        Row 2: cross-scatter A | cross-scatter B
        Row 3: cross-scatter C | cross-scatter D

    5 botones para cambiar la metrica seleccionada. Al elegir una, las otras
    4 aparecen en el grid inferior como cross-scatters.

    Args:
        strategy: Objeto de estrategia
        df_trade_metrics: DataFrame con metricas de trades
        save_path: Ruta para guardar HTML (opcional)

    Returns:
        go.Figure
    """
    df = df_trade_metrics
    available = [m for m in _METRICS if m in df.columns]

    if not available:
        fig = go.Figure()
        fig.add_annotation(text='No hay metricas disponibles', x=0.5, y=0.5,
                           xref='paper', yref='paper', showarrow=False,
                           font=dict(size=16, color=COLORS['text']))
        return fig

    winners = df[df['net_profit_loss'] > 0]
    losers = df[df['net_profit_loss'] <= 0]
    pnl = df['net_profit_loss'].values.astype(float)
    n_trades = len(df)

    # ── Subplot grid ─────────────────────────────────────────────────────
    fig = make_subplots(
        rows=3, cols=2,
        specs=[
            [{'colspan': 2}, None],
            [{}, {}],
            [{}, {}],
        ],
        row_heights=[0.45, 0.275, 0.275],
        vertical_spacing=0.08,
        horizontal_spacing=0.08,
    )

    # ── Discover axis refs from make_subplots ─────────────────────────────
    # Row 1 (main scatter): subplot (1,1)
    main_xaxis = fig.get_subplot(1, 1).xaxis.plotly_name   # 'xaxis'
    main_yaxis = fig.get_subplot(1, 1).yaxis.plotly_name   # 'yaxis'
    main_xref = main_xaxis.replace('xaxis', 'x')
    main_yref = main_yaxis.replace('yaxis', 'y')

    # Cross-scatter subplots: (2,1), (2,2), (3,1), (3,2)
    cross_positions = [(2, 1), (2, 2), (3, 1), (3, 2)]
    cross_axes = []
    for r, c in cross_positions:
        sp = fig.get_subplot(r, c)
        xa = sp.xaxis.plotly_name
        ya = sp.yaxis.plotly_name
        cross_axes.append({
            'xaxis': xa, 'yaxis': ya,
            'xref': xa.replace('xaxis', 'x'),
            'yref': ya.replace('yaxis', 'y'),
        })

    # ── First metric data ─────────────────────────────────────────────────
    first = available[0]
    first_vals = df[first].values.astype(float)
    first_cross = _CROSS_MAP[first]

    # ── Trace 0: Main scatter (metric vs P&L) ────────────────────────────
    fig.add_trace(go.Scatter(
        x=first_vals, y=pnl,
        mode='markers',
        marker=dict(
            size=7, opacity=0.7,
            color=pnl, colorscale=SCATTER_COLORSCALE,
            showscale=True,
            colorbar=dict(title='P&L', len=0.35, y=0.80),
            line=dict(color=COLORS['border'], width=0.3),
        ),
        showlegend=False,
        hovertemplate=(
            f'{_FRIENDLY[first]}: %{{x:.4f}}<br>'
            'P&L: %{y:.2f}<extra></extra>'
        ),
    ), row=1, col=1)

    # ── Traces 1-4: Cross-scatters ───────────────────────────────────────
    for i, cross_m in enumerate(first_cross):
        r, c = cross_positions[i]
        cross_vals = df[cross_m].values.astype(float)
        fig.add_trace(go.Scatter(
            x=first_vals, y=cross_vals,
            mode='markers',
            marker=dict(
                size=5, opacity=0.6,
                color=pnl, colorscale=SCATTER_COLORSCALE,
                showscale=False,
                line=dict(color=COLORS['border'], width=0.3),
            ),
            showlegend=False,
            hovertemplate=(
                f'{_FRIENDLY[first]}: %{{x:.4f}}<br>'
                f'{_FRIENDLY[cross_m]}: %{{y:.4f}}<br>'
                f'P&L: %{{marker.color:.2f}}<extra></extra>'
            ),
        ), row=r, col=c)

    # ── Initial shapes (regression lines) ─────────────────────────────────
    shapes = []
    # Main regression
    main_shape = _make_regression_shape(first_vals, pnl, main_xref, main_yref)
    if main_shape:
        shapes.append(main_shape)
    # Cross regressions
    for i, cross_m in enumerate(first_cross):
        cross_vals = df[cross_m].values.astype(float)
        s = _make_regression_shape(
            first_vals, cross_vals,
            cross_axes[i]['xref'], cross_axes[i]['yref'],
        )
        if s:
            shapes.append(s)

    # ── Initial annotations ───────────────────────────────────────────────
    first_corr = _compute_correlation(first_vals, pnl)
    stats_text = _build_stats_text(winners, losers, n_trades, first_corr)

    annotations = [
        dict(text=stats_text, x=0.5, y=1.0,
             xref='paper', yref='paper', showarrow=False,
             font=dict(size=12, color=COLORS['text'])),
    ]
    # Cross-scatter correlation labels
    for i, cross_m in enumerate(first_cross):
        cross_vals = df[cross_m].values.astype(float)
        r_val = _compute_correlation(first_vals, cross_vals)
        annotations.append(dict(
            text=f"r = {r_val:.2f}",
            xref=cross_axes[i]['xref'], yref=cross_axes[i]['yref'],
            x=0.98, y=0.98,
            xanchor='right', yanchor='top',
            showarrow=False, xshift=-5, yshift=-5,
            font=dict(size=11, color=COLORS['text_secondary']),
            bgcolor=COLORS['axes_bg'],
            borderpad=3,
        ))

    # ── Axis labels (initial) ─────────────────────────────────────────────
    fig.update_layout(**{
        main_xaxis: dict(title_text=_FRIENDLY[first]),
        main_yaxis: dict(title_text='P&L'),
    })
    for i, cross_m in enumerate(first_cross):
        fig.update_layout(**{
            cross_axes[i]['xaxis']: dict(title_text=_FRIENDLY[first]),
            cross_axes[i]['yaxis']: dict(title_text=_FRIENDLY[cross_m]),
        })

    # ── Precompute all metric data ────────────────────────────────────────
    metric_data = {}
    for m in available:
        metric_data[m] = df[m].values.astype(float)

    # ── Buttons: data replacement ─────────────────────────────────────────
    buttons = []
    for mi, metric in enumerate(available):
        m_vals = metric_data[metric]
        cross_metrics = _CROSS_MAP[metric]
        friendly = _FRIENDLY[metric]

        # ── Trace data: [main, cross0, cross1, cross2, cross3]
        trace_x = [m_vals.tolist()] * 5
        trace_y = [pnl.tolist()]
        trace_hover = [
            f'{friendly}: %{{x:.4f}}<br>P&L: %{{y:.2f}}<extra></extra>',
        ]

        for ci, cm in enumerate(cross_metrics):
            cv = metric_data[cm]
            trace_y.append(cv.tolist())
            trace_hover.append(
                f'{friendly}: %{{x:.4f}}<br>'
                f'{_FRIENDLY[cm]}: %{{y:.4f}}<br>'
                f'P&L: %{{marker.color:.2f}}<extra></extra>'
            )

        # ── Shapes: regression lines
        btn_shapes = []
        s = _make_regression_shape(m_vals, pnl, main_xref, main_yref)
        if s:
            btn_shapes.append(s)
        for ci, cm in enumerate(cross_metrics):
            cv = metric_data[cm]
            s = _make_regression_shape(
                m_vals, cv,
                cross_axes[ci]['xref'], cross_axes[ci]['yref'],
            )
            if s:
                btn_shapes.append(s)

        # ── Annotations: stats + 4 correlations
        main_corr = _compute_correlation(m_vals, pnl)
        btn_stats = _build_stats_text(winners, losers, n_trades, main_corr)

        btn_annots = [
            dict(text=btn_stats, x=0.5, y=1.0,
                 xref='paper', yref='paper', showarrow=False,
                 font=dict(size=12, color=COLORS['text'])),
        ]
        for ci, cm in enumerate(cross_metrics):
            cv = metric_data[cm]
            r_val = _compute_correlation(m_vals, cv)
            btn_annots.append(dict(
                text=f"r = {r_val:.2f}",
                xref=cross_axes[ci]['xref'], yref=cross_axes[ci]['yref'],
                x=0.98, y=0.98,
                xanchor='right', yanchor='top',
                showarrow=False, xshift=-5, yshift=-5,
                font=dict(size=11, color=COLORS['text_secondary']),
                bgcolor=COLORS['axes_bg'],
                borderpad=3,
            ))

        # ── Axis title updates
        layout_updates = {
            'shapes': btn_shapes,
            'annotations': btn_annots,
            f'{main_xaxis}.title.text': friendly,
        }
        for ci, cm in enumerate(cross_metrics):
            layout_updates[f'{cross_axes[ci]["xaxis"]}.title.text'] = friendly
            layout_updates[f'{cross_axes[ci]["yaxis"]}.title.text'] = _FRIENDLY[cm]

        btn_label = _BUTTON_LABELS.get(metric, friendly)
        if mi == 0:
            btn_label = f'\u25cf {btn_label}'

        buttons.append(dict(
            label=f'  {btn_label}  ',
            method='update',
            args=[
                {
                    'x': trace_x,
                    'y': trace_y,
                    'hovertemplate': trace_hover,
                },
                layout_updates,
            ],
        ))

    # ── Layout ────────────────────────────────────────────────────────────
    fig.update_layout(
        height=900,
        shapes=shapes,
        annotations=annotations,
        showlegend=False,
        updatemenus=[dict(
            type='buttons',
            direction='right',
            x=0.5, y=1.06,
            xanchor='center', yanchor='bottom',
            bgcolor=COLORS['axes_bg'],
            bordercolor=COLORS['border'],
            font=dict(color=COLORS['text'], size=12),
            buttons=buttons,
            active=0,
        )],
        margin=dict(t=80, b=50, l=60, r=30),
    )

    if save_path:
        fig.write_html(save_path)

    return fig
