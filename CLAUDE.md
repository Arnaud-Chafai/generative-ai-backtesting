## Backtesting Framework - Estado del Proyecto

**Ultima actualizacion**: Febrero 2026

## Arquitectura

```
backtesting/
├── core/                    Motor de backtest + orquestador
├── models/                  Enums y señales de trading (TradingSignal)
├── config/
│   ├── market_configs/      Datos estaticos de mercados (fees, slippage)
│   └── markets/             Clases Pydantic de mercados
├── data/
│   ├── loaders/             Providers de datos (CSV, MT5, ccxt/Binance)
│   └── preparation/         Limpieza y transformacion de datos
├── metrics/                 Metricas por trade y portfolio
├── strategies/              BaseStrategy + ejemplos
├── optimization/            Optimizacion de parametros (Grid Search)
├── visualization/
│   ├── chart_plotter.py     Charts de velas (estatico + interactivo)
│   ├── dashboard_manager.py Coordinador de dashboards
│   └── dashboards/          10 dashboards de analisis
├── utils/                   Timeframe enum + utilidades temporales
├── tests/                   Tests unitarios (pytest)
└── notebooks/               Notebooks de ejemplo
```

## Documentacion por modulo

Cada modulo tiene su propio CLAUDE.md con detalle completo:

| Modulo | Doc | Contenido principal |
|--------|-----|-------------------|
| [core/](core/CLAUDE.md) | BacktestEngine, BacktestRunner | Motor de ejecucion y orquestador |
| [models/](models/CLAUDE.md) | SignalType, TradingSignal | Enums y señales de dominio |
| [config/market_configs/](config/market_configs/CLAUDE.md) | CRYPTO_CONFIG, FUTURES_CONFIG | Fees, slippage, tick_size por exchange |
| [data/loaders/](data/loaders/CLAUDE.md) | CSVDataProvider, CcxtDataProvider | Carga de datos (CSV, MT5, Binance) |
| [data/preparation/](data/preparation/CLAUDE.md) | DataCleaner, DataTransformer | Limpieza y enriquecimiento de datos |
| [metrics/](metrics/CLAUDE.md) | TradeMetrics, BacktestMetrics | MAE, MFE, Sharpe, drawdown, etc. |
| [strategies/](strategies/CLAUDE.md) | BaseStrategy | Como crear estrategias nuevas |
| [optimization/](optimization/CLAUDE.md) | ParameterOptimizer | Grid Search + visualizacion 3D |
| [visualization/](visualization/CLAUDE.md) | Charts + dashboards | Graficos de velas y 10 dashboards |
| [visualization/dashboards/](visualization/dashboards/CLAUDE.md) | 10 dashboards | Detalle de cada dashboard |
| [utils/](utils/CLAUDE.md) | Timeframe | Enum de timeframes + constantes |
| [tests/](tests/CLAUDE.md) | pytest | Tests existentes y cobertura |

## Flujo principal

```python
# 1. Cargar datos
from data.loaders.data_provider import CcxtDataProvider
provider = CcxtDataProvider(symbol="BTC/USDT", timeframe="5m", start_date="2024-01-01")
provider.save_to_csv()

# 2. Crear estrategia
strategy = BreakoutSimple(symbol='BTC', exchange='Binance', timeframe=Timeframe.M5)

# 3. Ejecutar backtest
runner = BacktestRunner(strategy)
runner.run()
runner.print_summary()

# 4. Visualizar
runner.plot_trades()       # chart de velas interactivo
runner.plot_dashboards()   # 10 dashboards de analisis

# 5. Optimizar
optimizer = ParameterOptimizer(strategy_class=BreakoutSimple, market_data=df, symbol='BTC')
results = optimizer.optimize(param_ranges={...}, metric='sharpe_ratio')
```

## Fases completadas

| Fase | Descripcion | Estado |
|------|-------------|--------|
| 1-2 | Motor de backtest + metricas | ✅ |
| 3 | Visualizacion (10 dashboards + charts) | ✅ |
| 4a | Grid Search optimizer + viz 3D | ✅ |

## Roadmap

| Fase | Descripcion | Prioridad |
|------|-------------|-----------|
| 4b | Random Search + Bayesian optimization | Alta |
| 4c | Walk-Forward testing | Media |
| 4d | Multiprocessing | Baja |
| 5 | Mas estrategias (RSI, Bollinger, etc.) | Media |
| 6 | Comparador de estrategias | Media |
| 7 | Live Trading Bridge | Futuro |

## Documentacion adicional

- [docs/FASE3_RESUMEN.md](docs/FASE3_RESUMEN.md) — Visualizacion completada
- [docs/FASE4_RESUMEN.md](docs/FASE4_RESUMEN.md) — Parameter Optimizer v1.0
- [docs/OPTIMIZER_GUIDE.md](docs/OPTIMIZER_GUIDE.md) — Guia completa del optimizador

## Notas tecnicas

- Solo soporta posiciones LONG actualmente
- `BacktestRunner` hardcodea `get_crypto_config()` (solo crypto)
- `futures_config.py` existe pero no tiene consumidor activo
- `Timeframe` enum vive en `utils/` (conceptualmente es un enum de dominio)
- `set_style()` esta duplicada en 3 archivos de dashboards
