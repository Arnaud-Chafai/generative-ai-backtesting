"""
Crypto Trade - Definición de trade para criptomonedas.

Este módulo contiene la clase CryptoTrade que define
las características de un trade en mercados de criptomonedas.
"""

from datetime import datetime
from pydantic import Field
from models.trades.base_trade import Trade, TradeAction
from models.markets.crypto_market import CryptoMarketDefinition
from models.enums import SignalType, OrderType

class CryptoTrade(Trade):
    """
    Clase de Trade específica para Criptomonedas con:
    - Slippage en porcentaje.
    - Fees de exchange dinámicos.
    - Granularidad mínima del precio (`tick_size`).
    - Tamaño mínimo de trade.
    """

    exchange: str = Field(...)
    tick_size: float = Field(default=0.0)
    exchange_fee: float = Field(default=0.0)
    slippage: float = Field(default=0.0)
    price_precision: int = Field(default=2)
    apply_fees: bool = Field(default=True)
    apply_slippage: bool = Field(default=True)
    total_fees: float = Field(default=0.0)
    total_slippage_cost: float = Field(default=0.0)

    # P&L fields
    gross_profit_loss: float = Field(default=0.0)
    net_profit_loss: float = Field(default=0.0)
    fees: float = Field(default=0.0)
    slippage_cost: float = Field(default=0.0)

    def __init__(self, symbol: str, entry_time: datetime, exchange: str, apply_fees: bool = True, apply_slippage: bool = True):
        """
        Constructor simplificado que carga configuración automáticamente.
        """
        # Crear market definition y obtener configuración primero
        market_definition = CryptoMarketDefinition(
            market="Crypto",
            symbol=symbol,
            exchange=exchange
        )
        config = market_definition.get_config()

        # Llamar a super().__init__() con todos los campos requeridos
        super().__init__(
            symbol=symbol,
            entry_time=entry_time,
            exchange=exchange,
            tick_size=config["tick_size"],
            exchange_fee=config["exchange_fee"],
            slippage=config["slippage"],
            price_precision=config["price_precision"],
            apply_fees=apply_fees,
            apply_slippage=apply_slippage,
            total_fees=0.0,
            total_slippage_cost=0.0,
            gross_profit_loss=0.0,
            net_profit_loss=0.0,
            fees=0.0,
            slippage_cost=0.0
        )

        self.entries = []
        self.exits = []


    def calculate_fees(self) -> float:
        """ Devuelve las fees acumuladas (ya calculadas en add_entry/add_exit). """
        return self.total_fees

    def calculate_pnl(self) -> None:
        """
        Calcula el P&L (Profit and Loss) del trade.
        Debe llamarse después de añadir entry y exit.
        """
        if not self.entries or not self.exits:
            return

        # Calcular volumen total en crypto
        total_entry_crypto = sum(e.volume for e in self.entries)
        total_exit_crypto = sum(e.volume for e in self.exits)

        # Calcular valores totales en USDT
        total_entry_value = sum(e.volume * e.price for e in self.entries)
        total_exit_value = sum(e.volume * e.price for e in self.exits)

        # P&L bruto (diferencia entre exit y entry)
        self.gross_profit_loss = total_exit_value - total_entry_value

        # Calcular fees
        self.fees = self.calculate_fees()

        # Slippage cost (ya acumulado en total_slippage_cost)
        self.slippage_cost = self.total_slippage_cost

        # P&L neto (después de fees y slippage)
        self.net_profit_loss = self.gross_profit_loss - self.fees - self.slippage_cost

    def add_entry(self, timestamp, signal_type, volume, price, order_type):
        """
        volume => Cantidad de crypto (BTC, ETH, etc.)
        price  => Precio de referencia por unidad de crypto
        """
        # Aplicar slippage al precio (compra más cara por slippage)
        real_price = self._round_price(price * (1 + self.slippage)) if self.apply_slippage else price

        # Calcular valor en USDT
        usdt_value = volume * price

        # Calcular slippage cost en USDT
        if self.apply_slippage:
            slippage_cost = usdt_value * self.slippage
            self.total_slippage_cost += slippage_cost

        # ✅ Calcular fees en USDT
        trade_fee = usdt_value * self.exchange_fee if self.apply_fees else 0.0
        self.total_fees += trade_fee

        self.entries.append(
            TradeAction(timestamp=timestamp, signal_type=signal_type,
                        volume=volume, price=real_price, order_type=order_type)
        )

    def add_exit(self, timestamp, signal_type, volume, price, order_type):
        """
        volume => Cantidad de crypto (BTC, ETH, etc.)
        price  => Precio de referencia por unidad de crypto
        """
        # Aplicar slippage al precio (venta más barata por slippage)
        real_price = self._round_price(price * (1 - self.slippage)) if self.apply_slippage else price

        # Calcular valor en USDT
        usdt_value = volume * price

        # Calcular slippage cost en USDT
        if self.apply_slippage:
            slippage_cost = usdt_value * self.slippage
            self.total_slippage_cost += slippage_cost

        # ✅ Calcular fees en USDT
        trade_fee = usdt_value * self.exchange_fee if self.apply_fees else 0.0
        self.total_fees += trade_fee

        self.exits.append(
            TradeAction(timestamp=timestamp, signal_type=signal_type,
                        volume=volume, price=real_price, order_type=order_type)
        )


    def _round_price(self, price: float) -> float:
        """ Redondea el precio según `price_precision` antes de cualquier cálculo. """
        return round(price, self.price_precision)
