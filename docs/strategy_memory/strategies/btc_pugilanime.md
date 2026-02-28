# BTCPugilanime | CRYPTO BTC M5 | Tendencia (breakout-pullback)

## Edge

Sesgo alcista estructural de BTC. Correcciones en tendencia alcista generan pullbacks a EMAs que ofrecen entradas de alta expectativa. Se busca capturar el impulso post-acumulacion entrando en el retroceso con confirmacion de volumen.

## Regime Profile

*(Pendiente de primer ciclo /refine-strategy)*

| Periodo | Volatilidad | Tendencia | PF | Trades | Etiqueta |
|---------|-------------|-----------|-----|--------|----------|
| ...     | ...         | ...       | ... | ...    | ...      |

## Changelog

### v2.1 — 2026-02-28
**Contexto:** Cortando ganancias demasiado rapido. Los trades ganadores se cerraban antes de desarrollarse.
**Cambio:** Salida parcial 33% en 1R + break-even + trailing ATR(14)*1.5 en 67% runner + TP maximo 3R
**Resultado:** 69 posiciones, 38 con parcial (55%), 107 trades totales. Motor soporta partial_close.
**Dinamica:** En tendencias de BTC, los movimientos post-pullback suelen extenderse mas alla de 1R. Asegurar 1/3 y dejar correr el resto captura mejor la cola derecha de la distribucion.

### v2.0 — 2026-02-27
**Contexto:** v1 operaba sin filtro de tendencia, tomando trades en bear market.
**Cambio:** SMA200 trend filter, EMA30 pullback (vs EMA20), ATR stops dinamicos (vs minimo de velas), DCA temporal 3 entradas cada 15min, 2 cierres consecutivos para breakout, lookback 96 velas (8h)
**Resultado:** Eliminacion de trades en bear market. PF mejoro.
**Dinamica:** Los breakouts de acumulacion en BTC solo tienen edge en tendencia alcista macro. Sin filtro, el ratio de falsos breakouts es demasiado alto.

### v1.0 — 2026-02-26
**Contexto:** Primera version. Breakout simple sobre rango con entrada unica.
**Cambio:** Implementacion inicial basada en la hipotesis del edge.
**Resultado:** Funcionaba pero con muchos trades en contextos desfavorables.

## Robustness

*(Pendiente de primer ciclo /refine-strategy)*

## Edge Decay

*(Pendiente de primer ciclo /refine-strategy)*
