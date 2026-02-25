"""
Tema visual compartido para todos los dashboards.
"""

import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap

COLORS = {
    'profit': '#006D77',
    'loss': '#E29578',
    'text': '#333333',
    'background': '#f5f5f5',
    'highlight': '#2962FF',
}

PROFIT_LOSS_CMAP = LinearSegmentedColormap.from_list(
    'profit_loss', [COLORS['loss'], '#f5f5f5', COLORS['profit']]
)


def apply_dashboard_style() -> dict:
    """Aplica estilo global de matplotlib y retorna paleta de colores."""
    plt.style.use('seaborn-v0_8-whitegrid')
    plt.rcParams.update({
        'figure.facecolor': COLORS['background'],
        'axes.facecolor': '#ffffff',
        'axes.edgecolor': '#cccccc',
        'text.color': COLORS['text'],
        'axes.labelcolor': COLORS['text'],
        'xtick.color': COLORS['text'],
        'ytick.color': COLORS['text'],
        'font.size': 10,
    })
    return COLORS
