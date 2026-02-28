"""
Plotly theme for TradingView-style dark dashboards.

Mirrors the color palette from theme.py but targets Plotly instead of matplotlib.
Registers a 'tradingview_dark' template for consistent styling across all dashboards.
"""

import plotly.graph_objects as go
import plotly.io as pio


# ── Color Palette (matches theme.py) ─────────────────────────────────────────

COLORS = {
    'profit': '#26a69a',
    'loss': '#ef5350',
    'text': '#d1d4dc',
    'text_secondary': '#787b86',
    'background': '#131722',
    'axes_bg': '#1e222d',
    'grid': '#2a2e39',
    'highlight': '#2962FF',
    'border': '#363a45',
    'profit_bright': '#4caf50',
    'loss_bright': '#f44336',
}


# ── Colorscales ──────────────────────────────────────────────────────────────

# Loss (red) → neutral (bg) → Profit (green) — for heatmaps
PROFIT_LOSS_COLORSCALE = [
    [0.0, '#ef5350'],
    [0.5, '#1e222d'],
    [1.0, '#26a69a'],
]

# Loss (red) → neutral (gray) → Profit (green) — for scatter color mapping
SCATTER_COLORSCALE = [
    [0.0, '#ef5350'],
    [0.5, '#787b86'],
    [1.0, '#26a69a'],
]


# ── Register Plotly Template ─────────────────────────────────────────────────

_tv_template = go.layout.Template()
_tv_template.layout = go.Layout(
    paper_bgcolor=COLORS['background'],
    plot_bgcolor=COLORS['axes_bg'],
    font=dict(
        family='Trebuchet MS, Segoe UI, DejaVu Sans, sans-serif',
        size=12,
        color=COLORS['text'],
    ),
    title=dict(font=dict(size=16, color=COLORS['text'])),
    xaxis=dict(
        gridcolor=COLORS['grid'],
        gridwidth=1,
        griddash='dot',
        zerolinecolor=COLORS['border'],
        linecolor=COLORS['border'],
        tickfont=dict(color=COLORS['text_secondary']),
    ),
    yaxis=dict(
        gridcolor=COLORS['grid'],
        gridwidth=1,
        griddash='dot',
        zerolinecolor=COLORS['border'],
        linecolor=COLORS['border'],
        tickfont=dict(color=COLORS['text_secondary']),
    ),
    legend=dict(
        bgcolor='rgba(0,0,0,0)',
        font=dict(color=COLORS['text_secondary'], size=11),
        bordercolor=COLORS['border'],
        borderwidth=0,
    ),
    colorway=[
        COLORS['highlight'], COLORS['profit'], COLORS['loss'],
        '#e040fb', '#ff9800', '#00bcd4', '#ffeb3b', '#8bc34a',
    ],
    hoverlabel=dict(
        bgcolor=COLORS['axes_bg'],
        font=dict(color=COLORS['text'], size=12),
        bordercolor=COLORS['border'],
    ),
    margin=dict(l=60, r=30, t=60, b=50),
)

pio.templates['tradingview_dark'] = _tv_template
pio.templates.default = 'tradingview_dark'


# ── Helper ───────────────────────────────────────────────────────────────────

def create_base_figure(**kwargs):
    """Create a Figure pre-configured with the TradingView dark template."""
    return go.Figure(layout=go.Layout(template='tradingview_dark', **kwargs))
