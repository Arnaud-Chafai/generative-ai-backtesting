# Modulo: data/loaders

Proveedores de datos OHLCV para el sistema de backtesting. Todos devuelven DataFrames con el formato estandar del proyecto:

- **Indice**: `DatetimeIndex` llamado `Time`
- **Columnas**: `Open`, `High`, `Low`, `Close`, `Volume`

## Providers disponibles

### CSVDataProvider
Carga datos desde archivos CSV locales en `data/raw_data/`.

```python
provider = CSVDataProvider(asset="BTCUSDT_5m")  # busca data/raw_data/BTCUSDT_5m.csv
df = provider.get_all_data()
```

- Normaliza nombres de columnas automaticamente (capitaliza)
- Parsea la columna `Time` como DatetimeIndex

### MT5BacktestDataProvider
Descarga datos historicos desde MetaTrader 5 (requiere MT5 instalado y conectado).

```python
provider = MT5BacktestDataProvider(symbol_list=["EURUSD"], timeframe=Timeframe.H1)
df = provider.get_batch_data_from_mt5("EURUSD", num_bars=5000)
```

- Requiere: `MetaTrader5` (pip install MetaTrader5)
- Solo funciona en Windows con MT5 corriendo
- Nota: `PlatformConnector` fue eliminado, la conexion MT5 necesita reimplementarse

### CcxtDataProvider
Descarga datos OHLCV desde exchanges crypto (Binance por defecto) usando ccxt. Pagina automaticamente en batches de 1000 velas.

```python
provider = CcxtDataProvider(symbol="BTC/USDT", timeframe="5m", start_date="2023-01-01")
df = provider.get_all_data()
provider.save_to_csv()  # guarda en data/raw_data/BTCUSDT_5m.csv
```

- Requiere: `ccxt` (pip install ccxt)
- Import lazy: no rompe los otros providers si ccxt no esta instalado
- Respeta rate limits del exchange automaticamente
- Timeframes soportados: `1m`, `3m`, `5m`, `15m`, `30m`, `1h`, `2h`, `4h`, `6h`, `8h`, `12h`, `1d`, `1w`, `1M`
- `save_to_csv()` genera archivos compatibles con `CSVDataProvider`

## Formato de salida comun

Todos los providers producen un DataFrame identico:

```
                          Open      High       Low     Close    Volume
Time
2023-01-01 00:00:00  16541.77  16545.00  16540.00  16542.40  123.456
2023-01-01 00:05:00  16542.40  16550.00  16538.00  16548.30   98.765
```

## Flujo tipico

```python
# Opcion 1: Descargar y guardar
provider = CcxtDataProvider(symbol="BTC/USDT", timeframe="5m", start_date="2024-01-01")
provider.save_to_csv()

# Opcion 2: Cargar desde CSV existente
provider = CSVDataProvider(asset="BTCUSDT_5m")
df = provider.get_all_data()

# Luego pasar a DataTransformer
from data.preparation.data_transformer import DataTransformer
transformer = DataTransformer(df)
```
