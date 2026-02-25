"""
Futures Market Definition - Definición de mercado para futuros.

Sigue el mismo patrón que CryptoMarketDefinition.
"""

from typing import Any, Dict
from pydantic import Field
from config.markets.base_market import BaseMarketDefinition
from config.market_configs.futures_config import get_futures_config
from models.enums import MarketType


class FuturesMarketDefinition(BaseMarketDefinition):
    """
    Definición de mercado para futuros CME.
    Usa `get_futures_config` para obtener tick_size, fee, slippage, etc.
    """
    market: MarketType = MarketType.FUTURES
    exchange: str = Field(..., description="Exchange (e.g., 'CME')")

    def get_config(self) -> Dict[str, Any]:
        """Devuelve la configuración de mercado obtenida de `futures_config`."""
        return get_futures_config(self.exchange, self.symbol)
