# Modulo: core

Motor de backtest y orquestador. Es el corazon del sistema.

## Archivos

### simple_backtest_engine.py — Motor de ejecucion

Contiene 3 clases que forman el motor:

**`Entry`** (dataclass) — Una compra individual dentro de una posicion.
- `price`: precio real (con slippage aplicado)
- `size_usdt`: capital usado
- `fee`, `slippage_cost`: costos de esta entrada

**`Position`** — Posicion abierta que puede tener multiples entradas (DCA/promediado).
- `add_entry()`: agrega una compra mas
- `total_cost()`, `total_crypto()`, `average_entry_price()`: calculos agregados
- `total_fees_on_entries()`, `total_slippage_on_entries()`: costos acumulados

**`BacktestEngine`** — Motor principal. Procesa señales BUY/SELL en orden cronologico.

```python
engine = BacktestEngine(initial_capital=1000.0, market_config=config)
df_results = engine.run(signals)  # lista de TradingSignal
```

- `_handle_buy()`: abre posicion nueva o agrega entrada (promediado)
- `_handle_sell()`: cierra posicion completa, calcula P&L
- `_apply_slippage_to_price()`: simula deslizamiento, redondea a tick_size
- Retorna DataFrame con columnas: symbol, entry/exit_time, avg_entry_price, exit_price, total_cost, exit_value, fees, slippage, gross_pnl, net_pnl, capital_after, pnl_pct

### backtest_runner.py — Orquestador

**`BacktestRunner`** — Interfaz principal para el usuario. Conecta estrategia → motor → metricas → visualizacion.

```python
runner = BacktestRunner(strategy)
runner.run()
runner.print_summary()
runner.plot_trades()
runner.plot_dashboards()
```

**Flujo de `run()`:**
1. `strategy.generate_simple_signals()` → lista de TradingSignal
2. `get_crypto_config()` o `get_futures_config()` segun `strategy.market`
3. `BacktestEngine.run(signals)` → DataFrame de trades
4. `MetricsAggregator(results, strategy)` → metricas completas

**Metodos de visualizacion:**
- `plot_trades(interactive=True)` — chart de velas con marcadores de entrada/salida
- `plot_trades(interactive=False)` — graficos estaticos con mplfinance
- `plot_dashboards(modules=None)` — 10 dashboards de analisis
- `get_visualizer()` — acceso directo al visualizador

**Acceso a resultados:**
- `runner.results` → DataFrame crudo del motor
- `runner.metrics.trade_metrics_df` → metricas por trade
- `runner.metrics.all_metrics` → todas las metricas agregadas

## Dependencias

```
BacktestRunner
├── BacktestEngine (core)
├── MetricsAggregator (metrics)
├── get_crypto_config / get_futures_config (config) — dispatch por market type
├── BacktestVisualizer (visualization) — lazy import
└── create_dashboard (visualization) — lazy import
```

## Multi-mercado

El runner despacha la config segun `strategy.market`:
- `MarketType.CRYPTO` → `get_crypto_config()` (fees ratio, slippage porcentual)
- `MarketType.FUTURES` → `get_futures_config()` (fees fijos USD, slippage en ticks)

El engine detecta automaticamente si usar costos fijos o porcentuales via las keys `slippage_ticks` y `fee_fixed` en el config dict.
