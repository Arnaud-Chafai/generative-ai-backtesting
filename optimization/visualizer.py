"""
Visualizador para resultados de optimización de parámetros.

Genera gráficos de superficies 3D, heatmaps y scatter plots
para analizar la topología del espacio de parámetros.
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib import cm
from mpl_toolkits.mplot3d import Axes3D
from typing import Optional


class OptimizationPlotter:
    """
    Genera visualizaciones avanzadas de resultados de optimización.

    Uso:
        plotter = OptimizationPlotter(results_df)
        plotter.plot_3d_surface('lookback_period', 'position_size_pct', 'sharpe_ratio')
    """

    def __init__(self, results_df: pd.DataFrame):
        """
        Inicializa el visualizador con los resultados de optimización.

        Args:
            results_df: DataFrame retornado por ParameterOptimizer.get_summary()
        """
        self.df = results_df.copy()

        # Identificar columnas de parámetros vs métricas
        metric_cols = ['sharpe_ratio', 'roi', 'max_drawdown', 'profit_factor',
                      'total_trades', 'execution_time']
        self.param_cols = [col for col in self.df.columns if col not in metric_cols]
        self.metric_cols = [col for col in metric_cols if col in self.df.columns]

    def plot_3d_surface(
        self,
        x_param: str,
        y_param: str,
        metric: str = 'sharpe_ratio',
        fill_value: float = 0.0,
        figsize: tuple = (14, 10)
    ):
        """
        Genera un gráfico de superficie 3D estilo MATLAB.
        Ideal para visualizar la robustez de la estrategia.

        Args:
            x_param: Parámetro para el eje X
            y_param: Parámetro para el eje Y
            metric: Métrica para el eje Z
            fill_value: Valor para rellenar huecos en la matriz (default: 0.0)
            figsize: Tamaño de la figura

        Ejemplo:
            plotter.plot_3d_surface('lookback_period', 'position_size_pct', 'sharpe_ratio')
        """
        # Validaciones
        if x_param not in self.df.columns or y_param not in self.df.columns:
            raise ValueError(f"Parámetros {x_param} o {y_param} no encontrados en resultados")
        if metric not in self.df.columns:
            raise ValueError(f"Métrica {metric} no encontrada en resultados")

        # 1. Preparar datos en formato Rejilla (Grid)
        pivot_df = self.df.pivot_table(
            values=metric,
            index=y_param,
            columns=x_param,
            aggfunc=np.max  # Si hay duplicados, tomar el máximo
        ).fillna(fill_value)

        # 2. Crear las coordenadas X, Y (Meshgrid)
        X = pivot_df.columns.values
        Y = pivot_df.index.values
        X, Y = np.meshgrid(X, Y)
        Z = pivot_df.values

        # 3. Configurar el Plot 3D
        fig = plt.figure(figsize=figsize)
        ax = fig.add_subplot(111, projection='3d')

        # --- LA SUPERFICIE (La Malla) ---
        surf = ax.plot_surface(
            X, Y, Z,
            cmap=cm.coolwarm,       # Mapa de color (Rojo a Azul)
            linewidth=0.2,          # Grosor de la rejilla negra
            edgecolors='black',     # Color de la rejilla (efecto malla)
            alpha=0.9,              # Un poco de transparencia
            antialiased=True
        )

        # --- EL "SUELO" (Proyección de contornos abajo) ---
        # Dibuja el mapa de calor plano en el suelo para ver mejor las zonas
        z_range = Z.max() - Z.min()
        offset = Z.min() - z_range * 0.1  # Un poco más abajo del mínimo
        ax.contourf(X, Y, Z, zdir='z', offset=offset, cmap=cm.coolwarm, alpha=0.5)

        # 4. Etiquetas y Estética
        ax.set_xlabel(f'\n{x_param}', fontsize=11, linespacing=3)
        ax.set_ylabel(f'\n{y_param}', fontsize=11, linespacing=3)
        ax.set_zlabel(f'\n{metric}', fontsize=11, linespacing=3)
        ax.set_title(f'Topología de Estrategia: {metric.upper()}', fontsize=16, fontweight='bold')

        # Ajustar límites Z para que se vea el suelo
        ax.set_zlim(offset, Z.max())

        # Barra de color lateral
        fig.colorbar(surf, ax=ax, shrink=0.5, aspect=10, label=metric)

        # Vista inicial (Ángulo) - Puedes ajustarlo
        ax.view_init(elev=30, azim=-60)

        plt.tight_layout()
        plt.show()
