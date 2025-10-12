# 📖 Diccionario de Datos

Este documento describe todas las variables utilizadas en el dataset.

---

## 📈 Variables del Mercado

| **Variable**                | **Descripción**                                                                                              | **Tipo**   | **Unidad**               |
|-----------------------------|--------------------------------------------------------------------------------------------------------------|------------|--------------------------|
| `Open`                     | Precio de apertura del periodo.                                                                              | Numérico   | Moneda (ej. USD)         |
| `High`                     | Precio máximo alcanzado durante el periodo.                                                                  | Numérico   | Moneda (ej. USD)         |
| `Low`                      | Precio mínimo alcanzado durante el periodo.                                                                  | Numérico   | Moneda (ej. USD)         |
| `Close`                    | Precio de cierre del periodo.                                                                                | Numérico   | Moneda (ej. USD)         |
| `Volume`                   | Volumen total negociado durante el periodo.                                                                 | Numérico   | Número de unidades       |
| `EMA_9`                    | Media móvil exponencial (EMA) de 9 periodos del precio de cierre.                                            | Numérico   | Moneda (ej. USD)         |
| `EMA_20`                   | Media móvil exponencial (EMA) de 20 periodos del precio de cierre.                                           | Numérico   | Moneda (ej. USD)         |
| `EMA_50`                   | Media móvil exponencial (EMA) de 50 periodos del precio de cierre.                                           | Numérico   | Moneda (ej. USD)         |
| `EMA_100`                  | Media móvil exponencial (EMA) de 100 periodos del precio de cierre.                                          | Numérico   | Moneda (ej. USD)         |
| `EMA_200`                  | Media móvil exponencial (EMA) de 200 periodos del precio de cierre.                                          | Numérico   | Moneda (ej. USD)         |
| `Volatility_pct_change_5`  | Cambio porcentual de la volatilidad (desviación estándar) calculada sobre 5 periodos.                        | Numérico   | Porcentaje (%)           |
| `Volatility_pct_change_10` | Cambio porcentual de la volatilidad (desviación estándar) calculada sobre 10 periodos.                       | Numérico   | Porcentaje (%)           |
| `Volatility_pct_change_30` | Cambio porcentual de la volatilidad (desviación estándar) calculada sobre 30 periodos.                       | Numérico   | Porcentaje (%)           |
| `Pct_Change`               | Cambio porcentual del precio de cierre entre periodos consecutivos.                                          | Numérico   | Porcentaje (%)           |
| `Volume_pct_change`        | Cambio porcentual del volumen negociado entre periodos consecutivos.                                         | Numérico   | Porcentaje (%)           |
| `Day`                      | Día de la semana (0: Lunes, ..., 6: Domingo).                                                                | Numérico   | Entero (0-6)             |
| `Month`                    | Mes del año (1: Enero, ..., 12: Diciembre).                                                                  | Numérico   | Entero (1-12)            |
| `Trimester`                | Trimestre del año (1: Q1, ..., 4: Q4).                                                                       | Numérico   | Entero (1-4)             |
| `Year`                     | Año en el que se generaron los datos.                                                                        | Numérico   | Año (ej. 2023)           |
| `Hour`                     | Hora del día (0: medianoche, ..., 23: 11 PM).                                                                | Numérico   | Entero (0-23)            |
| `Minute`                   | Minuto de la hora (0: primer minuto, ..., 59: último minuto).                                                | Numérico   | Entero (0-59)            |
| `European_session`         | Indica si la fila corresponde a la sesión europea (1: Sí, 0: No). La sesión europea va de 09:00 a 15:30.      | Binario    | 1 (Sí) / 0 (No)          |
| `American_session`         | Indica si la fila corresponde a la sesión americana (1: Sí, 0: No). La sesión americana va de 15:30 a 22:00.  | Binario    | 1 (Sí) / 0 (No)          |
| `Asian_session`            | Indica si la fila corresponde a la sesión asiática (1: Sí, 0: No). Va de 22:00 a 09:00 del día siguiente.     | Binario    | 1 (Sí) / 0 (No)          |
| `Min_european_session`     | Valor mínimo de la columna `Low` durante la sesión europea, calculado para cada día.                         | Numérico   | Moneda (ej. USD)         |
| `Max_european_session`     | Valor máximo de la columna `High` durante la sesión europea, calculado para cada día.                        | Numérico   | Moneda (ej. USD)         |
| `Min_american_session`     | Valor mínimo de la columna `Low` durante la sesión americana, calculado para cada día.                       | Numérico   | Moneda (ej. USD)         |
| `Max_american_session`     | Valor máximo de la columna `High` durante la sesión americana, calculado para cada día.                      | Numérico   | Moneda (ej. USD)         |
| `Min_asian_session`        | Valor mínimo de la columna `Low` durante la sesión asiática, calculado para cada día.                        | Numérico   | Moneda (ej. USD)         |
| `Max_asian_session`        | Valor máximo de la columna `High` durante la sesión asiática, calculado para cada día.                       | Numérico   | Moneda (ej. USD)         |
| `OBP_alcista`              | Indica si la vela actual cumple con el patrón "One Bar Pullback Alcista".                                    | Binario    | 1 (Sí) / 0 (No)          |
| `OBP_alcista_extend`       | Indica si la vela actual cumple con el patrón "One Bar Pullback Alcista Extendido".                          | Binario    | 1 (Sí) / 0 (No)          |
| `OBP_bajista`              | Indica si la vela actual cumple con el patrón "One Bar Pullback Bajista".                                    | Binario    | 1 (Sí) / 0 (No)          |
| `OBP_bajista_extend`       | Indica si la vela actual cumple con el patrón "One Bar Pullback Bajista Extendido".                          | Binario    | 1 (Sí) / 0 (No)          |

---

## 📊 Variables de Trade Signals (Señales de Trading)

| **Variable**    | **Descripción**                                                         | **Tipo**    | **Valores posibles / Unidad**        |
|-----------------|-------------------------------------------------------------------------|------------|--------------------------------------|
| `id`            | Identificador único de la señal (UUID).                                | Texto      | Ejemplo: `550e8400-e29b-41d4-a716-446655440000` |
| `market`        | Tipo de mercado donde se genera la señal.                              | Categórico | `CRYPTO`, `FUTURES`, `STOCKS`        |
| `exchange`      | Exchange donde se ejecuta la orden.                                    | Categórico | `BINANCE`, `KUCOIN`, ...             |
| `symbol`        | Par de trading del activo.                                             | Texto      | Ejemplo: `BTC/USDT`                  |
| `currency`      | Divisa en la que se denomina la orden.                                 | Categórico | `USD`, `USDT`, `EUR`, ...            |
| `timeframe`     | Temporalidad de la señal.                                              | Texto      | Ejemplo: `M1`, `M5`, `H1`, `D1`      |
| `strategy_name` | Nombre de la estrategia que generó la señal.                           | Texto      | Ejemplo: `Momentum Breakout`         |
| `signal_type`   | Tipo de señal generada por la estrategia.                              | Categórico | `BUY`, `SELL`, `CLOSE`, `TAKE_PROFIT`, `STOP_LOSS` |
| `order_type`    | Tipo de orden utilizada para ejecutar la señal.                       | Categórico | `MARKET`, `LIMIT`, `STOP`, `STOP_LIMIT` |
| `timestamp`     | Momento en que se generó la señal.                                     | Timestamp  | `YYYY-MM-DD HH:MM:SS`                |
| `usdt_amount`   | Monto en USDT asignado a la operación.                                 | Numérico   | USD                                  |
| `price`         | Precio de ejecución de la orden (si aplica).                           | Numérico   | Moneda (ej. USD)                     |
| `stop_loss`     | Nivel de precio del Stop Loss (si aplica).                             | Numérico   | Moneda (ej. USD)                     |
| `take_profit`   | Nivel de precio del Take Profit (si aplica).                           | Numérico   | Moneda (ej. USD)                     |
| `slippage_in_ticks` | Desviación en ticks debido a slippage.                             | Numérico   | Número de ticks                      |
| `slippage_pct`  | Slippage como porcentaje del precio.                                   | Numérico   | Porcentaje (%)                       |
| `slippage_cost` | Costo del slippage en dólares.                                         | Numérico   | USD                                  |
| `fee`           | Comisión pagada por la ejecución de la orden.                         | Numérico   | USD                                  |
| `position_side` | Dirección del trade (`LONG` o `SHORT`).                                | Categórico | `LONG`, `SHORT`                      |

---

## 📈 Variables de Trade Metrics

| **Variable**       | **Descripción**                                                                 | **Tipo**   | **Unidad**        |
|--------------------|---------------------------------------------------------------------------------|-----------|-------------------|
| `entry_timestamp`  | Momento en que se abrió la operación.                                           | Timestamp | Fecha y hora      |
| `exit_timestamp`   | Momento en que se cerró la operación.                                           | Timestamp | Fecha y hora      |
| `position_side`    | Dirección del trade (`LONG` o `SHORT`).                                         | Categórico| `LONG` / `SHORT`  |
| `entry_price`      | Precio de entrada del trade.                                                    | Numérico  | USD               |
| `exit_price`       | Precio de salida del trade.                                                     | Numérico  | USD               |
| `usdt_amount`      | Monto en USDT utilizado en la operación.                                        | Numérico  | USD               |
| `fees`             | Costo total de las comisiones.                                                  | Numérico  | USD               |
| `slippage_cost`    | Pérdida por slippage en la operación.                                           | Numérico  | USD               |
| `gross_profit_loss`| Ganancia/Pérdida bruta antes de comisiones.                                     | Numérico  | USD               |
| `net_profit_loss`  | Ganancia/Pérdida neta después de comisiones y slippage.                         | Numérico  | USD               |
| `duration_bars`    | Número de velas (barras) que duró el trade.                                     | Numérico  | Velas             |
| `MAE`              | `Maximum Adverse Excursion`: Pérdida máxima flotante.                           | Numérico  | USD               |
| `MFE`              | `Maximum Favorable Excursion`: Ganancia máxima flotante.                        | Numérico  | USD               |
| `trade_volatility` | Variación del precio durante el trade en porcentaje.                            | Numérico  | Porcentaje (%)    |
| `profit_efficiency`| Porcentaje de la ganancia máxima flotante (MFE) realmente capturada.            | Numérico  | Porcentaje (%)    |
| `risk_efficiency`  | Relación entre la pérdida neta y la MAE (`net_profit_loss / MAE`).              | Numérico  | Porcentaje (%)    |
| `risk_reward_ratio`| Relación entre MFE y MAE (`MFE / MAE`).                                         | Numérico  | Decimal           |
| `riesgo_aplicado`  | Porcentaje del capital utilizado en la operación.                               | Numérico  | Porcentaje (%)    |
| `return_on_capital`| Retorno en porcentaje sobre el capital inicial del trade.                       | Numérico  | Porcentaje (%)    |
| `cumulative_capital`| Capital acumulado después de cada trade.                                       | Numérico  | USD               |

---

## 📌 Notas Finales

- Las métricas **EMA** (Exponential Moving Average) se basan en el precio de cierre (`Close`).
- Las métricas de volatilidad usan la desviación estándar como medida base.
- Todos los cambios porcentuales (`Pct_Change`, `Volume_pct_change`, etc.) están expresados como porcentajes.
- **`slippage_cost`** y **`fee`** reflejan los costos adicionales en el trading.
- **`profit_efficiency`** mide cuánto del beneficio máximo (MFE) se capturó.
- **`risk_reward_ratio`** relaciona la máxima ganancia flotante (MFE) con la peor pérdida flotante (MAE).

