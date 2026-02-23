"""
BTCPugilanime — Tendencia (breakout-pullback)
Compra en el pullback de una ruptura de acumulación con confirmación de volumen.

Edge: Sesgo alcista estructural de BTC. Las correcciones generan zonas de acumulación
que al romperse con volumen ofrecen entradas de alta expectativa siguiendo la tendencia.
Contexto: Impulso tras acumulación en 5min.

v1: Entrada única en pullback a EMA. Trailing stop por ATR.
v1.1: Detección real de consolidación (filtro ATR-normalizado + invalidación por retorno a zona).
v2 (pendiente): Averaging con 2-3 entradas + POC detection.
"""

from strategies.base_strategy import BaseStrategy
from models.enums import SignalType, MarketType
from utils.timeframe import Timeframe


class BTCPugilanime(BaseStrategy):
    """
    Estrategia de tendencia breakout-pullback sobre BTC 5min.

    Lógica:
        1. Detecta consolidación: rango de N períodos estrecho (< consolidation_threshold ATRs)
        2. Detecta breakout: Close > máximo del rango + volumen > media * multiplicador
        3. Invalida breakout si el precio vuelve bajo el piso del rango (breakout falso)
        4. Espera pullback hasta la EMA de referencia
        5. Entra en BUY cuando el precio toca la EMA en el pullback
        6. Gestiona trailing stop por ATR desde el máximo alcanzado

    Parámetros optimizables:
        lookback_period: Períodos para detectar el rango de acumulación (10-50)
        ema_period:      EMA de referencia para el pullback (20, 50, 200)
        atr_period:      Períodos del ATR para trailing stop (7-21)
        atr_multiplier:  Multiplicador ATR para el stop (1.5-4.0)
        volume_multiplier: Umbral de volumen vs media del rango (1.2-3.0)
        consolidation_threshold: Ancho máx del rango en ATRs (1.5-5.0). Bajo = más selectivo.
        position_size_pct: Porcentaje del capital por trade (0.1-0.5)
    """

    def __init__(
        self,
        symbol: str = "BTC",
        timeframe: Timeframe = Timeframe.M5,
        exchange: str = "Binance",
        # Parámetros optimizables:
        lookback_period: int = 20,
        ema_period: int = 20,
        atr_period: int = 14,
        atr_multiplier: float = 2.0,
        volume_multiplier: float = 1.5,
        consolidation_threshold: float = 3.0,  # Ancho max del rango en ATRs
        position_size_pct: float = 0.5,
        **kwargs
    ):
        super().__init__(
            market=MarketType.CRYPTO,
            symbol=symbol,
            strategy_name="BTCPugilanime",
            timeframe=timeframe,
            exchange=exchange,
            **kwargs
        )

        self.lookback_period = int(lookback_period)
        self.ema_period = int(ema_period)
        self.atr_period = int(atr_period)
        self.atr_multiplier = float(atr_multiplier)
        self.volume_multiplier = float(volume_multiplier)
        self.consolidation_threshold = float(consolidation_threshold)
        self.position_size_pct = float(position_size_pct)

        # Pre-calcular indicadores
        # Máximo del rango (nivel de ruptura)
        self.market_data['Range_High'] = self.market_data['High'].rolling(self.lookback_period).max()

        # EMA de referencia para detectar el pullback
        self.market_data['EMA'] = self.market_data['Close'].ewm(span=self.ema_period, adjust=False).mean()

        # Media de volumen del rango (filtro de ruptura)
        self.market_data['Volume_MA'] = self.market_data['Volume'].rolling(self.lookback_period).mean()

        # ATR para trailing stop
        high_low = self.market_data['High'] - self.market_data['Low']
        high_close = (self.market_data['High'] - self.market_data['Close'].shift()).abs()
        low_close = (self.market_data['Low'] - self.market_data['Close'].shift()).abs()
        true_range = high_low.combine(high_close, max).combine(low_close, max)
        self.market_data['ATR'] = true_range.rolling(self.atr_period).mean()

        # Piso del rango (para invalidación de breakout falso)
        self.market_data['Range_Low'] = self.market_data['Low'].rolling(self.lookback_period).min()

        # Ancho del rango normalizado por volatilidad (bajo = consolidación real)
        self.market_data['Range_Width_ATR'] = (
            (self.market_data['Range_High'] - self.market_data['Range_Low']) / self.market_data['ATR']
        )

        print(f"📊 BTCPugilanime configurada:")
        print(f"   - Lookback: {self.lookback_period} períodos")
        print(f"   - EMA pullback: {self.ema_period}")
        print(f"   - ATR trailing: período={self.atr_period}, multiplicador={self.atr_multiplier}")
        print(f"   - Filtro volumen: {self.volume_multiplier}x media")
        print(f"   - Consolidación: rango < {self.consolidation_threshold} ATRs")

    def generate_simple_signals(self) -> list:
        """
        Máquina de estados:
            SCANNING         → buscando consolidación + ruptura válida
                               (rango estrecho < consolidation_threshold ATRs)
            BREAKOUT         → ruptura detectada, esperando pullback a la EMA
                               Si close < range_low → breakout falso, vuelve a SCANNING
            IN_POSITION      → en trade, gestionando trailing stop ATR
            WAITING_RESET    → trade completado, esperando que precio baje bajo EMA
                               para consumir el movimiento antes del próximo setup

        Un breakout = un intento de entrada. Después del SELL, no se busca nuevo
        breakout hasta que el precio resetee por debajo de la EMA.
        """
        self.simple_signals = []

        # Estados del loop
        state = "SCANNING"
        breakout_range_high = None   # Nivel de ruptura
        breakout_range_low = None    # Piso de la zona (para invalidación)
        seen_above_ema = False       # Precio se alejó de la EMA (confirma impulso)
        max_price_since_entry = None # Para trailing stop ATR
        trailing_stop = None

        # Pre-extraer arrays numpy para velocidad (~10-50x vs .iloc)
        closes = self.market_data['Close'].values
        highs = self.market_data['High'].values
        lows = self.market_data['Low'].values
        volumes = self.market_data['Volume'].values
        emas = self.market_data['EMA'].values
        range_highs = self.market_data['Range_High'].values
        volume_mas = self.market_data['Volume_MA'].values
        atrs = self.market_data['ATR'].values
        range_lows = self.market_data['Range_Low'].values
        range_width_atrs = self.market_data['Range_Width_ATR'].values
        timestamps = self.market_data.index

        start = max(self.lookback_period, self.ema_period, self.atr_period) + 1

        for i in range(start, len(self.market_data)):
            close = closes[i]
            high = highs[i]
            low = lows[i]
            volume = volumes[i]
            ema = emas[i]
            range_high = range_highs[i - 1]  # prev para no usar el actual
            volume_ma = volume_mas[i - 1]
            atr = atrs[i]
            range_low = range_lows[i - 1]
            range_width_atr = range_width_atrs[i - 1]

            # ----------------------------------------------------------------
            if state == "SCANNING":
                # Condición de ruptura:
                # 1. Rango estrecho (consolidación real, no tendencia)
                # 2. Close supera el máximo de los últimos N períodos
                # 3. Volumen del breakout > media * multiplicador
                is_consolidation = range_width_atr < self.consolidation_threshold
                breakout = (
                    is_consolidation and
                    close > range_high and
                    volume > volume_ma * self.volume_multiplier
                )
                if breakout:
                    state = "BREAKOUT"
                    breakout_range_high = range_high  # guardar nivel para invalidación
                    breakout_range_low = range_low    # guardar piso para invalidación

            # ----------------------------------------------------------------
            elif state == "BREAKOUT":
                # Invalidación: precio vuelve a la zona -> breakout falso
                if close < breakout_range_low:
                    state = "SCANNING"
                    breakout_range_high = None
                    breakout_range_low = None
                    seen_above_ema = False
                    continue

                # Fase 1: el precio debe alejarse de la EMA (confirma impulso post-breakout)
                # Una vela entera por encima de la EMA = el breakout generó movimiento real
                if not seen_above_ema:
                    if low > ema:
                        seen_above_ema = True
                    continue  # No evaluar entrada hasta confirmar impulso

                # Fase 2: pullback — el precio vuelve a tocar la EMA desde arriba
                # La EMA actúa como árbitro automático:
                #   EMA > breakout_range_high → pullback válido, todavía por encima del rango
                #   EMA < breakout_range_high → pullback demasiado profundo, volvió al rango → no entrar
                #
                # TODO: explorar Hipótesis B — entrada por % de retroceso en vez de EMA
                pullback_touched_ema = low <= ema <= close  # el candle toca la EMA
                ema_above_breakout = ema > breakout_range_high  # EMA sigue sobre el rango

                if pullback_touched_ema and ema_above_breakout:
                    # Entrada en BUY
                    self.create_simple_signal(
                        signal_type=SignalType.BUY,
                        timestamp=timestamps[i],
                        price=close,
                        position_size_pct=self.position_size_pct
                    )
                    state = "IN_POSITION"
                    max_price_since_entry = close
                    trailing_stop = close - atr * self.atr_multiplier

            # ----------------------------------------------------------------
            elif state == "IN_POSITION":
                # Actualizar trailing stop: sube cuando el precio sube, nunca baja
                if high > max_price_since_entry:
                    max_price_since_entry = high
                    trailing_stop = max_price_since_entry - atr * self.atr_multiplier

                # Salida por trailing stop ATR
                if close < trailing_stop:
                    self.create_simple_signal(
                        signal_type=SignalType.SELL,
                        timestamp=timestamps[i],
                        price=close,
                        position_size_pct=1.0  # cerrar posición completa
                    )
                    # WAITING_RESET: un breakout = un intento. Esperamos que el
                    # precio baje bajo la EMA antes de buscar el próximo setup.
                    state = "WAITING_RESET"
                    breakout_range_high = None
                    breakout_range_low = None
                    seen_above_ema = False
                    max_price_since_entry = None
                    trailing_stop = None

            # ----------------------------------------------------------------
            elif state == "WAITING_RESET":
                # El movimiento se consumió. Esperamos que el precio vuelva
                # a estar por debajo de la EMA antes de escanear de nuevo.
                if close < ema:
                    state = "SCANNING"

        buys = sum(1 for s in self.simple_signals if s.signal_type == SignalType.BUY)
        sells = sum(1 for s in self.simple_signals if s.signal_type == SignalType.SELL)
        print(f"✓ Señales generadas: {len(self.simple_signals)} (BUY: {buys}, SELL: {sells})")
        return self.simple_signals
