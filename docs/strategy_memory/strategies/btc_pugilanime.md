# BTCPugilanime | CRYPTO BTC M5 | Tendencia (breakout-pullback)

## Edge

Sesgo alcista estructural de BTC. Correcciones en tendencia alcista generan pullbacks a EMAs que ofrecen entradas de alta expectativa. Se busca capturar el impulso post-acumulacion entrando en el retroceso con confirmacion de volumen.

## Regime Profile

*(Pendiente de primer ciclo /refine-strategy)*

| Periodo | Volatilidad | Tendencia | PF | Trades | Etiqueta |
|---------|-------------|-----------|-----|--------|----------|
| ...     | ...         | ...       | ... | ...    | ...      |

## Changelog

### v2.2 — 2026-02-28 (refine-strategy)
**Contexto:** Expectancy de $0.30/trade demasiado baja. Costos consumian 93% del gross profit. El trailing (ATR x1.5) y TP (3R) cortaban los ganadores antes de desarrollarse. Position size (50%) no aprovechaba el capital disponible.
**Cambio:** atr_trail_mult 1.5→2.5, max_tp_r 3.0→6.0, trail_activation_r 1.0→1.5, position_size_pct 0.5→0.8
**Resultado:** PF 1.36→1.67 (+23%), expectancy $0.30→$0.96 (+220%), net profit $32→$98 (+203%), avg winner $1.67→$3.69 (+121%), costs/gross 93%→59% (-37%). MaxDD 1.5%→2.1%. Robustness test: 5/5 parametros ROBUSTO (PF 1.42-1.72 en ±20%).
**Dinamica:** En tendencias de BTC, el trailing ATR x1.5 era demasiado ajustado — cerraba runners antes de capturar la extension del movimiento. Con x2.5 el trailing respeta mejor la estructura del pullback y deja correr. El TP de 3R era un techo artificial: muy pocos trades llegan al TP (el trailing cierra antes), pero los que si llegaban se cortaban prematuramente.

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

## Robustness (v2.2)

| Parametro | -20% | -10% | Base | +10% | +20% | Veredicto |
|-----------|------|------|------|------|------|-----------|
| atr_trail_mult | 1.63 | 1.60 | 1.67 | 1.68 | 1.63 | ROBUSTO |
| max_tp_r | 1.67 | 1.67 | 1.67 | 1.66 | 1.66 | ROBUSTO |
| trail_activation_r | 1.55 | 1.64 | 1.67 | 1.66 | 1.72 | ROBUSTO |
| position_size_pct | 1.67 | 1.67 | 1.67 | 1.67 | 1.66 | ROBUSTO |
| atr_stop_mult | 1.54 | 1.59 | 1.67 | 1.47 | 1.42 | ROBUSTO |

## Regime Profile (v2.2)

| Periodo | Vol(ATR%) | PF | WR | Trades | Net P&L | Contexto |
|---------|-----------|------|-----|--------|---------|----------|
| 2021 Q2 | 0.45 | 2.27 | 86% | 7 | +$3.9 | Alta vol post-halving 2020 |
| 2021 Q3 | 0.29 | 1.78 | 77% | 13 | +$5.9 | Rally verano |
| 2021 Q4 | 0.28 | 0.12 | 40% | 5 | -$9.8 | ATH $69k + crash. Fed tapering. Head fake alcista |
| 2022 Q1-Q3 | 0.27-0.29 | >1.5 | >67% | 7 | +$14.2 | Bear pero filtrado SMA200 |
| 2023 | 0.09-0.20 | variable | - | 15 | +$3.8 | Lateral baja vol |
| **2024 Q1** | **0.21** | **6.62** | **88%** | **16** | **+$27.6** | **ETFs spot + anticipacion halving** |
| 2024 Q2-Q3 | 0.18-0.20 | 0.12-0.57 | 40-50% | 11 | -$13.3 | Post-halving, lateral |
| 2024 Q4 | 0.19 | 1.87 | 71% | 14 | +$6.2 | Rally Trump/institucional |
| 2025 | 0.11-0.21 | variable | - | 16 | -$1.6 | Mixto |

## Edge Decay

Status: **Ciclico** — edge depende del regimen de mercado, no decae estructuralmente.
Q1 2024 concentra 86% del profit (evento ETF+halving). Sin ese trimestre, estrategia en breakeven.
Correlacion: volatilidad alta + tendencia alcista = optimo. Baja vol + lateral = debil.
