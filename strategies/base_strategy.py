from abc import ABC, abstractmethod
from typing import List, Optional
from datetime import datetime
import os
import uuid
import pandas as pd

# Imports de la nueva estructura
from models.enums import SignalType, OrderType, CurrencyType, ExchangeName, MarketType, SignalPositionSide
from models.simple_signals import TradingSignal
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
        fees: bool = True,
        data: Optional[pd.DataFrame] = None
    ):
        if market not in {MarketType.CRYPTO, MarketType.FUTURES}:
            raise ValueError(f"❌ Mercado no soportado: {market}. Solo 'Crypto', 'Futures' o 'Stocks'.")

        self.market = market
        self.symbol = symbol
        self.strategy_name = strategy_name
        self.timeframe = timeframe
        self.exchange = ExchangeName(exchange) if exchange else None
        self.initial_capital = initial_capital
        self.slippage_enabled = slippage
        self.fees_enabled = fees
        
        # 🔧 CAMBIO: Usar TradingSignal (sistema nuevo)
        self.simple_signals: List[TradingSignal] = []

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

        # ✅ NUEVA LÓGICA: Soportar datos inyectados O cargar del disco
        if data is not None:
            # Modo inyectado (optimizador)
            self.market_data = data
            print(f"✓ Datos inyectados: {len(self.market_data)} candles")
            print(f"  Período: {self.market_data.index[0]} a {self.market_data.index[-1]}\n")
        else:
            # Modo legacy (cargar del disco)
            current_file = os.path.abspath(__file__)
            strategies_dir = os.path.dirname(current_file)
            backtesting_dir = os.path.dirname(strategies_dir)

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

    # ========================================================================
    # NUEVO SISTEMA SIMPLIFICADO
    # ========================================================================
    
    def generate_simple_signals(self) -> List[TradingSignal]:
        """
        Método para generar señales simplificadas.
        
        Las estrategias hijas deben implementar este método para
        usar el motor simplificado de backtest.
        
        Returns:
            Lista de TradingSignal
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
    ) -> TradingSignal:
        """
        Helper para crear señales simplificadas desde estrategias.
        
        Args:
            signal_type: BUY o SELL
            timestamp: Momento de la señal (del índice del DataFrame)
            price: Precio de referencia (ej: Close del candle)
            position_size_pct: Porcentaje del capital a usar (0.1 = 10%)
        
        Returns:
            TradingSignal creado y añadido a la lista
        """
        signal = TradingSignal(
            timestamp=timestamp,
            signal_type=signal_type,
            symbol=self.symbol,
            price=price,
            position_size_pct=position_size_pct
        )
        
        self.simple_signals.append(signal)
        return signal