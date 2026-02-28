"""
Boxplots de metricas principales con Plotly.

6 boxplots horizontales separando winners vs losers.
"""

import plotly.graph_objects as go
from plotly.subplots import make_subplots
from visualization.plotly_theme import COLORS


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


def visualize_metrics_boxplot(strategy, df_trade_metrics, save_path=None):
    """
    Boxplots horizontales de metricas: winners vs losers.

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
                        vertical_spacing=0.12, horizontal_spacing=0.10)

    winners = df_trade_metrics[df_trade_metrics['net_profit_loss'] > 0]
    losers = df_trade_metrics[df_trade_metrics['net_profit_loss'] <= 0]

    for idx, metric in enumerate(available):
        row = idx // n_cols + 1
        col = idx % n_cols + 1

        if len(winners) > 0:
            fig.add_trace(go.Box(
                x=winners[metric],
                name='Ganador',
                orientation='h',
                marker=dict(color=COLORS['profit'], outliercolor=COLORS['profit']),
                line=dict(color=COLORS['profit']),
                boxmean=True,
                showlegend=(idx == 0),
                legendgroup='winners',
                hovertemplate='%{x:.2f}<extra>Ganador</extra>',
            ), row=row, col=col)

        if len(losers) > 0:
            fig.add_trace(go.Box(
                x=losers[metric],
                name='Perdedor',
                orientation='h',
                marker=dict(color=COLORS['loss'], outliercolor=COLORS['loss']),
                line=dict(color=COLORS['loss']),
                boxmean=True,
                showlegend=(idx == 0),
                legendgroup='losers',
                hovertemplate='%{x:.2f}<extra>Perdedor</extra>',
            ), row=row, col=col)

    fig.update_layout(
        height=250 * n_rows,
        margin=dict(t=80),
        showlegend=True,
        legend=dict(orientation='h', yanchor='bottom', y=1.06, xanchor='center', x=0.5),
    )

    if save_path:
        fig.write_html(save_path)

    return fig
