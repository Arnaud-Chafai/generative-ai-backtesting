# Spec: Soporte de posiciones SHORT

## Resumen

Extender el framework de backtesting para soportar posiciones SHORT (bajistas) en todos los mercados (Crypto + Futuros CME). Una posicion a la vez, cierre explicito (sin flip automatico), reutilizando BUY/SELL con un nuevo campo `position_side`.

## Decisiones de diseno

| Decision | Eleccion |
|----------|----------|
| Mercados | Ambos (Crypto + Futuros) |
| Posiciones simultaneas | No, una a la vez |
| Transicion de direccion | Cierre explicito, sin flip |
| Senales | Reusar BUY/SELL + `position_side` |
| Visualizacion | Fase 2 posterior (solo datos en esta fase) |
| Enfoque de engine | Signal routing por `signal_type + position_side` |

## Alcance

**Fase 1 (esta spec):** Signal model, engine, metricas, backward compatibility, tests.
**Fase 2 (futura):** Visualizacion de markers SHORT en charts y dashboards.

---

## 1. TradingSignal — Nuevo campo `position_side`

**Archivo:** `models/simple_signals.py`

Anadir `position_side` al dataclass con default LONG para backward compatibility:

```python
from models.enums import SignalPositionSide

@dataclass
class TradingSignal:
    timestamp: datetime
    signal_type: SignalType              # BUY o SELL
    symbol: str
    price: float
    position_size_pct: float
    position_side: SignalPositionSide = SignalPositionSide.LONG  # NUEVO
    stop_loss_price: Optional[float] = None
    contracts: Optional[int] = None
```

**Backward compatibility:** Todas las estrategias existentes que no pasan `position_side` obtienen LONG automaticamente. Cero cambios requeridos en estrategias existentes.

**Nota:** `SignalPositionSide` ya existe en `models/enums.py` con valores `LONG` y `SHORT`. No requiere cambios.

---

## 2. BaseStrategy — Parametro `position_side` en helper

**Archivo:** `strategies/base_strategy.py`

Anadir parametro al helper `create_simple_signal()`:

```python
def create_simple_signal(
    self,
    signal_type: SignalType,
    timestamp: datetime,
    price: float,
    position_size_pct: float,
    position_side: SignalPositionSide = SignalPositionSide.LONG,  # NUEVO
    stop_loss_price: float = None,
    contracts: int = None,
) -> TradingSignal:
```

Pasar `position_side` al constructor de `TradingSignal`.

**Ejemplo de uso para SHORT:**

```python
# Abrir SHORT: vender para entrar
self.create_simple_signal(
    signal_type=SignalType.SELL,
    price=df['Close'].iloc[i],
    position_side=SignalPositionSide.SHORT,
    timestamp=df.index[i],
    position_size_pct=1.0,
)

# Cerrar SHORT: comprar para cubrir
self.create_simple_signal(
    signal_type=SignalType.BUY,
    price=df['Close'].iloc[i],
    position_side=SignalPositionSide.SHORT,
    timestamp=df.index[i],
    position_size_pct=1.0,
)
```

---

## 3. BacktestEngine — Signal routing y P&L

**Archivo:** `core/simple_backtest_engine.py`

### 3.1 Routing de senales

Reemplazar la logica actual BUY→`_handle_buy` / SELL→`_handle_sell` por routing basado en `signal_type + position_side`:

```python
def _is_entry(self, signal) -> bool:
    """BUY+LONG = entry, SELL+SHORT = entry."""
    return (
        (signal.position_side == SignalPositionSide.LONG and signal.signal_type == SignalType.BUY) or
        (signal.position_side == SignalPositionSide.SHORT and signal.signal_type == SignalType.SELL)
    )

def _is_exit(self, signal) -> bool:
    """SELL+LONG = exit, BUY+SHORT = exit."""
    return (
        (signal.position_side == SignalPositionSide.LONG and signal.signal_type == SignalType.SELL) or
        (signal.position_side == SignalPositionSide.SHORT and signal.signal_type == SignalType.BUY)
    )
```

**Tabla de routing completa:**

| signal_type | position_side | Accion del engine |
|-------------|---------------|-------------------|
| BUY | LONG | Abre/amplia posicion LONG |
| SELL | LONG | Cierra posicion LONG |
| SELL | SHORT | Abre/amplia posicion SHORT |
| BUY | SHORT | Cierra posicion SHORT |

En el loop de `run()`:

```python
for signal in signals:
    if self._is_entry(signal):
        self._open_position(signal)     # renombrar de _handle_buy
    elif self._is_exit(signal):
        self._close_position(signal)    # renombrar de _handle_sell
```

### 3.2 Renombrar metodos internos

| Antes | Despues | Logica |
|-------|---------|--------|
| `_handle_buy(signal)` | `_open_position(signal)` | Abrir o ampliar posicion (DCA) |
| `_handle_sell(signal)` | `_close_position(signal)` | Cerrar total o parcial |

La logica interna de cada metodo permanece casi igual. Los cambios son:
1. `_open_position` guarda `position_side` en la posicion
2. `_close_position` usa `position_side` para calcular P&L

### 3.3 Position — tracking de direccion

La clase `Position` (interna del engine) gana un campo:

```python
class Position:
    def __init__(self):
        self.entries: list[Entry] = []
        self.position_side: SignalPositionSide = None  # enum, se setea al primer entry
```

**Nota sobre tipos:** `Position.position_side` almacena el **enum** `SignalPositionSide`, no un string. Solo se convierte a string (`.value`) al crear el dict de completed trades. Las comparaciones internas usan el enum directamente.

En `_open_position`:

```python
def _open_position(self, signal):
    if self.current_position is None:
        self.current_position = Position()
        self.current_position.position_side = signal.position_side
    else:
        # DCA: verificar misma direccion
        if self.current_position.position_side != signal.position_side:
            if self.verbose:
                print(f"  Warning: ignoring {signal.signal_type.value} signal — "
                      f"position is {self.current_position.position_side}")
            return
    # ... resto de la logica de entrada (igual que _handle_buy actual)
```

### 3.4 Validacion de coherencia en exit

```python
def _close_position(self, signal):
    if self.current_position is None:
        return  # ignorar exit sin posicion abierta (ya existe)
    if self.current_position.position_side != signal.position_side.value:
        return  # ignorar exit de direccion diferente
    # ... resto de la logica de cierre
```

### 3.5 Capital management para SHORT crypto

**El problema:** En LONG, el trader gasta USDT para comprar crypto. En SHORT, el trader vende crypto prestado y recibe USDT, pero tiene la obligacion de recomprar. ¿Como modelamos el capital?

**Solucion: margen simetrico.** El engine trata SHORT como un bloqueo de capital equivalente al notional de la posicion. El trader "gasta" la misma cantidad que en LONG (como colateral/margen), y al cerrar se calcula el P&L invertido.

```python
# _open_position — IGUAL para LONG y SHORT:
entry_size_usdt = self.capital * signal.position_size_pct
self.capital -= (entry_size_usdt + entry_fee + slippage_cost)
# El entry_size_usdt queda registrado como total_cost del Entry
```

**Al cerrar:**

```python
# LONG: exit_value = cantidad_crypto * exit_price
# SHORT: exit_value se calcula igual (es el valor de mercado al cerrar)
# La diferencia esta SOLO en el signo del P&L (ver seccion 3.6)
```

**Esto significa que:**
- `Entry.size_usdt` = capital comprometido (colateral), igual para ambas direcciones
- `Position.total_cost()` = suma de entries, semantica de "capital en riesgo"
- `pnl_pct = net_pnl / closed_cost * 100` funciona correctamente: retorno sobre capital comprometido

**Futuros:** No tienen este problema — el engine ya no resta capital por el notional (solo por fees). El P&L se calcula por diferencia de precios * contratos * point_value.

### 3.6 P&L — inversion para SHORT

**Crypto:**

```python
# En _close_position, al calcular P&L:
if self.current_position.position_side == SignalPositionSide.LONG:
    gross_pnl = exit_value - closed_cost
else:
    gross_pnl = closed_cost - exit_value
```

**Futuros:**

```python
if self.current_position.position_side == SignalPositionSide.LONG:
    gross_pnl = closed_contracts * self.point_value * (real_price - avg_entry)
else:
    gross_pnl = closed_contracts * self.point_value * (avg_entry - real_price)
```

### 3.6 Slippage — siempre en contra del trader

La regla: el slippage siempre empeora tu precio.

```python
def _apply_slippage_to_price(self, price, signal):
    """Apply slippage — always against the trader."""
    is_entry = self._is_entry(signal)

    # Determinar si el precio sube o baja por slippage
    # Entry LONG o Exit SHORT → precio sube (pagas mas / recompras mas caro)
    # Entry SHORT o Exit LONG → precio baja (recibes menos)
    price_goes_up = (
        (is_entry and signal.position_side == SignalPositionSide.LONG) or
        (not is_entry and signal.position_side == SignalPositionSide.SHORT)
    )

    if price_goes_up:
        return price + slippage_amount
    else:
        return price - slippage_amount
```

Esto reemplaza el parametro `is_buy` actual por la logica direction-aware.

**Nota:** La firma actual es `_apply_slippage_to_price(self, price, is_buy)`. Cambia a `_apply_slippage_to_price(self, price, signal)` para tener acceso a `signal.position_side`.

### 3.7 Completed trades — nueva columna

El dict de cada trade completado incluye `position_side`:

```python
completed_trade = {
    'symbol': self.current_position.entries[0].symbol if hasattr(...) else ...,
    'position_side': self.current_position.position_side,  # NUEVO: 'LONG' o 'SHORT'
    'entry_time': ...,
    'exit_time': ...,
    # ... resto igual
}
```

### 3.9 DataFrame vacio — incluir `position_side` en columnas

La funcion `_create_results_dataframe()` crea un DataFrame vacio cuando hay 0 trades. Debe incluir `'position_side'` en la lista de columnas para que el pipeline de metricas no falle:

```python
# En _create_results_dataframe(), anadir 'position_side' a la lista de columnas:
columns = ['symbol', 'position_side', 'entry_time', 'exit_time', ...]
```

---

## 4. MetricsAggregator — propagar position_side

**Archivo:** `metrics/metrics_aggregator.py`

### Cambio unico

Eliminar el hardcoded de linea 90:

```python
# ANTES:
adapted['position_side'] = 'LONG'  # TODO: adaptar cuando tengamos SHORT

# DESPUES:
# position_side ya viene del engine — no tocar
```

El campo `position_side` ya esta en el DataFrame del engine. El aggregator simplemente lo deja pasar.

---

## 5. TradeMetricsCalculator — eliminar default LONG

**Archivo:** `metrics/trade_metrics.py`

### Cambio en `_prepare_data()`

```python
# ANTES (linea ~69):
else:
    df["position_side"] = "LONG"

# DESPUES:
else:
    raise ValueError(
        "trade_data must include 'position_side' column. "
        "Ensure BacktestEngine outputs position_side."
    )
```

### Logica existente que YA funciona

`_calculate_mae_mfe()` ya tiene branches para SHORT:
- LONG: MAE = entry - low (precio baja = adverso), MFE = high - entry (precio sube = favorable)
- SHORT: MAE = high - entry (precio sube = adverso), MFE = entry - low (precio baja = favorable)

`_calculate_time_in_profit_loss()` ya tiene branches para SHORT:
- LONG: profit cuando close > entry
- SHORT: profit cuando close < entry

**No se necesitan cambios en la logica de calculo** — solo eliminar el fallback hardcoded.

---

## 6. Portfolio Metrics — sin cambios

**Archivo:** `metrics/portfolio_metrics.py`

**No requiere cambios.** Todas las metricas (sharpe, drawdown, profit_factor, etc.) operan sobre `net_pnl` firmado. Un trade SHORT que gana $50 es identico a un trade LONG que gana $50 a nivel portfolio.

---

## 7. Backward compatibility

| Componente | Default | Efecto |
|-----------|---------|--------|
| `TradingSignal.position_side` | `SignalPositionSide.LONG` | Estrategias existentes sin cambios |
| `create_simple_signal()` | `position_side=LONG` | API existente intacta |
| Engine routing | LONG+BUY=entry, LONG+SELL=exit | Mismo comportamiento actual |
| Completed trades | Incluye `position_side='LONG'` | Metricas reciben dato correcto |

**Test de regresion critico:** Ejecutar todas las estrategias existentes y verificar que los resultados son bit-a-bit identicos antes y despues del cambio.

---

## 8. Tests

### Engine tests (SHORT-specific)

1. **Test SHORT basico crypto:** SELL abre SHORT, BUY cierra. P&L correcto cuando precio baja (ganancia) y cuando sube (perdida).
2. **Test SHORT basico futuros:** Mismo con fee fijo y point_value.
3. **Test SHORT slippage crypto:** Slippage va en contra (SELL entry → precio baja, BUY exit → precio sube).
4. **Test SHORT slippage futuros:** Slippage en ticks va en contra.
5. **Test SHORT fees:** Fees se aplican igual que LONG (simetricos).
6. **Test SHORT partial close:** Cerrar 50% de SHORT, verificar P&L proporcional.
7. **Test SHORT DCA:** Dos SELL entries, promedio ponderado correcto, luego BUY cierra.
8. **Test mezcla incoherente:** BUY+SHORT con LONG abierto → se ignora.
9. **Test exit sin posicion:** BUY+SHORT sin posicion abierta → se ignora.

### Regression tests (LONG existing)

10. **Test LONG crypto:** Resultados identicos al comportamiento actual.
11. **Test LONG futuros:** Resultados identicos al comportamiento actual.

### Metrics tests

12. **Test MAE/MFE SHORT:** Precio sube = MAE, precio baja = MFE.
13. **Test position_side propagacion:** Verificar que `position_side` llega hasta `trade_metrics_df`.

### Integration tests

14. **Test end-to-end crypto SHORT:** Estrategia → runner → metricas → all_metrics correcto.
15. **Test end-to-end futuros SHORT:** Mismo para futuros.

---

## 9. Modulos sin cambios (confirmado)

| Modulo | Razon |
|--------|-------|
| `portfolio_metrics.py` | Opera sobre `net_pnl` firmado — agnostico a direccion |
| `backtest_runner.py` | Solo orquesta — pasa signals y results sin interpretarlos |
| `optimization/` | `ParameterOptimizer` no tiene referencias a position_side/LONG/SHORT |
| `validation/` | Los 3 validadores ejecutan BacktestRunner internamente — transparente |
| `config/market_configs/` | Fees son simetricos (LONG y SHORT cuestan igual en CME y Binance) |

## 10. Limitacion conocida: visualizacion

**`chart_plotter.py` NO se modifica en esta fase.** Si se ejecuta una estrategia SHORT despues de Fase 1:
- Los markers de entrada SHORT (SELL) apareceran como flechas de "exit" (arrowDown amarillo)
- Los markers de salida SHORT (BUY) apareceran como flechas de "entry" (arrowUp verde)
- Esto es visualmente confuso pero **los datos y metricas son correctos**

Archivos afectados para Fase 2:
- `visualization/chart_plotter.py` lineas 274-343 (`_serialize_markers`)
- `BacktestVisualizerStatic` variables `signals_long_entry` / `signals_long_exit`

## 11. Fase 2 (futura): Visualizacion SHORT

**Fuera de scope de esta fase.** Documentado como tarea pendiente:

- Markers invertidos en chart de velas (flechas abajo para entry SHORT, arriba para exit)
- Colores diferenciados (rojo/naranja para SHORT vs verde/amarillo para LONG)
- Legend que distingue LONG vs SHORT trades
- Dashboards: posible filtro por direccion en los dashboards Plotly
