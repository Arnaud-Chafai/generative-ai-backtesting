# Strategy Spec: BTCPugilanime v2

**Tipo:** Tendencia (breakout-pullback)
**Activo:** BTC | CRYPTO | Binance | M5
**Contexto de mercado:** Impulso tras acumulación, solo en tendencia alcista macro
**Edge:** Sesgo alcista estructural de BTC. Correcciones en tendencia alcista generan pullbacks a EMAs que ofrecen entradas de alta expectativa.

## Cambios vs v1

| Aspecto | v1 | v2 | Por qué |
|---------|----|----|---------|
| Filtro tendencia | Ninguno | SMA 200 (precio debe estar arriba) | Evita operar en bear market |
| EMA pullback | EMA 20 | EMA 50 | Pullbacks más significativos, menos ruido |
| Stop loss | Mínimo de 6 velas (30min) | ATR(14) * 1.5 bajo precio de entrada | Respeta la volatilidad real |
| Take profit | Fijo a 3R | Sin TP fijo → trailing stop | Deja correr winners |
| Trailing stop | No | ATR(14) * 2.0, se activa tras 1R profit | Captura tendencias extendidas |
| Confirmación breakout | 1 vela | 2 cierres consecutivos sobre range_high | Reduce falsos breakouts |
| Lookback rango | 48 (4h) | 96 (8h) | Rangos más significativos |
| Entrada | Una sola compra | DCA temporal: 3 compras cada 15min (33.3% c/u) | Promedia mejor precio en el pullback |
| Volumen | 1.5x media(20) | 2.0x media(20) | Filtro más estricto |

## Lógica

### Indicadores pre-calculados
- SMA 200 (filtro de tendencia macro)
- EMA 50 (referencia para pullback)
- ATR 14 (para stops dinámicos)
- Range_High / Range_Low (rolling 96 velas)
- Volume_MA (media 20 velas)

### Máquina de estados

**SCANNING** → Buscando ruptura del rango
- Condición: close > Range_High por 2 velas consecutivas + volumen > 2x media + precio > SMA 200
- Transición → BREAKOUT

**BREAKOUT** → Esperando pullback a EMA 50
- Invalidación: close < Range_Low → SCANNING
- Timeout: 96 velas (8h) sin pullback → SCANNING
- Confirma impulso: low > EMA 50 (seen_above_ema)
- Pullback toca EMA 50: low <= EMA 50 <= close AND EMA 50 > Range_High
- → BUY #1 (33.3% del capital asignado) al close
- → Calcula stop = entry - ATR(14) * 1.5
- → Transición → DCA_FILLING

**DCA_FILLING** → Completando las 3 entradas cada 15 minutos
- Lleva cuenta de: entries_done (1-3), bars_since_last_entry
- Cada 3 velas (15min en M5): emite BUY adicional (33.3%) al close actual
- Stop loss activo desde la primera entrada: si close <= stop_loss → SELL → WAITING_RESET
- Cuando entries_done == 3 → Transición → IN_POSITION
- Protección DCA: si durante el llenado close cae por debajo del stop_loss, cancela entradas restantes y vende todo → WAITING_RESET
- Nota: el stop se calcula sobre el avg_entry_price de la primera entrada (no se recalcula con cada DCA)

**IN_POSITION** → Gestionando trade con salida parcial + trailing
- Fase 1 (pre-parcial): stop fijo ATR, esperando 1R de profit
  - Si close <= stop_loss → SELL 100% → WAITING_RESET
  - Si profit >= 1R → SELL 33% (parcial), mover stop a break-even (avg_entry_price) → Fase 2
- Fase 2 (post-parcial): trailing ATR + TP máximo sobre el 67% restante
  - Trailing stop = highest_high - ATR(14) × atr_trail_mult (solo sube)
  - Si close <= trailing_stop → SELL 67% restante → WAITING_RESET
  - Si close <= avg_entry_price (break-even) → SELL 67% restante → WAITING_RESET
  - Si profit >= max_tp_r × R (default 3R) → SELL 67% restante → WAITING_RESET

**WAITING_RESET** → Esperando que precio resetee
- Condición: close < EMA 50 → SCANNING

## Requisito técnico: Soporte de SELL parcial en el engine

El motor actual (`BacktestEngine._handle_sell`) solo cierra posiciones al 100%.
Para la salida parcial de 33%, se necesita que el engine soporte `position_size_pct < 1.0`
en señales SELL, cerrando solo esa fracción y manteniendo el resto abierto.

**Cambios necesarios en `simple_backtest_engine.py`:**
1. `_handle_sell()`: si pct < 1.0, cerrar fracción de la posición, registrar trade parcial
2. `Position`: método `partial_close(pct)` que reduce entries proporcionalmente
3. El trade parcial se registra en el DataFrame con su P&L proporcional

## Parámetros optimizables

| Parámetro | Default | Rango | Descripción |
|-----------|---------|-------|-------------|
| lookback_period | 96 | 48-192 | Velas del rango de acumulación |
| ema_period | 30 | 20-100 | EMA para pullback |
| sma_trend_period | 200 | 100-300 | SMA filtro de tendencia |
| atr_period | 14 | 10-20 | Período del ATR |
| atr_stop_mult | 2.5 | 1.0-3.0 | Multiplicador ATR para stop loss |
| atr_trail_mult | 1.5 | 1.0-4.0 | Multiplicador ATR para trailing stop |
| trail_activation_r | 1.0 | 0.5-2.0 | R múltiplo para activar trailing (= parcial) |
| max_tp_r | 3.0 | 2.0-6.0 | R múltiplo para TP máximo del runner |
| partial_close_pct | 0.33 | 0.25-0.50 | Fracción a cerrar en el parcial |
| volume_multiplier | 2.0 | 1.5-3.0 | Umbral volumen vs media |
| breakout_confirm_bars | 2 | 1-3 | Velas consecutivas sobre range_high |
| breakout_timeout | 96 | 48-192 | Velas máx esperando pullback |
| dca_entries | 3 | 1-3 | Número de entradas DCA |
| dca_interval_bars | 3 | 2-6 | Velas entre cada entrada DCA (3 = 15min en M5) |

## Seguimiento
- Validar visualmente que el parcial ocurre en 1R y el runner se extiende más
- Comparar profit factor y avg winner vs v2 sin parciales
- El TP máximo a 3R debería reducir la pérdida de profit por trailing demasiado suelto
- Monitorear cuántos trades llegan al TP vs cuántos cierran por trailing/BE
