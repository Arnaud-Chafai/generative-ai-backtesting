import pandas as pd
import numpy as np
from utils.timeframe import Timeframe, prepare_datetime_data

class TradeMetricsCalculator:
    def __init__(self, initial_capital: float, market_data: pd.DataFrame, timeframe: Timeframe):
        self.initial_capital = initial_capital
        self.market_data = market_data
        self.timeframe = timeframe

    def create_trade_metrics_df(self, trade_data: pd.DataFrame) -> pd.DataFrame:
        """
        Función principal que genera el DataFrame con todas las métricas.
        Coordina la ejecución de los métodos privados que encapsulan cada lógica.
        """
        # 1. Copiamos el DataFrame para no modificar el original
        df = trade_data.copy()

        # 2. Preparamos los datos (columnas de timestamp, side, etc.)
        df = self._prepare_data(df)
        
        # 3. Procesamiento temporal - NUEVO: Añadir columnas de análisis temporal
        df = prepare_datetime_data(df)

        # 4. Añadir la duración en barras
        df = self._add_duration_bars(df)

        # 5. Añadir tiempo en pérdida/ganancia
        df = self._add_time_in_profit_loss(df)

        # 6. Calcular MAE, MFE, Volatilidad y Eficiencia de ganancia
        df = self._add_mae_mfe_volatility_efficiency(df)
        
        # 7. Calcular el drawdown del trade
        df = self._add_trade_drawdown(df)

        # 8. Calcular la relación riesgo-beneficio (risk_reward_ratio)
        df = self._add_risk_reward_ratio(df)

        # 9. Calcular el riesgo aplicado, retorno sobre capital y capital acumulado
        df = self._add_risk_management_metrics(df)

        # 10. Redondear a 2 decimales y devolver el DF
        return df.round(2)

    # -------------------------------------------------------------------------
    #                             MÉTODOS PRIVADOS
    # -------------------------------------------------------------------------
    def _prepare_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Se encarga de convertir tipos de dato (timestamps) y normalizar columnas.
        """
        df["entry_timestamp"] = pd.to_datetime(df["entry_timestamp"])
        df["exit_timestamp"] = pd.to_datetime(df["exit_timestamp"])
        
        # 🔧 Manejar position_side de forma más robusta
        if "position_side" in df.columns:
            df["position_side"] = (
                df["position_side"]
                .astype(str)
                .str.replace("SignalPositionSide.", "", regex=False)
                .str.upper()
            )
        else:
            # Si no existe la columna, asumir LONG por defecto
            df["position_side"] = "LONG"
        
        return df

    def _add_duration_bars(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Añade la columna 'duration_bars' al DF, calculada según el timeframe.
        """
        df["duration_bars"] = df.apply(
            lambda row: self._convert_duration_to_bars(
                row["entry_timestamp"], 
                row["exit_timestamp"]
            ),
            axis=1
        )
        return df

    def _add_mae_mfe_volatility_efficiency(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Itera sobre cada trade para calcular MAE, MFE, Volatilidad y Profit Efficiency.
        """
        maes = []
        mfes = []
        volatilities = []
        profit_efficiencies = []

        for _, row in df.iterrows():
            mae, mfe, min_price, max_price = self._calculate_mae_mfe(
                row["entry_timestamp"],
                row["exit_timestamp"],
                row["entry_price"],
                row["usdt_amount"],
                row["position_side"]
            )
            maes.append(round(mae, 2))
            mfes.append(round(mfe, 2))

            # Volatilidad en porcentaje
            if pd.notna(max_price) and pd.notna(min_price):
                trade_volatility = ((max_price - min_price) / row["entry_price"]) * 100
            else:
                trade_volatility = np.nan
            volatilities.append(round(trade_volatility, 2) if not np.isnan(trade_volatility) else np.nan)

            # Profit Efficiency en %
            if mfe > 0:
                profit_efficiency = (row["net_profit_loss"] / mfe) * 100
                # Limitar entre 0% y 100%
                profit_efficiency = min(max(profit_efficiency, 0), 100)
            else:
                profit_efficiency = 0
            profit_efficiencies.append(round(profit_efficiency, 2))

        df["MAE"] = maes
        df["MFE"] = mfes
        df["trade_volatility"] = volatilities
        df["profit_efficiency"] = profit_efficiencies

        return df

    def _add_risk_reward_ratio(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Añade la columna 'risk_reward_ratio' usando MAE y MFE.
        """
        df["risk_reward_ratio"] = np.where(
            df["MAE"] > 0,
            df["MFE"] / df["MAE"],
            np.nan
        )
        return df

    def _add_risk_management_metrics(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Añade las columnas de riesgo aplicado, retorno sobre capital y capital acumulado.
        """
        riesgo_aplicado = []
        return_on_capital = []
        capital_previo = self.initial_capital

        for _, row in df.iterrows():
            # Riesgo aplicado en %
            riesgo = (row["usdt_amount"] / capital_previo) * 100
            # Retorno sobre capital en %
            roc = (row["net_profit_loss"] / capital_previo) * 100

            riesgo_aplicado.append(round(riesgo, 2))
            return_on_capital.append(round(roc, 2))

            # Actualizar capital
            capital_previo += row["net_profit_loss"]

        df["riesgo_aplicado"] = riesgo_aplicado
        df["return_on_capital"] = return_on_capital
        df["cumulative_capital"] = self.initial_capital + df["net_profit_loss"].cumsum()

        return df

    # -------------------------------------------------------------------------
    #                         MÉTODOS DE UTILIDAD
    # -------------------------------------------------------------------------
    def _convert_duration_to_bars(self, entry_ts: pd.Timestamp, exit_ts: pd.Timestamp) -> float:
        """
        Convierte la diferencia de tiempo entre entry_ts y exit_ts a 'barras'
        según el timeframe configurado.
        """
        duration_seconds = (exit_ts - entry_ts).total_seconds()
        bar_duration_seconds = self.timeframe.hours * 3600
        return duration_seconds / bar_duration_seconds

    def _calculate_mae_mfe(self,
                        entry_ts: pd.Timestamp,
                        exit_ts: pd.Timestamp,
                        entry_price: float,
                        quantity: float,
                        position_side: str) -> tuple:
        """
        Calcula MAE y MFE en función de los precios mínimo y máximo
        entre el timestamp de entrada y salida.
        """
        sub_data = self.market_data.loc[entry_ts:exit_ts]

        if not sub_data.empty:
            # Se asume que el DF de market_data tiene columnas 'Low' y 'High'; 
            # en caso de que no, usamos 'Close' como fallback.
            min_price = sub_data["Low"].min() if "Low" in sub_data.columns else sub_data["Close"].min()
            max_price = sub_data["High"].max() if "High" in sub_data.columns else sub_data["Close"].max()

            if position_side.upper() == "LONG":
                mae = (entry_price - min_price) * (quantity / entry_price)
                mfe = (max_price - entry_price) * (quantity / entry_price)
            elif position_side.upper() == "SHORT":
                mae = (max_price - entry_price) * (quantity / entry_price)
                mfe = (entry_price - min_price) * (quantity / entry_price)
            else:
                raise ValueError(f"⚠️ `position_side` inválido: {position_side}. Debe ser 'LONG' o 'SHORT'.")
        else:
            mae, mfe, min_price, max_price = np.nan, np.nan, np.nan, np.nan

        return mae, mfe, min_price, max_price

    def _calculate_time_in_profit_loss(self,
                                    entry_ts: pd.Timestamp,
                                    exit_ts: pd.Timestamp,
                                    entry_price: float,
                                    position_side: str) -> tuple:
        """
        Retorna una tupla (bars_in_loss, bars_in_profit) indicando cuántas barras
        estuvo la posición en pérdidas y cuántas en ganancias entre entry_ts y exit_ts.
        """

        # 1. Filtramos datos de mercado en el rango de la operación
        sub_data = self.market_data.loc[entry_ts:exit_ts]

        # Si no hay datos en ese rango, devolvemos NaN
        if sub_data.empty:
            return np.nan, np.nan

        # 2. Usamos el precio de cierre para determinar profit o pérdida
        if "Close" in sub_data.columns:
            close_prices = sub_data["Close"]
        else:
            # Fallback: si no existe 'Close', tomamos la primera columna disponible
            close_prices = sub_data.iloc[:, 0]

        # 3. Definir cuándo está en pérdidas y cuándo en ganancias
        if position_side.upper() == "LONG":
            in_loss_mask = close_prices < entry_price   # precio actual < precio entrada
        elif position_side.upper() == "SHORT":
            in_loss_mask = close_prices > entry_price   # precio actual > precio entrada
        else:
            raise ValueError(f"⚠️ `position_side` inválido: {position_side}.")

        # 4. Contar barras en pérdida y en ganancia
        bars_in_loss = in_loss_mask.sum()
        bars_in_profit = len(sub_data) - bars_in_loss

        # 5. Devolver la tupla
        return bars_in_loss, bars_in_profit
    

    def _add_time_in_profit_loss(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Añade dos columnas al DataFrame:
        - 'bars_in_loss': cuántas barras estuvo el trade en pérdidas
        - 'bars_in_profit': cuántas barras estuvo el trade en ganancias
        """
        bars_in_loss_list = []
        bars_in_profit_list = []

        for _, row in df.iterrows():
            bil, bip = self._calculate_time_in_profit_loss(
                entry_ts=row["entry_timestamp"],
                exit_ts=row["exit_timestamp"],
                entry_price=row["entry_price"],
                position_side=row["position_side"]
            )
            bars_in_loss_list.append(bil)
            bars_in_profit_list.append(bip)

        df["bars_in_loss"] = bars_in_loss_list
        df["bars_in_profit"] = bars_in_profit_list

        # Si en vez de barras, quieres la duración en horas:
        # df["hours_in_loss"] = df["bars_in_loss"] * self.timeframe.hours
        # df["hours_in_profit"] = df["bars_in_profit"] * self.timeframe.hours

        return df

    def _add_trade_drawdown(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calcula y agrega la métrica 'trade_drawdown (%)' al DataFrame.
        """
        df["trade_drawdown"] = (df["MAE"] / df["entry_price"]) * 100
        return df