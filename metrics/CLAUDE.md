# Modulo: metrics

Calculo de metricas de backtest a dos niveles: por trade individual y a nivel portfolio. El `MetricsAggregator` coordina ambos.

## Archivos

### trade_metrics.py — `TradeMetricsCalculator`
Enriquece cada trade con metricas individuales. Recibe el DataFrame del motor y devuelve uno con columnas adicionales.

```python
calculator = TradeMetricsCalculator(
    initial_capital=1000,
    market_data=df_ohlcv,
    timeframe=Timeframe.M5
)
df_enriched = calculator.create_trade_metrics_df(trade_data)
```

**Columnas que genera:**
| Columna | Descripcion |
|---------|-------------|
| `duration_bars` | Duracion del trade en barras del timeframe |
| `bars_in_loss` / `bars_in_profit` | Barras en perdida/ganancia durante el trade |
| `MAE` | Maximum Adverse Excursion (peor momento del trade en USDT) |
| `MFE` | Maximum Favorable Excursion (mejor momento del trade en USDT) |
| `trade_volatility` | Volatilidad del precio durante el trade (%) |
| `profit_efficiency` | Cuanto del MFE se capturo como ganancia (0-100%) |
| `trade_drawdown` | Drawdown del trade individual (%) |
| `risk_reward_ratio` | MFE / MAE |
| `riesgo_aplicado` | % del capital arriesgado |
| `return_on_capital` | % de retorno sobre capital disponible |
| `cumulative_capital` | Capital acumulado despues del trade |

**Pipeline interno de `create_trade_metrics_df()`:**
1. `_prepare_data()` — parsea timestamps, normaliza position_side
2. `prepare_datetime_data()` — agrega columnas temporales (de utils)
3. `_add_duration_bars()` — duracion en barras
4. `_add_time_in_profit_loss()` — barras en ganancia/perdida
5. `_add_mae_mfe_volatility_efficiency()` — MAE, MFE, volatilidad, eficiencia
6. `_add_trade_drawdown()` — drawdown por trade
7. `_add_risk_reward_ratio()` — risk/reward
8. `_add_risk_management_metrics()` — riesgo, retorno, capital acumulado

### portfolio_metrics.py — `BacktestMetrics`
Metricas agregadas a nivel portfolio. Recibe el DataFrame enriquecido por `TradeMetricsCalculator`.

```python
metrics = BacktestMetrics(trade_data=df_enriched, initial_capital=1000)
all_metrics = metrics.compute_all_metrics()
```

**Secciones de metricas:**

| Metodo | Metricas clave |
|--------|---------------|
| `compute_general_summary()` | gross/net profit, ROI, total_trades, percent_profitable, profit_factor, win_loss_ratio, expectancy |
| `compute_profit_loss_analysis()` | avg/largest winning/losing trade, max consecutive wins/losses, rachas, std_profit |
| `compute_drawdown_analysis()` | max_drawdown, max_drawdown_pct, drawdown_duration, avg_drawdown |
| `compute_time_statistics()` | backtest_duration, time_in_market_pct, trades_per_day, avg duraciones en min y barras |
| `compute_performance_ratios()` | sharpe_ratio, sortino_ratio, recovery_factor |
| `compute_operational_costs()` | total_fees, total_slippage_cost, avg_fee_per_trade, fees_pct_of_capital |

### metrics_aggregator.py — `MetricsAggregator`
Orquestador que conecta el motor con ambos calculadores. Es la interfaz que usa `BacktestRunner`.

```python
aggregator = MetricsAggregator(results=engine_results, strategy=strategy)
aggregator.print_summary()
aggregator.save_results('outputs/')
```

**Acceso a resultados:**
- `aggregator.trade_metrics_df` — DataFrame con metricas por trade
- `aggregator.all_metrics` — dict con todas las metricas de portfolio
- `aggregator.portfolio_summary_df` — all_metrics como DataFrame de 1 fila
- `aggregator.print_summary(sections=['general', 'pnl', 'drawdown', 'ratios', 'time', 'costs'])`

**Adaptadores internos:**
El aggregator convierte nombres de columnas entre el motor y los calculadores:
- Motor usa: `entry_time`, `exit_time`, `avg_entry_price`, `total_cost`, `net_pnl`
- TradeMetrics espera: `entry_timestamp`, `exit_timestamp`, `entry_price`, `usdt_amount`, `net_profit_loss`

## Flujo de datos

```
BacktestEngine.run()
    │ DataFrame con trades crudos
    ▼
MetricsAggregator
    ├── _adapt_for_trade_metrics() → renombra columnas
    ├── TradeMetricsCalculator.create_trade_metrics_df() → enriquece cada trade
    ├── _adapt_for_portfolio_metrics() → renombra de vuelta
    └── BacktestMetrics.compute_all_metrics() → metricas agregadas
```

## Nota
Actualmente solo soporta posiciones LONG. El campo `position_side` se hardcodea a "LONG" en el aggregator.
