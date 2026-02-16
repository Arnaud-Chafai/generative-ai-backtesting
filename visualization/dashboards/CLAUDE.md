# Modulo: visualization/dashboards

10 dashboards de analisis de resultados de backtest. Se coordinan desde `dashboard_manager.py` (un nivel arriba).

## Archivos y sus dashboards

### performance_dashboard.py — `visualize_performance(strategy, df_trade_metrics)`
Dashboard general: equity curve, distribucion de P&L, win rate, metricas clave.
- Requiere: `strategy`

### temporal_heatmaps.py — `visualize_temporal_heatmap(strategy, df_trade_metrics)`
Dos heatmaps:
1. Metrica vs Hora y Dia de la semana
2. Metrica vs Dia del mes y Mes
- Requiere: `strategy`
- Usa: `DAYS_ORDER`, `MONTHS_ORDER` de `utils/timeframe`

### metrics_distribution.py — `visualize_metrics_distribution(strategy, df_trade_metrics)`
Histogramas de distribucion de metricas principales (P&L, MAE, MFE, etc.)
- Requiere: `strategy`

### metrics_boxplot.py — `visualize_metrics_boxplot(strategy, df_trade_metrics)`
Boxplots de 6 metricas: MAE, MFE, profit_efficiency, risk_reward_ratio, trade_volatility, duration_bars. Separados por trade ganador/perdedor.
- Requiere: `strategy`

### scatter_metrics.py — 5 funciones de scatter plots
Cada una genera 4 scatter plots (2x2) con linea de regresion:

| Funcion | Eje X principal | Subplots |
|---------|----------------|----------|
| `visualize_metrics_vs_mae()` | MAE | vs MFE, risk_reward, profit_efficiency, volatility |
| `visualize_metrics_vs_mfe()` | MFE | vs MAE, risk_reward, profit_efficiency, volatility |
| `visualize_metrics_vs_risk_reward()` | risk_reward | vs MAE, MFE, profit_efficiency, volatility |
| `visualize_metrics_vs_volatility()` | volatility | vs MAE, MFE, risk_reward, profit_efficiency |
| `visualize_metrics_vs_profit_efficiency()` | profit_efficiency | vs MAE, MFE, risk_reward, volatility |

- NO requieren `strategy` (solo `df_trade_metrics`)

### week_month_barchart.py — `time_chart(df_trade_metrics)`
Barras de P&L agrupadas por año, mes y dia de la semana. 3 paneles verticales.
- NO requiere `strategy`
- Usa: `DAYS_ORDER`, `MONTHS_ORDER` de `utils/timeframe`

## Como se invocan

Desde `BacktestRunner`:

```python
# Todos los dashboards
runner.plot_dashboards()

# Solo algunos
runner.plot_dashboards(modules=['performance', 'mae_scatter', 'time_chart'])
```

El `dashboard_manager.py` coordina via `MODULE_ORDER` y `MODULE_FUNCTIONS`.

## Modulos disponibles (nombres para el parametro `modules`)

```
performance, time_chart, temporal, metrics_distribution,
metrics_boxplot, mae_scatter, mfe_scatter, risk_reward_scatter,
volatility_scatter, profit_efficiency_scatter
```

## Estilo visual

Todos comparten paleta de colores consistente:
- Profit: `#006D77` (verde azulado)
- Loss: `#E29578` (salmon)
- Text: `#333333`
- Fondo: `#f5f5f5` (gris claro)

Nota: `set_style()` esta duplicada en varios archivos (performance, temporal, distribution). No es un problema funcional pero es codigo repetido.
