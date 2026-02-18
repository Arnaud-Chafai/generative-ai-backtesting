# Strategy Spec: Estrategia BTC Pugilánime

**Fecha:** 2026-02-18
**Estado:** Aprobado — pendiente de exploración en atelier

---

**Tipo:** Tendencia (breakout-pullback)
**Activo:** BTC | Crypto | Binance | 5min
**Contexto de mercado:** Impulso tras acumulación — el precio forma una zona de rango, rompe con fuerza y ofrece una ventana de entrada en el retroceso
**Edge:** BTC tiene sesgo alcista estructural a largo plazo. Las correcciones profundas generan zonas de acumulación que, al romperse con volumen, presentan oportunidades de entrada con alta expectativa siguiendo la tendencia principal

---

## Lógica

### Entrada (BUY) — Scaling in con 2-3 entradas escalonadas

La entrada se produce en el **pullback tras la ruptura** de la zona de acumulación, no en la ruptura en sí.

**Filtro de ruptura válida (obligatorio antes de buscar entrada):**
- Volumen de la ruptura > media del volumen del rango
- Variación % de la vela de ruptura > media de variación % del rango

**Niveles de entrada** *(a explorar en atelier — dos hipótesis):*
- Hipótesis A — por EMA: entrada en retorno a EMA 20 / EMA 50 / EMA 200
- Hipótesis B — por % retroceso: entrada en retrocesos del 25% / 50% / 61.8%

**Invalidación:** Si el precio vuelve a la zona de acumulación (rango original) → abortar trade y esperar. El breakout fue falso.

### Salida (SELL) — Trailing Stop por ATR

Una vez en posición, el stop se vuelve trailing basado en ATR.
- Parámetro a optimizar: multiplicador del ATR
- No se usa objetivo fijo de precio (para dejar correr la tendencia)

### Gestión de posición — Averaging

2-3 entradas parciales escalonadas en el pullback.
Cada entrada tiene su propio stop de protección inicial (ver abajo).

---

## Estructura de stops (por entrada)

| Entrada | Nivel de stop inicial |
|---------|----------------------|
| Entrada 1 (más agresiva) | Debajo del cierre de la vela de ruptura (close de la V) |
| Entrada 2 (media) | Debajo del POC de la acumulación (precio con mayor volumen del rango) |
| Entrada 3 (más profunda) | Debajo del mínimo de toda la zona de acumulación |

Una vez que el precio avanza a favor, todos los stops pasan a ser trailing ATR.

---

## Parámetros optimizables

| Parámetro | Descripción | Rango estimado |
|-----------|-------------|----------------|
| `entry_mode` | Hipótesis A (EMA) vs Hipótesis B (% retroceso) | A / B |
| `entry_levels` | Niveles específicos (EMA periods o % retroceso) | A explorar |
| `position_size_1` | % capital en entrada 1 | 0.1 – 0.4 |
| `position_size_2` | % capital en entrada 2 | 0.1 – 0.4 |
| `position_size_3` | % capital en entrada 3 | 0.1 – 0.4 |
| `atr_period` | Período del ATR para trailing stop | 7 – 21 |
| `atr_multiplier` | Multiplicador del ATR para el trailing | 1.5 – 4.0 |
| `volume_filter_period` | Período para calcular media de volumen del rango | 10 – 30 |

---

## Seguimiento

- **Filtro de régimen:** La estrategia solo opera en condiciones de breakout con volumen confirmado. En rango sin ruptura, no hay señal.
- **Invalidación activa:** Si el precio regresa a la zona de acumulación post-ruptura → la señal queda inválida. No se añaden entradas.
- **Re-optimización:** Revisar parámetros periódicamente — el comportamiento de BTC cambia entre ciclos (bull market vs corrección macro).

---

## Pendiente — Atelier

Antes de implementar la lógica completa, explorar en `notebooks/`:

1. ¿Cuánto suele retroceder BTC tras una ruptura de acumulación en 5min? (distribución de % retroceso)
2. ¿La EMA o el % de retroceso tiene mayor correlación con continuación de la tendencia?
3. ¿Qué umbral de volumen/variación separa mejor breakouts genuinos de falsos?
4. ¿Cuál es la distribución del POC dentro de las zonas de acumulación? ¿Es un nivel estable?
