import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

def visualize_metrics_boxplot(strategy, df_trade_metrics, save_path=None):
    """
    Función para visualizar la distribución de métricas principales de trading usando boxplots.
    Ahora los gráficos están organizados en pares (2 por fila).
    """

    # Configurar estilo
    colors = {
        True: '#006D77',       # Color para ganancias
        False: '#E29578',      # Color para pérdidas
        'text': '#333333',     # Color de texto
    }
    sns.set_theme(style="whitegrid")

    # Extraer información de la estrategia
    strategy_info = {
        "strategy_name": getattr(strategy, "strategy_name", "Trading Strategy"),
        "symbol": getattr(strategy, "symbol", ""),
        "timeframe": str(getattr(strategy, "timeframe", "")).replace("Timeframe.", ""),
    }

    # Definir las métricas a visualizar basadas en las columnas disponibles
    metrics = [
        'MAE', 'MFE', 'profit_efficiency', 'risk_reward_ratio', 'trade_volatility', 'duration_bars'
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

    # Asegurar que 'net_profit_loss' es numérico
    df_trade_metrics['net_profit_loss'] = pd.to_numeric(df_trade_metrics['net_profit_loss'], errors='coerce')

    # Crear columna booleana para diferenciar ganadores y perdedores
    df_trade_metrics['is_winner'] = (df_trade_metrics['net_profit_loss'] > 0).astype(int)

    # Filtrar solo las métricas disponibles
    available_metrics = [m for m in metrics if m in df_trade_metrics.columns]

    # Si no hay duration_bars, pero hay trade_duration_second, usar esa
    if 'duration_bars' not in available_metrics and 'trade_duration_second' in df_trade_metrics.columns:
        available_metrics.append('trade_duration_second')

    if not available_metrics:
        fig, ax = plt.subplots(figsize=(8, 4))
        ax.text(0.5, 0.5, "No hay métricas disponibles para visualizar", ha='center', va='center', fontsize=12)
        ax.axis('off')
        return fig

    # **Nueva distribución: 2 métricas por fila**
    n_metrics = len(available_metrics)
    n_cols = 2  # 2 gráficos por fila
    n_rows = (n_metrics + 1) // 2  # Número de filas (redondeo hacia arriba)

    # Crear figura con tamaño optimizado
    fig, axes = plt.subplots(n_rows, n_cols, figsize=(12, 2.5 * n_rows))  
    axes = axes.flatten()  # Asegurar que los ejes sean una lista plana para iterar

    # Crear boxplots organizados en pares
    for i, metric in enumerate(available_metrics):
        ax = axes[i]

        sns.boxplot(
            data=df_trade_metrics,
            y='is_winner',  
            x=metric,       
            hue='is_winner',
            palette=colors,
            ax=ax,
            legend=False,
            orient='h'
        )

        # Ajustar etiquetas y títulos
        metric_title = metric_names.get(metric, metric)
        ax.set_title(f'{metric_title}', fontsize=10)  # Título más pequeño
        ax.set_ylabel('Resultado (0 = Perdedor, 1 = Ganador)', fontsize=9)  
        ax.set_xlabel(metric_title, fontsize=9)  
        ax.set_yticks([0, 1])  

    # Ocultar ejes vacíos si hay un número impar de métricas
    for j in range(i + 1, len(axes)):
        axes[j].set_visible(False)

    # Ajustar diseño general
    plt.suptitle(
        f"Distribución de Métricas | {strategy_info['strategy_name']} ({strategy_info['symbol']} {strategy_info['timeframe']})",
        fontsize=12, y=0.98
    )
    plt.tight_layout(rect=[0, 0, 1, 0.95])  # Reduce margen superior

    # Guardar si es necesario
    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f"Dashboard guardado como {save_path}")

    return fig
