"""
Motor simplificado de backtest.

Este motor procesa señales de trading en orden cronológico y calcula
el P&L resultante considerando fees, slippage y múltiples entradas
por posición.

Filosofía: Todo el flujo de ejecución está en un solo lugar para que
sea fácil de entender y debuggear.
"""

from dataclasses import dataclass
from datetime import datetime
import pandas as pd
from models.enums import SignalType, SignalPositionSide
from models.simple_signals import TradingSignal


@dataclass
class Entry:
    """
    Una entrada individual dentro de una posición.

    Cuando haces múltiples compras para promediar, cada compra
    es un Entry separado que se guarda en la lista de entradas
    de la Position.
    """
    timestamp: datetime
    price: float  # Precio real después de aplicar slippage
    size_usdt: float       # Crypto: USDT gastados. Futuros: 0
    contracts: int          # Crypto: 0. Futuros: N contratos
    fee: float  # Fees pagados en esta entrada
    slippage_cost: float  # Costo del slippage en esta entrada


class Position:
    """
    Representa una posición abierta que puede tener múltiples entradas.

    Por ejemplo, si compras BTC a 50k, luego compras más a 48k para
    promediar, y luego vendes todo a 52k, esa es una Position con
    dos Entries (la compra a 50k y la compra a 48k).
    """

    def __init__(self, symbol: str, entry_time: datetime):
        self.symbol = symbol
        self.entry_time = entry_time  # Timestamp de la primera entrada
        self.entries: list[Entry] = []
        self.position_side: SignalPositionSide = None  # Set on first entry

    def add_entry(self, timestamp: datetime, price: float,
                  size_usdt: float, fee: float, slippage_cost: float,
                  contracts: int = 0):
        """
        Añade una entrada más a esta posición.

        Esto se llama cada vez que llega una señal BUY mientras
        ya hay una posición abierta. Es cómo implementamos el
        promediado de entradas.
        """
        self.entries.append(Entry(
            timestamp=timestamp,
            price=price,
            size_usdt=size_usdt,
            contracts=contracts,
            fee=fee,
            slippage_cost=slippage_cost
        ))

    def total_cost(self) -> float:
        """Cuántos USDT gastamos en total en todas las entradas."""
        return sum(entry.size_usdt for entry in self.entries)

    def total_fees_on_entries(self) -> float:
        """Fees totales pagados en todas las entradas."""
        return sum(entry.fee for entry in self.entries)

    def total_slippage_on_entries(self) -> float:
        """Slippage total pagado en todas las entradas."""
        return sum(entry.slippage_cost for entry in self.entries)

    def total_crypto(self) -> float:
        """
        Cuánto crypto tenemos en total sumando todas las entradas.

        Por ejemplo, si compramos 0.5 BTC a 50k (25k USDT) y luego
        0.5 BTC a 48k (24k USDT), tenemos 1.0 BTC en total.
        """
        return sum(entry.size_usdt / entry.price for entry in self.entries)

    def average_entry_price(self) -> float:
        """
        Precio promedio ponderado de todas las entradas.

        Esto es útil para análisis: te dice a qué precio "efectivo"
        compraste considerando todas tus entradas.
        """
        total_crypto = self.total_crypto()
        if total_crypto == 0:
            return 0.0
        return self.total_cost() / total_crypto

    def total_contracts(self) -> int:
        """Total de contratos en todas las entradas."""
        return sum(entry.contracts for entry in self.entries)

    def average_entry_price_futures(self) -> float:
        """Precio promedio ponderado por contratos (futuros)."""
        total_c = self.total_contracts()
        if total_c == 0:
            return 0.0
        return sum(e.price * e.contracts for e in self.entries) / total_c

    def partial_close_futures(self, pct: float) -> dict:
        """
        Cierra una fracción de la posición en futuros (floor por entrada).

        Returns:
            dict con total_contracts, total_entry_fees, total_entry_slippage
        """
        closed_contracts = 0
        closed_fees = 0.0
        closed_slippage = 0.0

        for entry in self.entries:
            contracts_to_close = int(entry.contracts * pct)  # floor
            if contracts_to_close == 0:
                continue
            ratio = contracts_to_close / entry.contracts
            closed_contracts += contracts_to_close
            closed_fees += entry.fee * ratio
            closed_slippage += entry.slippage_cost * ratio

            # Reducir la entrada restante
            remaining_ratio = 1 - ratio
            entry.contracts -= contracts_to_close
            entry.fee *= remaining_ratio
            entry.slippage_cost *= remaining_ratio

        return {
            'total_contracts': closed_contracts,
            'total_entry_fees': closed_fees,
            'total_entry_slippage': closed_slippage,
        }

    def partial_close(self, pct: float) -> dict:
        """
        Cierra una fracción de la posición proporcionalmente en todas las entradas.

        Reduce cada Entry in-place y retorna las métricas agregadas de la
        porción cerrada. El average_entry_price no cambia (reducción proporcional).

        Args:
            pct: Fracción a cerrar (0.33 = 33%)

        Returns:
            dict con total_cost, total_crypto, total_entry_fees, total_entry_slippage
        """
        closed_cost = 0.0
        closed_crypto = 0.0
        closed_fees = 0.0
        closed_slippage = 0.0

        for entry in self.entries:
            size_closed = entry.size_usdt * pct
            crypto_closed = size_closed / entry.price
            fee_closed = entry.fee * pct
            slip_closed = entry.slippage_cost * pct

            closed_cost += size_closed
            closed_crypto += crypto_closed
            closed_fees += fee_closed
            closed_slippage += slip_closed

            # Reducir la entrada restante
            entry.size_usdt -= size_closed
            entry.fee -= fee_closed
            entry.slippage_cost -= slip_closed

        return {
            'total_cost': closed_cost,
            'total_crypto': closed_crypto,
            'total_entry_fees': closed_fees,
            'total_entry_slippage': closed_slippage,
        }


class BacktestEngine:
    """
    Motor principal de backtest.

    Procesa señales de trading en orden cronológico y mantiene
    el estado del capital y las posiciones abiertas.
    """

    def __init__(self, initial_capital: float, market_config: dict):
        """
        Inicializa el motor.

        Args:
            initial_capital: Capital inicial en USDT (ej: 1000.0)
            market_config: Dict con configuración del mercado:
                - 'exchange_fee': Tasa de comisión (ej: 0.001 = 0.1%)
                - 'slippage': Slippage esperado (ej: 0.0005 = 0.05%)
                - 'tick_size': Tamaño mínimo de precio (ej: 0.01)
        """
        self.initial_capital = initial_capital
        self.capital = initial_capital  # Capital disponible actual

        # Extraer configuración del mercado
        self.tick_size = market_config['tick_size']

        # Futuros: slippage fijo en ticks, fee fijo en USD por contrato
        # Crypto: slippage porcentual, fee como ratio del volumen
        if 'slippage_ticks' in market_config:
            self.slippage_fixed = market_config['slippage_ticks'] * self.tick_size
            self.slippage_pct = 0.0
            self.fee_fixed = market_config['exchange_fee']
            self.fee_rate = 0.0
        else:
            self.slippage_fixed = 0.0
            self.slippage_pct = market_config['slippage']
            self.fee_fixed = 0.0
            self.fee_rate = market_config['exchange_fee']

        # Detectar tipo de mercado y campos de futuros
        self.is_futures = 'slippage_ticks' in market_config
        if self.is_futures:
            self.point_value = market_config['tick_value'] / market_config['tick_size']
            self.contract_size = market_config['contract_size']
        else:
            self.point_value = 0.0
            self.contract_size = 0

        # Estado del motor
        self.current_position: Position | None = None
        self.completed_trades: list[dict] = []

    def _is_entry(self, signal: TradingSignal) -> bool:
        """BUY+LONG = entry, SELL+SHORT = entry."""
        return (
            (signal.position_side == SignalPositionSide.LONG and signal.signal_type == SignalType.BUY) or
            (signal.position_side == SignalPositionSide.SHORT and signal.signal_type == SignalType.SELL)
        )

    def _is_exit(self, signal: TradingSignal) -> bool:
        """SELL+LONG = exit, BUY+SHORT = exit."""
        return (
            (signal.position_side == SignalPositionSide.LONG and signal.signal_type == SignalType.SELL) or
            (signal.position_side == SignalPositionSide.SHORT and signal.signal_type == SignalType.BUY)
        )

    def run(self, signals: list[TradingSignal]) -> pd.DataFrame:
        """
        Ejecuta el backtest procesando todas las señales.

        Args:
            signals: Lista de TradingSignal en orden cronológico

        Returns:
            DataFrame con los resultados de todos los trades completados
        """
        for signal in signals:
            if self._is_entry(signal):
                self._open_position(signal)
            elif self._is_exit(signal):
                self._close_position(signal)

        # Si quedó una posición abierta al final, no la incluimos
        # en los resultados porque no sabemos el P&L hasta que se cierre

        return self._create_results_dataframe()

    def _open_position(self, signal: TradingSignal):
        """
        Procesa una señal de entrada (apertura o DCA).

        Crypto: calcula size en USDT, compra/vende crypto.
        Futuros: calcula contratos por riesgo o usa override, solo paga fee.
        """
        real_price = self._apply_slippage(signal)
        slippage_per_unit = abs(real_price - signal.price)

        if self.is_futures:
            # --- FUTUROS ---
            if signal.contracts is not None:
                num_contracts = signal.contracts
            else:
                if signal.stop_loss_price is None:
                    return  # No se puede calcular sizing sin stop
                risk_usd = self.capital * signal.position_size_pct
                stop_distance = abs(real_price - signal.stop_loss_price)
                if stop_distance <= 0:
                    return
                num_contracts = int(risk_usd / (stop_distance * self.point_value))

            if num_contracts < 1:
                return  # Capital insuficiente para 1 contrato

            entry_fee = num_contracts * self.fee_fixed
            entry_slippage_cost = slippage_per_unit * num_contracts * self.point_value

            # Calcular risk_usd real (para pnl_pct)
            if signal.stop_loss_price is not None:
                stop_distance = abs(real_price - signal.stop_loss_price)
                risk_usd = num_contracts * stop_distance * self.point_value
            elif signal.contracts is not None:
                # Override sin stop: risk_usd = capital * pct como estimacion
                risk_usd = self.capital * signal.position_size_pct
            else:
                risk_usd = 0.0

            if self.current_position is None:
                self.current_position = Position(
                    symbol=signal.symbol,
                    entry_time=signal.timestamp
                )
                self.current_position.position_side = signal.position_side
                self.current_position._risk_usd = 0.0
            else:
                # DCA: verify same direction
                if self.current_position.position_side != signal.position_side:
                    return

            self.current_position._risk_usd += risk_usd
            self.current_position.add_entry(
                timestamp=signal.timestamp,
                price=real_price,
                size_usdt=0.0,
                contracts=num_contracts,
                fee=entry_fee,
                slippage_cost=entry_slippage_cost
            )
            self.capital -= entry_fee  # Solo fee, no notional

        else:
            # --- CRYPTO ---
            entry_size_usdt = self.capital * signal.position_size_pct
            if entry_size_usdt <= 0:
                return

            entry_fee = entry_size_usdt * self.fee_rate
            entry_slippage_cost = slippage_per_unit * (entry_size_usdt / real_price)

            if self.current_position is None:
                self.current_position = Position(
                    symbol=signal.symbol,
                    entry_time=signal.timestamp
                )
                self.current_position.position_side = signal.position_side
                self.current_position._risk_usd = 0.0
            else:
                # DCA: verify same direction
                if self.current_position.position_side != signal.position_side:
                    return

            self.current_position.add_entry(
                timestamp=signal.timestamp,
                price=real_price,
                size_usdt=entry_size_usdt,
                contracts=0,
                fee=entry_fee,
                slippage_cost=entry_slippage_cost
            )
            self.capital -= (entry_size_usdt + entry_fee)

    def _close_position(self, signal: TradingSignal):
        """
        Procesa una señal de cierre (total o parcial).

        Crypto: vende crypto, recibe USDT.
        Futuros: cierra contratos, cobra/paga P&L.
        """
        if self.current_position is None:
            return
        if self.current_position.position_side != signal.position_side:
            return

        pos = self.current_position
        pct = signal.position_size_pct
        real_price = self._apply_slippage(signal)
        slippage_per_unit = abs(signal.price - real_price)

        if self.is_futures:
            # --- FUTUROS ---
            # Calcular avg_entry ANTES del partial_close (que modifica entries)
            avg_entry = pos.average_entry_price_futures()

            if pct < 1.0:
                closed = pos.partial_close_futures(pct)
                closed_contracts = closed['total_contracts']
                closed_entry_fees = closed['total_entry_fees']
                closed_entry_slippage = closed['total_entry_slippage']
            else:
                closed_contracts = pos.total_contracts()
                closed_entry_fees = pos.total_fees_on_entries()
                closed_entry_slippage = pos.total_slippage_on_entries()

            if closed_contracts == 0:
                return

            if pos.position_side == SignalPositionSide.LONG:
                gross_pnl = closed_contracts * self.point_value * (real_price - avg_entry)
            else:
                gross_pnl = closed_contracts * self.point_value * (avg_entry - real_price)

            exit_fee = closed_contracts * self.fee_fixed
            exit_slippage_total = slippage_per_unit * closed_contracts * self.point_value
            net_pnl = gross_pnl - exit_fee

            self.capital += net_pnl

            risk_usd = getattr(pos, '_risk_usd', 0.0)
            pnl_pct = (net_pnl / risk_usd * 100) if risk_usd > 0 else 0

            self.completed_trades.append({
                'symbol': pos.symbol,
                'position_side': pos.position_side.value,
                'entry_time': pos.entry_time,
                'exit_time': signal.timestamp,
                'num_entries': len(pos.entries),
                'avg_entry_price': avg_entry,
                'exit_price': real_price,
                'total_cost': 0.0,
                'exit_value': 0.0,
                'contracts': closed_contracts,
                'risk_usd': risk_usd,
                'point_value': self.point_value,
                'total_entry_fees': closed_entry_fees,
                'exit_fee': exit_fee,
                'total_fees': closed_entry_fees + exit_fee,
                'entry_slippage': closed_entry_slippage,
                'exit_slippage': exit_slippage_total,
                'total_slippage': closed_entry_slippage + exit_slippage_total,
                'gross_pnl': gross_pnl,
                'net_pnl': net_pnl,
                'capital_after': self.capital,
                'pnl_pct': pnl_pct
            })

        else:
            # --- CRYPTO ---
            if pct < 1.0:
                closed = pos.partial_close(pct)
                closed_crypto = closed['total_crypto']
                closed_cost = closed['total_cost']
                closed_entry_fees = closed['total_entry_fees']
                closed_entry_slippage = closed['total_entry_slippage']
            else:
                closed_crypto = pos.total_crypto()
                closed_cost = pos.total_cost()
                closed_entry_fees = pos.total_fees_on_entries()
                closed_entry_slippage = pos.total_slippage_on_entries()

            exit_value = closed_crypto * real_price
            exit_fee = exit_value * self.fee_rate
            exit_slippage_cost = slippage_per_unit * closed_crypto

            if pos.position_side == SignalPositionSide.LONG:
                gross_pnl = exit_value - closed_cost
            else:
                gross_pnl = closed_cost - exit_value

            net_pnl = gross_pnl - exit_fee

            if pos.position_side == SignalPositionSide.LONG:
                self.capital += (exit_value - exit_fee)
            else:
                self.capital += (closed_cost + gross_pnl - exit_fee)

            avg_entry = closed_cost / closed_crypto if closed_crypto > 0 else 0.0

            self.completed_trades.append({
                'symbol': pos.symbol,
                'position_side': pos.position_side.value,
                'entry_time': pos.entry_time,
                'exit_time': signal.timestamp,
                'num_entries': len(pos.entries),
                'avg_entry_price': avg_entry,
                'exit_price': real_price,
                'total_cost': closed_cost,
                'exit_value': exit_value,
                'contracts': 0,
                'risk_usd': 0.0,
                'point_value': 0.0,
                'total_entry_fees': closed_entry_fees,
                'exit_fee': exit_fee,
                'total_fees': closed_entry_fees + exit_fee,
                'entry_slippage': closed_entry_slippage,
                'exit_slippage': exit_slippage_cost,
                'total_slippage': closed_entry_slippage + exit_slippage_cost,
                'gross_pnl': gross_pnl,
                'net_pnl': net_pnl,
                'capital_after': self.capital,
                'pnl_pct': (net_pnl / closed_cost * 100) if closed_cost > 0 else 0
            })

        if pct >= 1.0:
            self.current_position = None

    def _apply_slippage(self, signal: TradingSignal) -> float:
        """Apply slippage — always against the trader.

        Entry LONG or Exit SHORT → price goes UP (trader pays more)
        Entry SHORT or Exit LONG → price goes DOWN (trader receives less)
        """
        is_entry = self._is_entry(signal)
        price_goes_up = (
            (is_entry and signal.position_side == SignalPositionSide.LONG) or
            (not is_entry and signal.position_side == SignalPositionSide.SHORT)
        )

        price = signal.price
        if self.slippage_fixed > 0:
            real_price = price + self.slippage_fixed if price_goes_up else price - self.slippage_fixed
        elif price_goes_up:
            real_price = price * (1 + self.slippage_pct)
        else:
            real_price = price * (1 - self.slippage_pct)

        return round(real_price / self.tick_size) * self.tick_size

    def _create_results_dataframe(self) -> pd.DataFrame:
        """
        Convierte la lista de trades completados en un DataFrame.

        Este DataFrame es lo que usarás para análisis y visualización.
        """
        if not self.completed_trades:
            # Si no hubo trades, devolver DataFrame vacío con las columnas
            return pd.DataFrame(columns=[
                'symbol', 'position_side', 'entry_time', 'exit_time', 'num_entries',
                'avg_entry_price', 'exit_price', 'total_cost', 'exit_value',
                'contracts', 'risk_usd', 'point_value',
                'total_entry_fees', 'exit_fee', 'total_fees',
                'entry_slippage', 'exit_slippage', 'total_slippage',
                'gross_pnl', 'net_pnl', 'capital_after', 'pnl_pct'
            ])

        return pd.DataFrame(self.completed_trades)
