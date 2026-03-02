# Soporte completo de futuros en BacktestEngine

**Fecha**: 2026-03-02
**Estado**: Aprobado

## Problema

El engine calcula sizing, fees y P&L como si todo fuera crypto. Los campos `tick_value` y `contract_size` de `futures_config.py` nunca se usan. El soporte de futuros es un esqueleto funcional pero con resultados incorrectos.

## Decisiones de diseno

| Decision | Respuesta |
|----------|-----------|
| **Sizing** | Por riesgo: `contracts = floor(risk_usd / (stop_distance * point_value))` |
| **Override** | Si la senal trae `contracts=N`, usa eso directamente |
| **Redondeo** | Siempre `floor`. Si <1, skip trade |
| **Stop distance** | Del `stop_loss_price` de la senal |
| **Fees** | `contracts * fee_per_contract` por lado (entry + exit) |
| **Margen** | No validar, solo trackear capital (P&L + fees) |
| **Metricas** | Corregir MAE/MFE junto con el engine |
| **pnl_pct** | Return on Risk: `net_pnl / risk_usd * 100` |
| **DCA futuros** | Floor por entrada en partial_close |
| **Enfoque** | Branching directo con `is_futures` en las clases existentes |

## Modelo de capital

| | Crypto | Futuros |
|---|---|---|
| **Buy** | `capital -= size_usdt + fee` | `capital -= fee` |
| **Sell** | `capital += exit_value - fee` | `capital += P&L - fee` |
| **P&L** | `crypto_qty * exit_price - cost` | `contracts * point_value * delta_price` |

En futuros no hay "inversion" de capital. Solo se pagan comisiones al entrar y se cobra/paga P&L al salir.

## Formulas clave

```
point_value = tick_value / tick_size          # ES: 12.50/0.25 = $50/punto
risk_usd = capital * position_size_pct        # % capital a arriesgar
stop_distance = abs(entry_price - stop_loss_price)
num_contracts = floor(risk_usd / (stop_distance * point_value))

gross_pnl = contracts * point_value * (exit_price - avg_entry_price)
entry_fee = contracts * fee_per_contract
exit_fee = contracts * fee_per_contract
net_pnl = gross_pnl - entry_fee - exit_fee

pnl_pct = net_pnl / risk_usd * 100           # Return on Risk
```

## Archivos a modificar

| Archivo | Cambios |
|---------|---------|
| `models/simple_signals.py` | +`stop_loss_price: float = None`, +`contracts: int = None` |
| `core/simple_backtest_engine.py` | Entry: +contracts. Position: +total_contracts, adaptar partial_close. Engine: is_futures branching en buy/sell/P&L |
| `metrics/trade_metrics.py` | Constructor: +is_futures, +point_value. MAE/MFE: usar contracts*point_value para futuros |
| `metrics/metrics_aggregator.py` | Pasar is_futures/point_value al calculator. Adaptar columnas contracts/risk_usd |
| `strategies/base_strategy.py` | Adaptar `create_simple_signal` para aceptar stop_loss_price y contracts |

## Lo que NO cambia

- **Slippage**: ya funciona correctamente (fijo en ticks para futuros)
- **Portfolio metrics**: trabajan con `net_pnl`, que sera correcto
- **Dashboards**: consumen las mismas columnas
- **Estrategias crypto existentes**: campos opcionales = backward compatible
- **futures_config.py**: ya tiene los campos correctos

## TradingSignal extendido

```python
@dataclass
class TradingSignal:
    timestamp: datetime
    signal_type: SignalType
    symbol: str
    price: float
    position_size_pct: float        # Crypto: % capital a desplegar. Futuros: % capital a arriesgar
    stop_loss_price: float = None   # Requerido para auto-sizing en futuros
    contracts: int = None           # Override manual: ignora calculo automatico
```

Semantica dual de `position_size_pct`:
- Crypto: "10% = invierto 10% de mi capital"
- Futuros: "10% = arriesgo 10% de mi capital"

## Entry y Position

```python
@dataclass
class Entry:
    timestamp: datetime
    price: float
    size_usdt: float     # Crypto: USDT gastados. Futuros: 0
    contracts: int       # Crypto: 0. Futuros: N contratos
    fee: float
    slippage_cost: float

class Position:
    def total_contracts(self) -> int:
        return sum(e.contracts for e in self.entries)

    # partial_close: floor por entrada para contratos
```

## Metricas

```python
# MAE/MFE para futuros:
mae = (entry_price - min_price) * contracts * point_value  # USD
mfe = (max_price - entry_price) * contracts * point_value  # USD

# riesgo_aplicado para futuros:
riesgo = risk_usd / capital_previo * 100
```

## Columnas nuevas en el DataFrame de resultados

- `contracts`: numero de contratos operados
- `risk_usd`: capital en riesgo (para calcular pnl_pct)
- `point_value`: valor por punto (para que metricas lo usen)
