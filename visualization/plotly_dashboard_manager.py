"""
Coordinador de dashboards interactivos con Plotly.

Genera cada figura Plotly individualmente y las combina en un único archivo HTML
con navegación por tabs, estilo TradingView dark.
"""

import os
import webbrowser
import traceback

from visualization.plotly_dashboards.performance_dashboard import visualize_performance
from visualization.plotly_dashboards.temporal_analysis import visualize_temporal_analysis
from visualization.plotly_dashboards.metrics_distribution import visualize_metrics_distribution
from visualization.plotly_dashboards.metrics_boxplot import visualize_metrics_boxplot
from visualization.plotly_dashboards.scatter_metrics import visualize_scatter_consolidated


# ── Module registry ──────────────────────────────────────────────────────────

MODULE_ORDER = [
    'performance', 'temporal_analysis',
    'metrics_distribution', 'metrics_boxplot', 'scatter',
]

MODULE_FUNCTIONS = {
    'performance': visualize_performance,
    'temporal_analysis': visualize_temporal_analysis,
    'metrics_distribution': visualize_metrics_distribution,
    'metrics_boxplot': visualize_metrics_boxplot,
    'scatter': visualize_scatter_consolidated,
}

NON_STRATEGY_MODULES = {
    'scatter',
}

TAB_LABELS = {
    'performance': 'Performance',
    'temporal_analysis': 'Temporal Analysis',
    'metrics_distribution': 'Distributions',
    'metrics_boxplot': 'Boxplots',
    'scatter': 'Scatter Analysis',
}


# ── HTML template pieces ────────────────────────────────────────────────────

_HTML_HEAD = """\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>{title}</title>
<script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{
    background: #131722;
    color: #d1d4dc;
    font-family: 'Trebuchet MS', 'Segoe UI', sans-serif;
  }}
  .header {{
    background: #1e222d;
    padding: 14px 24px;
    border-bottom: 2px solid #2962FF;
    display: flex;
    align-items: center;
    gap: 16px;
  }}
  .header h1 {{
    font-size: 18px;
    font-weight: 600;
    color: #d1d4dc;
  }}
  .header .badge {{
    background: #2962FF;
    color: #fff;
    font-size: 11px;
    padding: 2px 8px;
    border-radius: 3px;
    font-weight: 600;
  }}
  .tab-bar {{
    background: #1e222d;
    display: flex;
    flex-wrap: wrap;
    gap: 2px;
    padding: 4px 16px;
    border-bottom: 1px solid #363a45;
  }}
  .tab-btn {{
    background: transparent;
    color: #787b86;
    border: none;
    padding: 8px 16px;
    font-size: 13px;
    cursor: pointer;
    border-bottom: 2px solid transparent;
    transition: all 0.15s;
    font-family: inherit;
  }}
  .tab-btn:hover {{ color: #d1d4dc; }}
  .tab-btn.active {{
    color: #d1d4dc;
    border-bottom-color: #2962FF;
    font-weight: 600;
  }}
  .panel {{ display: none; padding: 16px 24px; max-width: 1400px; margin: 0 auto; }}
  .panel.active {{ display: block; }}
</style>
</head>
<body>
<div class="header">
  <h1>{title}</h1>
  <span class="badge">Interactive</span>
</div>
<div class="tab-bar" id="tabBar">
{tab_buttons}
</div>
<div id="panels">
{panels}
</div>
<script>
function switchTab(id) {{
  document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
  document.querySelectorAll('.panel').forEach(p => p.classList.remove('active'));
  document.getElementById('tab-' + id).classList.add('active');
  var panel = document.getElementById('panel-' + id);
  panel.classList.add('active');
  // Resize plotly charts inside newly-visible panel
  var plots = panel.querySelectorAll('.js-plotly-plot');
  plots.forEach(function(p) {{ Plotly.Plots.resize(p); }});
}}
// Activate first tab
(function() {{
  var first = document.querySelector('.tab-btn');
  if (first) first.click();
}})();
</script>
</body>
</html>
"""


def create_interactive_dashboard(strategy, df_trade_metrics, modules=None,
                                  output_folder='dashboards', show=True):
    """
    Generate all Plotly dashboards and combine into a single HTML with tabs.

    Args:
        strategy: Strategy object
        df_trade_metrics: DataFrame with trade metrics
        modules: List of module names to include (None = all)
        output_folder: Folder to save the HTML
        show: If True, open the HTML in the default browser

    Returns:
        str: Path to the generated HTML file
    """
    os.makedirs(output_folder, exist_ok=True)

    if modules is None:
        modules = MODULE_ORDER

    # Keep only valid modules, in canonical order
    valid = [m for m in MODULE_ORDER if m in modules and m in MODULE_FUNCTIONS]
    invalid = [m for m in modules if m not in MODULE_FUNCTIONS]
    if invalid:
        print(f'Modulos invalidos ignorados: {invalid}')

    # ── Generate individual Plotly figures ────────────────────────────────
    figures = {}
    for mod in valid:
        try:
            print(f'Generando {mod}...')
            func = MODULE_FUNCTIONS[mod]
            if mod in NON_STRATEGY_MODULES:
                fig = func(df_trade_metrics)
            else:
                fig = func(strategy, df_trade_metrics)
            if fig is not None:
                figures[mod] = fig
        except Exception as e:
            print(f'Error en {mod}: {e}')
            traceback.print_exc()

    if not figures:
        print('No se genero ningun dashboard.')
        return None

    # ── Build combined HTML ──────────────────────────────────────────────
    tab_buttons = []
    panels = []

    for mod in valid:
        if mod not in figures:
            continue
        label = TAB_LABELS.get(mod, mod)
        tab_buttons.append(
            f'  <button class="tab-btn" id="tab-{mod}" onclick="switchTab(\'{mod}\')">{label}</button>'
        )

        # Convert figure to div HTML (without full HTML wrapper)
        fig = figures[mod]
        div_html = fig.to_html(
            full_html=False,
            include_plotlyjs=False,
            div_id=f'plot-{mod}',
        )
        panels.append(f'<div class="panel" id="panel-{mod}">{div_html}</div>')

    strategy_name = getattr(strategy, 'strategy_name', 'Backtest')
    symbol = getattr(strategy, 'symbol', '')
    title = f'{strategy_name} | {symbol} — Dashboard'

    html = _HTML_HEAD.format(
        title=title,
        tab_buttons='\n'.join(tab_buttons),
        panels='\n'.join(panels),
    )

    # ── Write file ───────────────────────────────────────────────────────
    filepath = os.path.join(output_folder, 'interactive_dashboard.html')
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(html)

    print(f'{len(figures)} dashboards generados en: {filepath}')

    if show:
        webbrowser.open(f'file://{os.path.abspath(filepath)}')

    return filepath
