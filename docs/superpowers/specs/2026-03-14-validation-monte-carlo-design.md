# Spec: validation/monte_carlo.py — MonteCarloValidator

## Contexto

Valida la robustez del equity curve permutando el orden de los trades. Si el equity final del backtest real está dentro de la distribución normal de las permutaciones, el resultado no depende de la secuencia específica de trades — es robusto.

**No re-ejecuta backtests.** Trabaja sobre un DataFrame de trades ya ejecutados.

## Ubicación

`validation/monte_carlo.py`

## Dependencias

```python
import numpy as np
import pandas as pd
from validation.results import MonteCarloResult
```

No depende de `BacktestRunner`, `BacktestEngine`, ni estrategias. Solo necesita el DataFrame de trades con columna `net_pnl`.

## Clase: MonteCarloValidator

### Constructor

```python
class MonteCarloValidator:
    def __init__(
        self,
        trades_df: pd.DataFrame,
        initial_capital: float = 1000.0,
    ):
```

- `trades_df`: DataFrame de trades. Debe tener columna `net_pnl` (o `net_profit_loss`). Puede ser `runner.metrics.trade_metrics_df` o `runner.results`.
- `initial_capital`: capital inicial para construir equity curves.
- Validar que `trades_df` tiene al menos 2 trades, lanzar `ValueError` si no.
- Detectar automáticamente si la columna de P&L se llama `net_pnl` o `net_profit_loss` (el framework usa ambas según el punto del pipeline).

### Método run()

```python
def run(
    self,
    n_simulations: int = 1000,
    confidence_level: float = 0.95,
    seed: int | None = None,
    verbose: bool = True,
) -> MonteCarloResult:
```

#### Algoritmo paso a paso

1. **Extraer P&L:**
   ```python
   # Detectar nombre de columna
   if 'net_pnl' in self.trades_df.columns:
       pnl_col = 'net_pnl'
   elif 'net_profit_loss' in self.trades_df.columns:
       pnl_col = 'net_profit_loss'
   else:
       raise ValueError(
           f"trades_df must have 'net_pnl' or 'net_profit_loss' column. "
           f"Found columns: {list(self.trades_df.columns)}"
       )
   pnl_series = self.trades_df[pnl_col].values.astype(float)
   n_trades = len(pnl_series)
   ```

2. **Equity curve original:**
   ```python
   original_equity = self.initial_capital + np.cumsum(pnl_series)
   original_final = original_equity[-1]
   ```

3. **Generar permutaciones (vectorizado con numpy):**
   ```python
   rng = np.random.default_rng(seed)
   simulated_equities = np.zeros((n_simulations, n_trades))
   max_drawdowns = np.zeros(n_simulations)

   for i in range(n_simulations):
       shuffled = rng.permutation(pnl_series)
       equity = self.initial_capital + np.cumsum(shuffled)
       simulated_equities[i] = equity

       # Max drawdown
       running_max = np.maximum.accumulate(equity)
       drawdown_pct = (running_max - equity) / running_max
       max_drawdowns[i] = drawdown_pct.max()
   ```

   **Nota de rendimiento:** Para n_simulations=1000 y n_trades=500, esto son 500K operaciones — numpy lo maneja en <1s. No es necesario paralelizar.

4. **Calcular percentiles:**
   ```python
   final_equities = simulated_equities[:, -1]
   percentiles = {
       p: float(np.percentile(final_equities, p))
       for p in [5, 25, 50, 75, 95]
   }
   ```

5. **Calcular p-value:**
   ```python
   p_value = float(np.mean(final_equities >= original_final))
   ```
   - `p_value` > 0.4 → robusto (la mayoría de órdenes alternativos también llegan a este equity).
   - `p_value` < 0.2 → frágil (el equity depende de cuándo ocurrieron los grandes ganadores).

6. **Intervalos de confianza:**
   ```python
   alpha = 1 - confidence_level
   lower_pct = (alpha / 2) * 100
   upper_pct = (1 - alpha / 2) * 100
   confidence_intervals = {
       'final_equity': (
           float(np.percentile(final_equities, lower_pct)),
           float(np.percentile(final_equities, upper_pct)),
       ),
       'max_drawdown': (
           float(np.percentile(max_drawdowns, lower_pct)),
           float(np.percentile(max_drawdowns, upper_pct)),
       ),
   }
   ```

7. **Verbose output:**
   ```
   === Monte Carlo Validation (1000 simulations) ===
   Original final equity: $1,250.00

   Simulated equity distribution:
     P5:  $980.00  |  P25: $1,100.00  |  P50: $1,200.00  |  P75: $1,320.00  |  P95: $1,450.00

   p-value: 0.62 (ROBUST — result does not depend on trade order)

   95% Confidence Intervals:
     Final equity: [$950.00, $1,480.00]
     Max drawdown: [8.2%, 24.5%]
   ```

8. **Retornar MonteCarloResult.**

### Casos edge

- **1 trade:** Lanzar `ValueError` — no se puede permutar un solo elemento.
- **Todos los trades con mismo P&L:** Todas las simulaciones producen el mismo equity curve. `p_value` será 1.0 (o cercano). Esto es correcto y esperado.
- **Capital llega a 0 en alguna simulación:** El equity puede ser negativo. No hay lógica de "margin call" — esto es una simulación estadística, no un backtest.

## Tests

Crear `tests/test_monte_carlo.py`:

1. **Test determinista con seed:** Verificar que con `seed=42` los resultados son reproducibles.
2. **Test con trades uniformes:** Si todos los trades son +$10, `p_value` ≈ 1.0 y todas las equity curves convergen al mismo punto.
3. **Test con trades extremos:** Un trade de +$1000 y 9 de -$10. El `p_value` debe ser bajo porque el orden del gran ganador importa mucho.
4. **Test de percentiles:** Verificar que P5 < P50 < P95.
5. **Test de validación:** DataFrame vacío o con 1 trade lanza `ValueError`.

## Ejemplo de uso

```python
from validation.monte_carlo import MonteCarloValidator

runner = BacktestRunner(strategy)
runner.run()

mc = MonteCarloValidator(
    trades_df=runner.metrics.trade_metrics_df,
    initial_capital=strategy.initial_capital,
)
result = mc.run(n_simulations=2000, seed=42)

print(f"p-value: {result.p_value:.2f}")
print(f"Equity CI 95%: {result.confidence_intervals['final_equity']}")
```
