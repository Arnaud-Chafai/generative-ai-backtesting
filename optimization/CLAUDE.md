# Modulo: optimization

Optimizacion automatica de parametros de estrategias. Version actual: **v1.0 (Grid Search)**.

## Estado: FASE 4a COMPLETADA

- Grid Search: ✅ funcional
- Random Search: ⏳ pendiente (FASE 4b)
- Bayesian Optimization: ⏳ pendiente (FASE 4b)
- Walk-Forward: ⏳ pendiente (FASE 4c)

## Archivos

### results.py — `OptimizationResult`
Dataclass simple con los resultados de una iteracion:
- `params`: dict con los parametros usados
- `metrics`: dict con todas las metricas (sharpe, roi, etc.)
- `execution_time`: segundos que tardo el backtest

### optimizer.py — `ParameterOptimizer`
Motor de optimizacion. Prueba combinaciones de parametros y encuentra la mejor.

```python
from optimization import ParameterOptimizer

optimizer = ParameterOptimizer(
    strategy_class=BreakoutSimple,
    market_data=df,
    symbol='BTC',
    exchange='Binance',
    timeframe=Timeframe.M5,
    initial_capital=1000
)

results_df = optimizer.optimize(
    param_ranges={
        'lookback_period': [10, 20, 30, 50],
        'position_size_pct': [0.3, 0.5, 0.7]
    },
    metric='sharpe_ratio'  # tambien: roi, profit_factor, max_drawdown, sortino_ratio
)

best = optimizer.get_best_params(min_trades=20)  # filtro anti-fantasma
optimizer.export_results('results.csv')
```

**Flujo interno de `optimize()`:**
1. `_validate_params()` — verifica que los parametros existan en el `__init__` de la estrategia (usa `inspect`)
2. `_generate_grid()` — genera todas las combinaciones con `itertools.product`
3. Loop con `tqdm`: por cada combinacion → crea estrategia → `BacktestRunner.run()` → extrae metricas
4. Retorna DataFrame ordenado por la metrica objetivo

**Detalles importantes:**
- Inyecta `market_data` a la estrategia (evita recargar CSV en cada iteracion, ~200x mas rapido)
- `get_best_params(min_trades=20)` filtra resultados con pocos trades para evitar overfitting
- Metricas validas: `sharpe_ratio`, `roi`, `profit_factor`, `max_drawdown`, `sortino_ratio`

### visualizer.py — `OptimizationPlotter`
Genera superficies 3D estilo MATLAB para visualizar la topologia del espacio de parametros.

```python
from optimization import OptimizationPlotter

plotter = OptimizationPlotter(results_df)
plotter.plot_3d_surface('lookback_period', 'position_size_pct', 'sharpe_ratio')
```

- Superficie 3D con colormap coolwarm (rojo → azul)
- Proyeccion de contornos en el "suelo" (heatmap plano)
- Rejilla negra estilo MATLAB

## Dependencias

```
ParameterOptimizer
├── BacktestRunner (core) — ejecuta cada backtest
├── OptimizationResult (results) — almacena cada iteracion
└── tqdm — barra de progreso

OptimizationPlotter
├── matplotlib (3D surface)
└── numpy (meshgrid)
```
