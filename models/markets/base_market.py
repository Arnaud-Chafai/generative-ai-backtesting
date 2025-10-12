# backtest_market_definition/base_market_definition.py

from abc import ABC, abstractmethod
from pydantic import BaseModel, Field
from typing import Any, Dict

class BaseMarketDefinition(BaseModel, ABC):
    """
    Clase base para definir la configuración de un mercado.
    """
    symbol: str = Field(..., description="Símbolo del activo")
    market: str = Field(..., description="Tipo de mercado, e.g. 'Crypto' o 'Futures'")

    @abstractmethod
    def get_config(self) -> Dict[str, Any]:
        """
        Retorna la configuración específica del mercado en forma de diccionario.
        """
        pass

    def __str__(self) -> str:
        return f"{self.market} - {self.symbol} configuration: {self.get_config()}"
