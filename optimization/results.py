"""
Estructura de datos para resultados de optimización.
"""

from dataclasses import dataclass
from typing import Dict, Any


@dataclass
class OptimizationResult:
    """
    Resultado de una iteración de optimización.

    Attributes:
        params: Diccionario con los parámetros usados en esta iteración
        metrics: Diccionario con todas las métricas calculadas (sharpe, roi, etc.)
        execution_time: Tiempo en segundos que tardó el backtest de esta iteración
    """
    params: Dict[str, Any]
    metrics: Dict[str, float]
    execution_time: float

    def __repr__(self) -> str:
        """Representación legible del resultado"""
        metrics_str = ", ".join([f"{k}={v:.2f}" for k, v in self.metrics.items()])
        return f"OptimizationResult({self.params} → {metrics_str} [{self.execution_time:.2f}s])"
