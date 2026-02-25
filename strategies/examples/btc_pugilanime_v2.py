"""
BTCPugilanime v2 — Tendencia (breakout-pullback)
Compra en el pullback de una ruptura de acumulación con confirmación de volumen.

Edge: Sesgo alcista estructural de BTC. Correcciones en tendencia alcista generan
pullbacks a EMAs que ofrecen entradas de alta expectativa.

v2: SMA 200 trend filter + EMA 30 pullback + ATR stop/trailing + DCA temporal (3 entradas).
"""

from strategies.base_strategy import BaseStrategy
from models.enums import SignalType, MarketType
from utils.timeframe import Timeframe


class BTCPugilanimeV2(BaseStrategy):
    """
    Estrategia breakout-pullback sobre BTC 5min con filtro de tendencia y DCA temporal.

    Mejoras vs v1:
        - Filtro tendencia: SMA 200 (solo opera en alcista)
        - EMA 50 para pullbacks significativos (vs EMA 20)
        - Stop dinámico por ATR (vs mínimo de N velas)
        - Trailing stop ATR tras 1R de profit (vs TP fijo)
        - DCA temporal: 3 entradas cada 15min (vs entrada única)
        - Confirmación breakout: 2 cierres consecutivos (vs 1)

    Parámetros optimizables:
        lookback_period, ema_period, sma_trend_period, atr_period,
        atr_stop_mult, atr_trail_mult, trail_activation_r,
        volume_multiplier, breakout_confirm_bars, breakout_timeout,
        dca_entries, dca_interval_bars, position_size_pct
    """

    def __init__(
        self,
        symbol: str = "BTC",
        timeframe: Timeframe = Timeframe.M5,
        exchange: str = "Binance",
        # Rango y tendencia:
        lookback_period: int = 96,
        ema_period: int = 30,
        sma_trend_period: int = 200,
        # ATR stop/trailing:
        atr_period: int = 14,
        atr_stop_mult: float = 2.5,
        atr_trail_mult: float = 1.5,
        trail_activation_r: float = 1.0,
        # Breakout:
        volume_multiplier: float = 2.0,
        breakout_confirm_bars: int = 2,
        breakout_timeout: int = 96,
        # DCA:
        dca_entries: int = 3,
        dca_interval_bars: int = 3,
        # Sizing:
        position_size_pct: float = 0.5,
        **kwargs
    ):
        super().__init__(
            market=MarketType.CRYPTO,
            symbol=symbol,
            strategy_name="BTCPugilanimeV2",
            timeframe=timeframe,
            exchange=exchange,
            **kwargs
        )

        self.lookback_period = int(lookback_period)
        self.ema_period = int(ema_period)
        self.sma_trend_period = int(sma_trend_period)
        self.atr_period = int(atr_period)
        self.atr_stop_mult = float(atr_stop_mult)
        self.atr_trail_mult = float(atr_trail_mult)
        self.trail_activation_r = float(trail_activation_r)
        self.volume_multiplier = float(volume_multiplier)
        self.breakout_confirm_bars = int(breakout_confirm_bars)
        self.breakout_timeout = int(breakout_timeout)
        self.dca_entries = int(dca_entries)
        self.dca_interval_bars = int(dca_interval_bars)
        self.position_size_pct = float(position_size_pct)

        # Tamaño por entrada DCA
        self.dca_size_pct = self.position_size_pct / self.dca_entries

        # Pre-calcular indicadores
        df = self.market_data

        # Rango de acumulación
        df['Range_High'] = df['High'].rolling(self.lookback_period).max()
        df['Range_Low'] = df['Low'].rolling(self.lookback_period).min()

        # Rango estable: máximo no cambió en lookback/2 velas
        half = self.lookback_period // 2
        df['Range_Stable'] = (df['Range_High'] == df['Range_High'].shift(half))

        # Tendencia y pullback
        df['SMA_Trend'] = df['Close'].rolling(self.sma_trend_period).mean()
        df['EMA'] = df['Close'].ewm(span=self.ema_period, adjust=False).mean()

        # Volumen
        df['Volume_MA'] = df['Volume'].rolling(20).mean()

        # ATR para stops dinámicos
        tr = df['High'] - df['Low']
        tr = tr.combine(abs(df['High'] - df['Close'].shift(1)), max)
        tr = tr.combine(abs(df['Low'] - df['Close'].shift(1)), max)
        df['ATR'] = tr.rolling(self.atr_period).mean()

        print(f"BTCPugilanimeV2 configurada:")
        print(f"   Rango: {self.lookback_period} velas ({self.lookback_period * 5 / 60:.0f}h)")
        print(f"   Tendencia: SMA {self.sma_trend_period} | Pullback: EMA {self.ema_period}")
        print(f"   Stop: ATR({self.atr_period}) x {self.atr_stop_mult} | Trail: ATR x {self.atr_trail_mult} tras {self.trail_activation_r}R")
        print(f"   DCA: {self.dca_entries} entradas cada {self.dca_interval_bars} velas ({self.dca_interval_bars * 5}min)")
        print(f"   Breakout: {self.breakout_confirm_bars} velas confirm, vol {self.volume_multiplier}x")

    def generate_simple_signals(self) -> list:
        """
        Máquina de estados:
            SCANNING      → buscando ruptura del rango con volumen + tendencia alcista
            BREAKOUT      → ruptura detectada, esperando pullback a EMA
            DCA_FILLING   → primera entrada hecha, completando DCA cada N velas
            IN_POSITION   → DCA completo, gestionando trailing stop
            WAITING_RESET → trade cerrado, esperando reset bajo EMA
        """
        self.simple_signals = []

        # Estado
        state = "SCANNING"
        breakout_range_high = None
        breakout_range_low = None
        seen_above_ema = False
        stop_loss = None
        entry_price_first = None      # Precio de la primera entrada (para calcular R)
        entry_risk = None             # Riesgo = entry - stop (para calcular trailing activation)
        trailing_stop = None
        trailing_active = False
        highest_high_since_entry = None
        bars_above_range = 0          # Conteo de cierres consecutivos sobre range_high
        volume_confirmed = False       # Volumen confirmado en primera vela del breakout
        bars_since_breakout = 0       # Timeout del breakout
        dca_entries_done = 0
        bars_since_last_entry = 0
        trades_this_consolidation = 0
        last_breakout_level = None

        # Pre-extraer arrays numpy
        closes = self.market_data['Close'].values
        highs = self.market_data['High'].values
        lows = self.market_data['Low'].values
        volumes = self.market_data['Volume'].values
        emas = self.market_data['EMA'].values
        sma_trends = self.market_data['SMA_Trend'].values
        range_highs = self.market_data['Range_High'].values
        range_lows = self.market_data['Range_Low'].values
        range_stables = self.market_data['Range_Stable'].values
        volume_mas = self.market_data['Volume_MA'].values
        atrs = self.market_data['ATR'].values
        timestamps = self.market_data.index

        start = max(self.lookback_period, self.sma_trend_period, self.atr_period) + 1

        for i in range(start, len(self.market_data)):
            close = closes[i]
            high = highs[i]
            low = lows[i]
            ema = emas[i]
            atr = atrs[i]

            # ----------------------------------------------------------------
            if state == "SCANNING":
                # Filtro de tendencia: solo operar en alcista
                if close < sma_trends[i]:
                    bars_above_range = 0
                    continue

                range_high = range_highs[i - 1]
                range_stable = range_stables[i - 1]
                volume_ma = volume_mas[i - 1]

                # Confirmación: N cierres consecutivos sobre range_high
                # Primera vela: necesita range_stable + volumen. Siguientes: solo close > range_high.
                if close > range_high:
                    if bars_above_range == 0:
                        # Primera vela: necesita range estable y volumen
                        if range_stable and volumes[i] > volume_ma * self.volume_multiplier:
                            bars_above_range = 1
                            volume_confirmed = True
                    else:
                        # Velas de confirmación: solo close > range_high
                        bars_above_range += 1
                else:
                    bars_above_range = 0
                    volume_confirmed = False

                if bars_above_range >= self.breakout_confirm_bars:
                    # Nueva consolidación?
                    if range_high != last_breakout_level:
                        trades_this_consolidation = 0
                        last_breakout_level = range_high
                    if trades_this_consolidation >= 2:
                        bars_above_range = 0
                        continue

                    state = "BREAKOUT"
                    breakout_range_high = range_high
                    breakout_range_low = range_lows[i - 1]
                    seen_above_ema = False
                    bars_since_breakout = 0
                    bars_above_range = 0

            # ----------------------------------------------------------------
            elif state == "BREAKOUT":
                bars_since_breakout += 1

                # Timeout
                if bars_since_breakout > self.breakout_timeout:
                    state = "SCANNING"
                    seen_above_ema = False
                    continue

                # Invalidación: precio vuelve bajo el rango
                if close < breakout_range_low:
                    state = "SCANNING"
                    seen_above_ema = False
                    continue

                # Fase 1: confirmar impulso post-breakout
                if not seen_above_ema:
                    if low > ema:
                        seen_above_ema = True
                    continue

                # Fase 2: pullback toca EMA desde arriba
                pullback_touched_ema = low <= ema <= close
                ema_above_breakout = ema > breakout_range_high

                if pullback_touched_ema and ema_above_breakout:
                    # Stop basado en ATR
                    stop_loss = close - atr * self.atr_stop_mult
                    entry_risk = close - stop_loss
                    if entry_risk <= 0:
                        continue

                    # Primera entrada DCA
                    entry_price_first = close
                    self.create_simple_signal(
                        signal_type=SignalType.BUY,
                        timestamp=timestamps[i],
                        price=close,
                        position_size_pct=self.dca_size_pct
                    )
                    dca_entries_done = 1
                    bars_since_last_entry = 0
                    highest_high_since_entry = high
                    trailing_stop = None
                    trailing_active = False
                    trades_this_consolidation += 1

                    if self.dca_entries == 1:
                        state = "IN_POSITION"
                    else:
                        state = "DCA_FILLING"

            # ----------------------------------------------------------------
            elif state == "DCA_FILLING":
                bars_since_last_entry += 1
                highest_high_since_entry = max(highest_high_since_entry, high)

                # Protección DCA: si toca stop, vender todo y salir
                if close <= stop_loss:
                    self.create_simple_signal(
                        signal_type=SignalType.SELL,
                        timestamp=timestamps[i],
                        price=close,
                        position_size_pct=1.0
                    )
                    state = "WAITING_RESET"
                    stop_loss = None
                    entry_price_first = None
                    entry_risk = None
                    trailing_stop = None
                    trailing_active = False
                    highest_high_since_entry = None
                    dca_entries_done = 0
                    seen_above_ema = False
                    continue

                # Siguiente entrada DCA cada N velas
                if bars_since_last_entry >= self.dca_interval_bars:
                    self.create_simple_signal(
                        signal_type=SignalType.BUY,
                        timestamp=timestamps[i],
                        price=close,
                        position_size_pct=self.dca_size_pct
                    )
                    dca_entries_done += 1
                    bars_since_last_entry = 0

                    if dca_entries_done >= self.dca_entries:
                        state = "IN_POSITION"

            # ----------------------------------------------------------------
            elif state == "IN_POSITION":
                highest_high_since_entry = max(highest_high_since_entry, high)

                # Check trailing activation
                if not trailing_active:
                    profit = close - entry_price_first
                    if profit >= entry_risk * self.trail_activation_r:
                        trailing_active = True
                        trailing_stop = highest_high_since_entry - atr * self.atr_trail_mult

                # Update trailing stop (solo sube)
                if trailing_active:
                    new_trail = highest_high_since_entry - atr * self.atr_trail_mult
                    if new_trail > trailing_stop:
                        trailing_stop = new_trail

                # Exit conditions
                hit_stop = close <= stop_loss
                hit_trail = trailing_active and close <= trailing_stop

                if hit_stop or hit_trail:
                    self.create_simple_signal(
                        signal_type=SignalType.SELL,
                        timestamp=timestamps[i],
                        price=close,
                        position_size_pct=1.0
                    )
                    state = "WAITING_RESET"
                    stop_loss = None
                    entry_price_first = None
                    entry_risk = None
                    trailing_stop = None
                    trailing_active = False
                    highest_high_since_entry = None
                    dca_entries_done = 0
                    seen_above_ema = False

            # ----------------------------------------------------------------
            elif state == "WAITING_RESET":
                if close < ema:
                    state = "SCANNING"

        buys = sum(1 for s in self.simple_signals if s.signal_type == SignalType.BUY)
        sells = sum(1 for s in self.simple_signals if s.signal_type == SignalType.SELL)
        print(f"Signals: {len(self.simple_signals)} (BUY: {buys}, SELL: {sells})")
        return self.simple_signals

