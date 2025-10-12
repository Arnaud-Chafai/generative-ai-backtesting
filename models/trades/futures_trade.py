# futures_trade.py

from models.trades.base_trade import Trade, TradeAction
from models.signals import StrategySignal

from datetime import datetime
from pydantic import Field
from typing import Optional
import uuid

class FuturesTrade(Trade):
    """
    Clase específica para operar en Futuros.
    Hereda de Trade y añade propiedades específicas como:
        - contract_size: Valor nominal de cada contrato.
        - margin_requirement: Porcentaje del margen requerido para abrir una posición.
        - fees: Puede incluir una lógica de comisiones particular para futuros.
    """
    # Propiedades específicas para futuros:
    contract_size: float = Field(..., gt=0, description="Valor nominal de un contrato de futuros")
    margin_requirement: float = Field(..., gt=0, description="Margen requerido en porcentaje")
    fee_per_contract: Optional[float] = Field(default=0.0, description="Comisión fija por contrato, si aplica")

    # Puedes agregar otros campos según las necesidades específicas del mercado de futuros

    def add_entry(self, timestamp: datetime, signal_type: str, volume: float, price: float) -> None:
        """
        Puedes sobreescribir add_entry si necesitas ajustar el precio o volumen
        de entrada en función de las características de los futuros.
        Por ejemplo, redondear el precio al tick size o aplicar un factor relacionado
        con el tamaño del contrato.
        """
        # Aquí podrías aplicar ajustes específicos para futuros:
        # Ejemplo: Ajustar el precio redondeándolo a un tick size (si lo tuvieras definido)
        # price_adjusted = self._adjust_price(price)
        # Por ahora, llamamos al método de la clase base.
        super().add_entry(timestamp, signal_type, volume, price)

    def add_exit(self, timestamp: datetime, signal_type: str, volume: float, price: float) -> None:
        """
        Similar a add_entry, este método puede ser extendido para aplicar
        reglas específicas en el cierre de posiciones de futuros.
        """
        # Aplica ajustes específicos si fueran necesarios
        super().add_exit(timestamp, signal_type, volume, price)

    # Opcional: Método para calcular el valor de la operación en función del tamaño del contrato
    def calculate_notional(self) -> float:
        """
        Calcula el valor nocional del trade.
        Por ejemplo, si se operan contratos de futuros, el notional podría ser:
            notional = total_volume * avg_entry_price * contract_size
        """
        if self.avg_entry_price is None:
            return 0.0
        return self.total_volume * self.avg_entry_price * self.contract_size

    # Opcional: Otros métodos específicos, por ejemplo, para calcular comisiones totales
    def calculate_total_fees(self) -> float:
        """
        Calcula la comisión total basada en el número de contratos operados.
        """
        # Supongamos que cada entrada y salida tiene una comisión fija por contrato
        total_contracts = self.total_volume  # O bien, se podría calcular en función del volumen
        return total_contracts * (self.fee_per_contract or 0.0)
    
    def validate_signal(self, signal: StrategySignal) -> None:
        """
        Valida que la señal cumpla las reglas del mercado de Futuros.
        (p. ej. volumen sea entero, precio >= tick_size, etc.)
        """
        # 1) Validar volumen (como # de contratos)
        #    Si tu "volumen" representa contratos, podrías exigir int
        if signal.volume <= 0:
            raise ValueError(f"❌ El número de contratos debe ser positivo, se recibió: {signal.volume}")
        # También podrías exigir que sea entero: 
        if not float(signal.volume).is_integer():
            raise ValueError(f"❌ El volumen {signal.volume} debe ser un número entero (contratos).")

        # 2) Validar precio
        if signal.price is not None and signal.price <= 0:
            raise ValueError(f"❌ El precio debe ser mayor que cero, se recibió: {signal.price}")

        # 3) Chequear si el precio coincide con el tick_size del futuro
        #    (Si tu FuturosTrade tuviera un `tick_size` similar a CryptoTrade).
        #    Como no está en esta clase, podrías derivarlo de la config del activo, etc.

        # 4) Otras validaciones:
        #    - margen mínimo, etc.
        
        print(f"✔ Señal válida para FuturesTrade: {signal}")