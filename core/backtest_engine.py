"""Backtest Engine - Motor simplificado de backtesting"""
from typing import List, Tuple
import pandas as pd
from datetime import datetime

from models.signals import StrategySignal
from models.enums import SignalType, SignalPositionSide
from models.trades.crypto_trade import CryptoTrade
from core.position_manager import PositionManager


class BacktestEngine:
    """Motor de backtest simplificado"""

    def __init__(self, initial_capital: float = 1000.0):
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        self.position_manager = PositionManager()
        self.completed_trades: List[CryptoTrade] = []

    def run(self, signals: List[StrategySignal]) -> Tuple[List[CryptoTrade], pd.DataFrame]:
        """
        Ejecuta el backtest procesando todas las señales.

        Returns:
            Tuple[List[CryptoTrade], pd.DataFrame]: (trades completados, dataframe de métricas)
        """
        for signal in signals:
            self._process_signal(signal)

        # Convertir trades a DataFrame de métricas
        df_metrics = self._trades_to_dataframe()
        return self.completed_trades, df_metrics

    def _process_signal(self, signal: StrategySignal) -> None:
        """Procesa una señal: abre, acumula o cierra posición"""
        symbol = signal.symbol

        if signal.signal_type == SignalType.BUY:
            if not self.position_manager.has_position(symbol):
                # Abrir nueva posición LONG
                self._open_long_position(signal)
            else:
                # Acumular entrada adicional a la posición existente
                self._add_entry_to_position(signal)

        elif signal.signal_type == SignalType.SELL:
            if self.position_manager.has_position(symbol):
                # Cerrar posición LONG
                self._close_position(signal)
            else:
                # Abrir posición SHORT (no implementado aún)
                pass

    def _open_long_position(self, signal: StrategySignal) -> None:
        """Abre una posición LONG"""
        # signal.exchange puede ser ExchangeName o str, manejamos ambos
        exchange_str = signal.exchange.value if hasattr(signal.exchange, 'value') else str(signal.exchange)

        trade = CryptoTrade(
            symbol=signal.symbol,
            entry_time=signal.timestamp,
            exchange=exchange_str,
            apply_fees=signal.fee > 0,  # Activar fees si la señal tiene fee
            apply_slippage=signal.slippage_cost > 0  # Activar slippage si la señal tiene slippage
        )

        # Añadir entrada al trade
        volume = signal.usdt_amount / signal.price  # Convertir USDT a crypto
        trade.add_entry(
            timestamp=signal.timestamp,
            signal_type=signal.signal_type,
            volume=volume,
            price=signal.price,
            order_type=signal.order_type
        )

        self.position_manager.open_position(signal.symbol, trade)

    def _add_entry_to_position(self, signal: StrategySignal) -> None:
        """Añade una entrada adicional a una posición existente (para promediar)"""
        trade = self.position_manager.get_position(signal.symbol)

        # Añadir entrada adicional al trade
        volume = signal.usdt_amount / signal.price
        trade.add_entry(
            timestamp=signal.timestamp,
            signal_type=signal.signal_type,
            volume=volume,
            price=signal.price,
            order_type=signal.order_type
        )

    def _close_position(self, signal: StrategySignal) -> None:
        """Cierra la posición actual"""
        trade = self.position_manager.close_position(signal.symbol)

        # Calcular volumen total de crypto de todas las entradas
        total_crypto_volume = sum(entry.volume for entry in trade.entries)

        # Añadir salida al trade vendiendo TODO el crypto que compramos
        trade.add_exit(
            timestamp=signal.timestamp,
            signal_type=signal.signal_type,
            volume=total_crypto_volume,  # ✅ Vendemos exactamente lo que compramos
            price=signal.price,
            order_type=signal.order_type
        )

        # Calcular P&L
        trade.calculate_pnl()

        # Actualizar capital
        self.current_capital += trade.net_profit_loss

        self.completed_trades.append(trade)

    def _trades_to_dataframe(self) -> pd.DataFrame:
        """Convierte los trades completados a DataFrame de métricas"""
        if not self.completed_trades:
            return pd.DataFrame()

        trades_data = []
        for trade in self.completed_trades:
            # Extraer datos básicos del trade
            entry = trade.entries[0] if trade.entries else None
            exit_trade = trade.exits[0] if trade.exits else None

            if not entry or not exit_trade:
                continue

            # Manejar signal_type que puede ser Enum o str
            signal_type_str = entry.signal_type.value if hasattr(entry.signal_type, 'value') else str(entry.signal_type)

            trades_data.append({
                'entry_timestamp': entry.timestamp,
                'exit_timestamp': exit_trade.timestamp,
                'market': 'Crypto',
                'exchange': trade.exchange,
                'symbol': trade.symbol,
                'currency': 'USDT',
                'Timeframe': None,  # Se puede añadir desde la estrategia
                'strategy_name': None,
                'signal_type': signal_type_str,
                'order_type': 'MARKET',
                'position_side': 'LONG',
                'entry_price': entry.price,
                'exit_price': exit_trade.price,
                'usdt_amount': entry.volume * entry.price,
                'fees': trade.fees,
                'slippage_cost': trade.slippage_cost,
                'gross_profit_loss': trade.gross_profit_loss,
                'net_profit_loss': trade.net_profit_loss,
                'cumulative_capital': self.current_capital,
                'return_on_capital': (trade.net_profit_loss / self.initial_capital) * 100,
            })

        return pd.DataFrame(trades_data)
