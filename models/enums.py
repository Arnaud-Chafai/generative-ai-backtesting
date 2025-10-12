"""
Enums compartidos - Definiciones de tipos usados por live_trading y backtesting.

Este módulo contiene todos los enums del sistema:
- SignalType: Tipos de señales (BUY, SELL, CLOSE, etc.)
- OrderType: Tipos de órdenes (MARKET, LIMIT, STOP, etc.)
- CurrencyType: Divisas soportadas (USD, EUR, USDT)
- MarketType: Tipos de mercado (CRYPTO, FUTURES, STOCKS)
- ExchangeName: Nombres de exchanges (BINANCE, KUCOIN, etc.)
- SignalStatus: Estados de señales (PENDING, EXECUTED, CANCELLED)
- SignalPositionSide: Lado de la posición (LONG, SHORT)
"""
from enum import Enum


class SignalType(str, Enum):
    """Tipos de señales generadas por una estrategia.
    
    Por ahora solo usamos BUY y SELL. En el futuro podríamos
    reactivar CLOSE, TAKE_PROFIT, STOP_LOSS si necesitamos
    distinguir semánticamente el motivo del cierre.
    """
    BUY = "BUY"
    SELL = "SELL"
    # CLOSE = "CLOSE"  # Desactivado temporalmente
    # TAKE_PROFIT = "TAKE_PROFIT"
    # STOP_LOSS = "STOP_LOSS"

class OrderType(str, Enum):
    """Tipos de órdenes disponibles."""
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP = "STOP"
    STOP_LIMIT = "STOP_LIMIT"


class CurrencyType(str, Enum):
    """Divisas soportadas."""
    USD = "USD"
    EUR = "EUR"
    USDT = "USDT"


class MarketType(str, Enum):
    """Tipos de mercado soportados."""
    CRYPTO = "Crypto"
    FUTURES = "Futures"
    STOCKS = "Stocks"


class ExchangeName(str, Enum):
    """Nombres de los exchanges soportados."""
    BINANCE = "Binance"
    KUCOIN = "Kucoin"


class SignalStatus(str, Enum):
    """Estados posibles de una señal generada."""
    PENDING = "PENDING"
    EXECUTED = "EXECUTED"
    CANCELLED = "CANCELLED"


class SignalPositionSide(str, Enum):
    """Define si la señal es LONG o SHORT."""
    LONG = "LONG"
    SHORT = "SHORT"
