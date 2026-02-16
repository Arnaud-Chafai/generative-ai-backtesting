# Modulo: visualization

Visualizacion de resultados de backtest: charts de velas con trades y dashboards de analisis.

## Archivos

### chart_plotter.py — Charts de velas con entrada/salida

Dos clases para visualizar trades sobre el grafico de precios:

**`BacktestVisualizerStatic`** — Graficos estaticos con mplfinance.
```python
viz = BacktestVisualizerStatic(strategy, trade_metrics_df)
viz.plot_trades(interval_hours=5, number_visualisation=10)
```
- Genera multiples graficos de velas segmentados por intervalo de horas
- Marcadores: triangulo verde (entrada), triangulo rojo (salida)
- Solo genera graficos para intervalos que contienen trades

**`BacktestVisualizerInteractive`** — Chart interactivo estilo TradingView con lightweight-charts.
```python
viz = BacktestVisualizerInteractive(strategy, trade_metrics_df)
viz.show(last_days=30, indicators=['EMA_20'])
```
- Abre ventana standalone con zoom, pan, crosshair
- Marcadores de entrada/salida con tooltips
- Lineas entry→exit (limitadas a MAX_TRADE_LINES=200)
- Requiere: `lightweight-charts`, `nest_asyncio` (para Jupyter)
- Soporta filtrado por fecha: `start/end` o `last_days`

### dashboard_manager.py — Coordinador de dashboards

Funcion principal: `create_dashboard(strategy, df_trade_metrics, modules=None)`

```python
from visualization.dashboard_manager import create_dashboard

figures = create_dashboard(strategy, df_trade_metrics, modules=['performance', 'mae_scatter'])
```

- Coordina los 10 dashboards de `dashboards/`
- Maneja la logica de que funciones reciben `strategy` y cuales no (`NON_STRATEGY_MODULES`)
- Guarda PNGs automaticamente en `output_folder`
- Funcion auxiliar: `create_time_analysis_dashboard()` para solo el analisis temporal

**Modulos disponibles:**
```
performance, time_chart, temporal, metrics_distribution,
metrics_boxplot, mae_scatter, mfe_scatter, risk_reward_scatter,
volatility_scatter, profit_efficiency_scatter
```

### dashboards/ (subdirectorio)
10 dashboards individuales. Ver `dashboards/CLAUDE.md` para detalle de cada uno.

## Acceso desde BacktestRunner

```python
runner = BacktestRunner(strategy)
runner.run()

# Charts de velas
runner.plot_trades()                    # interactivo (default)
runner.plot_trades(interactive=False)   # estatico

# Dashboards
runner.plot_dashboards()                          # todos
runner.plot_dashboards(modules=['performance'])    # solo uno

# Acceso directo al visualizador
viz = runner.get_visualizer(interactive=True)
```

## Dependencias externas

- `mplfinance` — graficos de velas estaticos
- `matplotlib` + `seaborn` — dashboards
- `lightweight-charts` — chart interactivo (opcional)
- `nest_asyncio` — compatibilidad con Jupyter (opcional)
