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

## Trailing ATR demasiado ajustado mata runners

Un trailing stop de ATR x1.5 en BTC M5 cierra runners prematuramente porque el ruido intraday supera ese umbral frecuentemente. Los movimientos post-pullback necesitan espacio para respirar. ATR x2.5 respeta mejor la estructura y captura extensiones significativamente mayores (avg winner +121% en BTCPugi). El TP fijo (3R) tambien actua como techo artificial — el trailing cierra la mayoria de trades antes del TP, pero los pocos que llegarian mas lejos se cortan innecesariamente.
**Impacto:** Estrategias de tendencia con trailing. Expectancy sube dramaticamente al aflojar trailing.
**Observado en:** BTCPugilanime v2.1→v2.2 (2026-02). Costs/gross 93%→59%, PF 1.36→1.67
**Indicadores proxy:** Ratio avg_winner / avg_loser. Si <1.0 en estrategia de tendencia, trailing demasiado ajustado.

## Lag del SMA200 en techos de ciclo

Cuando BTC transiciona de tendencia alcista a distribucion/bear, el SMA200 sigue confirmando "alcista" durante semanas o meses por su inercia. Estrategias que usan SMA200 como filtro de tendencia compran pullbacks que en realidad son piernas de correccion. El resultado son losses grandes concentrados en 1-2 trimestres (ej: Q4 2021 BTC ATH $69k → crash).
**Impacto:** Todas las estrategias de tendencia con filtro SMA largo. Losses en techos de ciclo.
**Observado en:** BTCPugilanime Q4 2021. Fed anuncio tapering, BTC cayo 52% desde ATH.
**Indicadores proxy:** Divergencia precio-SMA200 extrema (>30%), volumen decreciente en nuevos maximos, VIX en expansion.

## Convergencia de catalizadores macro como contexto optimo

Cuando multiples factores macro convergen (regulacion favorable + evento de escasez + flujos institucionales), las estrategias de tendencia rinden excepcionalmente. Estos periodos son raros pero concentran la mayor parte del profit a largo plazo. En BTCPugi, Q1 2024 (ETFs spot + anticipacion halving) genero el 86% del profit total en 5 anos.
**Impacto:** Estrategias de tendencia crypto. Periodos de convergencia macro son el "sweet spot" del edge.
**Observado en:** BTCPugilanime Q1 2024. BTC $40k→$73k en 3 meses. PF 6.62, 16 trades.
**Indicadores proxy:** Aprobaciones regulatorias, halvings, flujos ETF, narrativa mediatic de adopcion institucional.
