# Dinamicas de Mercado

Observaciones sobre comportamiento del mercado de orden superior. No son reglas de parametros — son patrones de como se mueve el mercado y que impacto tienen en las estrategias.

## Breakouts en tendencia alcista vs sin filtro

Los breakouts de acumulacion en BTC tienen edge solo cuando el precio esta por encima de la SMA200 (tendencia alcista macro). Sin filtro de tendencia, la tasa de falsos breakouts se dispara porque las rupturas en mercado bajista/lateral suelen ser trampas de liquidez.
**Impacto:** Estrategias de breakout sin filtro macro pierden dinero en bear/lateral
**Observado en:** BTCPugilanime v1→v2 (2026-02)
**Indicadores proxy:** Precio vs SMA(200), pendiente SMA(200)

## Extension de movimientos post-pullback en BTC

En tendencias alcistas de BTC, los movimientos post-pullback a EMAs rapidas (20-50) suelen extenderse significativamente mas alla de 1R. Cerrar al 100% en un target fijo corta la cola derecha de la distribucion de ganancias. Parciales (asegurar 1/3 en 1R + trailing en el resto) capturan mejor esta dinamica.
**Impacto:** Estrategias con TP fijo subestiman el potencial. Trailing > TP fijo en tendencia.
**Observado en:** BTCPugilanime v2.0→v2.1 (2026-02)
**Indicadores proxy:** Distribucion de MFE (Maximum Favorable Excursion) vs punto de salida
