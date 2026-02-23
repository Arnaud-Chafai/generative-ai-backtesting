from data.loaders.data_provider import CSVDataProvider, MT5BacktestDataProvider
from data.preparation.data_cleaner import DataCleaner
from utils.timeframe import Timeframe
import pandas as pd
import numpy as np
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
        Calcula el VWAP (Volume Weighted Average Price) con reset diario.
        """
        tp = (self.df["High"] + self.df["Low"] + self.df["Close"]) / 3
        tp_vol = tp * self.df["Volume"]
        date = self.df.index.date
        self.df["VWAP"] = tp_vol.groupby(date).cumsum() / self.df["Volume"].groupby(date).cumsum()
        return self


    def add_temporal_features(self) -> 'DataTransformer':
        """
        Añade las 6 columnas temporales al DataFrame:
        Hour, Minute, Day, Month, Trimester, Year.
        """
        self.df["Hour"] = self.df.index.hour
        self.df["Minute"] = self.df.index.minute
        self.df["Day"] = self.df.index.dayofweek
        self.df["Month"] = self.df.index.month
        self.df["Trimester"] = self.df.index.quarter
        self.df["Year"] = self.df.index.year
        return self


    def add_session_flags(self) -> 'DataTransformer':
        """
        Añade columnas de flags para las 3 sesiones de trading:
        Asian_session, European_session, American_session.
        """
        hour = self.df.index.hour
        minute = self.df.index.minute

        # Sesión asiática: 00:00 a 08:59
        self.df["Asian_session"] = ((hour >= 0) & (hour < 9)).astype(int)

        # Sesión europea: 09:00 a 15:29
        self.df["European_session"] = (
            ((hour >= 9) & (hour < 15)) |
            ((hour == 15) & (minute < 30))
        ).astype(int)

        # Sesión americana: 15:30 a 23:59
        self.df["American_session"] = (
            ((hour == 15) & (minute >= 30)) |
            (hour >= 16)
        ).astype(int)

        return self


    def add_session_extremes(self) -> 'DataTransformer':
        """
        Añade columnas de máximos y mínimos por día para cada sesión:
        Max/Min_asian_session, Max/Min_european_session, Max/Min_american_session.
        """
        sessions = {
            "asian": "Asian_session",
            "european": "European_session",
            "american": "American_session",
        }
        date_series = pd.Series(self.df.index.date, index=self.df.index)

        for name, col in sessions.items():
            session_data = self.df[self.df[col] == 1]
            grouped = session_data.groupby(session_data.index.date)

            max_per_day = grouped["High"].max()
            min_per_day = grouped["Low"].min()

            self.df[f"Max_{name}_session"] = date_series.map(max_per_day)
            self.df[f"Min_{name}_session"] = date_series.map(min_per_day)

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


    def add_periodic_high_low(self) -> 'DataTransformer':
        """
        Añade columnas de high/low del periodo anterior para daily, weekly y monthly:
        Daily_high_before, Daily_low_before, Weekly_high_before, Weekly_low_before,
        Monthly_high_before, Monthly_low_before.
        """
        periods = {
            "Daily": lambda idx: idx.date,
            "Weekly": lambda idx: idx.to_period("W"),
            "Monthly": lambda idx: idx.to_period("M"),
        }

        for label, period_fn in periods.items():
            period_keys = period_fn(self.df.index)
            period_series = pd.Series(period_keys, index=self.df.index)

            high_per_period = self.df.groupby(period_keys)["High"].max().shift(1)
            low_per_period = self.df.groupby(period_keys)["Low"].min().shift(1)

            self.df[f"{label}_high_before"] = period_series.map(high_per_period).bfill()
            self.df[f"{label}_low_before"] = period_series.map(low_per_period).bfill()

        return self


    def convert_to_heiken_ashi(self) -> 'DataTransformer':
        """
        Convierte las velas OHLC del DataFrame a formato Heiken Ashi,
        reemplazando las columnas originales: 'Open', 'High', 'Low', 'Close'.
        Usa vectorización con numpy para evitar loops de Python.
        """
        ha_close = (self.df["Open"] + self.df["High"] + self.df["Low"] + self.df["Close"]) / 4

        # Vectorized HA open using numpy iteration (inherently sequential)
        n = len(self.df)
        ha_open = np.empty(n)
        ha_open[0] = self.df["Open"].iloc[0]
        close_vals = ha_close.values
        for i in range(1, n):
            ha_open[i] = (ha_open[i - 1] + close_vals[i - 1]) / 2

        self.df["Open"] = ha_open
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
                        obp_range: int, heikin_ashi: bool = False) -> dict:
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
                heikin_ashi (bool): Si True, convierte velas a Heikin Ashi antes de calcular indicadores.

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
                if heikin_ashi:
                    transformer_resampled.convert_to_heiken_ashi()
                enriched_df = (
                    transformer_resampled
                    .calculate_ema(ema_periods)
                    .calculate_volatility_pct_change(volatility_periods)
                    .calculate_pct_change(pct_change_periods)
                    .volume_pct_change(volume_periods)
                    .calculate_cumulative_volume_pct(cumulative_volume_periods)
                    .add_temporal_features()
                    .calculate_vwap()
                    .add_session_flags()
                    .add_session_extremes()
                    .add_periodic_high_low()
                    .clean_sessions()
                    .detectar_onebar_pullback_alcista()
                    .detectar_onebar_pullback_bajista()
                    .detectar_onebar_pullback_alcista_extendido(obp_range)
                    .detectar_onebar_pullback_bajista_extendido(obp_range)
                    .transform()
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
