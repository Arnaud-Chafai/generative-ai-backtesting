"""
Señales simplificadas para el motor de backtest.

La filosofía aquí es: una señal es solo una DECISIÓN de trading,
no incluye cálculos de costos. Los costos se calculan en el motor
cuando la señal se ejecuta.
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from models.enums import SignalType  # Importar desde enums.py

@dataclass
class TradingSignal:
    """
    Una señal de trading simple.
    
    Representa únicamente la DECISIÓN de comprar o vender en un momento dado.
    No calcula costos, no tiene validaciones complejas, no lleva metadatos
    innecesarios. Es información pura.
    
    Campos:
        timestamp: Momento exacto en que se genera la señal (del índice del DataFrame)
        signal_type: BUY o SELL
        symbol: El activo que queremos operar (ej: "BTC", "ETH", "ES")
        price: Precio de referencia del mercado en ese momento (ej: df['Close'])
        position_size_pct: Qué porcentaje del capital disponible usar (0.1 = 10%)
    
    Ejemplo de uso:
        signal = TradingSignal(
            timestamp=df.index[100],
            signal_type=SignalType.BUY,
            symbol="BTC",
            price=df['Close'].iloc[100],
            position_size_pct=0.10  # Usar 10% del capital
        )
    """
    timestamp: datetime
    signal_type: SignalType
    symbol: str
    price: float
    position_size_pct: float  # Fracción del capital: 0.1 = 10%, 0.5 = 50%, etc.
    
    def __post_init__(self):
        """
        Validaciones básicas después de crear la señal.
        
        Solo validamos lo esencial: que los números tengan sentido.
        No hacemos validaciones complejas como Pydantic porque no las necesitamos.
        """
        if self.price <= 0:
            raise ValueError(f"El precio debe ser positivo, recibido: {self.price}")
        
        if not (0 < self.position_size_pct <= 1):
            raise ValueError(
                f"position_size_pct debe estar entre 0 y 1 (0% a 100%), "
                f"recibido: {self.position_size_pct}"
            )
    
    def __repr__(self):
        """Representación legible de la señal para debugging."""
        return (
            f"TradingSignal({self.signal_type.value} {self.symbol} "
            f"@ {self.price:.2f} on {self.timestamp}, "
            f"size={self.position_size_pct*100:.1f}%)"
        )