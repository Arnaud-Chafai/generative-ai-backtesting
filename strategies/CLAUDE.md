# Modulo: strategies

Estrategias de trading. Todas heredan de `BaseStrategy` e implementan `generate_simple_signals()`.

## base_strategy.py — `BaseStrategy`

Clase abstracta que provee:

### Parametros del constructor

| Parametro | Tipo | Descripcion |
|-----------|------|-------------|
| `market` | MarketType | CRYPTO o FUTURES |
| `symbol` | str | Activo (e.g., "BTC") |
| `strategy_name` | str | Nombre para logs y outputs |
| `timeframe` | Timeframe | Timeframe de la data |
| `exchange` | str (opcional) | Exchange (e.g., "Binance") |
| `initial_capital` | float | Capital inicial (default: 1000) |
| `data` | DataFrame (opcional) | Datos inyectados. Si None, carga de disco |

### Carga de datos

Dos modos:
1. **Inyectado**: pasar `data=df` (usado por el optimizador, ~200x mas rapido)
2. **Disco**: busca automaticamente en `data/laboratory_data/{symbol}/Timeframe.{timeframe}.csv`

### Metodo a implementar

```python
def generate_simple_signals(self) -> List[TradingSignal]:
    """Debe retornar lista de TradingSignal con las señales BUY/SELL."""
```

### Helper disponible

```python
self.create_simple_signal(
    signal_type=SignalType.BUY,
    timestamp=df.index[i],
    price=df['Close'].iloc[i],
    position_size_pct=0.5  # 50% del capital
)
```
Crea un `TradingSignal` y lo agrega automaticamente a `self.simple_signals`.

### Atributos utiles dentro de la estrategia

- `self.market_data` — DataFrame OHLCV con DatetimeIndex
- `self.symbol`, `self.timeframe`, `self.exchange`
- `self.initial_capital`
- `self.slippage_value` — valor de slippage del mercado

## Como crear una nueva estrategia

```python
from strategies.base_strategy import BaseStrategy
from models.enums import SignalType, MarketType
from utils.timeframe import Timeframe

class MiEstrategia(BaseStrategy):
    def __init__(self, mi_parametro: int = 20, **kwargs):
        super().__init__(
            market=MarketType.CRYPTO,
            symbol=kwargs.get('symbol', 'BTC'),
            strategy_name="Mi_Estrategia",
            timeframe=kwargs.get('timeframe', Timeframe.H1),
            exchange=kwargs.get('exchange', 'Binance'),
            **kwargs
        )
        self.mi_parametro = mi_parametro

    def generate_simple_signals(self):
        signals = []
        df = self.market_data

        for i in range(self.mi_parametro, len(df)):
            if condicion_compra:
                signals.append(self.create_simple_signal(
                    SignalType.BUY, df.index[i], df['Close'].iloc[i], 0.5
                ))
            elif condicion_venta:
                signals.append(self.create_simple_signal(
                    SignalType.SELL, df.index[i], df['Close'].iloc[i], 1.0
                ))

        return signals
```

**Importante:** Usar `**kwargs` en el `__init__` para que el optimizador pueda inyectar `data=`, `initial_capital=`, etc.

## examples/

Estrategias de ejemplo funcionales:
- `breakout_simple.py` — Breakout de maximos/minimos de N periodos
- `ma_crossover_simple.py` — Cruce de medias moviles

## Ejecucion

```python
strategy = MiEstrategia(mi_parametro=30, symbol='BTC', exchange='Binance')
runner = BacktestRunner(strategy)
runner.run()
runner.print_summary()
```
