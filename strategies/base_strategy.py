from abc import ABC, abstractmethod
from typing import List, Optional
from datetime import datetime
import os
import uuid
import pandas as pd

# Imports de la nueva estructura
from models.enums import SignalType, OrderType, CurrencyType, ExchangeName, MarketType, SignalPositionSide
from models.signals import StrategySignal
from models.markets.crypto_market import CryptoMarketDefinition
from utils.timeframe import Timeframe

# TODO: CryptoCapitalManager será reemplazado por el nuevo sistema de capital management
# from backtest_capital_manager.properties.crypto_capital_manager_properties import CryptoCapitalManager

class BaseStrategy(ABC):
    def __init__(
        self,
        market: MarketType,  
        symbol: str,
        strategy_name: str,
        timeframe: Timeframe,
        exchange: Optional[str] = None,
        initial_capital: float = 1000.0,
        slippage: bool = True,
        fees: bool = True  # ✅ NUEVO PARAMETRO PARA ACTIVAR/DESACTIVAR FEES
    ):
        if market not in {MarketType.CRYPTO, MarketType.FUTURES, MarketType.STOCKS}:
            raise ValueError(f"❌ Mercado no soportado: {market}. Solo 'Crypto', 'Futures' o 'Stocks'.")

        self.market = market
        self.symbol = symbol
        self.strategy_name = strategy_name
        self.timeframe = timeframe
        self.exchange = ExchangeName(exchange) if exchange else None
        self.initial_capital = initial_capital
        self.slippage_enabled = slippage
        self.fees_enabled = fees  # ✅ Guardamos la configuración de fees
        self.signals: List[StrategySignal] = []

        if self.market == MarketType.CRYPTO:
            self.market_definition = CryptoMarketDefinition(
                market=market.value,  
                symbol=symbol,
                exchange=exchange
            )
            self.slippage_value = self.market_definition.get_config()["slippage"]
        else:
            self.market_definition = None
            self.slippage_value = 1  

        data_path = f"data/laboratory_data/{symbol}/Timeframe.{timeframe.name}.csv"
        if not os.path.exists(data_path):
            raise FileNotFoundError(f"❌ No se encontró el archivo {data_path}")

        self.market_data = pd.read_csv(data_path, index_col="Time", parse_dates=["Time"])
        if self.market_data.empty:
            raise ValueError(f"❌ El archivo {data_path} no contiene datos.")

        print(f"[OK] Datos cargados correctamente desde {data_path}.\n")



    @abstractmethod
    def generate_signals(self) -> None:
        pass

    def create_crypto_signal(
        self,
        signal_type: SignalType,
        order_type: OrderType,
        volume_pct: float,
        timestamp: datetime,
        price: Optional[float] = None,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None
    ) -> None:
        if price is None:
            price = self.get_market_price()
        if price is None or price <= 0:
            raise ValueError("❌ No se pudo determinar un precio válido para la orden.")

        # TODO: Reemplazar CryptoCapitalManager con nuevo sistema de capital management
        # capital_manager = CryptoCapitalManager(
        #     self.initial_capital,
        #     self.market_definition,
        #     fees_enabled=self.fees_enabled
        # )
        # usdt_allocated = capital_manager.allocate(volume_pct, price)

        # TEMPORAL: Cálculo directo de capital allocation
        # volume_pct viene como fracción (ej: 0.1 = 10%, 0.5 = 50%)
        usdt_allocated = self.initial_capital * volume_pct

        # Obtenemos el exchange_fee sólo si fees están activadas; si no, 0.0
        exchange_fee = (self.market_definition.get_config()["exchange_fee"]
                        if self.fees_enabled else 0.0)
        
        # Fuerza que fee sea 0.0 cuando fees_enabled=False
        fee = 0.0 if not self.fees_enabled else round(usdt_allocated * exchange_fee, 4)

        # Slippage
        slippage_pct = self.slippage_value if self.slippage_enabled else 0.0
        slippage_cost = 0.0 if not self.slippage_enabled else round(usdt_allocated * slippage_pct, 4)
        
        # ✅ Determinar si la señal es LONG o SHORT
        position_side = SignalPositionSide.LONG if signal_type == SignalType.BUY else SignalPositionSide.SHORT

        
        
        # 🔹 Ahora `volume` en la señal será el monto en USDT, no en cripto
        signal = StrategySignal(
            id=str(uuid.uuid4()),
            market=self.market,
            exchange=ExchangeName(self.exchange),
            strategy_name=self.strategy_name,
            symbol=self.symbol,
            currency=CurrencyType.USDT,
            timeframe=self.timeframe,
            signal_type=signal_type,
            order_type=order_type,
            usdt_amount=usdt_allocated,
            price=price,
            slippage_pct=slippage_pct,
            slippage_cost=slippage_cost,  # ✅ Ahora siempre se calcula correctamente
            timestamp=timestamp,
            stop_loss=stop_loss,
            take_profit=take_profit,
            fee=fee,  # ✅ Ahora la fee no aparece cuando fees=False
            position_side=position_side  # ✅ Agregamos el campo obligatorio
        )

        self.signals.append(signal)

        # Mostrar el log correctamente solo si fees/slippage están activados
        # print(f"[SIGNAL] Señal creada: {signal}")  # Comentado para tests - descomentar si necesitas debug

    def create_futures_signal(
        self,
        signal_type: SignalType,
        order_type: OrderType,
        volume: float,
        price: Optional[float],
        timestamp: datetime,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None
    ) -> None:
        """ 
        Crea una señal específica para Futuros con `slippage_in_ticks` y `USD` como currency.
        """

        # ✅ Determinar slippage en ticks
        slippage_in_ticks = 1  # ⚠ Aquí iría la configuración real de Futuros

        signal = StrategySignal(
            id=str(uuid.uuid4()),
            market=self.market,
            strategy_name=self.strategy_name,
            symbol=self.symbol,
            currency=CurrencyType.USD,  # ✅ Futuros opera con USD
            timeframe=self.timeframe,
            signal_type=signal_type,
            order_type=order_type,
            volume=volume,
            price=price,
            slippage_pct=None,  # ❌ No usamos slippage en porcentaje para Futuros
            slippage_in_ticks=slippage_in_ticks,  # ✅ Usamos slippage en ticks
            timestamp=timestamp,
            stop_loss=stop_loss,
            take_profit=take_profit,

        )

        self.signals.append(signal)
        # print(f"[SIGNAL] Señal creada: {signal}")  # Comentado para tests - descomentar si necesitas debug
