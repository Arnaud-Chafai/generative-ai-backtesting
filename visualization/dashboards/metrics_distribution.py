"""
Módulo simplificado para visualizar distribuciones de métricas principales de trading.
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from visualization.theme import apply_dashboard_style

def visualize_metrics_distribution(strategy, df_trade_metrics, save_path=None):
    """
    Función principal para generar el dashboard de distribución de métricas.
    """
    # Configurar estilo
    colors = apply_dashboard_style()
    
    # Extraer información de la estrategia
    strategy_info = {
        "strategy_name": getattr(strategy, "strategy_name", "Trading Strategy"),
        "symbol": getattr(strategy, "symbol", ""),
        "timeframe": str(getattr(strategy, "timeframe", "")).replace("Timeframe.", ""),
    }
    
    # Definir las métricas a visualizar basadas en las columnas disponibles
    metrics = [
        'MAE',                        # Máximo Adverse Excursion
        'MFE',                        # Máximo Favorable Excursion
        'profit_efficiency',          # Eficiencia de beneficio
        'risk_reward_ratio',          # Ratio de riesgo-beneficio
        'trade_volatility',           # Volatilidad del trade
        'duration_bars'               # Duración en barras
    ]
    
    # Nombres amigables para las métricas
    metric_names = {
        'MAE': 'MAE',
        'MFE': 'MFE',
        'profit_efficiency': 'Eficiencia',
        'risk_reward_ratio': 'Risk-Reward',
        'trade_volatility': 'Volatilidad',
        'duration_bars': 'Duración (barras)',
        'trade_duration_second': 'Duración (segundos)'
    }
    
    # Definir qué métricas mostrar para operaciones perdedoras
    show_losers = {
        'MAE': True,
        'MFE': True,
        'profit_efficiency': False,  # No mostrar perdedores para eficiencia
        'risk_reward_ratio': True,
        'trade_volatility': True,
        'duration_bars': True,
        'trade_duration_second': True
    }
    
    # Filtrar solo las métricas disponibles
    available_metrics = [m for m in metrics if m in df_trade_metrics.columns]
    
    # Si no hay duration_bars, pero hay trade_duration_second, usar esa
    if 'duration_bars' not in available_metrics and 'trade_duration_second' in df_trade_metrics.columns:
        available_metrics.append('trade_duration_second')
    
    if not available_metrics:
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.text(0.5, 0.5, "No hay métricas disponibles para visualizar", 
               ha='center', va='center', fontsize=14)
        ax.axis('off')
        return fig
    
    # Determinar número de filas y columnas
    n_metrics = len(available_metrics)
    n_cols = 2
    n_rows = (n_metrics + 1) // 2  # Redondeo hacia arriba
    
    # Crear figura
    fig, axes = plt.subplots(n_rows, n_cols, figsize=(12, 4*n_rows))
    if n_rows == 1 and n_cols == 1:
        axes = np.array([axes])
    axes = axes.flatten()
    
    # Separar operaciones ganadoras y perdedoras
    winners = df_trade_metrics[df_trade_metrics['net_profit_loss'] > 0]
    losers = df_trade_metrics[df_trade_metrics['net_profit_loss'] <= 0]
    
    # Crear gráficos para cada métrica disponible
    for i, metric in enumerate(available_metrics):
        if i < len(axes):
            ax = axes[i]
            
            # Crear histogramas con borde negro
            if len(winners) > 0:
                sns.histplot(
                    winners[metric], 
                    ax=ax, 
                    color=colors['profit'], 
                    alpha=0.7, 
                    label='Ganadores', 
                    kde=True, 
                    edgecolor='black',  # Borde negro
                    linewidth=1         # Grosor del borde
                )
            
            # Solo mostrar perdedores si está configurado para esta métrica
            if show_losers.get(metric, True) and len(losers) > 0:
                sns.histplot(
                    losers[metric], 
                    ax=ax, 
                    color=colors['loss'], 
                    alpha=0.7, 
                    label='Perdedores', 
                    kde=True, 
                    edgecolor='black',  # Borde negro
                    linewidth=1
                )
            
            # Añadir líneas verticales para las medias
            if len(winners) > 0:
                avg_winners = winners[metric].mean()
                ax.axvline(avg_winners, color=colors['profit'], linestyle='--', alpha=0.7)
                ax.text(
                    avg_winners,
                    ax.get_ylim()[1]*0.9,
                    f'Prom. Gan: {avg_winners:.2f}',
                    fontsize=9,
                    color='black',  # Texto en negro
                    ha='left',
                    va='top'
                )
            
            # Solo mostrar línea para perdedores si mostramos su histograma
            if show_losers.get(metric, True) and len(losers) > 0:
                avg_losers = losers[metric].mean()
                ax.axvline(avg_losers, color=colors['loss'], linestyle='--', alpha=0.7)
                ax.text(
                    avg_losers,
                    ax.get_ylim()[1]*0.8,
                    f'Prom. Perd: {avg_losers:.2f}',
                    fontsize=9,
                    color='black',  # Texto en negro
                    ha='left',
                    va='top'
                )
            
            # Título y etiquetas del gráfico
            metric_title = metric_names.get(metric, metric)
            ax.set_title(f'Distribución de {metric_title}', fontsize=12)
            ax.set_xlabel(metric_title, fontsize=10)
            ax.set_ylabel('Frecuencia', fontsize=10)
            ax.legend(fontsize=9)
    
    # Ocultar ejes no utilizados
    for i in range(n_metrics, len(axes)):
        axes[i].set_visible(False)
    
    # Título general
    plt.suptitle(
        f"Distribución de Métricas | {strategy_info['strategy_name']} ({strategy_info['symbol']} {strategy_info['timeframe']})",
        fontsize=14, y=0.98
    )
    
    # Ajustar espacios
    plt.tight_layout(rect=[0, 0, 1, 0.96])
    
    # Guardar si se proporciona una ruta
    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f"Dashboard guardado como {save_path}")
    
    return fig
