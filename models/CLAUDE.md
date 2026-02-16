# Modulo: models

Tipos de datos del dominio de trading: enums y señales.

## Archivos

### enums.py
Todos los enums del sistema. Los mas usados actualmente:

- **`SignalType`**: `BUY`, `SELL` — usado por TradingSignal y BacktestEngine
- **`MarketType`**: `CRYPTO`, `FUTURES`, `STOCKS` — usado por CryptoMarketDefinition

Otros enums definidos pero con uso limitado al backtest actual:
- `OrderType`: MARKET, LIMIT, STOP, STOP_LIMIT (pensado para live trading futuro)
- `CurrencyType`: USD, EUR, USDT
- `ExchangeName`: Binance, Kucoin
- `SignalStatus`: PENDING, EXECUTED, CANCELLED (pensado para live trading)
- `SignalPositionSide`: LONG, SHORT

### simple_signals.py — `TradingSignal`
Dataclass que representa una decision de trading. Es la interfaz entre las estrategias y el motor.

```python
signal = TradingSignal(
    timestamp=df.index[100],
    signal_type=SignalType.BUY,
    symbol="BTC",
    price=df['Close'].iloc[100],
    position_size_pct=0.10  # 10% del capital
)
```

**Campos:**
- `timestamp`: momento de la señal (del indice del DataFrame)
- `signal_type`: BUY o SELL
- `symbol`: activo (e.g., "BTC")
- `price`: precio de referencia (Close del candle)
- `position_size_pct`: fraccion del capital (0.1 = 10%)

**Validaciones en `__post_init__`:**
- `price > 0`
- `0 < position_size_pct <= 1`

## Quien usa que

```
strategies/     → importa TradingSignal, SignalType
core/engine     → importa TradingSignal, SignalType
core/runner     → importa get_crypto_config (directamente, no usa markets/)
metrics/        → importa SignalPositionSide (indirectamente via position_side string)
```
