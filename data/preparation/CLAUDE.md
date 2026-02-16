# Modulo: data/preparation

Pipeline de limpieza y transformacion de datos OHLCV. Recibe DataFrames crudos de los loaders y produce DataFrames enriquecidos listos para estrategias.

## Archivos

### data_cleaner.py — `DataCleaner`
Validacion y limpieza basica del DataFrame crudo.

```python
cleaner = DataCleaner(csv_provider=provider)
df = cleaner.clean_csv_data()  # o clean_data(df) directamente
```

**Pipeline de `clean_data()`:**
1. `validate_index()` — verifica que el indice sea `DatetimeIndex`
2. `validate_columns()` — verifica que existan `Open`, `High`, `Low`, `Close`, `Volume`
3. `fill_missing_values()` — rellena NaN con ffill + bfill (lanza error si el indice tiene nulos)

### data_transformer.py — `DataTransformer`
Enriquecimiento del DataFrame con indicadores, features temporales, sesiones y patrones.

```python
transformer = DataTransformer(df)
enriched = (
    transformer
    .convert_to_heiken_ashi()
    .calculate_ema([20, 50, 200])
    .add_temporal_features()
    .add_session_flags()
    .add_session_extremes()
    .add_periodic_high_low()
    .transform()
)
```

**Metodos principales:**

| Metodo | Columnas que genera |
|--------|-------------------|
| `convert_to_heiken_ashi()` | Reemplaza Open/High/Low/Close con Heiken Ashi |
| `calculate_ema(periods)` | `EMA_{n}` por cada periodo |
| `calculate_volatility_pct_change(periods)` | `Volatility_pct_change_{n}` |
| `calculate_pct_change(periods)` | `Pct_change_{n}` |
| `volume_pct_change(periods)` | `Volume_pct_change_{n}` |
| `calculate_cumulative_volume_pct(periods)` | `Cumulative_Volume_pct_{n}` |
| `calculate_vwap()` | `VWAP` |
| `add_temporal_features()` | `Hour`, `Minute`, `Day`, `Month`, `Trimester`, `Year` |
| `add_session_flags()` | `Asian_session`, `European_session`, `American_session` |
| `add_session_extremes()` | `Max/Min_asian/european/american_session` |
| `add_periodic_high_low()` | `Daily/Weekly/Monthly_high/low_before` |
| `clean_sessions()` | Elimina filas sin datos en las 6 columnas de extremos de sesion |
| `detectar_onebar_pullback_alcista()` | `OBP_alcista` |
| `detectar_onebar_pullback_bajista()` | `OBP_bajista` |
| `detectar_onebar_pullback_alcista_extendido(n)` | `OBP_alcista_extend` |
| `detectar_onebar_pullback_bajista_extendido(n)` | `OBP_bajista_extend` |

**Metodo all-in-one:**

`prepare_data()` ejecuta todo el pipeline completo (resample + todos los indicadores + patrones) para multiples timeframes y devuelve un `dict[timeframe, DataFrame]`.

**Otros:**
- `resample_data(timeframe)` / `resample_timeframes(list)` — resampling OHLCV
- `export_dataframes_to_csv(dict, dir)` — exporta diccionario de DataFrames a CSVs
- `transform()` — devuelve `self.df` (usado al final de la cadena)

## Flujo tipico

```python
# 1. Cargar
provider = CSVDataProvider(asset="BTCUSDT_5m")

# 2. Limpiar
cleaner = DataCleaner(csv_provider=provider)
df = cleaner.clean_csv_data()

# 3. Transformar
transformer = DataTransformer(df)
data = transformer.prepare_data(
    timeframes=[Timeframe.M5, Timeframe.H1],
    ema_periods=[20, 50, 200],
    volatility_periods=[20],
    pct_change_periods=[1, 5],
    volume_periods=[1, 5],
    cumulative_volume_periods=[20],
    obp_range=10
)
# data[Timeframe.M5] → DataFrame enriquecido
```

## Horarios de sesiones

- **Asiatica**: 00:00 — 08:59
- **Europea**: 09:00 — 15:29
- **Americana**: 15:30 — 23:59
