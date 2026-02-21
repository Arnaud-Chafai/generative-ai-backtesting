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

**`BacktestVisualizerInteractive`** — Chart interactivo estilo TradingView (HTML + JS).
```python
viz = BacktestVisualizerInteractive(strategy, trade_metrics_df)
viz.show(last_days=30, indicators=['EMA_20'])
```
- Genera HTML autocontenido con TradingView Lightweight Charts JS v4.2.3 (CDN)
- Abre el archivo HTML en el navegador del sistema
- Zero dependencias Python adicionales (usa json, webbrowser, tempfile, os — stdlib)
- Zoom con scroll, pan con drag, crosshair con precio/hora
- Marcadores BUY (verde, arrowUp) y SELL (rojo, arrowDown) con size=2
- Volume como overlay semi-transparente en el 25% inferior
- Indicadores como LineSeries con colores del palette
- Soporta filtrado por fecha: `start/end` o `last_days`
- Resize automatico al tamaño de la ventana del navegador
- Legend OHLC + Vol se actualiza al mover el crosshair
- Archivos HTML guardados en `{tempdir}/backtesting_charts/`

**Lecciones clave (bugs resueltos):**
- Markers DEBEN estar ordenados por tiempo → unsorted = invisibles
- NO usar `fitContent()` con >200 barras → `setVisibleLogicalRange()` ultimas 200
- Altura EXPLICITA en pixeles en `createChart()` → nunca CSS flex/porcentajes
- Volume con `priceScaleId: ''` y `scaleMargins` para overlay

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
- Lightweight Charts JS v4.2.3 (CDN, no requiere instalacion Python) — chart interactivo
