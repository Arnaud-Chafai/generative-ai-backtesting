# Modulo: validation

Validacion estadistica de estrategias para detectar **overfitting** — el problema fundamental del backtesting.

## El problema que resuelve

Un backtest estatico sobre datos historicos puede dar resultados espectaculares simplemente porque la estrategia se "ajusto" al ruido del pasado. Sin validacion, no hay forma de distinguir entre una estrategia que descubrio un patron real y una que memorizo datos historicos.

Este modulo implementa 3 validadores independientes, cada uno atacando una fuente distinta de overfitting:

| Validador | Pregunta que responde | Fuente de overfitting que detecta |
|-----------|----------------------|----------------------------------|
| **OOS Split** | "¿Funciona en datos que nunca vio?" | Sobreajuste a datos especificos |
| **Monte Carlo** | "¿El resultado depende de la suerte secuencial?" | Dependencia del orden de trades |
| **Walk-Forward** | "¿Los parametros optimos se mantienen en el tiempo?" | Inestabilidad de la optimizacion |

## Archivos

### results.py — Dataclasses de resultados

Tipos compartidos que todos los validadores retornan. No contiene logica — solo estructuras de datos.

- `OOSResult` — metricas IS vs OOS + degradacion porcentual
- `MonteCarloResult` — distribucion de equities permutadas + p-value
- `WalkForwardWindow` / `WalkForwardResult` — resultados por ventana + efficiency ratio
- `ValidationReport` — reporte consolidado con `summary['is_robust']`

### oos_split.py — `OOSSplitValidator`

**Que hace:** Divide los datos en dos periodos: in-sample (IS, 70% por defecto) y out-of-sample (OOS, 30% final). Ejecuta backtests completamente independientes en cada porcion y compara metricas.

**Por que sirve:** Si el sharpe ratio es 2.0 en IS pero 0.3 en OOS, la estrategia memorizo el pasado en lugar de encontrar un patron real. La degradacion IS→OOS es el indicador mas directo de overfitting.

**Detalles clave:**
- El split siempre es **temporal** (nunca aleatorio) — en series de tiempo, el OOS debe ser el futuro
- Son dos backtests independientes — no hay leak de informacion entre IS y OOS
- Compara 5 metricas: `sharpe_ratio`, `ROI`, `profit_factor`, `percent_profitable`, `max_drawdown_pct`
- El `pct_change` mide cuanto cae cada metrica: `(oos - is) / |is| * 100`
- Usa `contextlib.redirect_stdout` para suprimir los prints de `BaseStrategy.__init__`

```python
oos = OOSSplitValidator(strategy_class=MiEstrategia, market_data=df, oos_ratio=0.3,
                        symbol='BTC', timeframe=Timeframe.M5, exchange='Binance')
result = oos.run()
# result.degradation['sharpe_ratio'] → {'is': 1.8, 'oos': 1.1, 'pct_change': -38.9}
```

### monte_carlo.py — `MonteCarloValidator`

**Que hace:** Toma los trades ya ejecutados y baraja su orden N veces (default 1000). Cada permutacion genera una equity curve diferente. Compara la curva real contra la distribucion simulada.

**Por que sirve:** Si una estrategia gano porque tuvo 3 trades enormes al principio (que inflaron el capital para los siguientes), barajar esos trades al final produciria resultados muy distintos. Una estrategia robusta produce curvas similares sin importar el orden — su edge es consistente, no dependiente de cuando ocurrieron los ganadores.

**Detalles clave:**
- **No re-ejecuta backtests** — trabaja sobre el DataFrame de trades ya computados
- Acepta tanto `net_pnl` como `net_profit_loss` como nombre de columna (auto-detecta)
- El `p_value` indica que fraccion de permutaciones igualo o supero el equity final real
- Los `max_drawdowns` varian entre permutaciones — ahi esta el valor real del analisis
- Los `confidence_intervals` al 95% dan el rango esperado de equity final y max drawdown

```python
mc = MonteCarloValidator(runner.metrics.trade_metrics_df, initial_capital=1000)
result = mc.run(n_simulations=2000, seed=42)
# result.p_value → 0.62 (robusto)
# result.confidence_intervals['max_drawdown'] → (0.08, 0.25)
```

### walk_forward.py — `WalkForwardValidator`

**Que hace:** Divide los datos en N ventanas consecutivas. En cada ventana, una porcion es in-sample (para optimizar/ejecutar) y otra es out-of-sample (para validar). Mide si la estrategia y sus parametros se mantienen robustos al avanzar en el tiempo.

**Por que sirve:** El Grid Search puede encontrar parametros que funcionan en un periodo especifico pero fallan en otro. Walk-Forward simula lo que haria un trader real: optimizar con datos pasados y tradear en datos futuros, repetidamente.

**Dos modos de ventana:**
```
Rolling (anchored=False, default):
|---IS---|--OOS--|
         |---IS---|--OOS--|
                  |---IS---|--OOS--|

Anchored (anchored=True):
|---IS---|--OOS--|
|------IS------|--OOS--|
|----------IS---------|--OOS--|
```

**Dos modos de ejecucion:**
- **Parametros fijos** (`param_ranges=None`): ejecuta la estrategia con los mismos params en cada ventana. Mide si la estrategia se degrada con el tiempo.
- **Re-optimizacion** (`param_ranges={...}`): en cada ventana IS, corre el `ParameterOptimizer` para encontrar los mejores params, luego valida en OOS. Mide si la optimizacion es robusta.

**Metricas de salida:**
- `efficiency_ratio` = promedio OOS / promedio IS de la metrica objetivo. >0.5 = robusto, <0.3 = overfitting
- `param_stability` = coeficiente de variacion (CV = std/mean) de cada parametro optimizado entre ventanas. CV bajo = parametro estable, CV alto = parametro sensible al periodo (mala señal)

**Detalles clave:**
- La ultima ventana absorbe barras residuales para cubrir el 100% del dataset
- Usa `ParameterOptimizer` internamente (import lazy para evitar dependencia circular)
- `VALID_OPT_METRICS` excluye `'roi'` por un bug existente en el optimizer (clave `'ROI'` en mayusculas vs `'roi'` en minusculas)
- `_run_single_backtest` envuelve en try/except y retorna `{'error': msg}` si falla

```python
# Con re-optimizacion
wf = WalkForwardValidator(strategy_class=MiEstrategia, market_data=df, n_windows=5,
                          symbol='BTC', timeframe=Timeframe.M5, exchange='Binance')
result = wf.run(param_ranges={'lookback_period': [10, 15, 20, 25, 30]})
# result.efficiency_ratio → 0.65 (robusto)
# result.param_stability['lookback_period']['cv'] → 0.18 (estable)
```

### validation_suite.py — `ValidationSuite`

**Que hace:** Orquesta los 3 validadores en secuencia y produce un `ValidationReport` consolidado con diagnostico automatico.

**Orden de ejecucion:**
```
1. OOS Split      → backtest IS + backtest OOS (sobre datos partidos)
2. Monte Carlo    → backtest FULL → permutar trades (backtest independiente)
3. Walk-Forward   → N backtests IS + N backtests OOS (ventanas)
```

**Skip logic:** Cualquier validador se omite poniendo su parametro de control a 0:
- `oos_ratio=0` → skip OOS
- `mc_simulations=0` → skip Monte Carlo
- `wf_windows=0` → skip Walk-Forward

**Diagnostico automatico (`_generate_summary`):**
El summary evalua umbrales y genera una lista de `issues`:

| Validador | Condicion de alerta | Significado |
|-----------|--------------------|----|
| OOS | sharpe degrada > 50% | La estrategia no generaliza a datos nuevos |
| Monte Carlo | p-value < 0.2 | El equity depende del orden especifico de los trades |
| Walk-Forward | efficiency < 0.3 | Los parametros optimos no se mantienen en el tiempo |
| Walk-Forward | param CV > 0.5 | Los parametros cambian drasticamente entre ventanas |

`summary['is_robust'] = True` solo si no hay ninguna alerta.

```python
suite = ValidationSuite(strategy_class=MiEstrategia, market_data=df,
                        symbol='BTC', timeframe=Timeframe.M5, exchange='Binance')
report = suite.run_all(oos_ratio=0.3, mc_simulations=1000, wf_windows=5,
                       param_ranges={'lookback': [10, 15, 20, 25, 30]})

if report.summary['is_robust']:
    print("Estrategia robusta!")
else:
    for issue in report.summary['issues']:
        print(f"⚠ {issue}")
```

## Umbrales de robustez

| Validador | Metrica | Robusto | Marginal | Overfitting |
|-----------|---------|---------|----------|-------------|
| OOS | sharpe degradation | < 30% | 30-50% | > 50% |
| Monte Carlo | p-value | > 0.4 | 0.2-0.4 | < 0.2 |
| Walk-Forward | efficiency_ratio | > 0.5 | 0.3-0.5 | < 0.3 |
| Walk-Forward | param CV | < 0.3 | 0.3-0.5 | > 0.5 |

## Flujo de datos

```
                          strategy_class + market_data + params
                                         │
                    ┌────────────────────┼────────────────────┐
                    ▼                    ▼                    ▼
             OOSSplitValidator    MonteCarloValidator   WalkForwardValidator
                    │                    │                    │
              split IS/OOS        backtest FULL         N ventanas IS/OOS
              backtest × 2        permutar trades       [ParameterOptimizer]
                    │                    │               backtest × 2N
                    ▼                    ▼                    ▼
              OOSResult          MonteCarloResult      WalkForwardResult
                    │                    │                    │
                    └────────────────────┼────────────────────┘
                                         ▼
                              ValidationSuite._generate_summary()
                                         │
                                         ▼
                                  ValidationReport
                            {is_robust, issues, scores}
```

## Dependencias

```
OOSSplitValidator     → BacktestRunner (core)
MonteCarloValidator   → (ninguna — solo numpy)
WalkForwardValidator  → BacktestRunner + ParameterOptimizer (optimization)
ValidationSuite       → los 3 validadores + BacktestRunner (para MC trades)
```

## Notas tecnicas

- Todos los backtests suprimen stdout con `contextlib.redirect_stdout` (BaseStrategy imprime al instanciar con data inyectada)
- Monte Carlo asume trades independientes — si la estrategia tiene autocorrelacion fuerte (ej: DCA donde cada entrada depende de la anterior), el p-value pierde validez
- Walk-Forward no puede usar `optimization_metric='roi'` por un bug existente en `ParameterOptimizer` (clave `'ROI'` vs `'roi'`)
- Los 3 validadores retornan `{'error': msg}` en vez de crashear cuando un backtest individual falla (ej: 0 trades en una ventana)
