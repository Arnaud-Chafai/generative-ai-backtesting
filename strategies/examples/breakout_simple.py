"""
Estrategia de Breakout Simple
Compra cuando el precio rompe el máximo de N períodos.
Vende cuando el precio rompe el mínimo de N períodos.
"""

from strategies.base_strategy import BaseStrategy
from models.enums import SignalType, MarketType
from utils.timeframe import Timeframe


class BreakoutSimple(BaseStrategy):
    """
    Estrategia de breakout de máximos/mínimos.
    
    Parámetros:
        lookback_period: Cuántas velas usar para calcular máximo/mínimo
        position_size_pct: Porcentaje del capital por trade
    """
    
    def __init__(
        self,
        symbol: str = "BTC",
        timeframe: Timeframe = Timeframe.H1,
        exchange: str = "Binance",
        lookback_period: int = 20,  # Breakout de 20 períodos
        position_size_pct: float = 0.5,  # 50% del capital por trade
        **kwargs
    ):
        super().__init__(
            market=MarketType.CRYPTO,
            symbol=symbol,
            strategy_name="Breakout_Simple",
            timeframe=timeframe,
            exchange=exchange,
            **kwargs
        )
        
        self.lookback_period = lookback_period
        self.position_size_pct = position_size_pct
        
        # Calcular máximos y mínimos rodantes
        self.market_data['High_Max'] = self.market_data['High'].rolling(
            window=lookback_period
        ).max()
        
        self.market_data['Low_Min'] = self.market_data['Low'].rolling(
            window=lookback_period
        ).min()
        
        print(f"📊 Estrategia Breakout configurada:")
        print(f"   - Lookback: {lookback_period} períodos")
        print(f"   - Position size: {position_size_pct*100}% del capital")
    
    def generate_signals(self):
        """Método viejo - no lo usamos"""
        raise NotImplementedError("Usa generate_simple_signals() en su lugar")
    
    def generate_simple_signals(self) -> list:
        """
        Genera señales de breakout.
        
        Lógica:
        - Compra cuando Close > High_Max[anterior]
        - Vende cuando Close < Low_Min[anterior]
        
        Returns:
            Lista de TradingSignal
        """
        self.simple_signals = []
        
        in_position = False
        
        # Empezar después del período de lookback
        for i in range(self.lookback_period + 1, len(self.market_data)):
            
            current_close = self.market_data['Close'].iloc[i]
            previous_high_max = self.market_data['High_Max'].iloc[i-1]
            previous_low_min = self.market_data['Low_Min'].iloc[i-1]
            
            # Breakout alcista: precio rompe por encima del máximo
            if current_close > previous_high_max and not in_position:
                self.create_simple_signal(
                    signal_type=SignalType.BUY,
                    timestamp=self.market_data.index[i],
                    price=current_close,
                    position_size_pct=self.position_size_pct
                )
                in_position = True
            
            # Breakout bajista: precio rompe por debajo del mínimo
            elif current_close < previous_low_min and in_position:
                self.create_simple_signal(
                    signal_type=SignalType.SELL,
                    timestamp=self.market_data.index[i],
                    price=current_close,
                    position_size_pct=1.0  # Cerrar posición completa
                )
                in_position = False
        
        print(f"✓ Generadas {len(self.simple_signals)} señales")
        print(f"  - Señales BUY: {sum(1 for s in self.simple_signals if s.signal_type == SignalType.BUY)}")
        print(f"  - Señales SELL: {sum(1 for s in self.simple_signals if s.signal_type == SignalType.SELL)}")
        
        return self.simple_signals