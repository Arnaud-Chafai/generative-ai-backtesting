# Modulo: utils

Utilidades compartidas por todo el framework.

## timeframe.py

Contiene tres cosas distintas:

### `Timeframe` (enum)
Enum con los timeframes estandar del framework. Usado en practicamente todos los modulos.

```python
from utils.timeframe import Timeframe

tf = Timeframe.H1
tf.value    # "1h"
tf.hours    # 1.0
tf.name     # "H1"
```

**Valores disponibles:**

| Enum | Value | Hours |
|------|-------|-------|
| M1 | "1min" | 0.017 |
| M5 | "5min" | 0.083 |
| M15 | "15min" | 0.25 |
| M30 | "30min" | 0.5 |
| H1 | "1h" | 1.0 |
| H4 | "4h" | 4.0 |
| D1 | "1d" | 24.0 |
| W1 | "1w" | 168.0 |
| MN1 | "1M" | 720.0 |

**Metodos:**
- `.hours` — property que retorna duracion en horas
- `Timeframe.to_mt5(tf)` — convierte a constante de MetaTrader 5
- `Timeframe.from_string("1h")` — convierte string a enum

### `prepare_datetime_data(df)` (funcion)
Agrega columnas temporales a un DataFrame de trades: `hour`, `day_of_week`, `day`, `month`, `year`, `quarter`, `week`. Busca automaticamente la columna de timestamp (entry_datetime, entry_timestamp, etc.)

Usado por: `TradeMetricsCalculator`

### Constantes
- `DAYS_ORDER` — `["Monday", "Tuesday", ..., "Sunday"]`
- `MONTHS_ORDER` — `["January", "February", ..., "December"]`
- `MONTHS_ABBR` — `["Jan", "Feb", ..., "Dec"]`

Usadas por: dashboards (temporal_heatmaps, week_month_barchart)

## Nota arquitectonica
`Timeframe` es conceptualmente un enum de dominio (como `SignalType`) y podria vivir en `models/enums.py`. Se mantiene aqui porque moverlo tocaria 10+ archivos sin beneficio funcional.
