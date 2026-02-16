from data.loaders.data_provider import CSVDataProvider, MT5BacktestDataProvider
import pandas as pd

class DataCleaner:
    def __init__(self, csv_provider: CSVDataProvider = None, mt5_provider: MT5BacktestDataProvider = None):
        self.csv_provider = csv_provider
        self.mt5_provider = mt5_provider
        self.expected_columns = ["Open", "High", "Low", "Close", "Volume"]


    def validate_index(self, df: pd.DataFrame) -> None:
        """
        Valida que el índice del DataFrame sea de tipo DatetimeIndex.
        """
        if not isinstance(df.index, pd.DatetimeIndex):
            raise ValueError("El índice del DataFrame debe ser de tipo DatetimeIndex.")
        print("✔ Índice validado correctamente: es un DatetimeIndex.")


    def validate_columns(self, df: pd.DataFrame) -> bool:
        """
        Comprueba si las columnas coinciden con el formato esperado.
        """
        missing_columns = set(self.expected_columns) - set(df.columns)
        if missing_columns:
            print(f"⚠ ¡Advertencia!: Faltan las columnas: {missing_columns}. Verifica el formato.")
            return False
        print("✔ Las columnas coinciden con el formato esperado.")
        return True


    def fill_missing_values(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Rellena los valores nulos en los datos con forward-fill y back-fill.
        Requiere revisión manual si el índice contiene valores nulos.
        """
        # Verificar valores nulos en el índice
        i_missing = df.index.isnull().sum()
        if i_missing > 0:
            print(f"⚠ ¡Advertencia!: {i_missing} Valores nulos en el índice detectados. Revisar manualmente.")
            raise ValueError("El índice contiene valores nulos. Corrígelo antes de continuar.")
        
        # Verificar y rellenar valores nulos en los datos
        n_missing = df.isnull().sum().sum()
        if n_missing > 0:
            print(f"⚠ ¡Advertencia!: {n_missing} Valores nulos detectados. Rellenando con forward-fill y back-fill.")
            # Rellenar valores nulos en las columnas de datos
            df = df.ffill().bfill()
        else:
            print("✔ No se encontraron valores nulos en los datos.")

        return df


    def clean_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Limpia el DataFrame completo: valida columnas, convierte el índice y rellena nulos.
        """
        print("\nIniciando el proceso de limpieza de datos...")
        self.validate_index(df)
        if not self.validate_columns(df):
            raise ValueError("⚠ ¡Advertencia!: El DataFrame no cumple con el formato esperado.")
        df = self.fill_missing_values(df)
        print("✔ Limpieza completada.")
        return df


    def clean_csv_data(self) -> pd.DataFrame:
        """
        Limpia y retorna los datos cargados desde CSV.
        """
        if not self.csv_provider:
            raise ValueError("No se ha proporcionado un proveedor de datos CSV.")
        df = self.csv_provider.get_all_data()
        return self.clean_data(df)


    def clean_mt5_data(self, symbol: str, num_bars: int = 1000) -> pd.DataFrame:
        """
        Limpia y retorna los datos cargados desde MetaTrader 5.
        """
        if not self.mt5_provider:
            raise ValueError("No se ha proporcionado un proveedor de datos MT5.")
        df = self.mt5_provider.get_batch_data_from_mt5(symbol, num_bars=num_bars)
        return self.clean_data(df)
