# Modulo: validation

Validacion estadistica de estrategias para detectar overfitting. Tres validadores independientes + un orquestador.

## Archivos

### results.py — Dataclasses de resultados
- `OOSResult` — Resultado de split IS/OOS
- `MonteCarloResult` — Resultado de permutacion de trades
- `WalkForwardWindow` / `WalkForwardResult` — Resultado de walk-forward
- `ValidationReport` — Reporte consolidado de los 3 validadores

### oos_split.py — `OOSSplitValidator`
Divide datos en in-sample (IS) y out-of-sample (OOS). Ejecuta backtests independientes y mide degradacion de metricas clave.

### monte_carlo.py — `MonteCarloValidator`
Permuta el orden de trades N veces para generar distribucion de equity curves. Calcula p-value e intervalos de confianza.

### walk_forward.py — `WalkForwardValidator`
Divide datos en N ventanas rodantes. Soporta modo fijo (params constantes) y modo optimizacion (re-optimiza en cada ventana IS).

### validation_suite.py — `ValidationSuite`
Orquestador que ejecuta los 3 validadores en secuencia y genera `ValidationReport` consolidado.

## Uso rapido

```python
from validation import ValidationSuite

suite = ValidationSuite(
    strategy_class=MiEstrategia,
    market_data=df,
    symbol='BTC', timeframe=Timeframe.M5, exchange='Binance',
    lookback_period=20,
)
report = suite.run_all(
    oos_ratio=0.3,
    mc_simulations=1000,
    wf_windows=5,
    param_ranges={'lookback_period': [10, 15, 20, 25, 30]},
)

if report.summary['is_robust']:
    print("Estrategia robusta!")
else:
    for issue in report.summary['issues']:
        print(f"Warning: {issue}")
```

## Uso individual

```python
from validation import MonteCarloValidator, OOSSplitValidator, WalkForwardValidator

# Monte Carlo (sobre trades existentes)
mc = MonteCarloValidator(runner.metrics.trade_metrics_df, initial_capital=1000)
result = mc.run(n_simulations=2000, seed=42)

# OOS Split
oos = OOSSplitValidator(strategy_class=MiEstrategia, market_data=df, oos_ratio=0.3, ...)
result = oos.run()

# Walk-Forward
wf = WalkForwardValidator(strategy_class=MiEstrategia, market_data=df, n_windows=5, ...)
result = wf.run(param_ranges={'lookback': [10, 20, 30]})
```

## Umbrales de robustez

| Validador | Metrica | Robusto | Marginal | Overfitting |
|-----------|---------|---------|----------|-------------|
| OOS | sharpe degradation | < 30% | 30-50% | > 50% |
| Monte Carlo | p-value | > 0.4 | 0.2-0.4 | < 0.2 |
| Walk-Forward | efficiency_ratio | > 0.5 | 0.3-0.5 | < 0.3 |
| Walk-Forward | param CV | < 0.3 | 0.3-0.5 | > 0.5 |

## Specs

Detalle completo en `docs/superpowers/specs/2026-03-14-validation-*-design.md`
