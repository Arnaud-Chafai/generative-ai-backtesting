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
from models.enums import SignalType
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
    size_usdt: float  # Cuántos USDT usamos en esta entrada
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
    
    def add_entry(self, timestamp: datetime, price: float, 
                  size_usdt: float, fee: float, slippage_cost: float):
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
        
        # Estado del motor
        self.current_position: Position | None = None
        self.completed_trades: list[dict] = []
    
    def run(self, signals: list[TradingSignal]) -> pd.DataFrame:
        """
        Ejecuta el backtest procesando todas las señales.
        
        Args:
            signals: Lista de TradingSignal en orden cronológico
            
        Returns:
            DataFrame con los resultados de todos los trades completados
        """
        for signal in signals:
            if signal.signal_type == SignalType.BUY:
                self._handle_buy(signal)
            elif signal.signal_type == SignalType.SELL:
                self._handle_sell(signal)
        
        # Si quedó una posición abierta al final, no la incluimos
        # en los resultados porque no sabemos el P&L hasta que se cierre
        
        return self._create_results_dataframe()
    
    def _handle_buy(self, signal: TradingSignal):
        """
        Procesa una señal de compra.
        
        Si no hay posición abierta, crea una nueva.
        Si ya hay posición abierta, añade otra entrada (promediado).
        """
        # Paso 1: Calcular tamaño de esta entrada en USDT
        entry_size_usdt = self.capital * signal.position_size_pct
        
        if entry_size_usdt <= 0:
            return  # No hay capital disponible, no podemos comprar
        
        # Paso 2: Aplicar slippage (compramos más caro de lo esperado)
        real_price = self._apply_slippage_to_price(signal.price, is_buy=True)
        
        # Paso 3: Calcular fees de esta entrada
        entry_fee = self.fee_fixed if self.fee_fixed > 0 else entry_size_usdt * self.fee_rate
        
        # Paso 3.5: Calcular costo de slippage de entrada
        # Slippage cost = diferencia entre precio ideal y precio real * cantidad de crypto
        entry_slippage_cost = abs(real_price - signal.price) * (entry_size_usdt / real_price)
        
        # Paso 4: Si no hay posición abierta, crear nueva
        if self.current_position is None:
            self.current_position = Position(
                symbol=signal.symbol,
                entry_time=signal.timestamp
            )
        
        # Paso 5: Añadir esta entrada a la posición
        self.current_position.add_entry(
            timestamp=signal.timestamp,
            price=real_price,
            size_usdt=entry_size_usdt,
            fee=entry_fee,
            slippage_cost=entry_slippage_cost
        )
        
        # Paso 6: Restar tanto el capital de la entrada como la fee
        self.capital -= (entry_size_usdt + entry_fee)
    
    def _handle_sell(self, signal: TradingSignal):
        """
        Procesa una señal de venta.
        
        Cierra completamente la posición actual si existe.
        """
        if self.current_position is None:
            return  # No hay posición que cerrar
        
        # Paso 1: Aplicar slippage (vendemos más barato de lo esperado)
        real_price = self._apply_slippage_to_price(signal.price, is_buy=False)
        
        # Paso 2: Calcular cuánto crypto tenemos en total
        total_crypto = self.current_position.total_crypto()
        
        # Paso 3: Calcular el valor de venta en USDT
        exit_value_usdt = total_crypto * real_price
        
        # Paso 4: Calcular fee de salida
        exit_fee = self.fee_fixed if self.fee_fixed > 0 else exit_value_usdt * self.fee_rate
        
        # Paso 4.5: Calcular costo de slippage de salida
        exit_slippage_cost = abs(signal.price - real_price) * total_crypto
        
        # Paso 5: Calcular P&L
        total_cost = self.current_position.total_cost()
        total_entry_fees = self.current_position.total_fees_on_entries()
        total_entry_slippage = self.current_position.total_slippage_on_entries()
        
        gross_pnl = exit_value_usdt - total_cost
        net_pnl = gross_pnl - exit_fee
        
        # Paso 6: Actualizar capital
        # Recuperamos el valor neto de venta (ya descontada la exit_fee)
        self.capital += (exit_value_usdt - exit_fee)
        
        # Paso 7: Guardar trade completado
        self.completed_trades.append({
            'symbol': self.current_position.symbol,
            'entry_time': self.current_position.entry_time,
            'exit_time': signal.timestamp,
            'num_entries': len(self.current_position.entries),
            'avg_entry_price': self.current_position.average_entry_price(),
            'exit_price': real_price,
            'total_cost': total_cost,
            'exit_value': exit_value_usdt,
            'total_entry_fees': total_entry_fees,
            'exit_fee': exit_fee,
            'total_fees': total_entry_fees + exit_fee,
            'entry_slippage': total_entry_slippage,
            'exit_slippage': exit_slippage_cost,
            'total_slippage': total_entry_slippage + exit_slippage_cost,
            'gross_pnl': gross_pnl,
            'net_pnl': net_pnl,
            'capital_after': self.capital,
            'pnl_pct': (net_pnl / total_cost * 100) if total_cost > 0 else 0
        })
        
        # Paso 8: Cerrar posición
        self.current_position = None
    
    def _apply_slippage_to_price(self, price: float, is_buy: bool) -> float:
        """
        Aplica slippage al precio según la dirección del trade.
        
        Slippage simula el hecho de que en la vida real nunca ejecutas
        exactamente al precio que ves en el gráfico. Siempre hay un pequeño
        deslizamiento desfavorable.
        
        Args:
            price: Precio del gráfico (ej: Close del candle)
            is_buy: True si estamos comprando, False si vendiendo
            
        Returns:
            Precio real después de slippage, redondeado al tick_size
        """
        if self.slippage_fixed > 0:
            # Futuros: slippage fijo en ticks
            real_price = price + self.slippage_fixed if is_buy else price - self.slippage_fixed
        elif is_buy:
            # Crypto: slippage porcentual, compramos más caro
            real_price = price * (1 + self.slippage_pct)
        else:
            # Crypto: slippage porcentual, vendemos más barato
            real_price = price * (1 - self.slippage_pct)
        
        # Redondear al tick_size del mercado
        # Por ejemplo, si tick_size = 0.01, el precio debe ser múltiplo de 0.01
        return round(real_price / self.tick_size) * self.tick_size
    
    def _create_results_dataframe(self) -> pd.DataFrame:
        """
        Convierte la lista de trades completados en un DataFrame.
        
        Este DataFrame es lo que usarás para análisis y visualización.
        """
        if not self.completed_trades:
            # Si no hubo trades, devolver DataFrame vacío con las columnas
            return pd.DataFrame(columns=[
                'symbol', 'entry_time', 'exit_time', 'num_entries',
                'avg_entry_price', 'exit_price', 'total_cost', 'exit_value',
                'total_entry_fees', 'exit_fee', 'total_fees',
                'entry_slippage', 'exit_slippage', 'total_slippage',
                'gross_pnl', 'net_pnl', 'capital_after', 'pnl_pct'
            ])
        
        return pd.DataFrame(self.completed_trades)