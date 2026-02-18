---
name: create-strategy
description: "Usar cuando se quiere crear una nueva estrategia de trading. Guía el proceso completo: validación del edge, diseño del spec, e implementación técnica estandarizada."
---

# Crear Nueva Estrategia de Trading

## Visión

El framework es el motor. El usuario es el piloto. Este skill estandariza el proceso técnico para que el foco de la sesión sea 100% la lógica de trading y la exploración de ideas.

---

## FASE 0 — Edge Validation (HARD-GATE)

<HARD-GATE>
NO pasar a Fase 1 hasta que el usuario haya articulado la ventaja de mercado que busca explotar.
</HARD-GATE>

Antes de diseñar nada, preguntar:

**"¿Tienes una hipótesis clara sobre la ventaja (edge) que quieres explotar con esta estrategia?"**

- **Sí, tengo el edge** → continuar a Fase 1
- **No / quiero explorar primero** → dirigir al usuario a `notebooks/` para análisis exploratorio. Recordar que la hipótesis debe venir antes que la implementación.

---

## FASE 1 — Strategy Spec (10 preguntas, una a la vez)

Hacer estas preguntas en orden, **una por mensaje**. Esperar respuesta antes de la siguiente.

1. ¿Cómo se llama la estrategia y de qué tipo es? *(momentum / reversión / breakout / tendencia / mean-reversion)*
2. ¿Qué activo y mercado? *(crypto/futures, ticker, exchange, timeframe)*
3. ¿Qué contexto de mercado busca capturar? *(ej: "lateralización tras impulso", "momentum en apertura de sesión")*
4. ¿Cuál es la ventaja (edge) concreta que crees estar explotando?
5. ¿Cuál es la condición de entrada (BUY)? *(puede ser aproximada al principio)*
6. ¿Cuál es la condición de salida (SELL)?
7. ¿Cómo es la gestión de posición? *(una entrada única / averaging / reciclado de órdenes)*
8. ¿Qué R:R y tipo de stop? *(1:1, 1:2 / por porcentaje / ATR / temporal)*
9. ¿Qué parámetros serán optimizables? *(lista con rango estimado)*
10. ¿Qué tipo de seguimiento tendrá la estrategia? *(cómo se adapta en el tiempo)*

**Output de Fase 1:** Generar un strategy spec en markdown y guardarlo en `docs/strategies/{nombre}-spec.md`. Presentarlo al usuario y pedir aprobación explícita antes de continuar.

**Formato del spec:**

```
# Strategy Spec: {Nombre}

**Tipo:** {tipo}
**Activo:** {ticker} | {market} | {exchange} | {timeframe}
**Contexto de mercado:** {contexto}
**Edge:** {edge}

## Lógica
- **Entrada (BUY):** {condicion_entrada}
- **Salida (SELL):** {condicion_salida}
- **Gestión de posición:** {gestion_posicion}
- **R:R / Stop:** {rr_stop}

## Parámetros optimizables
{parametros_con_rangos}

## Seguimiento
{tipo_seguimiento}
```

---

## FASE 2 — Implementación técnica (checklist)

<HARD-GATE>
NO generar código hasta que el strategy spec de Fase 1 esté aprobado explícitamente por el usuario.
</HARD-GATE>

Con el spec aprobado, generar el boilerplate y seguir este checklist en orden:

```
[ ] 1. Generar strategies/examples/{nombre}.py con el boilerplate base
[ ] 2. Revisar y confirmar los parámetros del __init__ con el usuario
[ ] 3. Implementar generate_simple_signals() — el usuario lidera la lógica
[ ] 4. Correr backtest de validación inicial (BacktestRunner)
[ ] 5. ★ Visualizar entradas/salidas (runner.plot_trades())
         → Confirmar que las señales aparecen donde el spec indica
         → Si algo no coincide, volver al paso 3
[ ] 6. Revisar métricas con dashboards (runner.plot_dashboards())
[ ] 7. Optimizar parámetros (ParameterOptimizer) si el comportamiento visual es correcto
[ ] 8. Documentar en strategies/CLAUDE.md
[ ] 9. Commit: feat(strategy): add {nombre}
```

**Principio del paso 5:** Primero validar visualmente que la estrategia hace lo que se diseñó. Solo entonces tiene sentido interpretar métricas (Sharpe, drawdown, etc.).

---

## Boilerplate base (paso 1 de Fase 2)

Generar este archivo con los datos del spec completados. Sustituir todos los `{placeholders}`:

```python
"""
{NombreClase} — {tipo}
{descripcion_corta}

Edge: {edge}
Contexto: {contexto_mercado}
"""

from strategies.base_strategy import BaseStrategy
from models.enums import SignalType, MarketType
from utils.timeframe import Timeframe


class {NombreClase}(BaseStrategy):
    """
    {descripcion}

    Parámetros optimizables:
        {parametros}
    """

    def __init__(
        self,
        symbol: str = "{ticker}",
        timeframe: Timeframe = Timeframe.{TIMEFRAME},
        exchange: str = "{exchange}",
        # Parámetros optimizables:
        {parametros_init},
        position_size_pct: float = 0.5,
        **kwargs
    ):
        super().__init__(
            market=MarketType.{MARKET},
            symbol=symbol,
            strategy_name="{NombreClase}",
            timeframe=timeframe,
            exchange=exchange,
            **kwargs
        )

        {asignacion_parametros}
        self.position_size_pct = position_size_pct

        # Pre-calcular indicadores en __init__:
        # TODO: self.market_data['{indicador}'] = ...

    def generate_simple_signals(self) -> list:
        """
        Entrada: {condicion_entrada}
        Salida:  {condicion_salida}
        Gestión: {gestion_posicion}
        R:R:     {rr_stop}
        """
        self.simple_signals = []
        in_position = False

        for i in range({lookback}, len(self.market_data)):
            # TODO: implementar condición de entrada
            if False and not in_position:
                self.create_simple_signal(
                    signal_type=SignalType.BUY,
                    timestamp=self.market_data.index[i],
                    price=self.market_data['Close'].iloc[i],
                    position_size_pct=self.position_size_pct
                )
                in_position = True

            # TODO: implementar condición de salida
            elif False and in_position:
                self.create_simple_signal(
                    signal_type=SignalType.SELL,
                    timestamp=self.market_data.index[i],
                    price=self.market_data['Close'].iloc[i],
                    position_size_pct=1.0
                )
                in_position = False

        print(f"✓ Señales generadas: {len(self.simple_signals)}")
        return self.simple_signals
```

---

## Referencia técnica del framework

### Patrones obligatorios

```python
# ✅ Siempre usar **kwargs (compatibilidad con el optimizador)
def __init__(self, param: int = 20, **kwargs):
    super().__init__(..., **kwargs)

# ✅ Pre-calcular indicadores en __init__, no en generate_simple_signals
self.market_data['MA'] = self.market_data['Close'].rolling(self.period).mean()

# ✅ Resetear simple_signals al inicio de generate_simple_signals
self.simple_signals = []

# ✅ SELL siempre cierra la posición completa
position_size_pct=1.0
```

### Correr backtest (paso 4)

```python
from core.backtest_runner import BacktestRunner
strategy = MiEstrategia(symbol='BTC', exchange='Binance', timeframe=Timeframe.H1)
runner = BacktestRunner(strategy)
runner.run()
runner.print_summary()
```

### Visualizar entradas/salidas (paso 5 — CRÍTICO antes de métricas)

```python
runner.plot_trades()  # Chart interactivo con señales BUY/SELL sobre velas
```

### Ver dashboards de métricas (paso 6)

```python
runner.plot_dashboards()  # 10 dashboards de análisis
```

### Optimizar parámetros (paso 7)

```python
from optimization.parameter_optimizer import ParameterOptimizer
optimizer = ParameterOptimizer(
    strategy_class=MiEstrategia,
    market_data=strategy.market_data,
    symbol='BTC'
)
results = optimizer.optimize(
    param_ranges={'param1': range(10, 50, 5)},
    metric='sharpe_ratio'
)
```
