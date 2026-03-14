# Spec: validation/validation_suite.py — ValidationSuite

## Contexto

Orquestador que ejecuta los tres validadores en secuencia y produce un `ValidationReport` consolidado. Es el punto de entrada "todo en uno" — pero cada validador también funciona standalone.

## Ubicación

`validation/validation_suite.py`

## Dependencias

```python
import pandas as pd
from core.backtest_runner import BacktestRunner
from validation.oos_split import OOSSplitValidator
from validation.monte_carlo import MonteCarloValidator
from validation.walk_forward import WalkForwardValidator
from validation.results import ValidationReport
```

## Clase: ValidationSuite

### Constructor

```python
class ValidationSuite:
    def __init__(
        self,
        strategy_class: type,
        market_data: pd.DataFrame,
        **strategy_params
    ):
```

- `strategy_class`: clase que hereda de `BaseStrategy`.
- `market_data`: DataFrame OHLCV con `DatetimeIndex`.
- `**strategy_params`: kwargs fijos de la estrategia.

### Método run_all()

```python
def run_all(
    self,
    # OOS params
    oos_ratio: float = 0.3,
    # Monte Carlo params
    mc_simulations: int = 1000,
    mc_seed: int | None = None,
    mc_confidence: float = 0.95,
    # Walk-Forward params
    wf_windows: int = 5,
    wf_oos_ratio: float = 0.25,
    wf_anchored: bool = False,
    # Walk-Forward optimization
    param_ranges: dict | None = None,
    optimization_metric: str = 'sharpe_ratio',
    wf_min_trades: int = 10,
    # General
    verbose: bool = True,
) -> ValidationReport:
```

#### Lógica de skip

- `oos_ratio <= 0` → skip OOS
- `mc_simulations <= 0` → skip Monte Carlo
- `wf_windows <= 0` → skip Walk-Forward

Esto permite usar la suite para ejecutar solo un subconjunto de validadores.

#### Algoritmo paso a paso

```python
def run_all(self, ...) -> ValidationReport:
    oos_result = None
    mc_result = None
    wf_result = None

    # 1. OOS Split
    if oos_ratio > 0:
        if verbose:
            print("=" * 50)
            print("STEP 1/3: Out-of-Sample Split")
            print("=" * 50)
        oos_validator = OOSSplitValidator(
            strategy_class=self.strategy_class,
            market_data=self.market_data,
            oos_ratio=oos_ratio,
            **self.strategy_params,
        )
        oos_result = oos_validator.run(verbose=verbose)

    # 2. Monte Carlo (necesita trades del backtest completo)
    if mc_simulations > 0:
        if verbose:
            print("\n" + "=" * 50)
            print("STEP 2/3: Monte Carlo Simulation")
            print("=" * 50)
        # Ejecutar backtest completo para obtener trades
        strategy_full = self.strategy_class(data=self.market_data, **self.strategy_params)
        runner_full = BacktestRunner(strategy_full)
        runner_full.run(verbose=False)

        mc_validator = MonteCarloValidator(
            trades_df=runner_full.metrics.trade_metrics_df,
            initial_capital=strategy_full.initial_capital,
        )
        mc_result = mc_validator.run(
            n_simulations=mc_simulations,
            confidence_level=mc_confidence,
            seed=mc_seed,
            verbose=verbose,
        )

    # 3. Walk-Forward
    if wf_windows > 0:
        if verbose:
            print("\n" + "=" * 50)
            print("STEP 3/3: Walk-Forward Validation")
            print("=" * 50)
        wf_validator = WalkForwardValidator(
            strategy_class=self.strategy_class,
            market_data=self.market_data,
            n_windows=wf_windows,
            oos_ratio=wf_oos_ratio,
            anchored=wf_anchored,
            **self.strategy_params,
        )
        wf_result = wf_validator.run(
            param_ranges=param_ranges,
            optimization_metric=optimization_metric,
            min_trades=wf_min_trades,
            verbose=verbose,
        )

    # 4. Generar summary
    summary = self._generate_summary(oos_result, mc_result, wf_result, optimization_metric)

    if verbose:
        print("\n" + "=" * 50)
        print("VALIDATION SUMMARY")
        print("=" * 50)
        if summary['is_robust']:
            print("Result: ROBUST — no significant issues detected")
        else:
            print("Result: ISSUES DETECTED")
            for issue in summary['issues']:
                print(f"  ⚠ {issue}")
        print(f"Scores: {summary['scores']}")

    return ValidationReport(
        oos=oos_result,
        monte_carlo=mc_result,
        walk_forward=wf_result,
        summary=summary,
    )
```

### Método _generate_summary()

```python
def _generate_summary(self, oos, mc, wf, optimization_metric) -> dict:
    issues = []
    scores = {}

    # OOS checks
    oos_degradation = None
    if oos is not None:
        sharpe_deg = oos.degradation.get('sharpe_ratio', {})
        oos_degradation = sharpe_deg.get('pct_change', 0)
        scores['oos_degradation'] = oos_degradation
        if oos_degradation < -50:
            issues.append(
                f"OOS: sharpe_ratio degraded {oos_degradation:.1f}% vs in-sample"
            )

    # Monte Carlo checks
    if mc is not None:
        scores['mc_p_value'] = mc.p_value
        if mc.p_value < 0.2:
            issues.append(
                f"MC: equity depends on trade order (p-value={mc.p_value:.2f})"
            )

    # Walk-Forward checks
    if wf is not None:
        scores['wf_efficiency'] = wf.efficiency_ratio
        if wf.efficiency_ratio < 0.3:
            issues.append(
                f"WF: low efficiency ratio ({wf.efficiency_ratio:.2f}), "
                f"possible overfitting"
            )
        if wf.param_stability:
            unstable = [
                p for p, s in wf.param_stability.items()
                if s['cv'] > 0.5
            ]
            if unstable:
                issues.append(
                    f"WF: unstable parameters across windows: {unstable}"
                )

    return {
        'is_robust': len(issues) == 0,
        'issues': issues,
        'scores': scores,
    }
```

## Actualizar __init__.py

Añadir a `validation/__init__.py`:

```python
from .oos_split import OOSSplitValidator
from .monte_carlo import MonteCarloValidator
from .walk_forward import WalkForwardValidator
from .validation_suite import ValidationSuite
from .results import (
    OOSResult,
    MonteCarloResult,
    WalkForwardWindow,
    WalkForwardResult,
    ValidationReport,
)
```

## Tests

Crear `tests/test_validation_suite.py`:

1. **Test run_all completo:** Ejecutar con los 3 validadores. Verificar que `ValidationReport` tiene los 3 resultados.
2. **Test skip selectivo:** `wf_windows=0` → `walk_forward` es `None`. Similar para los otros.
3. **Test summary robusto:** Con estrategia que funciona bien, `is_robust` debe ser `True`.
4. **Test summary con issues:** Mockear métricas malas para verificar que se detectan issues.

### Nota de diseño: backtest redundante para Monte Carlo

La suite ejecuta un backtest completo adicional sobre `market_data` para obtener los trades que Monte Carlo necesita. Aunque el OOS validator ya ejecutó backtests IS + OOS (que cubren todo el dataset), sus trades no son equivalentes al backtest completo — el split puede cortar una posición abierta. El backtest full es la referencia correcta. Esta redundancia es intencional.

## Ejemplo de uso

```python
from validation import ValidationSuite

suite = ValidationSuite(
    strategy_class=BreakoutSimple,
    market_data=df,
    symbol='BTC',
    timeframe=Timeframe.M5,
    exchange='Binance',
    lookback_period=20,
)

# Todo
report = suite.run_all(
    oos_ratio=0.3,
    mc_simulations=2000,
    wf_windows=5,
    param_ranges={'lookback_period': [10, 15, 20, 25, 30]},
)

if report.summary['is_robust']:
    print("Strategy is robust!")
else:
    for issue in report.summary['issues']:
        print(f"Warning: {issue}")

# Solo Monte Carlo + OOS
report2 = suite.run_all(wf_windows=0)
```
