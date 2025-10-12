# models/trades/base_trade.py
from models.enums import SignalType, OrderType
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from enum import Enum

class TradeStatus(str, Enum):
    OPEN = "OPEN"
    CLOSED = "CLOSED"

class TradeAction(BaseModel):
    timestamp: datetime
    signal_type: str
    volume: float
    price: float
    order_type: OrderType 

class Trade(BaseModel):
    """
    Clase base para un Trade, con entradas (entries) y salidas (exits).
    """
    id: str = Field(default_factory=lambda: "trade_default_id")
    symbol: str
    entry_time: datetime
    close_time: Optional[datetime] = None

    entries: List[TradeAction] = Field(default_factory=list)
    exits: List[TradeAction] = Field(default_factory=list)

    @property
    def total_volume(self) -> float:
        return sum(a.volume for a in self.entries)

    @property
    def avg_entry_price(self) -> Optional[float]:
        if not self.entries:
            return None
        total_cost = sum(a.price * a.volume for a in self.entries)
        total_vol = self.total_volume
        return total_cost / total_vol if total_vol > 0 else None

    @property
    def avg_exit_price(self) -> Optional[float]:
        if not self.exits:
            return None
        total_cost = sum(a.price * a.volume for a in self.exits)
        vol_exits = sum(a.volume for a in self.exits)
        return total_cost / vol_exits if vol_exits > 0 else None

    def add_entry(self, timestamp: datetime, signal_type: str, volume: float, price: float):
        self.entries.append(
            TradeAction(timestamp=timestamp, signal_type=signal_type, volume=volume, price=price)
        )

    def add_exit(self, timestamp: datetime, signal_type: str, volume: float, price: float):
        self.exits.append(
            TradeAction(timestamp=timestamp, signal_type=signal_type, volume=volume, price=price)
        )

    @property
    def status(self) -> TradeStatus:
        if not self.exits:
            return TradeStatus.OPEN
        # Si la suma de exits >= sum(entries), consideramos el trade cerrado
        total_entry_vol = sum(a.volume for a in self.entries)
        total_exit_vol = sum(a.volume for a in self.exits)
        if total_exit_vol >= total_entry_vol:
            return TradeStatus.CLOSED
        return TradeStatus.OPEN
