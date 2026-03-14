# Spec: validation/oos_split.py — OOSSplitValidator

## Contexto

Divide los datos en dos períodos: in-sample (IS) y out-of-sample (OOS). Ejecuta backtests independientes en cada porción para detectar overfitting. El OOS siempre es el tramo final cronológico — nunca se barajan datos en series de tiempo.

## Ubicación

`validation/oos_split.py`

## Dependencias

```python
import pandas as pd
from core.backtest_runner import BacktestRunner
from validation.results import OOSResult
```

## Clase: OOSSplitValidator

### Constructor

```python
class OOSSplitValidator:
    def __init__(
        self,
        strategy_class: type,
        market_data: pd.DataFrame,
        oos_ratio: float = 0.3,
        **strategy_params
    ):
```

- `strategy_class`: clase (no instancia) que hereda de `BaseStrategy`.
- `market_data`: DataFrame OHLCV con `DatetimeIndex`.
- `oos_ratio`: fracción de datos para OOS. Debe estar en (0.0, 1.0). Validar y lanzar `ValueError` si no.
- `**strategy_params`: todos los kwargs que la estrategia necesita (`symbol`, `timeframe`, `exchange`, `lookback_period`, etc.)

### Método run()

```python
def run(self, verbose: bool = True) -> OOSResult:
```

#### Algoritmo paso a paso

1. **Calcular punto de corte:**
   ```python
   split_index = int(len(self.market_data) * (1 - self.oos_ratio))
   ```

2. **Dividir datos:**
   ```python
   is_data = self.market_data.iloc[:split_index].copy()
   oos_data = self.market_data.iloc[split_index:].copy()
   split_date = oos_data.index[0]
   ```

3. **Ejecutar backtest IS:**
   ```python
   strategy_is = self.strategy_class(data=is_data, **self.strategy_params)
   runner_is = BacktestRunner(strategy_is)
   runner_is.run(verbose=False)
   is_metrics = runner_is.metrics.all_metrics
   ```

4. **Ejecutar backtest OOS:**
   ```python
   strategy_oos = self.strategy_class(data=oos_data, **self.strategy_params)
   runner_oos = BacktestRunner(strategy_oos)
   runner_oos.run(verbose=False)
   oos_metrics = runner_oos.metrics.all_metrics
   ```

5. **Calcular degradación:**
   ```python
   METRICS_TO_COMPARE = ['sharpe_ratio', 'ROI', 'profit_factor', 'percent_profitable', 'max_drawdown_pct']
   degradation = {}
   for metric in METRICS_TO_COMPARE:
       is_val = is_metrics.get(metric, 0)
       oos_val = oos_metrics.get(metric, 0)
       if abs(is_val) > 1e-10:
           pct_change = (oos_val - is_val) / abs(is_val) * 100
       elif abs(oos_val) > 1e-10:
           pct_change = float('inf')
       else:
           pct_change = 0.0
       degradation[metric] = {'is': is_val, 'oos': oos_val, 'pct_change': pct_change}
   ```

6. **Verbose output:**
   Si `verbose=True`, imprimir:
   ```
   === OOS Split Validation ===
   Split date: 2025-08-15
   In-Sample: 7000 bars | Out-of-Sample: 3000 bars

   Metric            IS        OOS       Change
   sharpe_ratio      1.80      1.10      -38.9%
   roi               25.3%     8.2%      -67.6%
   ...
   ```

7. **Retornar OOSResult.**

### Casos edge

- Si IS o OOS produce 0 trades: `all_metrics` contendrá valores por defecto (0 o NaN según la métrica). El validador no debe crashear — incluir warning si `verbose=True`.
- Si `market_data` tiene menos de 20 filas: lanzar `ValueError` con mensaje descriptivo.

## Tests

Crear `tests/test_oos_split.py`:

1. **Test con estrategia de ejemplo:** Usar `BreakoutSimple` o una estrategia mock. Verificar que `OOSResult` tiene campos correctos, `split_date` está en el rango esperado, `is_size + oos_size == len(market_data)`.
2. **Test de degradation:** Verificar que `pct_change` se calcula correctamente con valores conocidos.
3. **Test de validación:** `oos_ratio=0` y `oos_ratio=1` deben lanzar `ValueError`.
4. **Test con datos insuficientes:** DataFrame con <20 filas debe lanzar `ValueError`.

## Ejemplo de uso

```python
from validation.oos_split import OOSSplitValidator
from strategies.examples.breakout_simple import BreakoutSimple
from utils.timeframe import Timeframe

oos = OOSSplitValidator(
    strategy_class=BreakoutSimple,
    market_data=df,
    oos_ratio=0.3,
    symbol='BTC',
    timeframe=Timeframe.M5,
    exchange='Binance',
    lookback_period=20,
)
result = oos.run()

print(result.split_date)
print(result.degradation['sharpe_ratio'])
```
