# Modulo: tests

Tests unitarios del proyecto. Se ejecutan con `pytest`.

```bash
pytest tests/                    # todos los tests
pytest tests/test_optimizer.py   # solo un archivo
pytest tests/ -v                 # verbose (ver cada test)
```

## Archivos

### test_breakout_strategy.py
Tests de la estrategia BreakoutSimple: generacion de señales, parametros, ejecucion del backtest.

### test_optimizer.py
Tests del ParameterOptimizer: grid search, validacion de parametros, filtro min_trades, export CSV.

## Convencion

- Archivos: `test_{modulo}.py`
- Funciones: `test_{que_testea}()`
- Usar `pytest` (no unittest)

## Cobertura actual

| Modulo | Tests | Estado |
|--------|-------|--------|
| optimization/ | test_optimizer.py | ✅ |
| strategies/examples/ | test_breakout_strategy.py | ✅ |
| core/ | — | ❌ sin tests |
| metrics/ | — | ❌ sin tests |
| data/ | — | ❌ sin tests |
