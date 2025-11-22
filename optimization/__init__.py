"""
Módulo de Optimización de Parámetros

Proporciona utilidades para encontrar automáticamente
la mejor combinación de parámetros para estrategias de trading.
"""

from .results import OptimizationResult
from .optimizer import ParameterOptimizer
from .visualizer import OptimizationPlotter

__all__ = ['OptimizationResult', 'ParameterOptimizer', 'OptimizationPlotter']
