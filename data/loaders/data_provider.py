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


class CcxtDataProvider:
    """
    Proveedor de datos OHLCV desde exchanges crypto usando ccxt.
    Descarga en batches con paginación automática.

    Uso:
        provider = CcxtDataProvider(symbol="BTC/USDT", timeframe="5m", start_date="2023-01-01")
        df = provider.get_all_data()

    Requiere: pip install ccxt
    """

    _TIMEFRAME_MS = {
        "1m": 60_000, "3m": 180_000, "5m": 300_000, "15m": 900_000,
        "30m": 1_800_000, "1h": 3_600_000, "2h": 7_200_000, "4h": 14_400_000,
        "6h": 21_600_000, "8h": 28_800_000, "12h": 43_200_000,
        "1d": 86_400_000, "1w": 604_800_000, "1M": 2_592_000_000,
    }

    BATCH_SIZE = 1000  # Máximo de velas por request en Binance

    def __init__(self, symbol: str, timeframe: str, start_date: str, exchange: str = "binance"):
        """
        Args:
            symbol: Par de trading (e.g., "BTC/USDT")
            timeframe: Timeframe ccxt (e.g., "1m", "5m", "1h", "1d")
            start_date: Fecha inicio en formato "YYYY-MM-DD"
            exchange: Nombre del exchange ccxt (default: "binance")
        """
        import ccxt
        self.symbol = symbol
        self.timeframe = timeframe
        self.start_date = start_date
        self.exchange = getattr(ccxt, exchange)()
        self.data = pd.DataFrame()

        if timeframe not in self._TIMEFRAME_MS:
            raise ValueError(f"Timeframe '{timeframe}' no soportado. Opciones: {list(self._TIMEFRAME_MS.keys())}")

        self._load_data()

    def _load_data(self) -> None:
        """
        Descarga OHLCV en batches desde start_date hasta ahora.
        """
        import time as _time

        since_ms = self.exchange.parse8601(f"{self.start_date}T00:00:00Z")
        now_ms = self.exchange.milliseconds()
        tf_ms = self._TIMEFRAME_MS[self.timeframe]
        all_candles = []

        total_candles_est = (now_ms - since_ms) // tf_ms
        fetched = 0

        print(f"Descargando {self.symbol} {self.timeframe} desde {self.start_date}...")
        print(f"  Estimado: ~{total_candles_est:,} velas en batches de {self.BATCH_SIZE}")

        while since_ms < now_ms:
            try:
                batch = self.exchange.fetch_ohlcv(
                    self.symbol, self.timeframe, since=since_ms, limit=self.BATCH_SIZE
                )
            except Exception as e:
                print(f"  Error en batch (reintentando en 5s): {e}")
                _time.sleep(5)
                continue

            if not batch:
                break

            all_candles.extend(batch)
            fetched += len(batch)

            # Avanzar el cursor al timestamp después de la última vela
            since_ms = batch[-1][0] + tf_ms

            # Progreso
            pct = min(100, int(fetched / max(total_candles_est, 1) * 100))
            print(f"  {fetched:,} velas descargadas ({pct}%)", end="\r")

            # Rate limit: ~1200 req/min en Binance, pero ser conservador
            _time.sleep(self.exchange.rateLimit / 1000)

        if not all_candles:
            print(f"\nNo se encontraron datos para {self.symbol} desde {self.start_date}.")
            return

        # Construir DataFrame con formato estándar del proyecto
        df = pd.DataFrame(all_candles, columns=["Time", "Open", "High", "Low", "Close", "Volume"])
        df["Time"] = pd.to_datetime(df["Time"], unit="ms")
        df.set_index("Time", inplace=True)
        df = df[~df.index.duplicated(keep="last")]  # Eliminar duplicados de solapamiento entre batches
        df.sort_index(inplace=True)

        self.data = df
        print(f"\n✔ {len(df):,} velas descargadas para {self.symbol} ({df.index[0]} → {df.index[-1]})")

    def get_all_data(self) -> pd.DataFrame:
        """Devuelve todos los datos descargados."""
        if self.data.empty:
            print("No hay datos descargados.")
            return pd.DataFrame()
        return self.data

    def get_latest_closed_bars(self, num_bars: int = 1) -> pd.DataFrame:
        """Obtiene las últimas `num_bars` barras cerradas."""
        if self.data.empty:
            print("No hay datos descargados.")
            return pd.DataFrame()
        return self.data.tail(num_bars)

    def save_to_csv(self, path: str = None) -> str:
        """
        Guarda los datos en CSV. Si no se pasa path, usa el formato estándar del proyecto.
        Retorna la ruta del archivo guardado.
        """
        if self.data.empty:
            print("No hay datos para guardar.")
            return ""

        if path is None:
            safe_symbol = self.symbol.replace("/", "")
            path = f"data/raw_data/{safe_symbol}_{self.timeframe}.csv"

        self.data.to_csv(path, index=True)
        print(f"✔ Datos guardados en {path}")
        return path
