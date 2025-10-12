"""
Signal models - Definición de señales de trading.

Este módulo contiene la clase StrategySignal que representa una señal
generada por una estrategia de trading. Es usada tanto por el sistema
de backtesting como por el sistema de live trading.
"""

from enum import Enum
from pydantic import BaseModel, Field, field_validator
from datetime import datetime
from typing import Optional
import uuid

# Importar desde el módulo de enums
from models.enums import (
    SignalType,
    OrderType,
    CurrencyType,
    MarketType,
    ExchangeName,
    SignalStatus,
    SignalPositionSide
)


class StrategySignal(BaseModel):
    """
    Clase que representa una señal generada por la estrategia.

    Attributes:
        id: Identificador único de la señal
        market: Tipo de mercado (CRYPTO, FUTURES, STOCKS)
        exchange: Exchange donde se opera (opcional)
        symbol: Símbolo del activo (ej: BTC, ETH)
        currency: Divisa utilizada (USD, USDT, EUR)
        timeframe: Timeframe de la estrategia (opcional)
        strategy_name: Nombre de la estrategia que generó la señal
        signal_type: Tipo de señal (BUY, SELL, CLOSE, etc.)
        order_type: Tipo de orden (MARKET, LIMIT, STOP, etc.)
        timestamp: Momento en que se generó la señal
        usdt_amount: Cantidad en USDT a operar
        price: Precio de referencia (opcional según order_type)
        stop_loss: Precio de stop loss (opcional)
        take_profit: Precio de take profit (opcional)
        slippage_in_ticks: Slippage en ticks para futuros (opcional)
        slippage_pct: Slippage en porcentaje para crypto (opcional)
        slippage_cost: Costo estimado del slippage (opcional)
        fee: Comisión de la operación
        position_side: Lado de la posición (LONG o SHORT)
    """
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    market: str
    exchange: Optional[str] = None
    symbol: str
    currency: str
    timeframe: Optional[str] = None
    strategy_name: Optional[str] = None
    signal_type: str
    order_type: str
    timestamp: datetime
    usdt_amount: float = Field(..., gt=0)
    price: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    slippage_in_ticks: Optional[int] = None
    slippage_pct: Optional[float] = None
    slippage_cost: Optional[float] = None
    fee: float = Field(default=0.0)
    position_side: SignalPositionSide

    # ✅ Convertir automáticamente `Enum` a `str`
    @field_validator("market", "exchange", "currency", "signal_type", "order_type", "position_side", mode="before")
    @classmethod
    def convert_enum_to_str(cls, value):
        """Convierte valores de Enum a string automáticamente."""
        return value.value if isinstance(value, Enum) else value

    # ✅ Asegurar que valores clave sean positivos
    @field_validator("price", "stop_loss", "take_profit", "slippage_in_ticks", "slippage_pct")
    @classmethod
    def check_positive(cls, value):
        """Asegura que estos valores sean positivos."""
        if value is not None and value < 0:
            raise ValueError("Los valores de precio, stop_loss, take_profit y slippage deben ser positivos")
        return value

    # ✅ Validar que órdenes `LIMIT` y `STOP` tengan un precio definido
    @field_validator("price")
    @classmethod
    def validate_price_for_order_type(cls, value, info):
        order_type = info.data.get("order_type")
        if order_type in {"LIMIT", "STOP"} and value is None:
            raise ValueError(f"El precio debe especificarse para órdenes de tipo {order_type}.")
        return value

    # ✅ Formatear `usdt_amount` a 2 decimales
    @field_validator("usdt_amount")
    @classmethod
    def format_usdt(cls, v):
        return round(v, 2)

    def __str__(self):
        """Muestra los datos relevantes de la señal sin valores `None`."""
        data = self.model_dump(exclude_none=True)
        data["usdt_amount"] = round(self.usdt_amount, 2)

        if self.fee > 0:
            data["fee"] = round(self.fee, 4)

        if self.slippage_cost and self.slippage_cost > 0:
            data["slippage_cost"] = round(self.slippage_cost, 4)

        return str(data)
