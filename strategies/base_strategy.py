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
        fees: bool = True
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
        self.fees_enabled = fees
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

        # 🔧 ARREGLO: Construir ruta absoluta desde la ubicación del archivo
        current_file = os.path.abspath(__file__)  # .../backtesting/strategies/base_strategy.py
        strategies_dir = os.path.dirname(current_file)  # .../backtesting/strategies/
        backtesting_dir = os.path.dirname(strategies_dir)  # .../backtesting/

        # Construir ruta a data/laboratory_data
        data_path = os.path.join(
            backtesting_dir,
            "data",
            "laboratory_data",
            symbol,
            f"Timeframe.{timeframe.name}.csv"
        )

        print(f"🔍 Buscando datos en: {data_path}")

        if not os.path.exists(data_path):
            raise FileNotFoundError(
                f"❌ No se encontró el archivo:\n{data_path}\n\n"
                f"Verifica que existe:\n"
                f"  - backtesting/data/laboratory_data/{symbol}/Timeframe.{timeframe.name}.csv"
            )

        self.market_data = pd.read_csv(data_path, index_col="Time", parse_dates=["Time"])
        if self.market_data.empty:
            raise ValueError(f"❌ El archivo {data_path} no contiene datos.")

        print(f"✅ Datos cargados: {len(self.market_data)} candles")
        print(f"   Período: {self.market_data.index[0]} a {self.market_data.index[-1]}\n")

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

        usdt_allocated = self.initial_capital * volume_pct

        exchange_fee = (self.market_definition.get_config()["exchange_fee"]
                        if self.fees_enabled else 0.0)
        
        fee = 0.0 if not self.fees_enabled else round(usdt_allocated * exchange_fee, 4)

        slippage_pct = self.slippage_value if self.slippage_enabled else 0.0
        slippage_cost = 0.0 if not self.slippage_enabled else round(usdt_allocated * slippage_pct, 4)
        
        position_side = SignalPositionSide.LONG if signal_type == SignalType.BUY else SignalPositionSide.SHORT
        
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
            slippage_cost=slippage_cost,
            timestamp=timestamp,
            stop_loss=stop_loss,
            take_profit=take_profit,
            fee=fee,
            position_side=position_side
        )

        self.signals.append(signal)

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
        slippage_in_ticks = 1

        signal = StrategySignal(
            id=str(uuid.uuid4()),
            market=self.market,
            strategy_name=self.strategy_name,
            symbol=self.symbol,
            currency=CurrencyType.USD,
            timeframe=self.timeframe,
            signal_type=signal_type,
            order_type=order_type,
            volume=volume,
            price=price,
            slippage_pct=None,
            slippage_in_ticks=slippage_in_ticks,
            timestamp=timestamp,
            stop_loss=stop_loss,
            take_profit=take_profit,
        )

        self.signals.append(signal)

    # ========================================================================
    # NUEVO SISTEMA SIMPLIFICADO
    # ========================================================================
    
    def generate_simple_signals(self) -> list:
        """
        Método abstracto para generar señales simplificadas.
        
        Las estrategias hijas deben implementar este método en lugar de
        generate_signals() cuando quieran usar el motor simplificado.
        
        Returns:
            Lista de TradingSignal (del módulo simple_signals)
        """
        raise NotImplementedError(
            "Las estrategias deben implementar generate_simple_signals() "
            "para usar el motor simplificado"
        )
    
    def create_simple_signal(
        self,
        signal_type: SignalType,
        timestamp: datetime,
        price: float,
        position_size_pct: float
    ):
        """
        Helper para crear señales simplificadas desde estrategias.
        
        Args:
            signal_type: BUY o SELL
            timestamp: Momento de la señal (del índice del DataFrame)
            price: Precio de referencia (ej: Close del candle)
            position_size_pct: Porcentaje del capital a usar (0.1 = 10%)
        """
        from models.simple_signals import TradingSignal
        
        signal = TradingSignal(
            timestamp=timestamp,
            signal_type=signal_type,
            symbol=self.symbol,
            price=price,
            position_size_pct=position_size_pct
        )
        
        if not hasattr(self, 'simple_signals'):
            self.simple_signals = []
        
        self.simple_signals.append(signal)
        
        return signal