"""
Distribucion de metricas principales con Plotly.

Histogramas de winners vs losers con KDE overlay para 6 metricas.
"""

import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from visualization.plotly_theme import COLORS


# Metrics to visualize (in order)
_METRICS = ['MAE', 'MFE', 'profit_efficiency', 'risk_reward_ratio',
            'trade_volatility', 'duration_bars']

_FRIENDLY_NAMES = {
    'MAE': 'MAE', 'MFE': 'MFE',
    'profit_efficiency': 'Eficiencia',
    'risk_reward_ratio': 'Risk-Reward',
    'trade_volatility': 'Volatilidad',
    'duration_bars': 'Duracion (barras)',
    'trade_duration_second': 'Duracion (segundos)',
}

# Metrics where losers histogram is hidden
_HIDE_LOSERS = {'profit_efficiency'}


def visualize_metrics_distribution(strategy, df_trade_metrics, save_path=None):
    """
    Dashboard de distribuciones de metricas con histogramas winners vs losers.

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

    available = [m for m in _METRICS if m in df_trade_metrics.columns]
    if 'duration_bars' not in available and 'trade_duration_second' in df_trade_metrics.columns:
        available.append('trade_duration_second')

    if not available:
        fig = go.Figure()
        fig.add_annotation(text='No hay metricas disponibles', x=0.5, y=0.5,
                           xref='paper', yref='paper', showarrow=False,
                           font=dict(size=16, color=COLORS['text']))
        return fig

    n = len(available)
    n_cols = 2
    n_rows = (n + 1) // 2

    titles = [_FRIENDLY_NAMES.get(m, m) for m in available]
    fig = make_subplots(rows=n_rows, cols=n_cols, subplot_titles=titles,
                        vertical_spacing=0.10, horizontal_spacing=0.08)

    winners = df_trade_metrics[df_trade_metrics['net_profit_loss'] > 0]
    losers = df_trade_metrics[df_trade_metrics['net_profit_loss'] <= 0]

    for idx, metric in enumerate(available):
        row = idx // n_cols + 1
        col = idx % n_cols + 1

        # Winners histogram
        if len(winners) > 0:
            w_vals = winners[metric].dropna()
            fig.add_trace(go.Histogram(
                x=w_vals, name='Ganadores',
                marker=dict(color=COLORS['profit'], line=dict(color=COLORS['border'], width=0.5)),
                opacity=0.7, showlegend=(idx == 0),
                legendgroup='winners',
                hovertemplate='%{x:.2f}<br>Count: %{y}<extra>Ganadores</extra>',
            ), row=row, col=col)

            # KDE
            try:
                from scipy.stats import gaussian_kde
                if len(w_vals) > 2:
                    kde_x = np.linspace(w_vals.min(), w_vals.max(), 150)
                    kde_y = gaussian_kde(w_vals)(kde_x)
                    bin_w = (w_vals.max() - w_vals.min()) / 20
                    fig.add_trace(go.Scatter(
                        x=kde_x, y=kde_y * len(w_vals) * bin_w,
                        mode='lines', line=dict(color=COLORS['profit'], width=2, dash='dot'),
                        showlegend=False, hoverinfo='skip',
                    ), row=row, col=col)
            except ImportError:
                pass

            # Mean line
            avg_w = w_vals.mean()
            fig.add_vline(x=avg_w, line_dash='dash', line_color=COLORS['profit'],
                          opacity=0.7, row=row, col=col)
            fig.add_annotation(
                x=avg_w, y=1, yref='y domain', xref='x',
                text=f'Prom: {avg_w:.2f}', showarrow=False,
                font=dict(size=9, color=COLORS['profit']),
                yshift=10, row=row, col=col,
            )

        # Losers histogram
        if metric not in _HIDE_LOSERS and len(losers) > 0:
            l_vals = losers[metric].dropna()
            fig.add_trace(go.Histogram(
                x=l_vals, name='Perdedores',
                marker=dict(color=COLORS['loss'], line=dict(color=COLORS['border'], width=0.5)),
                opacity=0.7, showlegend=(idx == 0),
                legendgroup='losers',
                hovertemplate='%{x:.2f}<br>Count: %{y}<extra>Perdedores</extra>',
            ), row=row, col=col)

            try:
                from scipy.stats import gaussian_kde
                if len(l_vals) > 2:
                    kde_x = np.linspace(l_vals.min(), l_vals.max(), 150)
                    kde_y = gaussian_kde(l_vals)(kde_x)
                    bin_w = (l_vals.max() - l_vals.min()) / 20
                    fig.add_trace(go.Scatter(
                        x=kde_x, y=kde_y * len(l_vals) * bin_w,
                        mode='lines', line=dict(color=COLORS['loss'], width=2, dash='dot'),
                        showlegend=False, hoverinfo='skip',
                    ), row=row, col=col)
            except ImportError:
                pass

            avg_l = l_vals.mean()
            fig.add_vline(x=avg_l, line_dash='dash', line_color=COLORS['loss'],
                          opacity=0.7, row=row, col=col)

        # Overlay mode for stacked histograms
        fig.update_layout(barmode='overlay')

    fig.update_layout(
        height=350 * n_rows,
        margin=dict(t=80),
        showlegend=True,
        legend=dict(orientation='h', yanchor='bottom', y=1.06, xanchor='center', x=0.5),
    )

    if save_path:
        fig.write_html(save_path)

    return fig
