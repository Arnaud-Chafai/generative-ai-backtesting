"""
Scatter plots de metricas con Plotly — version consolidada.

Un solo go.Figure con dropdown para elegir la metrica X.
Reemplaza los 5 tabs separados del diseno original.

Tambien exporta las 5 funciones individuales para compatibilidad
con el dashboard_manager de matplotlib.
"""

import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from visualization.plotly_theme import COLORS, SCATTER_COLORSCALE


_ALL_METRICS = ['MAE', 'MFE', 'risk_reward_ratio', 'profit_efficiency', 'trade_volatility']

_FRIENDLY = {
    'MAE': 'MAE', 'MFE': 'MFE',
    'risk_reward_ratio': 'Risk-Reward',
    'profit_efficiency': 'Profit Efficiency',
    'trade_volatility': 'Trade Volatility',
}

# For each x-metric, which 4 y-metrics to show (the other 4)
_Y_MAP = {m: [y for y in _ALL_METRICS if y != m] for m in _ALL_METRICS}

# Traces per metric group: 4 subplots × 2 traces (scatter + regression) = 8
_TRACES_PER_GROUP = 8


def _check_metrics(df, required):
    missing = [m for m in required if m not in df.columns]
    if missing:
        print(f'Faltan metricas: {", ".join(missing)}')
        return False
    return True


def _add_regression(fig, xv, yv, row, col):
    """Add regression line trace. Always adds a trace (empty if fails) to keep indexing stable."""
    try:
        mask = ~(np.isnan(xv) | np.isnan(yv))
        xv_c, yv_c = xv[mask], yv[mask]
        if len(xv_c) > 2:
            coeffs = np.polyfit(xv_c, yv_c, 1)
            x_line = np.linspace(xv_c.min(), xv_c.max(), 50)
            y_line = np.polyval(coeffs, x_line)
            fig.add_trace(go.Scatter(
                x=x_line, y=y_line, mode='lines',
                line=dict(color=COLORS['text'], width=2, dash='dot'),
                opacity=0.7, showlegend=False, hoverinfo='skip', visible=False,
            ), row=row, col=col)
            return
    except (np.linalg.LinAlgError, ValueError):
        pass
    # Fallback: empty trace to keep indexing consistent
    fig.add_trace(go.Scatter(
        x=[], y=[], mode='lines', showlegend=False, hoverinfo='skip', visible=False,
    ), row=row, col=col)


def visualize_scatter_consolidated(df_trade_metrics, save_path=None):
    """
    Scatter dashboard consolidado con dropdown para seleccionar metrica X.

    Args:
        df_trade_metrics: DataFrame con metricas de trades
        save_path: Ruta para guardar HTML (opcional)

    Returns:
        go.Figure
    """
    if not _check_metrics(df_trade_metrics, _ALL_METRICS):
        return None

    df = df_trade_metrics
    pnl = df['net_profit_loss']

    fig = make_subplots(
        rows=2, cols=2,
        vertical_spacing=0.14, horizontal_spacing=0.10,
    )

    # ── Add all trace groups (5 x-metrics × 8 traces each) ──────────────
    for x_col in _ALL_METRICS:
        y_cols = _Y_MAP[x_col]
        for idx, y_col in enumerate(y_cols):
            row = idx // 2 + 1
            col = idx % 2 + 1
            x_name = _FRIENDLY[x_col]
            y_name = _FRIENDLY[y_col]

            # Scatter trace
            fig.add_trace(go.Scatter(
                x=df[x_col], y=df[y_col],
                mode='markers',
                marker=dict(
                    size=7, opacity=0.75,
                    color=pnl, colorscale=SCATTER_COLORSCALE,
                    showscale=False,
                    line=dict(color=COLORS['border'], width=0.5),
                ),
                showlegend=False, visible=False,
                hovertemplate=(
                    f'{x_name}: %{{x:.4f}}<br>'
                    f'{y_name}: %{{y:.4f}}<br>'
                    f'P&L: %{{marker.color:.2f}}<extra></extra>'
                ),
            ), row=row, col=col)

            # Regression trace (always added)
            _add_regression(
                fig,
                df[x_col].values.astype(float),
                df[y_col].values.astype(float),
                row, col,
            )

    # ── Build dropdown buttons ───────────────────────────────────────────
    n_groups = len(_ALL_METRICS)
    total_traces = n_groups * _TRACES_PER_GROUP

    buttons = []
    for gi, x_col in enumerate(_ALL_METRICS):
        # Visibility: only this group's 8 traces are True
        vis = [False] * total_traces
        start = gi * _TRACES_PER_GROUP
        for j in range(start, start + _TRACES_PER_GROUP):
            vis[j] = True

        y_cols = _Y_MAP[x_col]
        x_name = _FRIENDLY[x_col]

        # Build axis title updates
        layout_updates = {
            'title.text': f'Relacion de {x_name} con Otras Metricas',
        }
        # Subplot axis naming: xaxis, xaxis2, xaxis3, xaxis4 / yaxis, yaxis2...
        axis_map = {0: '', 1: '2', 2: '3', 3: '4'}
        for idx, y_col in enumerate(y_cols):
            suffix = axis_map[idx]
            layout_updates[f'xaxis{suffix}.title.text'] = x_name
            layout_updates[f'yaxis{suffix}.title.text'] = _FRIENDLY[y_col]

        buttons.append(dict(
            label=x_name,
            method='update',
            args=[{'visible': vis}, layout_updates],
        ))

    # ── Activate first group by default ──────────────────────────────────
    for j in range(_TRACES_PER_GROUP):
        fig.data[j].visible = True
    # Enable colorbar on first scatter of default group
    fig.data[0].marker.showscale = True
    fig.data[0].marker.colorbar = dict(title='P&L', len=0.4, y=0.8)

    first_x = _ALL_METRICS[0]
    first_x_name = _FRIENDLY[first_x]
    first_ys = _Y_MAP[first_x]
    axis_map = {0: '', 1: '2', 2: '3', 3: '4'}
    for idx, y_col in enumerate(first_ys):
        suffix = axis_map[idx]
        fig.update_layout(**{
            f'xaxis{suffix}': dict(title_text=first_x_name),
            f'yaxis{suffix}': dict(title_text=_FRIENDLY[y_col]),
        })

    fig.update_layout(
        title=dict(text=f'Relacion de {first_x_name} con Otras Metricas', x=0.5),
        height=700,
        updatemenus=[dict(
            type='dropdown',
            direction='down',
            x=0.02, y=1.15,
            xanchor='left', yanchor='top',
            bgcolor=COLORS['axes_bg'],
            bordercolor=COLORS['border'],
            font=dict(color=COLORS['text'], size=12),
            buttons=buttons,
            active=0,
        )],
        annotations=[dict(
            text='Metrica X:', x=0.0, y=1.18, xref='paper', yref='paper',
            showarrow=False, font=dict(size=12, color=COLORS['text_secondary']),
        )],
    )

    if save_path:
        fig.write_html(save_path)

    return fig


# ── Individual wrappers (kept for backward compatibility / matplotlib manager) ──

def _create_scatter_dashboard(df, x_col, y_cols, title):
    """Create a 2x2 scatter dashboard for a single x-metric."""
    x_name = _FRIENDLY.get(x_col, x_col)
    subtitles = [f'{x_name} vs {_FRIENDLY.get(y, y)}' for y in y_cols]
    fig = make_subplots(rows=2, cols=2, subplot_titles=subtitles,
                        vertical_spacing=0.12, horizontal_spacing=0.10)
    pnl = df['net_profit_loss']

    for idx, y_col in enumerate(y_cols):
        row = idx // 2 + 1
        col = idx % 2 + 1
        fig.add_trace(go.Scatter(
            x=df[x_col], y=df[y_col], mode='markers',
            marker=dict(size=7, opacity=0.75, color=pnl, colorscale=SCATTER_COLORSCALE,
                        showscale=(idx == 0),
                        colorbar=dict(title='P&L', len=0.4, y=0.8) if idx == 0 else None,
                        line=dict(color=COLORS['border'], width=0.5)),
            showlegend=False,
            hovertemplate=f'{x_name}: %{{x:.4f}}<br>{_FRIENDLY.get(y_col, y_col)}: %{{y:.4f}}<br>P&L: %{{marker.color:.2f}}<extra></extra>',
        ), row=row, col=col)
        try:
            mask = df[[x_col, y_col]].dropna().index
            xv = df.loc[mask, x_col].values.astype(float)
            yv = df.loc[mask, y_col].values.astype(float)
            if len(xv) > 2:
                coeffs = np.polyfit(xv, yv, 1)
                x_line = np.linspace(xv.min(), xv.max(), 50)
                fig.add_trace(go.Scatter(x=x_line, y=np.polyval(coeffs, x_line), mode='lines',
                    line=dict(color=COLORS['text'], width=2, dash='dot'),
                    opacity=0.7, showlegend=False, hoverinfo='skip'), row=row, col=col)
        except (np.linalg.LinAlgError, ValueError):
            pass
        fig.update_xaxes(title_text=x_name, row=row, col=col)
        fig.update_yaxes(title_text=_FRIENDLY.get(y_col, y_col), row=row, col=col)
    fig.update_layout(title=dict(text=title, x=0.5), height=700)
    return fig


def visualize_metrics_vs_mae(df_trade_metrics, save_path=None):
    if not _check_metrics(df_trade_metrics, _ALL_METRICS): return None
    fig = _create_scatter_dashboard(df_trade_metrics, 'MAE', _Y_MAP['MAE'], 'Relacion de MAE con Otras Metricas')
    if save_path: fig.write_html(save_path)
    return fig

def visualize_metrics_vs_mfe(df_trade_metrics, save_path=None):
    if not _check_metrics(df_trade_metrics, _ALL_METRICS): return None
    fig = _create_scatter_dashboard(df_trade_metrics, 'MFE', _Y_MAP['MFE'], 'Relacion de MFE con Otras Metricas')
    if save_path: fig.write_html(save_path)
    return fig

def visualize_metrics_vs_risk_reward(df_trade_metrics, save_path=None):
    if not _check_metrics(df_trade_metrics, _ALL_METRICS): return None
    fig = _create_scatter_dashboard(df_trade_metrics, 'risk_reward_ratio', _Y_MAP['risk_reward_ratio'], 'Relacion de Risk-Reward con Otras Metricas')
    if save_path: fig.write_html(save_path)
    return fig

def visualize_metrics_vs_volatility(df_trade_metrics, save_path=None):
    if not _check_metrics(df_trade_metrics, _ALL_METRICS): return None
    fig = _create_scatter_dashboard(df_trade_metrics, 'trade_volatility', _Y_MAP['trade_volatility'], 'Relacion de Volatility con Otras Metricas')
    if save_path: fig.write_html(save_path)
    return fig

def visualize_metrics_vs_profit_efficiency(df_trade_metrics, save_path=None):
    if not _check_metrics(df_trade_metrics, _ALL_METRICS): return None
    fig = _create_scatter_dashboard(df_trade_metrics, 'profit_efficiency', _Y_MAP['profit_efficiency'], 'Relacion de Profit Efficiency con Otras Metricas')
    if save_path: fig.write_html(save_path)
    return fig
