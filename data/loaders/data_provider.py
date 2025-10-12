import pandas as pd
import MetaTrader5 as mt5
from utils.timeframe import Timeframe

# TODO: PlatformConnector ya no existe (era parte del módulo de live trading eliminado)
# Si se necesita conectividad MT5 para backtesting, se debe reimplementar aquí
# from platform_connector.platform_connector import PlatformConector

class CSVDataProvider:
    def __init__(self, asset: str):
        """
        Inicializa el proveedor de datos con archivos CSV desde la carpeta correcta.
        """
        self.csv_path = f"data/raw_data/{asset}.csv"
        self.csv_data = pd.DataFrame()
        self.load_csv_data()

    def load_csv_data(self) -> None:
        """
        Carga datos desde un archivo CSV y los almacena en un DataFrame.
        """
        try:
            # Cargar archivo CSV
            self.csv_data = pd.read_csv(self.csv_path)
            
            # Normalizar el nombre de la columna para manejar 'time' y 'Time'
            self.csv_data.columns = [col.capitalize() for col in self.csv_data.columns]
            
            # Asegurarte de que 'Time' exista como columna
            if "Time" not in self.csv_data.columns:
                raise ValueError("No se encontró una columna de tiempo en el archivo CSV.")
            
            # Parsear fechas y establecer 'Time' como índice
            self.csv_data["Time"] = pd.to_datetime(self.csv_data["Time"])
            self.csv_data.set_index("Time", inplace=True)
            print(f"Datos cargados correctamente desde {self.csv_path}.")
        except Exception as e:
            print(f"Error al cargar los datos del archivo CSV: {e}")



    def get_latest_closed_bars_from_csv(self, num_bars: int = 1) -> pd.DataFrame:
        """
        Obtiene las últimas `num_bars` barras cerradas desde los datos cargados en CSV.
        """
        if self.csv_data.empty:
            print("Los datos CSV están vacíos.")
            return pd.DataFrame()

        # Retornar las últimas `num_bars` barras cerradas
        return self.csv_data.tail(num_bars)


    def get_all_data(self) -> pd.DataFrame:
        """
        Devuelve todos los datos cargados desde el CSV.
        """
        if self.csv_data.empty:
            print("Los datos CSV están vacíos.")
            return pd.DataFrame()

        return self.csv_data



# TODO: PlatformConector ya no existe - reimplementar si se necesita MT5 live trading
class MT5BacktestDataProvider:
    def __init__(self, symbol_list: list, timeframe: Timeframe):
        """
        Inicializa el MT5BacktestDataProvider y establece conexión con MetaTrader 5.
        """
        # super().__init__(symbol_list)  # Comentado - PlatformConector eliminado
        self.symbol_list = symbol_list
        self.timeframe = timeframe  # Timeframe para obtener los datos

    def _map_timeframe(self) -> int:
        """ Mapea el Timeframe del framework a su equivalente en MT5. """
        return Timeframe.to_mt5(self.timeframe)  # 


    def get_batch_data_from_mt5(self, symbol: str, num_bars: int = 1000) -> pd.DataFrame:
        """
        Obtiene un batch de datos OHLC desde MetaTrader 5 usando `copy_rates_from_pos`.
        """
        tf = self._map_timeframe()
        from_position = 0  # Desde la barra más antigua disponible
        bars_count = num_bars  # Número de barras a recuperar

        try:
            # Obtener datos históricos desde MT5
            bars_np_array = mt5.copy_rates_from_pos(symbol, tf, from_position, bars_count)
            if bars_np_array is None:
                print(f"El símbolo {symbol} no tiene datos disponibles en MT5.")
                return pd.DataFrame()

            # Convertir a DataFrame y limpiar los datos
            bars = pd.DataFrame(bars_np_array)
            bars["time"] = pd.to_datetime(bars["time"], unit="s")
            bars.set_index("time", inplace=True)
            bars = bars.rename_axis("Time")# Renombrar el índice
            bars.rename(columns={"open": "Open","high": "High","low": "Low", "close": "Close", "real_volume": "Volume"}, inplace=True)
            bars = bars[["Open", "High", "Low", "Close", "Volume"]]

            print(f"Datos cargados correctamente para {symbol} en {self.timeframe} desde MT5.")

        except Exception as e:
            print(f"Error al recuperar los datos de {symbol}: {e}")
            return pd.DataFrame()

        return bars

        
