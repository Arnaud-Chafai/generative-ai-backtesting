# Spec: validation/walk_forward.py — WalkForwardValidator

## Contexto

El validador más complejo. Divide los datos en N ventanas rodantes, ejecuta backtest (con o sin re-optimización) en la porción in-sample (IS), y valida en la porción out-of-sample (OOS) de cada ventana. Mide si la estrategia y sus parámetros se mantienen robustos al avanzar en el tiempo.

## Ubicación

`validation/walk_forward.py`

## Dependencias

```python
import numpy as np
import pandas as pd
from core.backtest_runner import BacktestRunner
from optimization.optimizer import ParameterOptimizer
from validation.results import WalkForwardWindow, WalkForwardResult
```

## Clase: WalkForwardValidator

### Constructor

```python
class WalkForwardValidator:
    def __init__(
        self,
        strategy_class: type,
        market_data: pd.DataFrame,
        n_windows: int = 5,
        oos_ratio: float = 0.25,
        anchored: bool = False,
        **strategy_params
    ):
```

- `strategy_class`: clase que hereda de `BaseStrategy`.
- `market_data`: DataFrame OHLCV con `DatetimeIndex`.
- `n_windows`: número de ventanas. Validar >= 2.
- `oos_ratio`: fracción de cada ventana dedicada a OOS. Validar en (0.0, 1.0).
- `anchored`: `False` = rolling window (IS se desplaza), `True` = anchored (IS crece desde el inicio).
- `**strategy_params`: kwargs fijos de la estrategia.

### Método run()

```python
def run(
    self,
    param_ranges: dict | None = None,
    optimization_metric: str = 'sharpe_ratio',
    min_trades: int = 10,
    verbose: bool = True,
) -> WalkForwardResult:
```

- `param_ranges`: si se proporciona, activa modo re-optimización. Si `None`, usa parámetros fijos de `strategy_params`.
- `optimization_metric`: métrica objetivo para el optimizer y para calcular `efficiency_ratio`.
- `min_trades`: mínimo de trades para que una ventana se considere válida en la optimización.

#### Algoritmo: Cálculo de ventanas

**Modo Rolling (`anchored=False`):**

```python
total_bars = len(market_data)

# Las ventanas NO se solapan. Cubren todo el dataset secuencialmente.
# Cada ventana tiene una porción IS seguida de una porción OOS.
window_total_size = total_bars // n_windows
oos_size = int(window_total_size * oos_ratio)
is_size = window_total_size - oos_size

windows_ranges = []
for i in range(n_windows):
    base = i * window_total_size
    is_start_idx  = base
    is_end_idx    = base + is_size
    oos_start_idx = is_end_idx
    oos_end_idx   = base + window_total_size
    # Última ventana absorbe residuo
    if i == n_windows - 1:
        oos_end_idx = total_bars
    windows_ranges.append((is_start_idx, is_end_idx, oos_start_idx, oos_end_idx))
```

**Modo Anchored (`anchored=True`):**

```python
total_bars = len(market_data)

# IS siempre empieza en 0 y crece. OOS es un bloque fijo después de IS.
# Dividir la zona OOS total en N bloques iguales.
oos_total_size = int(total_bars * oos_ratio)
is_base_size = total_bars - oos_total_size
oos_per_window = oos_total_size // n_windows

windows_ranges = []
for i in range(n_windows):
    is_start_idx  = 0                                          # siempre desde el inicio
    is_end_idx    = is_base_size + i * oos_per_window          # crece con cada ventana
    oos_start_idx = is_end_idx
    oos_end_idx   = is_end_idx + oos_per_window
    # Última ventana absorbe residuo
    if i == n_windows - 1:
        oos_end_idx = total_bars
    windows_ranges.append((is_start_idx, is_end_idx, oos_start_idx, oos_end_idx))
```

#### Algoritmo: Ejecución por ventana

```python
windows = []

for i, (is_start, is_end, oos_start, oos_end) in enumerate(windows_ranges):
    is_data = market_data.iloc[is_start:is_end].copy()
    oos_data = market_data.iloc[oos_start:oos_end].copy()

    if verbose:
        print(f"Window {i+1}/{n_windows}: "
              f"IS [{is_data.index[0]} → {is_data.index[-1]}] ({len(is_data)} bars) | "
              f"OOS [{oos_data.index[0]} → {oos_data.index[-1]}] ({len(oos_data)} bars)")

    # --- MODO OPTIMIZACIÓN ---
    if param_ranges is not None:
        optimizer = ParameterOptimizer(
            strategy_class=strategy_class,
            market_data=is_data,
            **strategy_params
        )
        optimizer.optimize(
            param_ranges=param_ranges,
            metric=optimization_metric,
            show_progress=False,
        )
        best_params = optimizer.get_best_params(min_trades=min_trades)

        if best_params is None:
            # Ninguna combinación alcanzó min_trades en IS
            if verbose:
                print(f"  ⚠ Window {i+1}: no valid params found (min_trades={min_trades})")
            best_params = {}

        full_params = {**strategy_params, **best_params}
    # --- MODO PARÁMETROS FIJOS ---
    else:
        best_params = None
        full_params = strategy_params

    # Backtest IS
    is_metrics = _run_single_backtest(strategy_class, is_data, full_params)

    # Backtest OOS
    oos_metrics = _run_single_backtest(strategy_class, oos_data, full_params)

    windows.append(WalkForwardWindow(
        window_id=i,
        is_start=is_data.index[0],
        is_end=is_data.index[-1],
        oos_start=oos_data.index[0],
        oos_end=oos_data.index[-1],
        best_params=best_params if param_ranges else None,
        is_metrics=is_metrics,
        oos_metrics=oos_metrics,
    ))

    if verbose:
        is_score = is_metrics.get(optimization_metric, 0)
        oos_score = oos_metrics.get(optimization_metric, 0)
        print(f"  IS {optimization_metric}={is_score:.3f} | OOS {optimization_metric}={oos_score:.3f}")
```

#### Función helper privada

```python
def _run_single_backtest(strategy_class, data, params) -> dict:
    """Ejecuta un backtest y retorna all_metrics. Retorna dict vacío si hay error."""
    try:
        strategy = strategy_class(data=data, **params)
        runner = BacktestRunner(strategy)
        runner.run(verbose=False)
        return runner.metrics.all_metrics
    except Exception as e:
        return {'error': str(e)}
```

Puede ser un método estático o una función a nivel de módulo.

#### Algoritmo: Métricas agregadas

```python
# 1. Métricas combinadas OOS
#    Concatenar los trades OOS de todas las ventanas y recalcular métricas
#    NO es un promedio — es una re-ejecución sobre los trades concatenados
#    SIMPLIFICACIÓN: Promediar las métricas OOS de todas las ventanas.
#    La concatenación de trades requiere re-pasar por MetricsAggregator, que necesita
#    el market_data original completo. El promedio es la aproximación estándar de la industria.
valid_windows = [w for w in windows if 'error' not in w.oos_metrics]

if valid_windows:
    oos_combined_metrics = {}
    all_metric_keys = valid_windows[0].oos_metrics.keys()
    for key in all_metric_keys:
        values = [w.oos_metrics[key] for w in valid_windows
                  if isinstance(w.oos_metrics.get(key), (int, float))]
        if values:
            oos_combined_metrics[key] = sum(values) / len(values)
else:
    oos_combined_metrics = {}

# 2. Efficiency ratio
is_scores = [w.is_metrics.get(optimization_metric, 0) for w in valid_windows
             if isinstance(w.is_metrics.get(optimization_metric), (int, float))]
oos_scores = [w.oos_metrics.get(optimization_metric, 0) for w in valid_windows
              if isinstance(w.oos_metrics.get(optimization_metric), (int, float))]

if is_scores and oos_scores:
    is_avg = sum(is_scores) / len(is_scores)
    oos_avg = sum(oos_scores) / len(oos_scores)
    efficiency_ratio = oos_avg / is_avg if abs(is_avg) > 1e-10 else 0.0
else:
    efficiency_ratio = 0.0

# 3. Param stability (solo modo optimización)
param_stability = None
if param_ranges is not None:
    windows_with_params = [w for w in valid_windows if w.best_params]
    if len(windows_with_params) >= 2:
        param_stability = {}
        all_param_names = windows_with_params[0].best_params.keys()
        for param in all_param_names:
            values = [w.best_params[param] for w in windows_with_params
                      if param in w.best_params]
            if values and all(isinstance(v, (int, float)) for v in values):
                mean = np.mean(values)
                std = np.std(values)
                cv = std / abs(mean) if abs(mean) > 1e-10 else float('inf')
                param_stability[param] = {
                    'values': values,
                    'mean': float(mean),
                    'std': float(std),
                    'cv': float(cv),
                }
```

#### Verbose final

```
=== Walk-Forward Validation (5 windows, rolling) ===

Window  IS Period                OOS Period               IS Sharpe  OOS Sharpe  Params
1       2024-01-01 → 2024-04-15  2024-04-15 → 2024-06-01  1.80       1.20       {lookback: 20}
2       2024-06-01 → 2024-09-15  2024-09-15 → 2024-11-01  1.65       1.10       {lookback: 15}
...

Efficiency Ratio: 0.65 (ROBUST)
Param Stability:
  lookback_period: mean=18.0, std=3.2, cv=0.18 (STABLE)
```

### Casos edge

- **Ventana OOS con 0 trades:** Incluir en results con métricas vacías. Imprimir warning. No contar para efficiency_ratio.
- **Optimizer no encuentra params válidos:** `best_params` queda `{}`, se usan los `strategy_params` fijos como fallback.
- **n_windows > total_bars / 50:** Warning — ventanas demasiado pequeñas para resultados significativos.
- **Datos insuficientes:** Si `total_bars < n_windows * 20`, lanzar `ValueError`.

### Known limitations

- **Stdout noise de BaseStrategy:** Cada instanciación de estrategia con `data=` imprime 2 líneas a stdout ("Datos inyectados: N candles..."). En modo optimización con muchas combinaciones esto genera ruido considerable. Usar `contextlib.redirect_stdout(io.StringIO())` alrededor de las instanciaciones de estrategia para suprimirlo.
- **Stdout de ParameterOptimizer.get_best_params():** Imprime un bloque de texto con los mejores parámetros. Suprimir igualmente con `redirect_stdout`.
- **Métricas válidas para optimization_metric:** El `ParameterOptimizer` acepta solo: `'sharpe_ratio'`, `'roi'`, `'profit_factor'`, `'max_drawdown'`, `'sortino_ratio'`. Documentar en el docstring del `run()` y lanzar `ValueError` antes de empezar si la métrica no está en esa whitelist.

## Tests

Crear `tests/test_walk_forward.py`:

1. **Test modo fijo (sin optimización):** Verificar N ventanas, cada una con IS y OOS metrics.
2. **Test modo optimización:** Verificar que `best_params` se llena y `param_stability` se calcula.
3. **Test rolling vs anchored:** Verificar que en anchored `is_start` siempre es el primer timestamp.
4. **Test efficiency_ratio:** Con valores conocidos, verificar cálculo.
5. **Test validación:** `n_windows=0` o `n_windows=1` lanza `ValueError`.
6. **Test cobertura completa:** Verificar que las ventanas cubren todo el dataset sin huecos ni solapamientos, y que la última ventana absorbe el residuo.

## Ejemplo de uso

```python
from validation.walk_forward import WalkForwardValidator

# Modo optimización
wf = WalkForwardValidator(
    strategy_class=BreakoutSimple,
    market_data=df,
    n_windows=5,
    oos_ratio=0.25,
    symbol='BTC', timeframe=Timeframe.M5, exchange='Binance',
)
result = wf.run(
    param_ranges={'lookback_period': [10, 15, 20, 25, 30]},
    optimization_metric='sharpe_ratio',
)
print(f"Efficiency: {result.efficiency_ratio:.2f}")
print(f"Param stability: {result.param_stability}")

# Modo fijo
wf2 = WalkForwardValidator(
    strategy_class=BreakoutSimple,
    market_data=df,
    n_windows=8,
    anchored=True,
    symbol='BTC', timeframe=Timeframe.M5, exchange='Binance',
    lookback_period=20,
)
result2 = wf2.run()  # sin param_ranges → modo fijo
```
