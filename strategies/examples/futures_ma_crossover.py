"""
Estrategia simple de cruce de medias moviles para futuros CME.

Compra cuando la MA rapida cruza por encima de la MA lenta.
Vende cuando la MA rapida cruza por debajo de la MA lenta.
Stop loss fijo en puntos para calcular sizing por riesgo.

Funciona con cualquier futuro configurado: ES, NQ, GC, CL.
"""

from strategies.base_strategy import BaseStrategy
from models.enums import SignalType, MarketType
from utils.timeframe import Timeframe


class FuturesMACrossover(BaseStrategy):
    """
    Cruce de medias moviles para futuros CME.

    Parametros:
        symbol: Activo (ES, NQ, GC, CL)
        fast_period: Periodo de la MA rapida
        slow_period: Periodo de la MA lenta
        stop_points: Distancia del stop loss en puntos del precio
        risk_pct: Porcentaje del capital a arriesgar por trade
    """

    def __init__(
        self,
        symbol: str = "CL",
        fast_period: int = 10,
        slow_period: int = 30,
        stop_points: float = 2.0,
        risk_pct: float = 0.02,
        **kwargs
    ):
        super().__init__(
            market=MarketType.FUTURES,
            symbol=symbol,
            strategy_name=f"{symbol}_MA_Crossover",
            timeframe=kwargs.pop('timeframe', Timeframe.D1),
            exchange="CME",
            **kwargs
        )
        self.fast_period = fast_period
        self.slow_period = slow_period
        self.stop_points = stop_points
        self.risk_pct = risk_pct

    def generate_simple_signals(self):
        df = self.market_data
        signals = []

        ma_fast = df['Close'].rolling(self.fast_period).mean()
        ma_slow = df['Close'].rolling(self.slow_period).mean()

        in_position = False

        for i in range(self.slow_period + 1, len(df)):
            # Cruce alcista: MA rapida cruza por encima de MA lenta
            if ma_fast.iloc[i] > ma_slow.iloc[i] and ma_fast.iloc[i-1] <= ma_slow.iloc[i-1]:
                if not in_position:
                    price = df['Close'].iloc[i]
                    stop_loss = price - self.stop_points

                    signals.append(self.create_simple_signal(
                        signal_type=SignalType.BUY,
                        timestamp=df.index[i],
                        price=price,
                        position_size_pct=self.risk_pct,
                        stop_loss_price=stop_loss
                    ))
                    in_position = True

            # Cruce bajista: MA rapida cruza por debajo de MA lenta
            elif ma_fast.iloc[i] < ma_slow.iloc[i] and ma_fast.iloc[i-1] >= ma_slow.iloc[i-1]:
                if in_position:
                    signals.append(self.create_simple_signal(
                        signal_type=SignalType.SELL,
                        timestamp=df.index[i],
                        price=df['Close'].iloc[i],
                        position_size_pct=1.0
                    ))
                    in_position = False

        return signals
