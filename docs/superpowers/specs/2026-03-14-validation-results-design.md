# Spec: validation/results.py — Dataclasses de resultados

## Contexto

Este archivo define las dataclasses que todos los validadores del módulo `validation/` retornan. Es una dependencia compartida — los demás módulos importan de aquí.

## Ubicación

`validation/results.py`

## Dependencias

```python
from dataclasses import dataclass, field
import numpy as np
import pandas as pd
```

No depende de ningún otro módulo del framework.

## Dataclasses a implementar

### OOSResult

```python
@dataclass
class OOSResult:
    in_sample_metrics: dict        # all_metrics del período IS
    out_of_sample_metrics: dict    # all_metrics del período OOS
    split_date: pd.Timestamp       # timestamp donde se cortaron los datos
    is_size: int                   # número de filas (velas) en IS
    oos_size: int                  # número de filas (velas) en OOS
    degradation: dict              # {metric_name: {'is': float, 'oos': float, 'pct_change': float}}
```

- `degradation` se calcula para las métricas clave: `sharpe_ratio`, `ROI`, `profit_factor`, `percent_profitable`, `max_drawdown_pct` (estas son las claves exactas de `BacktestMetrics.compute_all_metrics()`)
- `pct_change` = `(oos - is) / abs(is) * 100`. Si `is == 0`, usar `float('inf')` o `0.0` según `oos` sea distinto o igual a cero.

### MonteCarloResult

```python
@dataclass
class MonteCarloResult:
    original_final_equity: float        # equity final del backtest real
    simulated_equities: np.ndarray      # shape (n_simulations, n_trades) — curvas de equity
    percentiles: dict                   # {5: float, 25: float, 50: float, 75: float, 95: float}
    p_value: float                      # fracción de simulaciones con equity >= original
    max_drawdowns: np.ndarray           # shape (n_simulations,) — max DD de cada sim
    confidence_intervals: dict          # {'final_equity': (lower, upper), 'max_drawdown': (lower, upper)}
```

- `p_value` alto (>0.4) = robusto, bajo (<0.2) = frágil (depende del orden).
- `percentiles` son sobre `final_equities` (última columna de `simulated_equities`).

### WalkForwardWindow

```python
@dataclass
class WalkForwardWindow:
    window_id: int
    is_start: pd.Timestamp
    is_end: pd.Timestamp
    oos_start: pd.Timestamp
    oos_end: pd.Timestamp
    best_params: dict | None           # params óptimos encontrados (modo opt) o None (modo fijo)
    is_metrics: dict                   # all_metrics del IS de esta ventana
    oos_metrics: dict                  # all_metrics del OOS de esta ventana
```

### WalkForwardResult

```python
@dataclass
class WalkForwardResult:
    windows: list[WalkForwardWindow]
    oos_combined_metrics: dict          # métricas agregadas de todos los períodos OOS
    efficiency_ratio: float             # oos_avg / is_avg del metric optimizado
    param_stability: dict | None        # {param: {'values': list, 'mean': float, 'std': float, 'cv': float}} o None
```

- `efficiency_ratio` > 0.5 = robusto, < 0.3 = overfitting.
- `param_stability` solo se llena en modo optimización. `cv` = coeficiente de variación (std/mean).

### ValidationReport

```python
@dataclass
class ValidationReport:
    oos: OOSResult | None
    monte_carlo: MonteCarloResult | None
    walk_forward: WalkForwardResult | None
    summary: dict                       # {'is_robust': bool, 'issues': list[str], 'scores': dict}
```

- `summary.scores` contiene: `oos_degradation` (pct_change del sharpe), `mc_p_value`, `wf_efficiency`.
- Cualquier campo puede ser `None` si ese validador no se ejecutó.

## Archivo __init__.py

Crear también `validation/__init__.py` con:

```python
from .results import (
    OOSResult,
    MonteCarloResult,
    WalkForwardWindow,
    WalkForwardResult,
    ValidationReport,
)
```

Se ampliará conforme se añadan los validadores.

## Tests

Crear `tests/test_validation_results.py`:

- Verificar que cada dataclass se puede instanciar con valores de ejemplo.
- Verificar que `ValidationReport` acepta `None` en los 3 validadores.
- No se necesita lógica compleja — son dataclasses puras.
