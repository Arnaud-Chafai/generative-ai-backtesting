from enum import Enum
import MetaTrader5 as mt5
import pandas as pd
import numpy as np

class Timeframe(str, Enum):
    """
    Timeframes estándar utilizados en todo el framework.
    """
    M1 = "1min"   # 1 minuto
    M5 = "5min"   # 5 minutos
    M15 = "15min" # 15 minutos
    M30 = "30min" # 30 minutos
    H1 = "1h"     # 1 hora
    H4 = "4h"     # 4 horas
    D1 = "1d"     # 1 día
    W1 = "1w"     # 1 semana
    MN1 = "1M"    # 1 mes

    @staticmethod
    def to_mt5(timeframe: str) -> int:
        """
        Mapea un timeframe estándar a su equivalente en MetaTrader 5.
        """
        mapping = {
            Timeframe.M1: mt5.TIMEFRAME_M1,
            Timeframe.M5: mt5.TIMEFRAME_M5,
            Timeframe.M15: mt5.TIMEFRAME_M15,
            Timeframe.M30: mt5.TIMEFRAME_M30,
            Timeframe.H1: mt5.TIMEFRAME_H1,
            Timeframe.H4: mt5.TIMEFRAME_H4,
            Timeframe.D1: mt5.TIMEFRAME_D1,
            Timeframe.W1: mt5.TIMEFRAME_W1,
            Timeframe.MN1: mt5.TIMEFRAME_MN1,
        }
        if timeframe not in mapping:
            raise ValueError(f"Timeframe '{timeframe}' no es válido en MetaTrader 5.")
        return mapping[timeframe]

    @staticmethod
    def from_string(timeframe: str):
        """
        Convierte un string en un objeto `Timeframe`.
        """
        valid_timeframes = {tf.value: tf for tf in Timeframe}
        if timeframe not in valid_timeframes:
            raise ValueError(f"Timeframe '{timeframe}' no es válido.")
        return valid_timeframes[timeframe]

    @property
    def hours(self) -> float:
        """
        Retorna la duración del timeframe en horas.
        
        Ejemplos:
            Timeframe.M1 (o "1min")  -> 1 minuto = 1/60 horas
            Timeframe.M5 (o "5min")  -> 5 minutos = 5/60 horas
            Timeframe.H1 (o "1h")    -> 1 hora
            Timeframe.D1 (o "1d")    -> 24 horas
            etc.
        """
        mapping = {
            Timeframe.M1: 1/60.0,
            Timeframe.M5: 5/60.0,
            Timeframe.M15: 15/60.0,
            Timeframe.M30: 30/60.0,
            Timeframe.H1: 1.0,
            Timeframe.H4: 4.0,
            Timeframe.D1: 24.0,
            Timeframe.W1: 168.0,
            Timeframe.MN1: 720.0,
        }
        return mapping[self]


"""
Utilidades para procesamiento de datos temporales en el análisis de trading.
"""

def prepare_datetime_data(df):
    """
    Prepara los datos temporales del DataFrame para el análisis.
    Añade columnas como hour, day_of_week, day, month, year si no existen.
    
    Args:
        df: DataFrame con datos de trading
        
    Returns:
        DataFrame con columnas temporales añadidas
    """
    df_copy = df.copy()
    
    # Verificar si ya existen las columnas de tiempo
    has_month = "month" in df_copy.columns
    has_day_of_week = "day_of_week" in df_copy.columns
    has_hour = "hour" in df_copy.columns
    has_day = "day" in df_copy.columns
    has_year = "year" in df_copy.columns
    
    # Si todas las columnas ya existen, devolver el DataFrame tal cual
    if has_month and has_day_of_week and has_hour and has_day and has_year:
        # print("[OK] Las columnas temporales ya existen. Usando datos existentes.")
        return df_copy
    
    # Buscar columna de tiempo (puede ser entry_datetime, entry_timestamp, etc.)
    datetime_col = None
    for col in ['entry_datetime', 'entry_timestamp', 'entry_time', 'timestamp', 'date', 'time']:
        if col in df_copy.columns:
            if pd.api.types.is_datetime64_any_dtype(df_copy[col]):
                datetime_col = col
                break
            else:
                try:
                    # Intentar convertir a datetime
                    df_copy[col] = pd.to_datetime(df_copy[col])
                    datetime_col = col
                    break
                except:
                    continue
    
    if datetime_col is None:
        raise ValueError("[ERROR] No se encontró una columna de tiempo válida en el DataFrame")

    # print(f"[*] Usando columna '{datetime_col}' como fuente para datos temporales")
    
    # Agregar columnas que faltan
    if not has_hour:
        df_copy["hour"] = df_copy[datetime_col].dt.hour
        
    if not has_day_of_week:
        df_copy["day_of_week"] = df_copy[datetime_col].dt.day_name()
        
    if not has_day:
        df_copy["day"] = df_copy[datetime_col].dt.day
        
    if not has_month:
        df_copy["month"] = df_copy[datetime_col].dt.month_name()
        
    if not has_year:
        df_copy["year"] = df_copy[datetime_col].dt.year
        
    # Columnas adicionales útiles para análisis
    if "quarter" not in df_copy.columns:
        df_copy["quarter"] = df_copy[datetime_col].dt.quarter
        
    if "week" not in df_copy.columns:
        df_copy["week"] = df_copy[datetime_col].dt.isocalendar().week

    # print(f"[OK] Columnas temporales agregadas/verificadas: hour, day_of_week, day, month, year, quarter, week")

    return df_copy

# Constantes útiles
DAYS_ORDER = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
MONTHS_ORDER = [
    "January", "February", "March", "April", "May", "June", 
    "July", "August", "September", "October", "November", "December"
]
MONTHS_ABBR = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]