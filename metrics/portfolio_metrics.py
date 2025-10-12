import numpy as np
import pandas as pd
from metrics.trade_metrics import TradeMetricsCalculator

class BacktestMetrics:
    def __init__(self, trade_data: pd.DataFrame, initial_capital: float):
        """
        Inicializa el cálculo de métricas del backtest.

        :param trade_data: DataFrame con los datos de cada trade (salida de TradeMetricsCalculator)
        :param initial_capital: Capital inicial utilizado en el backtest.
        """
        self.trade_data = trade_data
        self.initial_capital = initial_capital
        
        # Extraer la moneda del DataFrame, si está disponible
        self.currency = trade_data["currency"].iloc[0] if not trade_data.empty and "currency" in trade_data.columns else "USDT"

    def compute_all_metrics(self) -> dict:
        """
        Calcula todas las métricas del backtest y devuelve un diccionario con los resultados.
        """
        avg_bars_positive, avg_bars_negative = self.calculate_average_trade_durations_in_bars()

        return {
            **self.compute_general_summary(),
            **self.compute_profit_loss_analysis(),
            **self.compute_drawdown_analysis(),
            **self.compute_time_statistics(),
            **self.compute_performance_ratios(),
            **self.compute_operational_costs(),
            "avg_bars_positive": avg_bars_positive,
            "avg_bars_negative": avg_bars_negative,
        }

    def compute_general_summary(self) -> dict:
        """
        Calcula el resumen general del backtest.
        """
        total_trades = len(self.trade_data)
        winning_trades_net = self.trade_data[self.trade_data["net_profit_loss"] > 0]
        losing_trades_net = self.trade_data[self.trade_data["net_profit_loss"] < 0]

        # (A) Beneficio bruto total (suma de 'gross_profit_loss')
        gross_profit = self.trade_data["gross_profit_loss"].sum()

        # (B) Beneficio neto total (suma de 'net_profit_loss')
        net_profit = self.trade_data["net_profit_loss"].sum()

        # (C) Calcular costos totales (solo fees, ya que slippage está en el precio)
        total_fees = self.trade_data["fees"].sum()
        
        # ✅ FIX: No sumar slippage_cost como un costo separado, ya está incluido en el precio
        # total_slippage_cost = self.trade_data["slippage_cost"].sum()
        # total_costs = total_fees + total_slippage_cost
        total_costs = total_fees  # ✅ Solo consideramos fees como costos

        # (D) Verificación: net_profit debería ser igual a (gross_profit - total_fees)
        # print(f"Verif -> net_profit calculado: {net_profit}, "
        #       f"gross_profit - total_costs: {gross_profit - total_costs}")

        # (E) Otras métricas
        total_profit_net = winning_trades_net["net_profit_loss"].sum()
        total_loss_net = abs(losing_trades_net["net_profit_loss"].sum())
        profit_factor = total_profit_net / total_loss_net if total_loss_net > 0 else np.nan

        # ✅ MEJORA: Mover las métricas relevantes al resumen general
        num_wins_net = len(winning_trades_net)
        num_loss_net = len(losing_trades_net)
        win_loss_ratio = (num_wins_net / num_loss_net) if num_loss_net > 0 else np.nan

        expectancy = 0.0
        if len(self.trade_data) > 0:
            avg_winning_trade = winning_trades_net["net_profit_loss"].mean() if not winning_trades_net.empty else 0
            avg_losing_trade = losing_trades_net["net_profit_loss"].mean() if not losing_trades_net.empty else 0
            expectancy = ((avg_winning_trade * num_wins_net) -
                        (abs(avg_losing_trade) * num_loss_net)) / len(self.trade_data)

        percent_profitable = 0.0
        if total_trades > 0:
            percent_profitable = (len(winning_trades_net) / total_trades) * 100
            
        # Calcular el ROI sobre el capital inicial
        roi_percentage = (net_profit / self.initial_capital) * 100 if self.initial_capital > 0 else 0

        # ✅ Añadir información de moneda a los valores
        result = {
            "gross_profit": round(gross_profit, 2),      # Antes de costos, pero ya incluye slippage
            "net_profit": round(net_profit, 2),          # Después de costos (fees)
            "ROI": round(roi_percentage, 2),             # Retorno sobre inversión en porcentaje
            "total_trades": total_trades,
            "percent_profitable": round(percent_profitable, 2),
            "profit_factor": round(profit_factor, 2),
            # ✅ NUEVAS MÉTRICAS EN EL RESUMEN
            "win_loss_ratio": round(win_loss_ratio, 2) if not np.isnan(win_loss_ratio) else "N/A",
            "expectancy": round(expectancy, 2),
        }
        
        return result
        
    def compute_profit_loss_analysis(self) -> dict:
        """
        Métricas de beneficios/pérdidas a nivel bruto (sin comisiones).
        Si deseas métricas netas, deberás cambiar a 'net_profit_loss'.
        """

        # 📌 Usamos 'gross_profit_loss' para separar bien lo BRUTO.
        winning_trades_gross = self.trade_data[self.trade_data["gross_profit_loss"] > 0]
        losing_trades_gross = self.trade_data[self.trade_data["gross_profit_loss"] < 0]

        # Beneficio Bruto Total en trades ganadores
        total_gross_profit = winning_trades_gross["gross_profit_loss"].sum()

        # Pérdida Bruta Total en trades perdedores
        total_gross_loss = losing_trades_gross["gross_profit_loss"].sum()

        # 'gross_profit' = suma total bruta (ganancias + pérdidas)
        gross_profit = total_gross_profit + total_gross_loss

        # Rachas ganadoras y perdedoras (en NET)
        winning_trades_net = self.trade_data[self.trade_data["net_profit_loss"] > 0]
        losing_trades_net = self.trade_data[self.trade_data["net_profit_loss"] < 0]
        
        # ✅ FIX: Cálculo correcto de rachas consecutivas
        # Crear una serie con 1 para ganadores, 0 para perdedores
        win_streak = (self.trade_data["net_profit_loss"] > 0).astype(int)
        
        # Inicializar contadores
        current_win_streak = 0
        current_loss_streak = 0
        max_win_streak = 0
        max_loss_streak = 0
        
        # Iterar a través de los resultados de los trades
        for is_win in win_streak:
            if is_win == 1:
                # Trade ganador
                current_win_streak += 1
                current_loss_streak = 0
                # Actualizar máximo de racha ganadora si es necesario
                max_win_streak = max(max_win_streak, current_win_streak)
            else:
                # Trade perdedor
                current_loss_streak += 1
                current_win_streak = 0
                # Actualizar máximo de racha perdedora si es necesario
                max_loss_streak = max(max_loss_streak, current_loss_streak)

        # Estadísticas de trades individuales (netas)
        avg_trade_net_profit = self.trade_data["net_profit_loss"].mean()
        avg_winning_trade = winning_trades_net["net_profit_loss"].mean() if not winning_trades_net.empty else 0
        avg_losing_trade = losing_trades_net["net_profit_loss"].mean() if not losing_trades_net.empty else 0
        largest_winning_trade = winning_trades_net["net_profit_loss"].max() if not winning_trades_net.empty else 0
        largest_losing_trade = losing_trades_net["net_profit_loss"].min() if not losing_trades_net.empty else 0

        # Porcentaje de ganancia/pérdida media por trade
        avg_winning_pct = (winning_trades_net["net_profit_loss"] / self.initial_capital * 100).mean() if not winning_trades_net.empty else 0
        avg_losing_pct = (losing_trades_net["net_profit_loss"] / self.initial_capital * 100).mean() if not losing_trades_net.empty else 0

        std_profit = self.trade_data["net_profit_loss"].std()

        return {
            # Bruto
            "total_gross_profit": round(total_gross_profit, 2),
            "total_gross_loss": round(total_gross_loss, 2),
            # Rachas (en neto)
            "max_consecutive_wins": max_win_streak,
            "max_consecutive_losses": max_loss_streak,
            # Estadísticas netas
            "avg_trade_net_profit": round(avg_trade_net_profit, 2),
            "avg_winning_trade": round(avg_winning_trade, 2),
            "avg_losing_trade": round(avg_losing_trade, 2),
            "avg_winning_trade_pct": round(avg_winning_pct, 2),
            "avg_losing_trade_pct": round(avg_losing_pct, 2),
            "largest_winning_trade": round(largest_winning_trade, 2),
            "largest_losing_trade": round(largest_losing_trade, 2),
            "std_profit": round(std_profit, 2),
        }

    def calculate_average_trade_durations_in_bars(self) -> tuple:
        """
        Calcula el promedio de duración en barras de los trades ganadores y perdedores.
        """
        winning_trades = self.trade_data[self.trade_data["net_profit_loss"] > 0]
        losing_trades = self.trade_data[self.trade_data["net_profit_loss"] < 0]

        avg_bars_positive = winning_trades["duration_bars"].mean() if not winning_trades.empty else 0
        avg_bars_negative = losing_trades["duration_bars"].mean() if not losing_trades.empty else 0

        return round(avg_bars_positive, 2), round(avg_bars_negative, 2)


    def compute_drawdown_analysis(self) -> dict:
        """
        Calcula el análisis de drawdown: 
        - Máximo drawdown (en valor absoluto y porcentaje)
        - Duración del drawdown
        - Drawdown medio
        """
        cumulative_capital = self.trade_data["cumulative_capital"]

        # 1. Calcular los picos de capital
        peak_capital = cumulative_capital.cummax()

        # 2. Calcular el drawdown como la caída desde el pico
        drawdown = peak_capital - cumulative_capital

        # 3. Máximo Drawdown (valor absoluto)
        max_drawdown = drawdown.max()

        # 4. Porcentaje de Drawdown Máximo respecto al pico máximo
        max_drawdown_pct = (max_drawdown / peak_capital.max()) * 100 if peak_capital.max() > 0 else 0

        # 5. Duración del Drawdown: Tiempo entre el máximo drawdown y la recuperación del capital
        drawdown_periods = (drawdown > 0).astype(int)  # 1 si hay drawdown, 0 si no
        drawdown_duration = drawdown_periods.groupby((drawdown_periods != drawdown_periods.shift()).cumsum()).cumsum().max()

        # 6. 📌 Drawdown Medio 📌 (Promedio de todos los drawdowns registrados)
        avg_drawdown = drawdown.mean()

        return {
            "max_drawdown": round(max_drawdown, 2),
            "max_drawdown_pct": round(max_drawdown_pct, 2),
            "drawdown_duration": int(drawdown_duration),
            "avg_drawdown": round(avg_drawdown, 2),
        }


    def compute_time_statistics(self) -> dict:
        """
        Calcula estadísticas detalladas relacionadas con el tiempo de las operaciones.
        Utiliza la clase Timeframe para conversiones precisas de tiempo.
        """
        # 1. Convertir timestamps a segundos para calcular duración en tiempo real
        self.trade_data["trade_duration_seconds"] = (
            self.trade_data["exit_timestamp"] - self.trade_data["entry_timestamp"]
        ).dt.total_seconds()

        winning_trades = self.trade_data[self.trade_data["net_profit_loss"] > 0]
        losing_trades = self.trade_data[self.trade_data["net_profit_loss"] < 0]

        # 2. Duración promedio de trades ganadores y perdedores (en minutos)
        avg_winning_trade_duration_minutes = (
            winning_trades["trade_duration_seconds"].mean() / 60 if not winning_trades.empty else 0
        )
        avg_losing_trade_duration_minutes = (
            losing_trades["trade_duration_seconds"].mean() / 60 if not losing_trades.empty else 0
        )
        
        # Calcular duración máxima y mínima de trades
        max_trade_duration_minutes = self.trade_data["trade_duration_seconds"].max() / 60 if not self.trade_data.empty else 0
        min_trade_duration_minutes = self.trade_data["trade_duration_seconds"].min() / 60 if not self.trade_data.empty else 0

        # 3. Media de barras en pérdida y ganancia para trades ganadores
        avg_bars_in_loss_winners = (
            winning_trades["bars_in_loss"].mean() if not winning_trades.empty else 0
        )
        avg_bars_in_profit_winners = (
            winning_trades["bars_in_profit"].mean() if not winning_trades.empty else 0
        )

        # 4. Media de barras en pérdida y ganancia para trades perdedores
        avg_bars_in_loss_losers = (
            losing_trades["bars_in_loss"].mean() if not losing_trades.empty else 0
        )
        avg_bars_in_profit_losers = (
            losing_trades["bars_in_profit"].mean() if not losing_trades.empty else 0
        )

        # 5. Calcular el tiempo total en el mercado
        total_time_in_trades = self.trade_data["trade_duration_seconds"].sum()
        
        # 6. Calcular duración total del backtest
        backtest_start = self.trade_data["entry_timestamp"].min()
        backtest_end = self.trade_data["exit_timestamp"].max()
        total_backtest_duration = (backtest_end - backtest_start).total_seconds()
        
        # Convertir a formato más legible (días, horas, minutos)
        days = int(total_backtest_duration // (24 * 3600))
        remaining = total_backtest_duration % (24 * 3600)
        hours = int(remaining // 3600)
        remaining %= 3600
        minutes = int(remaining // 60)
        
        backtest_duration_str = ""
        if days > 0:
            backtest_duration_str += f"{days}d "
        if hours > 0 or days > 0:
            backtest_duration_str += f"{hours}h "
        backtest_duration_str += f"{minutes}m"
        
        # 7. Tiempo en mercado en porcentaje y horas
        time_in_market_pct = (total_time_in_trades / total_backtest_duration) * 100 if total_backtest_duration > 0 else 0
        time_in_market_hours = total_time_in_trades / 3600  # Convertir segundos a horas
        
        # 8. Frecuencia de operaciones (trades por día)
        trades_per_day = (len(self.trade_data) / (total_backtest_duration / (24 * 3600))) if total_backtest_duration > 0 else 0
        
        # 9. Obtener y usar la información del timeframe directamente de la estrategia
        # Usar la propiedad "hours" del objeto Timeframe si está disponible
        timeframe_hours = 0
        
        # Intentar obtener el objeto Timeframe
        if hasattr(self, 'timeframe') and hasattr(self.timeframe, 'hours'):
            timeframe_hours = self.timeframe.hours
            timeframe_str = self.timeframe.value
        else:
            # Fallback: extraer del DataFrame o usar valor por defecto
            tf_obj = self.trade_data["Timeframe"].iloc[0] if "Timeframe" in self.trade_data.columns else None
            if hasattr(tf_obj, 'hours'):
                timeframe_hours = tf_obj.hours
                timeframe_str = tf_obj.value
            else:
                # Extraer del string del timeframe si no es un objeto Timeframe
                timeframe_str = str(tf_obj).split(".")[-1] if tf_obj else "M1"
                
                # Convertir a horas basado en la nomenclatura estándar
                if timeframe_str.startswith("M"):
                    # Formatos como M1, M5, M15, M30
                    minutes = int(timeframe_str[1:]) if len(timeframe_str) > 1 else 1
                    timeframe_hours = minutes / 60
                elif timeframe_str.startswith("H"):
                    # Formatos como H1, H4
                    timeframe_hours = int(timeframe_str[1:]) if len(timeframe_str) > 1 else 1
                elif timeframe_str == "D1":
                    timeframe_hours = 24  # 1 día = 24 horas
                elif timeframe_str == "W1":
                    timeframe_hours = 24 * 7  # 1 semana = 168 horas
                elif timeframe_str == "MN1":
                    timeframe_hours = 24 * 30  # 1 mes ≈ 720 horas
                else:
                    timeframe_hours = 1/60  # Valor por defecto: 1 minuto
        
        # Convertir periodos de barras a minutos usando el timeframe
        bar_to_minutes = timeframe_hours * 60
        
        # 10. Duración media en unidades de timeframe
        avg_winning_trade_duration_bars = avg_winning_trade_duration_minutes / bar_to_minutes if bar_to_minutes > 0 else 0
        avg_losing_trade_duration_bars = avg_losing_trade_duration_minutes / bar_to_minutes if bar_to_minutes > 0 else 0

        return {
            "backtest_duration": backtest_duration_str,
            "avg_winning_trade_duration_min": round(avg_winning_trade_duration_minutes, 2),
            "avg_losing_trade_duration_min": round(avg_losing_trade_duration_minutes, 2),
            "avg_winning_trade_duration_bars": round(avg_winning_trade_duration_bars, 2),
            "avg_losing_trade_duration_bars": round(avg_losing_trade_duration_bars, 2),
            "max_trade_duration_min": round(max_trade_duration_minutes, 2),
            "min_trade_duration_min": round(min_trade_duration_minutes, 2),
            "time_in_market_pct": round(time_in_market_pct, 2),
            "time_in_market_hours": round(time_in_market_hours, 2),
            "trades_per_day": round(trades_per_day, 2),
            "avg_bars_in_loss_winners": round(avg_bars_in_loss_winners, 2),
            "avg_bars_in_profit_winners": round(avg_bars_in_profit_winners, 2),
            "avg_bars_in_loss_losers": round(avg_bars_in_loss_losers, 2),
            "avg_bars_in_profit_losers": round(avg_bars_in_profit_losers, 2),
            "timeframe": timeframe_str,
            "timeframe_hours": timeframe_hours,
            "bar_to_minutes": bar_to_minutes,
        }

    def compute_performance_ratios(self) -> dict:
        """
        Calcula las métricas de rendimiento:
        - Índice de Sharpe
        - Ratio de Sortino
        - Factor de Recuperación
        - Índice de TradeStation (TS Index)
        """
        returns = self.trade_data["net_profit_loss"]  # Retornos por trade
        mean_return = returns.mean()
        std_return = returns.std()  # Desviación estándar de los retornos
        downside_std = returns[returns < 0].std()  # Desviación estándar de pérdidas

        # 1. Índice de Sharpe: Exceso de retorno sobre la volatilidad total
        sharpe_ratio = mean_return / std_return if std_return > 0 else np.nan

        # 2. Ratio de Sortino: Exceso de retorno sobre la volatilidad de pérdidas
        sortino_ratio = mean_return / downside_std if downside_std > 0 else np.nan

        # 3. Factor de Recuperación: Beneficio Neto / Máximo Drawdown
        drawdown_analysis = self.compute_drawdown_analysis()
        max_drawdown = drawdown_analysis["max_drawdown"]
        recovery_factor = (self.compute_general_summary()["net_profit"] / max_drawdown) if max_drawdown > 0 else np.nan

        return {
            "sharpe_ratio": round(sharpe_ratio, 2),
            "sortino_ratio": round(sortino_ratio, 2),
            "recovery_factor": round(recovery_factor, 2),
        }

    def compute_operational_costs(self) -> dict:
        """
        Calcula los costos operacionales del backtest:
        """
        total_fees = self.trade_data["fees"].sum()
        total_slippage_cost = self.trade_data["slippage_cost"].sum()
        total_costs = total_fees  # ✅ FIX: Solo fees para cálculos de P&L

        # Tomamos 'gross_profit' de la sumatoria global (compute_general_summary)
        gross_profit_global = self.compute_general_summary()["gross_profit"]
        # Evitar división por cero
        if abs(gross_profit_global) > 1e-9:
            costs_as_pct_of_gross_profit = (total_fees / abs(gross_profit_global)) * 100
        else:
            costs_as_pct_of_gross_profit = np.nan

        # Costos por trade
        avg_fee_per_trade = total_fees / len(self.trade_data) if len(self.trade_data) > 0 else 0
        
        # Costos como porcentaje del capital inicial
        fees_pct_of_capital = (total_fees / self.initial_capital) * 100 if self.initial_capital > 0 else 0

        return {
            "total_fees": round(total_fees, 2),
            "total_slippage_cost": round(total_slippage_cost, 2),  # Solo informativo
            "total_costs": round(total_fees, 2),  # ✅ Solo fees, no incluir slippage
            "avg_fee_per_trade": round(avg_fee_per_trade, 2),
            "fees_pct_of_capital": round(fees_pct_of_capital, 2),
            "costs_as_pct_of_gross_profit": round(costs_as_pct_of_gross_profit, 2) if not np.isnan(costs_as_pct_of_gross_profit) else "N/A",
        }