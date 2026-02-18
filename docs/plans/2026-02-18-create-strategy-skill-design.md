# Design: Skill `create-strategy`

**Fecha:** 2026-02-18
**Autor:** Diseñado colaborativamente
**Estado:** Aprobado — listo para implementación

---

## Propósito

Estandarizar el proceso completo de creación de estrategias de trading en este framework, de modo que el foco de cada sesión sea 100% la lógica de trading y la exploración de ideas — nunca la plumbing técnica.

Se invoca con `/create-strategy` y guía la sesión de principio a fin.

---

## Visión del proyecto

El framework es el motor. El usuario es el piloto. Este skill existe para que el proceso técnico sea tan fluido que nunca saque al usuario del modo de exploración creativa.

---

## Estructura del skill: 3 fases

---

### FASE 0 — Edge Validation (gate de entrada)

**HARD-GATE:** Antes de cualquier diseño o código, el skill pregunta si existe una hipótesis clara sobre la ventaja de mercado que se está explotando.

**Opciones:**
- **Sí, tengo el edge claro** → continuar a Fase 1
- **No / quiero explorar primero** → redirigir al módulo de exploración de datos (`exploration/`) para analizar hipótesis con datos reales antes de diseñar

> **Nota:** El módulo `exploration/` no existe aún y debe crearse como parte de la infraestructura del proyecto. Por ahora, redirigir a notebooks/ como alternativa temporal.

**Principio:** No se construyen estrategias sin ventaja articulada. Primero la hipótesis, luego la implementación.

---

### FASE 1 — Strategy Spec (10 preguntas guiadas)

El skill hace estas preguntas **una a la vez**. Al final genera un **strategy spec** en markdown que ambos revisan y aprueban antes de escribir código.

| # | Pregunta | Captura |
|---|----------|---------|
| 1 | ¿Cómo se llama la estrategia? | `nombre`, `tipo`: momentum / reversión / breakout / tendencia |
| 2 | ¿Qué activo y mercado? | `crypto/futures`, `ticker`, `exchange`, `timeframe` |
| 3 | ¿Qué contexto de mercado busca capturar? | Ej: "lateralización tras impulso", "momentum en apertura" |
| 4 | ¿Cuál es la ventaja (edge) que crees estar explotando? | Articulación concreta del edge |
| 5 | ¿Cuál es la señal de entrada (BUY)? | Condición exacta o aproximada |
| 6 | ¿Cuál es la señal de salida (SELL)? | Condición exacta o aproximada |
| 7 | ¿Cómo es la gestión de posición? | Una entrada / averaging / reciclado de órdenes |
| 8 | ¿Qué R:R y tipo de stop? | 1:1 / 1:2 / porcentaje / ATR / temporal |
| 9 | ¿Qué parámetros serán optimizables? | Lista de variables con rango estimado |
| 10 | ¿Qué tipo de seguimiento tendrá? | Cómo se adapta la estrategia en el tiempo |

**Output de Fase 1:** Un strategy spec aprobado en texto (guardado como `docs/strategies/{nombre}-spec.md`)

---

### FASE 2 — Implementación técnica (checklist estandarizado)

Con el spec aprobado, el skill genera el boilerplate y guía el proceso técnico paso a paso.

```
[ ] 1. Generar strategies/examples/{nombre}.py con boilerplate base
[ ] 2. Revisar y confirmar parámetros en __init__
[ ] 3. Implementar generate_simple_signals() — el usuario lidera la lógica aquí
[ ] 4. Correr backtest de validación inicial (BacktestRunner)
[ ] 5. ★ Visualizar entradas/salidas en el chart (runner.plot_trades())
         → Validar que las señales están donde el diseño indica
         → Si algo no coincide, volver al paso 3
[ ] 6. Revisar métricas con dashboards (runner.plot_dashboards())
[ ] 7. Optimizar parámetros (ParameterOptimizer) si el comportamiento visual es correcto
[ ] 8. Documentar la estrategia en strategies/CLAUDE.md
[ ] 9. Commit final: feat(strategy): add {nombre}
```

**Principio del paso 5:** Las entradas/salidas visuales son el gate antes de las métricas. Si la estrategia no hace lo que se diseñó, los números no tienen sentido.

---

## Boilerplate base (output de Fase 2, paso 1)

El skill genera este template con los datos del spec completados:

```python
"""
{nombre} — {tipo}
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
        # TODO: añadir parámetros optimizables aquí
        position_size_pct: float = 0.5,
        **kwargs
    ):
        super().__init__(
            market=MarketType.{MARKET},
            symbol=symbol,
            strategy_name="{nombre}",
            timeframe=timeframe,
            exchange=exchange,
            **kwargs
        )

        self.position_size_pct = position_size_pct

        # TODO: pre-calcular indicadores aquí

    def generate_simple_signals(self) -> list:
        """
        Lógica: {descripcion_logica}

        Entrada: {condicion_entrada}
        Salida: {condicion_salida}
        Gestión posición: {gestion_posicion}
        R:R / Stop: {rr_stop}
        """
        self.simple_signals = []
        in_position = False

        for i in range(self.lookback, len(self.market_data)):
            # TODO: implementar lógica de entrada y salida
            pass

        return self.simple_signals
```

---

## Archivos a crear

| Archivo | Descripción |
|---------|-------------|
| `~/.claude/skills/create-strategy.md` | El skill en sí |
| `docs/strategies/{nombre}-spec.md` | Strategy spec (output de Fase 1) |
| `strategies/examples/{nombre}.py` | Implementación de la estrategia |

---

## Pendiente: módulo de exploración

El skill referencia un módulo `exploration/` que aún no existe. Si el usuario llega a Fase 0 sin edge claro, se necesita:

- `exploration/` — notebooks o scripts para análisis exploratorio de hipótesis
- Guías para visualizar distribuciones, correlaciones, y patrones en los datos

Este módulo es parte del roadmap y se creará cuando sea necesario.

---

## Restricciones de diseño

- El skill NO genera código hasta que Fase 1 esté aprobada (HARD-GATE)
- El skill NO interpreta métricas hasta que Fase 2 paso 5 (visualización) esté completo
- El usuario siempre lidera las decisiones de lógica de trading
- El skill lidera el proceso técnico y la estandarización
