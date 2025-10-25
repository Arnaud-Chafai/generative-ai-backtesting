"""
Estrategia de ejemplo: Cruce de Medias Móviles
Usando el sistema simplificado de señales.
"""

from strategies.base_strategy import BaseStrategy
from models.enums import SignalType, MarketType
from utils.timeframe import Timeframe


class MACrossoverSimple(BaseStrategy):
    """
    Estrategia simple: compra cuando MA rápida cruza por encima de MA lenta,
    vende cuando cruza por debajo.
    """
    
    def __init__(
        self,
        symbol: str = "BTC",
        timeframe: Timeframe = Timeframe.M5,
        exchange: str = "Binance",
        fast_period: int = 10,
        slow_period: int = 30,
        position_size_pct: float = 0.3,  # Usar 30% del capital por trade
        **kwargs
    ):
        super().__init__(
            market=MarketType.CRYPTO,
            symbol=symbol,
            strategy_name="MA_Crossover_Simple",
            timeframe=timeframe,
            exchange=exchange,
            **kwargs
        )
        
        self.fast_period = fast_period
        self.slow_period = slow_period
        self.position_size_pct = position_size_pct
        
        # Calcular medias móviles
        self.market_data['MA_Fast'] = self.market_data['Close'].rolling(fast_period).mean()
        self.market_data['MA_Slow'] = self.market_data['Close'].rolling(slow_period).mean()
    
    def generate_signals(self):
        """Método viejo - no lo usamos"""
        raise NotImplementedError("Usa generate_simple_signals() en su lugar")
    
    def generate_simple_signals(self) -> list:
        """
        Genera señales cuando las medias móviles se cruzan.
        
        Returns:
            Lista de TradingSignal simplificadas
        """
        self.simple_signals = []  # Reset
        
        in_position = False
        
        for i in range(self.slow_period, len(self.market_data)):
            ma_fast_current = self.market_data['MA_Fast'].iloc[i]
            ma_slow_current = self.market_data['MA_Slow'].iloc[i]
            ma_fast_previous = self.market_data['MA_Fast'].iloc[i-1]
            ma_slow_previous = self.market_data['MA_Slow'].iloc[i-1]
            
            # Cruce alcista (Golden Cross): MA rápida cruza por encima
            if (ma_fast_previous <= ma_slow_previous and 
                ma_fast_current > ma_slow_current and 
                not in_position):
                
                self.create_simple_signal(
                    signal_type=SignalType.BUY,
                    timestamp=self.market_data.index[i],
                    price=self.market_data['Close'].iloc[i],
                    position_size_pct=self.position_size_pct
                )
                in_position = True
            
            # Cruce bajista (Death Cross): MA rápida cruza por debajo
            elif (ma_fast_previous >= ma_slow_previous and 
                  ma_fast_current < ma_slow_current and 
                  in_position):
                
                self.create_simple_signal(
                    signal_type=SignalType.SELL,
                    timestamp=self.market_data.index[i],
                    price=self.market_data['Close'].iloc[i],
                    position_size_pct=1.0  # Cerrar 100% de la posición
                )
                in_position = False
        
        print(f"✓ Generadas {len(self.simple_signals)} señales")
        return self.simple_signals


