"""
Estrategia SMA Crossover para CL (Crude Oil Futures).

Estrategia sencilla para validar el pipeline de futuros:
- Compra cuando SMA rápida cruza por encima de SMA lenta
- Vende cuando SMA rápida cruza por debajo de SMA lenta
"""

from strategies.base_strategy import BaseStrategy
from models.enums import SignalType, MarketType
from utils.timeframe import Timeframe


class CLSmaCrossover(BaseStrategy):

    def __init__(
        self,
        fast_period: int = 10,
        slow_period: int = 30,
        position_size_pct: float = 1.0,
        **kwargs
    ):
        super().__init__(
            market=MarketType.FUTURES,
            symbol=kwargs.get('symbol', 'CL'),
            strategy_name="CL_SMA_Crossover",
            timeframe=kwargs.get('timeframe', Timeframe.D1),
            exchange=kwargs.get('exchange', 'CME'),
            **kwargs
        )

        self.fast_period = int(fast_period)
        self.slow_period = int(slow_period)
        self.position_size_pct = float(position_size_pct)

        self.market_data['SMA_fast'] = self.market_data['Close'].rolling(self.fast_period).mean()
        self.market_data['SMA_slow'] = self.market_data['Close'].rolling(self.slow_period).mean()

    def generate_simple_signals(self) -> list:
        self.simple_signals = []
        df = self.market_data
        in_position = False

        for i in range(self.slow_period + 1, len(df)):
            fast_prev = df['SMA_fast'].iloc[i - 1]
            fast_curr = df['SMA_fast'].iloc[i]
            slow_prev = df['SMA_slow'].iloc[i - 1]
            slow_curr = df['SMA_slow'].iloc[i]

            # Golden cross: SMA rápida cruza por encima de SMA lenta
            if fast_prev <= slow_prev and fast_curr > slow_curr and not in_position:
                self.create_simple_signal(
                    signal_type=SignalType.BUY,
                    timestamp=df.index[i],
                    price=df['Close'].iloc[i],
                    position_size_pct=self.position_size_pct
                )
                in_position = True

            # Death cross: SMA rápida cruza por debajo de SMA lenta
            elif fast_prev >= slow_prev and fast_curr < slow_curr and in_position:
                self.create_simple_signal(
                    signal_type=SignalType.SELL,
                    timestamp=df.index[i],
                    price=df['Close'].iloc[i],
                    position_size_pct=1.0
                )
                in_position = False

        return self.simple_signals
