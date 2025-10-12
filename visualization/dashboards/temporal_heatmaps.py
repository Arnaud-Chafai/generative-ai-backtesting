"""
Módulo para generar heatmaps temporales de métricas de trading usando Seaborn.
Incluye dos heatmaps:
    1) Métrica vs. Hora y Día de la Semana
    2) Métrica vs. Día del Mes y Mes
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import matplotlib.gridspec as gridspec
from matplotlib.colors import LinearSegmentedColormap
from utils.timeframe import DAYS_ORDER, MONTHS_ORDER

# Configuración global de estilo
def set_style():
    """Configura el estilo global para todas las visualizaciones"""
    sns.set_theme(style="whitegrid")
    plt.rcParams['font.family'] = 'sans-serif'
    plt.rcParams['font.sans-serif'] = ['Arial', 'DejaVu Sans', 'Liberation Sans']
    plt.rcParams['axes.facecolor'] = '#f5f5f5'
    plt.rcParams['figure.facecolor'] = 'white'
    plt.rcParams['grid.color'] = '#dddddd'
    plt.rcParams['grid.linestyle'] = '-'
    plt.rcParams['grid.linewidth'] = 0.5
    
    # Paleta de colores personalizada
    return {
        'profit': '#006D77',       # Color para ganancias
        'loss': '#E29578',         # Color para pérdidas
        'neutral': '#EAEAEA',      # Color neutral
        'accent': '#FFDDD2',       # Color de acento
        'highlight': '#83C5BE',    # Color para resaltar
        'text': '#333333',         # Color de texto
        'grid': '#dddddd',         # Color de la cuadrícula
        'background': '#f5f5f5'    # Color de fondo
    }

# Crear paletas personalizadas
profit_loss_cmap = LinearSegmentedColormap.from_list(
    "profit_loss",
    ["#E29578", "#FFFFFF", "#006D77"]  # loss -> neutral -> profit
)

def create_temporal_heatmap(strategy, df_trade_metrics, metric_column='net_profit_loss', 
                        figsize=(18, 12), save_path=None):  # Reducimos altura total
    """
    Crea un dashboard con dos heatmaps temporales:
    1. Métrica por hora y día de la semana
    2. Métrica por día del mes y mes
    
    Args:
        strategy: Objeto de estrategia
        df_trade_metrics: DataFrame con métricas de trades
        metric_column: Columna a analizar
        figsize: Tamaño de la figura
        save_path: Ruta para guardar la imagen (opcional)
        
    Returns:
        matplotlib.figure.Figure: La figura generada
    """
    # Configurar estilo
    colors = set_style()
    
    # Extraer información de la estrategia
    strategy_info = {
        "strategy_name": getattr(strategy, "strategy_name", "Trading Strategy"),
        "symbol": getattr(strategy, "symbol", ""),
        "timeframe": str(getattr(strategy, "timeframe", "")).replace("Timeframe.", ""),
        "exchange": str(getattr(strategy, "exchange", "")).replace("ExchangeName.", ""),
    }
    
    # Verificar que las columnas necesarias existen
    required_cols = ["day_of_week", "month", "hour", "day"]
    for col in required_cols:
        if col not in df_trade_metrics.columns:
            raise ValueError(f"La columna '{col}' no existe en el DataFrame. Asegúrate de que TradeMetricsCalculator ha procesado los datos temporales.")
    
    # Verificar que la columna de métrica existe
    if metric_column not in df_trade_metrics.columns:
        raise ValueError(f"La columna '{metric_column}' no existe en el DataFrame")
    
    # Usar directamente el DataFrame sin preprocesamiento temporal
    df = df_trade_metrics
    
    # Crear figura - NO usamos constrained_layout aquí para mayor control
    fig = plt.figure(figsize=figsize, constrained_layout=False)
    
    # Usamos GridSpec con espacio negativo para que se solapen ligeramente
    gs = gridspec.GridSpec(2, 1, figure=fig, height_ratios=[1, 1])
    
    # 1. HEATMAP: Métrica por Hora y Día de la Semana
    ax1 = fig.add_subplot(gs[0])
    
    pivot_hour_day = pd.pivot_table(
        df,
        values=metric_column,
        index='day_of_week',
        columns='hour',
        aggfunc='mean'
    ).reindex(DAYS_ORDER)
    
    # Crear tabla de conteo para identificar celdas sin datos
    count_pivot = pd.pivot_table(
        df,
        values=metric_column,
        index='day_of_week',
        columns='hour',
        aggfunc='count'
    ).reindex(DAYS_ORDER)
    
    # Crear máscara para celdas sin datos
    mask = count_pivot == 0
    
    # Crear heatmap
    hm1 = sns.heatmap(
        pivot_hour_day,
        ax=ax1,
        cmap=profit_loss_cmap,
        center=0,
        annot=True,
        fmt=".2f",
        linewidths=0.3,
        linecolor= "black",
        cbar_kws={"shrink": 0.75, "label": metric_column},
        mask=mask,
        square=True  # Esto asegura que cada celda sea cuadrada
    )
    
    # Configurar etiquetas y título con menor padding
    ax1.set_title(f"{metric_column} por Hora y Día de la Semana", 
                fontsize=14, fontweight='bold', color=colors['text'], pad=5)
    ax1.set_xlabel("Hora del día", fontsize=12, color=colors['text'], labelpad=5)
    ax1.set_ylabel("Día de la semana", fontsize=12, color=colors['text'], labelpad=5)
    
    # Configurar ejes
    ax1.set_xticks(np.arange(0, 24, 2) + 0.5)
    ax1.set_xticklabels([f"{h}:00" for h in range(0, 24, 2)], rotation=45)
    
    # 2. HEATMAP: Métrica por Día del Mes y Mes
    ax2 = fig.add_subplot(gs[1])
    
    # Crear tabla pivote para el segundo heatmap
    pivot_month_day = pd.pivot_table(
        df,
        values=metric_column,
        index='month',
        columns='day',
        aggfunc='mean'
    )
    
    # Ordenar meses
    if not pivot_month_day.empty:
        # Convertir índice a categoría ordenada
        month_cat = pd.CategoricalIndex(pivot_month_day.index, categories=MONTHS_ORDER, ordered=True)
        pivot_month_day = pivot_month_day.reindex(month_cat.sort_values())
        
        # Crear tabla de conteo para identificar celdas sin datos
        count_pivot_month = pd.pivot_table(
            df,
            values=metric_column,
            index='month',
            columns='day',
            aggfunc='count'
        )
        count_pivot_month = count_pivot_month.reindex(pivot_month_day.index)
        
        # Crear máscara para celdas sin datos
        mask_month = count_pivot_month == 0
        
        # Crear heatmap
        hm2 = sns.heatmap(
            pivot_month_day,
            ax=ax2,
            cmap=profit_loss_cmap,
            center=0,
            annot=True,
            fmt=".2f",
            linewidths=0.3,
            linecolor= "black",
            cbar_kws={"shrink": 0.75, "label": metric_column},
            mask=mask_month,
            square=True
        )
        
        # Configurar etiquetas y título con menor padding
        ax2.set_title(f"{metric_column} por Mes y Día del Mes", 
                    fontsize=14, fontweight='bold', color=colors['text'], pad=5)
        ax2.set_xlabel("Día del mes", fontsize=12, color=colors['text'], labelpad=5)
        ax2.set_ylabel("Mes", fontsize=12, color=colors['text'], labelpad=5)
        
        # Configurar tamaño de fuente para valores dentro de las celdas
        for text in ax2.texts:
            text.set_fontsize(9)
    else:
        ax2.text(0.5, 0.5, "No hay suficientes datos para el análisis por mes",
                ha='center', va='center', fontsize=14, color=colors['text'])
        ax2.axis('off')
    
    # Título general
    metric_name = metric_column.replace("_", " ").title()
    plt.suptitle(
        f"Análisis Temporal: {metric_name} | {strategy_info['strategy_name']} ({strategy_info['symbol']} {strategy_info['timeframe']})", 
        fontsize=16, fontweight='bold', color=colors['text'], y=0.99
    )
    
    # Ajustes manuales para eliminar el espacio en blanco
    # Usamos subplots_adjust con valores negativos para hspace
    plt.subplots_adjust(hspace=-0.3, top=0.95, bottom=0.05)
    
    # Guardar si se proporciona una ruta
    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f"Dashboard guardado como {save_path}")
    
    return fig


def create_temporal_heatmap_compact(strategy, df_trade_metrics, metric_column='net_profit_loss', 
                            figsize=(18, 11), save_path=None):
    """
    Versión más compacta de los heatmaps temporales con menos espacio entre
    el título principal y el primer heatmap.
    """
    # Configurar estilo
    colors = set_style()
    
    # Extraer información de la estrategia
    strategy_info = {
        "strategy_name": getattr(strategy, "strategy_name", "Trading Strategy"),
        "symbol": getattr(strategy, "symbol", ""),
        "timeframe": str(getattr(strategy, "timeframe", "")).replace("Timeframe.", ""),
        "exchange": str(getattr(strategy, "exchange", "")).replace("ExchangeName.", ""),
    }
    
    # Verificar que las columnas necesarias existen
    required_cols = ["day_of_week", "month", "hour", "day"]
    for col in required_cols:
        if col not in df_trade_metrics.columns:
            raise ValueError(f"La columna '{col}' no existe en el DataFrame. Asegúrate de que TradeMetricsCalculator ha procesado los datos temporales.")
    
    # Verificar que la columna de métrica existe
    if metric_column not in df_trade_metrics.columns:
        raise ValueError(f"La columna '{metric_column}' no existe en el DataFrame")
    
    # Usar directamente el DataFrame sin preprocesamiento temporal
    df = df_trade_metrics
    
    # Crear figura más compacta con subplots directamente
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=figsize, gridspec_kw={
        'hspace': 0.1,  # Espacio muy pequeño entre gráficos
        'height_ratios': [1, 1.2]  # Ligeramente más alto el segundo para compensar por días del mes
    })
    
    # 1. HEATMAP: Métrica por Hora y Día de la Semana
    pivot_hour_day = pd.pivot_table(
        df,
        values=metric_column,
        index='day_of_week',
        columns='hour',
        aggfunc='mean'
    ).reindex(DAYS_ORDER)
    
    # Crear tabla de conteo para identificar celdas sin datos
    count_pivot = pd.pivot_table(
        df,
        values=metric_column,
        index='day_of_week',
        columns='hour',
        aggfunc='count'
    ).reindex(DAYS_ORDER)
    
    # Crear máscara para celdas sin datos
    mask = count_pivot == 0
    
    # Crear heatmap 1
    hm1 = sns.heatmap(
        pivot_hour_day,
        ax=ax1,
        cmap=profit_loss_cmap,
        center=0,
        annot=True,
        fmt=".2f",
        linewidths=0.3,
        linecolor= "black",
        cbar_kws={"shrink": 0.75, "label": metric_column},
        mask=mask,
        square=True
    )
    
    # Configurar etiquetas y título
    ax1.set_title(f"{metric_column} por Hora y Día de la Semana", 
                fontsize=14, fontweight='bold', color=colors['text'], pad=2)
    ax1.set_xlabel("Hora del día", fontsize=11, color=colors['text'], labelpad=2)
    ax1.set_ylabel("Día de la semana", fontsize=11, color=colors['text'], labelpad=2)
    
    # Configurar ejes
    ax1.set_xticks(np.arange(0, 24, 2) + 0.5)
    ax1.set_xticklabels([f"{h}:00" for h in range(0, 24, 2)], rotation=45)
    
    # 2. HEATMAP: Métrica por Día del Mes y Mes
    pivot_month_day = pd.pivot_table(
        df,
        values=metric_column,
        index='month',
        columns='day',
        aggfunc='mean'
    )
    
    if not pivot_month_day.empty:
        # Convertir índice a categoría ordenada
        month_cat = pd.CategoricalIndex(pivot_month_day.index, categories=MONTHS_ORDER, ordered=True)
        pivot_month_day = pivot_month_day.reindex(month_cat.sort_values())
        
        # Crear tabla de conteo para identificar celdas sin datos
        count_pivot_month = pd.pivot_table(
            df,
            values=metric_column,
            index='month',
            columns='day',
            aggfunc='count'
        )
        count_pivot_month = count_pivot_month.reindex(pivot_month_day.index)
        
        # Crear máscara para celdas sin datos
        mask_month = count_pivot_month == 0
        
        # Crear heatmap 2
        hm2 = sns.heatmap(
            pivot_month_day,
            ax=ax2,
            cmap=profit_loss_cmap,
            center=0,
            annot=True,
            fmt=".2f",
            linewidths=0.3,
            linecolor= "black",
            cbar_kws={"shrink": 0.75, "label": metric_column},
            mask=mask_month,
            square=True
        )
        
        # Configurar etiquetas y título
        ax2.set_title(f"{metric_column} por Mes y Día del Mes", 
                    fontsize=14, fontweight='bold', color=colors['text'], pad=2)
        ax2.set_xlabel("Día del mes", fontsize=11, color=colors['text'], labelpad=2)
        ax2.set_ylabel("Mes", fontsize=11, color=colors['text'], labelpad=2)
        
        # Reducir el tamaño de fuente de las anotaciones
        for text in ax2.texts:
            text.set_fontsize(8)
    else:
        ax2.text(0.5, 0.5, "No hay suficientes datos para el análisis por mes",
                ha='center', va='center', fontsize=14, color=colors['text'])
        ax2.axis('off')
    
    # Título general - Ahora con valor de 'y' reducido para acercarlo al gráfico
    metric_name = metric_column.replace("_", " ").title()
    fig.suptitle(
        f"Análisis Temporal: {metric_name} | {strategy_info['strategy_name']} ({strategy_info['symbol']} {strategy_info['timeframe']})", 
        fontsize=16, fontweight='bold', color=colors['text'], y=0.95  # Reducido de 0.98 a 0.95
    )
    
    # Ajustar los márgenes - Reducir el margen superior
    plt.subplots_adjust(top=0.9, hspace=0.1)  # Reducido el top de 0.95 a 0.9
    
    # Guardar si se proporciona una ruta
    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f"Dashboard guardado como {save_path}")
    
    return fig


def visualize_temporal_heatmap(strategy, df_trade_metrics, metric_column='net_profit_loss', save_path=None):
    """
    Función principal para generar el dashboard de heatmaps temporales.
    Esta función será llamada desde dashboard_manager.py
    
    Args:
        strategy: Objeto de estrategia
        df_trade_metrics: DataFrame con métricas de trades
        metric_column: Columna a analizar
        save_path: Ruta opcional para guardar el gráfico
    
    Returns:
        fig: Figura de matplotlib generada
    """
    # Usar la versión alternativa más compacta
    fig = create_temporal_heatmap_compact(
        strategy=strategy,
        df_trade_metrics=df_trade_metrics,
        metric_column=metric_column,
        save_path=save_path
    )
    return fig