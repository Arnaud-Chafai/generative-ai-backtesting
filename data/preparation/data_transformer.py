from data.loaders.data_provider import CSVDataProvider, MT5BacktestDataProvider
from data.preparation.data_cleaner import DataCleaner
from utils.timeframe import Timeframe
import pandas as pd
import os

class DataTransformer:
    def __init__(self, df: pd.DataFrame):
        """
        Inicializa el DataTransformer con un DataFrame.
        """
        self.df = df

    def resample_data(self, timeframe: Timeframe) -> pd.DataFrame:
        """
        Realiza resampling del DataFrame para el timeframe especificado.
        """
        # Validar índice
        if not isinstance(self.df.index, pd.DatetimeIndex):
            raise ValueError("El índice del DataFrame debe ser un DatetimeIndex.")

        # Mapeo de timeframes a pandas
        timeframe_mapping = {
            Timeframe.M1: "1min",
            Timeframe.M5: "5min",
            Timeframe.M15: "15min",
            Timeframe.M30: "30min",
            Timeframe.H1: "1h",
            Timeframe.H4: "4h",
            Timeframe.D1: "1d",
            Timeframe.W1: "1w",
            Timeframe.MN1: "1M",
        }

        if timeframe not in timeframe_mapping:
            raise ValueError(f"El timeframe '{timeframe}' no está soportado.")

        resampled_df = self.df.resample(timeframe_mapping[timeframe]).agg({
            "Open": "first",
            "High": "max",
            "Low": "min",
            "Close": "last",
            "Volume": "sum"
        })

        # Eliminar NaN (opcional)
        resampled_df.dropna(inplace=True)
        return resampled_df


    def resample_timeframes(self, timeframes: list[Timeframe]) -> dict:
        """
        Realiza resampling del DataFrame para múltiples timeframes.
        """
        resampled_data = {}

        for timeframe in timeframes:
            print(f"Resampleando datos para el timeframe: {timeframe.value}...")
            resampled_data[timeframe.value] = self.resample_data(timeframe)

        return resampled_data


    def calculate_ema(self, periods: list) -> 'DataTransformer':
        """
        Calcula las EMAs para los periodos especificados y las añade al DataFrame.
        """
        for period in periods:
            self.df[f"EMA_{period}"] = self.df["Close"].ewm(span=period).mean()
        return self


    def calculate_volatility_pct_change(self, periods: list) -> 'DataTransformer':
        """
        Calcula el cambio porcentual de la volatilidad (desviación estándar)
        para los periodos especificados y las añade al DataFrame.
        Rellena los valores NaN con  back-fill.
        """
        for period in periods:
            col_name = f"Volatility_pct_change_{period}"
            # Calcular la volatilidad (desviación estándar) y su cambio porcentual
            self.df[col_name] = (
                self.df["Close"]
                .rolling(period)
                .std()
                .pct_change(fill_method=None)
                .round(2)
            )
            # Rellenar valores NaN con back-fill
            self.df[col_name] = self.df[col_name].bfill()
        return self


    def calculate_pct_change(self, periods: list) -> 'DataTransformer':
        """
        Calcula el cambio porcentual para los periodos especificados y las añade al DataFrame.
        Escala los resultados para que sean porcentajes más intuitivos.
        Rellena los valores NaN con  back-fill.
        """
        for period in periods:
            col_name = f"Pct_change_{period}"
            # Calcular el cambio porcentual
            self.df[col_name] = (
                self.df["Close"]
                .pct_change(period)
                .mul(100)
                .round(2)
            )
            # Rellenar valores NaN con forward-fill
            self.df[col_name] = self.df[col_name].bfill()
        return self


    def volume_pct_change(self, periods: list) -> 'DataTransformer':
        """
        Calcula el cambio porcentual del volumen para los periodos especificados y las añade al DataFrame.
        Rellena los valores NaN con  back-fill.
        """
        for period in periods:
            col_name = f"Volume_pct_change_{period}"
            # Calcular el cambio porcentual del volumen
            self.df[col_name] = (
                self.df["Volume"]
                .pct_change(period)
                .mul(100)
                .round(2)
            )
            # Rellenar valores NaN con forward-fill
            self.df[col_name] = self.df[col_name].bfill()
        return self


    def calculate_cumulative_volume_pct(self, periods: list) -> 'DataTransformer':
        """
        Calcula el cambio porcentual acumulativo del volumen para distintos periodos
        y lo añade al DataFrame.
        Rellena los valores NaN con  back-fill.
        """
        for period in periods:
            col_name = f"Cumulative_Volume_pct_{period}"
            # Calcular el volumen acumulativo
            cumulative_volume = self.df["Volume"].rolling(window=period, min_periods=1).sum()
            # Calcular el cambio porcentual acumulativo
            self.df[col_name] = cumulative_volume.pct_change().mul(100).round(2)
            # Rellenar valores NaN con forward-fill
            self.df[col_name] = self.df[col_name].bfill()
        return self


    def calculate_vwap(self) -> 'DataTransformer':
        """
        Calcula el precio promedio ponderado por volumen (VWAP) y lo añade al DataFrame.
        """
        # Calcular el precio promedio ponderado por volumen (VWAP)
        self.df["VWAP"] = (self.df["Close"] * self.df["Volume"]).cumsum() / self.df["Volume"].cumsum().round(3)
        return self  


    def hour(self) -> 'DataTransformer':
        """
        Añade la columna 'Hour' al DataFrame con la hora del día (0-23).
        """
        self.df["Hour"] = self.df.index.hour
        return self


    def minute(self) -> 'DataTransformer':
        """
        Añade la columna 'Minute' al DataFrame con el minuto de la hora (0-59).
        """
        self.df["Minute"] = self.df.index.minute
        return self


    def day_of_week(self) -> 'DataTransformer':
        """
        Añade la columna 'Day_of_Week' al DataFrame con el día de la semana (0-6).
        """
        self.df["Day"] = self.df.index.dayofweek
        return self


    def month_of_year(self) -> 'DataTransformer':
        """
        Añade la columna 'Month_of_Year' al DataFrame con el mes del año (1-12).
        """
        self.df["Month"] = self.df.index.month
        return self


    def trimester_of_year(self) -> 'DataTransformer':
        """
        Añade la columna 'Trimester_of_Year' al DataFrame con el trimestre del año (1-4).
        """
        self.df["Trimester"] = self.df.index.quarter
        return self


    def year(self) -> 'DataTransformer':
        """
        Añade la columna 'Year' al DataFrame con el año.
        """
        self.df["Year"] = self.df.index.year
        return self


    def asian_session(self) -> 'DataTransformer':
        """Sesión asiática: de 00:00 a 08:59 del mismo día"""
        self.df["Asian_session"] = ((self.df.index.hour >= 0) & (self.df.index.hour < 9)).astype(int)
        return self

    def european_session(self) -> 'DataTransformer':
        """Sesión europea: de 09:00 a 15:29"""
        self.df["European_session"] = (
            ((self.df.index.hour >= 9) & (self.df.index.hour < 15)) |
            ((self.df.index.hour == 15) & (self.df.index.minute < 30))
        ).astype(int)
        return self

    def american_session(self) -> 'DataTransformer':
        """Sesión americana: de 15:30 a 23:59"""
        self.df["American_session"] = (
            ((self.df.index.hour == 15) & (self.df.index.minute >= 30)) |
            (self.df.index.hour >= 16)
        ).astype(int)
        return self


    def clean_sessions(self) -> 'DataTransformer':
        """
        Elimina filas del DataFrame donde no hay datos válidos para las sesiones.
        """
        session_cols = [
            "Max_european_session", 
            "Min_european_session", 
            "Max_american_session", 
            "Min_american_session", 
            "Max_asian_session", 
            "Min_asian_session"
        ]
        # Mantener solo las filas donde no hay valores NaN en las columnas de sesiones
        self.df = self.df.loc[self.df[session_cols].notna().all(axis=1)]
        return self


    def max_asian_session(self) -> 'DataTransformer':
        asian_data = self.df[self.df["Asian_session"] == 1]
        max_per_day = asian_data.groupby(asian_data.index.date)["High"].max()
        self.df["Max_asian_session"] = pd.Series(self.df.index.date, index=self.df.index).map(max_per_day)
        return self

    def min_asian_session(self) -> 'DataTransformer':
        asian_data = self.df[self.df["Asian_session"] == 1]
        min_per_day = asian_data.groupby(asian_data.index.date)["Low"].min()
        self.df["Min_asian_session"] = pd.Series(self.df.index.date, index=self.df.index).map(min_per_day)
        return self

    def max_european_session(self) -> 'DataTransformer':
        european_data = self.df[self.df["European_session"] == 1]
        max_per_day = european_data.groupby(european_data.index.date)["High"].max()
        self.df["Max_european_session"] = pd.Series(self.df.index.date, index=self.df.index).map(max_per_day)
        return self

    def min_european_session(self) -> 'DataTransformer':
        european_data = self.df[self.df["European_session"] == 1]
        min_per_day = european_data.groupby(european_data.index.date)["Low"].min()
        self.df["Min_european_session"] = pd.Series(self.df.index.date, index=self.df.index).map(min_per_day)
        return self

    def max_american_session(self) -> 'DataTransformer':
        american_data = self.df[self.df["American_session"] == 1]
        max_per_day = american_data.groupby(american_data.index.date)["High"].max()
        self.df["Max_american_session"] = pd.Series(self.df.index.date, index=self.df.index).map(max_per_day)
        return self

    def min_american_session(self) -> 'DataTransformer':
        american_data = self.df[self.df["American_session"] == 1]
        min_per_day = american_data.groupby(american_data.index.date)["Low"].min()
        self.df["Min_american_session"] = pd.Series(self.df.index.date, index=self.df.index).map(min_per_day)
        return self



    def add_daily_high(self) -> 'DataTransformer':
        daily_highs = self.df.groupby(self.df.index.date)["High"].max().shift(1)
        self.df["Daily_high_before"] = pd.Series(self.df.index.date, index=self.df.index).map(daily_highs).bfill()
        return self


    def add_daily_low(self) -> 'DataTransformer':
        daily_lows = self.df.groupby(self.df.index.date)["Low"].min().shift(1)
        self.df["Daily_low_before"] = pd.Series(self.df.index.date, index=self.df.index).map(daily_lows).bfill()
        return self


    def add_weekly_high(self) -> 'DataTransformer':
        weekly_highs = self.df.groupby(self.df.index.to_period("W"))["High"].max().shift(1)
        self.df["Weekly_high_before"] = pd.Series(self.df.index.to_period("W"), index=self.df.index).map(weekly_highs).bfill()
        return self


    def add_weekly_low(self) -> 'DataTransformer':
        weekly_lows = self.df.groupby(self.df.index.to_period("W"))["Low"].min().shift(1)
        self.df["Weekly_low_before"] = pd.Series(self.df.index.to_period("W"), index=self.df.index).map(weekly_lows).bfill()
        return self

    def add_monthly_high(self) -> 'DataTransformer':
        monthly = self.df["High"].groupby(self.df.index.to_period("M")).max()
        shifted = monthly.shift(1)
        mapping = pd.Series(self.df.index.to_period("M"), index=self.df.index).map(shifted)
        self.df["Monthly_high_before"] = mapping.bfill()
        return self

    def add_monthly_low(self) -> 'DataTransformer':
        monthly = self.df["Low"].groupby(self.df.index.to_period("M")).min()
        shifted = monthly.shift(1)
        mapping = pd.Series(self.df.index.to_period("M"), index=self.df.index).map(shifted)
        self.df["Monthly_low_before"] = mapping.bfill()
        return self

    def convert_to_heiken_ashi(self) -> 'DataTransformer':
        """
        Convierte las velas OHLC del DataFrame a formato Heiken Ashi,
        reemplazando las columnas originales: 'Open', 'High', 'Low', 'Close'.
        """
        ha_close = (self.df["Open"] + self.df["High"] + self.df["Low"] + self.df["Close"]) / 4
        ha_open = [self.df["Open"].iloc[0]]  # Primer valor inicial

        for i in range(1, len(self.df)):
            ha_open.append((ha_open[i - 1] + ha_close.iloc[i - 1]) / 2)

        self.df["Open"] = pd.Series(ha_open, index=self.df.index)
        self.df["Close"] = ha_close
        self.df["High"] = self.df[["High", "Open", "Close"]].max(axis=1)
        self.df["Low"] = self.df[["Low", "Open", "Close"]].min(axis=1)

        return self


    def detectar_onebar_pullback_alcista(self) -> 'DataTransformer':
        """
        Detecta el patrón 'one bar pullback alcista' y añade una columna booleana 'OBP_alcista'
        que indica True cuando se detecta el patrón.
        """
        # Inicializar la columna
        self.df = self.df.assign(OBP_alcista=False)

        # Lista para almacenar índices que cumplen el patrón
        indices_obp = []

        for i in range(2, len(self.df)):
            vela1 = self.df.iloc[i - 2]  # Primera vela
            vela2 = self.df.iloc[i - 1]  # Segunda vela (pullback)
            vela3 = self.df.iloc[i]      # Tercera vela (ruptura)

            try:
                # Condiciones del patrón
                vela1_alcista = vela1['Close'] > vela1['Open']  # Primera vela alcista
                pullback_valido = (vela2['High'] < vela1['High'] and vela2['Low'] >= vela1['Low'])
                ruptura = vela3['High'] > vela1['High']

                # Si todas las condiciones se cumplen, añadir el índice a la lista
                if all([vela1_alcista, pullback_valido, ruptura]):
                    indices_obp.append(self.df.index[i])

            except Exception as e:
                print(f"Error procesando índice {i}: {e}")
                continue

        # Actualizar la columna en una sola operación
        self.df.loc[indices_obp, 'OBP_alcista'] = True

        return self


    def detectar_onebar_pullback_alcista_extendido(self, max_pullback_length: int = 10) -> 'DataTransformer':
        """
        Detecta el patrón 'one bar pullback alcista extendido'.
        Permite entre 1 y `max_pullback_length` velas dentro del rango de la vela inicial.
        Añade una columna booleana 'OBP_alcista_extend' al DataFrame.
        """
        # Inicializar la columna con valores False
        self.df = self.df.assign(OBP_alcista_extend=False)

        # Lista para almacenar índices que cumplen el patrón
        indices_obp = []

        for i in range(1, len(self.df)):  # Recorremos cada vela
            # Intentar pullbacks de 1 a max_pullback_length velas
            for pb_length in range(1, max_pullback_length + 1):
                if i - pb_length - 1 < 0:  # Verificar que haya suficiente historia
                    break

                vela1 = self.df.iloc[i - pb_length - 1]  # Vela inicial

                # Verificar si la primera vela es alcista
                if vela1['Close'] > vela1['Open']:
                    pullback_valido = True

                    # Evaluar todas las velas dentro del pullback
                    for j in range(i - pb_length, i):
                        vela_actual = self.df.iloc[j]

                        # Si alguna vela no cumple el rango del pullback, descartar
                        if vela_actual['High'] > vela1['High'] or vela_actual['Low'] < vela1['Low']:
                            pullback_valido = False
                            break

                    # Si todas las velas cumplen el rango y se encuentra ruptura
                    if pullback_valido and self.df.iloc[i]['High'] > vela1['High']:
                        indices_obp.append(self.df.index[i])
                        break  # Detener al encontrar un patrón válido

        # Actualizar la columna en una sola operación
        self.df.loc[indices_obp, 'OBP_alcista_extend'] = True

        return self


    def detectar_onebar_pullback_bajista(self) -> 'DataTransformer':
        """
        Detecta el patrón 'one bar pullback bajista' y añade una columna booleana 'OBP_bajista'
        que indica True cuando se detecta el patrón.
        """
        # Inicializar la columna con valores False
        self.df = self.df.assign(OBP_bajista=False)

        # Lista para almacenar índices que cumplen el patrón
        indices_obp = []

        for i in range(2, len(self.df)):
            vela1 = self.df.iloc[i - 2]  # Primera vela
            vela2 = self.df.iloc[i - 1]  # Segunda vela (pullback)
            vela3 = self.df.iloc[i]      # Tercera vela (ruptura)

            try:
                # Condiciones del patrón
                vela1_bajista = vela1['Close'] < vela1['Open']  # Primera vela bajista
                pullback_valido = (vela2['Low'] > vela1['Low'] and 
                                    vela2['High'] <= vela1['High'])  # Pullback dentro de la primera vela
                ruptura = vela3['Low'] < vela1['Low']  # Tercera vela rompe el mínimo de la primera

                # Agregar índice si todas las condiciones se cumplen
                if all([vela1_bajista, pullback_valido, ruptura]):
                    indices_obp.append(self.df.index[i])

            except Exception as e:
                print(f"Error procesando índice {i}: {e}")
                continue

        # Actualizar la columna en una sola operación
        self.df.loc[indices_obp, 'OBP_bajista'] = True

        return self


    def detectar_onebar_pullback_bajista_extendido(self, max_pullback_length: int = 10) -> 'DataTransformer':
        """
        Detecta el patrón 'one bar pullback bajista extendido'.
        Permite entre 1 y `max_pullback_length` velas dentro del rango de la vela inicial.
        Añade una columna booleana 'OBP_bajista_extend' al DataFrame.
        """
        # Inicializar la columna con valores False
        self.df = self.df.assign(OBP_bajista_extend=False)

        # Lista para almacenar índices que cumplen el patrón
        indices_obp = []

        for i in range(1, len(self.df)):  # Recorremos cada vela
            # Intentar pullbacks de 1 a max_pullback_length velas
            for pb_length in range(1, max_pullback_length + 1):
                if i - pb_length - 1 < 0:  # Verificar que haya suficiente historia
                    break

                vela1 = self.df.iloc[i - pb_length - 1]  # Vela inicial

                # Verificar si la primera vela es bajista
                if vela1['Close'] < vela1['Open']:
                    pullback_valido = True

                    # Evaluar todas las velas dentro del pullback
                    for j in range(i - pb_length, i):
                        vela_actual = self.df.iloc[j]

                        # Si alguna vela no cumple el rango del pullback, descartar
                        if vela_actual['Low'] < vela1['Low'] or vela_actual['High'] > vela1['High']:
                            pullback_valido = False
                            break

                    # Si todas las velas cumplen el rango y se encuentra ruptura
                    if pullback_valido and self.df.iloc[i]['Low'] < vela1['Low']:
                        indices_obp.append(self.df.index[i])
                        break  # Detener al encontrar un patrón válido

        # Actualizar la columna en una sola operación
        self.df.loc[indices_obp, 'OBP_bajista_extend'] = True

        return self


    def prepare_data(self, timeframes: list, ema_periods: list, volatility_periods: list, 
                        pct_change_periods: list, volume_periods: list, cumulative_volume_periods: list, 
                        obp_range: int) -> dict:
            """
            Prepara los datos resampleando, calculando indicadores y limpiando los datos.

            Args:
                timeframes (list): Lista de timeframes para resampling (e.g., ['5min', '15min', 'h']).
                ema_periods (list): Períodos para calcular EMAs.
                volatility_periods (list): Períodos para calcular cambios porcentuales de volatilidad.
                pct_change_periods (list): Períodos para calcular cambios porcentuales de precios.
                volume_periods (list): Períodos para calcular cambios porcentuales de volumen.
                cumulative_volume_periods (list): Períodos para calcular el volumen acumulativo.
                obp_range (int): Rango máximo para detectar patrones OBP extendidos.

            Returns:
                dict: Diccionario con DataFrames procesados para cada timeframe.
            """
            enriched_data = {}

            # Iterar sobre los timeframes y procesar los datos
            for timeframe in timeframes:
                print(f"Procesando timeframe: {timeframe}...")

                # Resamplear los datos
                resampled_df = self.resample_data(timeframe)

                # Procesar los datos resampleados
                transformer_resampled = DataTransformer(resampled_df)
                enriched_df = (
                    transformer_resampled
                    .convert_to_heiken_ashi()                                       # Convertir a Heiken Ashi
                    .calculate_ema(ema_periods)                                     # Calcular EMAs
                    .calculate_volatility_pct_change(volatility_periods)            # Calcular volatilidad
                    .calculate_pct_change(pct_change_periods)                       # Calcular cambios porcentuales
                    .volume_pct_change(volume_periods)                              # Calcular cambios porcentuales en volumen
                    .calculate_cumulative_volume_pct(cumulative_volume_periods)     # Calcular volumen acumulado
                    .day_of_week()                                                  # Día de la semana
                    .hour()                                                         # Hora
                    .minute()                                                       # Minuto
                    .month_of_year()                                                # Mes del año
                    .trimester_of_year()                                            # Trimestre del año
                    .year()                                                         # Año
                    .calculate_vwap()                                               # Calcular VWAP
                    .european_session()                                             # Marcar sesión europea
                    .american_session()                                             # Marcar sesión americana
                    .asian_session()                                                # Marcar sesión asiática
                    .max_european_session()                                         # Máximo sesión europea
                    .min_european_session()                                         # Mínimo sesión europea
                    .max_american_session()                                         # Máximo sesión americana
                    .min_american_session()                                         # Mínimo sesión americana
                    .max_asian_session()                                            # Máximo sesión asiática
                    .min_asian_session()                                            # Mínimo sesión asiática
                    .add_daily_high()                                               # Máximo diario
                    .add_daily_low()                                                # Mínimo diario
                    .add_weekly_high()                                              # Máximo semanal
                    .add_weekly_low()                                               # Mínimo semanal
                    .add_monthly_high()                                             # Máximo mensual
                    .add_monthly_low()                                              # Mínimo mensual
                    .clean_sessions()                                               # Limpiar filas sin datos de sesiones
                    .detectar_onebar_pullback_alcista()                             # Detectar pullback alcista
                    .detectar_onebar_pullback_bajista()                             #Detectar pullback bajista
                    .detectar_onebar_pullback_alcista_extendido(obp_range)          # Detectar pullback alcista extendido
                    .detectar_onebar_pullback_bajista_extendido(obp_range)          # Detectar pullback bajista extendido
                    .transform()                                                    # Transformar y devolver el DataFrame procesado
                )
                print(f"✔ Datos procesados para el timeframe: {timeframe}.\n")

                # Almacenar el DataFrame procesado en el diccionario
                enriched_data[timeframe] = enriched_df

            return enriched_data


    def export_dataframes_to_csv(self, dataframes: dict, output_dir: str) -> None:
            """
            Exporta todos los DataFrames de un diccionario a archivos CSV separados.

            Args:
                dataframes (dict): Diccionario donde las claves son los nombres de los timeframes
                                y los valores son los DataFrames.
                output_dir (str): Directorio donde se guardarán los archivos CSV.
            """
            import os

            # Crear el directorio si no existe
            os.makedirs(output_dir, exist_ok=True)

            # Iterar sobre los DataFrames y exportar cada uno
            for timeframe, df in dataframes.items():
                output_path = os.path.join(output_dir, f"{timeframe}.csv")
                print(f"Exportando {timeframe} a {output_path}...")
                df.to_csv(output_path, index=True)
            print("✔ Exportación completada.")


    def transform(self) -> pd.DataFrame:

        """
        Devuelve el DataFrame transformado.
        """
        return self.df