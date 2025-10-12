"""Position Manager - Gestión simple de posiciones"""
from typing import Optional, Dict
from models.trades.crypto_trade import CryptoTrade


class PositionManager:
    """Gestiona posiciones abiertas durante el backtest"""

    def __init__(self):
        self.positions: Dict[str, CryptoTrade] = {}  # symbol -> CryptoTrade

    def has_position(self, symbol: str) -> bool:
        """Verifica si hay una posición abierta para el símbolo"""
        return symbol in self.positions

    def open_position(self, symbol: str, trade: CryptoTrade) -> None:
        """Abre una nueva posición"""
        if self.has_position(symbol):
            raise ValueError(f"Ya existe una posición abierta para {symbol}")
        self.positions[symbol] = trade

    def get_position(self, symbol: str) -> Optional[CryptoTrade]:
        """Obtiene la posición actual del símbolo"""
        return self.positions.get(symbol)

    def close_position(self, symbol: str) -> CryptoTrade:
        """Cierra y retorna la posición"""
        if not self.has_position(symbol):
            raise ValueError(f"No hay posición abierta para {symbol}")
        return self.positions.pop(symbol)
