"""
Futures Market Definition - Definición de mercado para futuros.

Este módulo contiene las clases para definir mercados de futuros
y trades en esos mercados.
"""

from datetime import datetime
from typing import Any, Dict
from pydantic import Field
from models.trades.base_trade import Trade, TradeAction
from models.markets.base_market import BaseMarketDefinition
from models.enums import SignalType, MarketType
from models.signals import StrategySignal
from config.market_configs.futures_config import get_futures_config
import math


class FuturesMarketDefinition(BaseMarketDefinition):
    """
    Definición de mercado para futuros.
    Usa `get_futures_config` para obtener tick_size, fees, contract_size, etc.
    """
    market: MarketType = MarketType.FUTURES  # ✅ Valor por defecto
    exchange: str = Field(..., description="Exchange en el que se opera (e.g., 'Binance', 'CME', 'Bybit')")

    def get_config(self) -> Dict[str, Any]:
        """ Devuelve la configuración de mercado obtenida de `futures_config`. """
        return get_futures_config(self.exchange, self.symbol)


class FuturesTrade(Trade):
    """ 
    Clase de Trade específica para Futuros con:
    - Comisiones por operación.
    - Tick size y tick value dinámicos según el activo.
    - Slippage basado en número de ticks en entradas y salidas.
    - Soporte para contratos micro y mini.
    """

    tick_size: float = Field(default=0.25)
    tick_value: float = Field(default=12.50)
    commission_per_trade: float = Field(default=5.00)
    micro_contract: bool = Field(default=False)
    slippage_in_ticks: int = Field(default=1)  # 🔹 Slippage de 1 tick por defecto
    price_precision: int = Field(default=2)  # 🔹 Precisión decimal de precios

    def __init__(self, symbol: str, entry_time: datetime):
        super().__init__(symbol=symbol, entry_time=entry_time)
        self.entries = []
        self.exits = []

        # ✅ Obtener configuración desde utils
        config = get_futures_config(symbol)
        object.__setattr__(self, "tick_size", config["tick_size"])
        object.__setattr__(self, "tick_value", config["tick_value"])
        object.__setattr__(self, "commission_per_trade", config["commission_per_trade"])
        object.__setattr__(self, "micro_contract", config["micro_contract"])
        object.__setattr__(self, "price_precision", config.get("price_precision", 2))  # Por defecto 2 decimales

    def _round_price(self, price: float) -> float:
        """ 🔹 Redondear precio con `price_precision` antes de cualquier cálculo. """
        return round(price, self.price_precision)

    def add_entry(self, timestamp: datetime, signal_type: SignalType, volume: float, price: float, slippage_in_ticks: int = 1) -> None:
        """ Agregar una entrada con slippage basado en ticks. """
        slippage_adjustment = slippage_in_ticks * self.tick_size  # 🔹 Ajuste en precio
        real_price = self._round_price(price + slippage_adjustment if signal_type == SignalType.BUY else price - slippage_adjustment)

        self.entries.append(TradeAction(
            timestamp=timestamp,
            signal_type=signal_type,
            volume=volume,
            price=real_price,
            comment=f"Slippage aplicado: {slippage_in_ticks} ticks = {slippage_in_ticks * self.tick_value} USD"
        ))

    def add_exit(self, timestamp: datetime, signal_type: SignalType, volume: float, price: float, slippage_in_ticks: int = 1) -> None:
        """ Agregar una salida con slippage basado en ticks. """
        slippage_adjustment = slippage_in_ticks * self.tick_size  # 🔹 Ajuste en precio
        real_price = self._round_price(price - slippage_adjustment if signal_type == SignalType.BUY else price + slippage_adjustment)

        self.exits.append(TradeAction(
            timestamp=timestamp,
            signal_type=signal_type,
            volume=volume,
            price=real_price,
            comment=f"Slippage aplicado: {slippage_in_ticks} ticks = {slippage_in_ticks * self.tick_value} USD"
        ))

    def validate_signal(self, signal: StrategySignal) -> None:
        """ Valida que la señal tenga los atributos correctos según el activo. """
        if signal.price is None:
            raise ValueError("⚠ En el mercado de Futuros, las órdenes deben tener un precio definido.")

        # ✅ Redondear `price` antes de la validación para evitar errores flotantes
        signal.price = self._round_price(signal.price)

    def calculate_commission(self) -> float:
        """ Retorna la comisión total basada en el número de trades ejecutados. """
        return len(self.entries + self.exits) * self.commission_per_trade

    def calculate_slippage_cost(self) -> float:
        """ Calcula el costo total del slippage en USD basado en `slippage_in_ticks` y `tick_value`. """
        total_slippage = sum(self.slippage_in_ticks * self.tick_value for _ in self.entries + self.exits)
        return total_slippage  # 🔹 Sumamos el slippage total en USD

