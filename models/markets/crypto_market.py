"""
Crypto Market Definition - Definición de mercado para criptomonedas.

Este módulo contiene la clase CryptoMarketDefinition que define
las características de un mercado de criptomonedas.
"""

from typing import Any, Dict
from pydantic import Field
from models.markets.base_market import BaseMarketDefinition
from config.market_configs.crypto_config import get_crypto_config
from models.enums import MarketType

class CryptoMarketDefinition(BaseMarketDefinition):
    """
    Definición de mercado para criptomonedas.
    Usa `get_crypto_config` para obtener tick_size, fee, slippage, etc.
    """
    market: MarketType = MarketType.CRYPTO  # ✅ Valor por defecto
    exchange: str = Field(..., description="Exchange en el que se opera (e.g., 'Binance', 'Kucoin')")

    def get_config(self) -> Dict[str, Any]:
        """ Devuelve la configuración de mercado obtenida de `crypto_config`. """
        return get_crypto_config(self.exchange, self.symbol)
