import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import matplotlib.gridspec as gridspec
from matplotlib.ticker import FuncFormatter

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

# Modifica esta parte en la función create_performance_dashboard
def create_performance_dashboard(strategy, df_trade_metrics, figsize=(12, 8), save_path=None):
    """
    Crea un dashboard de rendimiento completo con Seaborn.
    
    Args:
        strategy: Objeto de estrategia con información de configuración
        df_trade_metrics: DataFrame con métricas de trades
        figsize: Tamaño de la figura (ancho, alto)
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
        "initial_capital": getattr(strategy.capital_manager, "initial_capital", 10000),
        "currency": "USDT"  # Por defecto, se puede cambiar si la estrategia usa otra moneda
    }
    
    # Calcular métricas de backtest
    backtest_metrics = calculate_backtest_metrics(df_trade_metrics, strategy_info["initial_capital"])
    
    # Crear figura base con GridSpec para control más flexible
    fig = plt.figure(figsize=figsize, constrained_layout=True)
    
    # Modificamos el GridSpec para tener 2 filas y 2 columnas
    # La primera fila ocupa ambas columnas, la segunda fila tiene dos gráficos lado a lado
    gs = gridspec.GridSpec(2, 2, figure=fig, height_ratios=[1.5, 1])
    
    # Obtener información importante
    initial_capital = strategy_info["initial_capital"]
    currency = strategy_info["currency"]
    
    # 1. Curva de Equity (Gráfico principal, ocupa todo el ancho de la primera fila)
    ax_equity = fig.add_subplot(gs[0, :])  # Primera fila, ambas columnas
    
    # Asegurar que 'cumulative_capital' existe o calcularla
    if 'cumulative_capital' in df_trade_metrics.columns:
        equity_curve = df_trade_metrics['cumulative_capital']
    else:
        equity_curve = initial_capital + df_trade_metrics["net_profit_loss"].cumsum()
    
    # Crear array de índices para el eje x
    x = np.arange(len(equity_curve))
    
    # Añadir línea de capital inicial
    ax_equity.axhline(y=initial_capital, linestyle='--', color=colors['text'], alpha=0.5, 
                      label=f'Capital Inicial: {initial_capital} {currency}')
    
    # Pintar la curva de equity con colores diferentes para ganancias/pérdidas
    # Calcular donde cambia la tendencia
    changes = np.diff(np.signbit(equity_curve.values - initial_capital))
    changes = np.insert(changes, 0, False)  # Añadir el primer punto
    
    # Definir regiones de ganancias/pérdidas
    regions = []
    start = 0
    
    # El primer punto se compara con el capital inicial
    if equity_curve.iloc[0] >= initial_capital:
        current_color = colors['profit']
    else:
        current_color = colors['loss']
    
    # Encontrar regiones continuas con la misma condición
    for i, change in enumerate(changes):
        if change or i == len(changes) - 1:
            # Guardar región actual
            regions.append((start, i, current_color))
            # Cambiar color para la siguiente región
            current_color = colors['profit'] if current_color == colors['loss'] else colors['loss']
            # Actualizar punto de inicio
            start = i
    
    # Si la última región no se agregó
    if start < len(equity_curve) - 1:
        regions.append((start, len(equity_curve) - 1, current_color))
    
    # Dibujar cada región con su color
    for start, end, color in regions:
        if end >= start:  # Asegurar que la región es válida
            ax_equity.plot(x[start:end+1], equity_curve.iloc[start:end+1], color=color, linewidth=2)
    
    # Formato y etiquetas
    ax_equity.set_title('Curva de Equity', fontsize=14, fontweight='bold', color=colors['text'])
    ax_equity.set_xlabel('Operación #', fontsize=12, color=colors['text'])
    ax_equity.set_ylabel(f'Capital ({currency})', fontsize=12, color=colors['text'])
    
    # Añadir una sombra suave debajo de la curva para mejorar visibilidad
    ax_equity.fill_between(x, initial_capital, equity_curve, where=(equity_curve >= initial_capital), 
                           color=colors['profit'], alpha=0.15)
    ax_equity.fill_between(x, initial_capital, equity_curve, where=(equity_curve < initial_capital), 
                           color=colors['loss'], alpha=0.15)
    
    # Añadir etiquetas para capital final
    final_capital = equity_curve.iloc[-1]
    ax_equity.text(0.02, 0.13, f"Capital Final: {final_capital:.2f} {currency}", 
                  transform=ax_equity.transAxes, fontsize=12, fontweight='bold',
                  color=colors['text'], verticalalignment='top', 
                  bbox=dict(facecolor='white', alpha=0.7, edgecolor='none', pad=3))
    
    # Añadir ROI
    if 'ROI' in backtest_metrics:
        roi = backtest_metrics['ROI']
        roi_color = colors['profit'] if roi >= 0 else colors['loss']
        ax_equity.text(0.02, 0.05, f"ROI: {roi:.2f}%", 
                      transform=ax_equity.transAxes, fontsize=12, fontweight='bold',
                      color=roi_color, verticalalignment='top',
                      bbox=dict(facecolor='white', alpha=0.7, edgecolor='none', pad=3))
    
    # 2. Distribución de P&L (Histograma) - Ahora en la segunda fila, primera columna
    ax_hist = fig.add_subplot(gs[1, 0])
    
    # Usando KDE para mostrar distribución suavizada
    sns.histplot(df_trade_metrics["net_profit_loss"], ax=ax_hist, kde=True, 
                 color=colors['highlight'], edgecolor=colors['text'], alpha=0.7,
                 bins=20)
    
    # Añadir línea vertical en cero
    ax_hist.axvline(0, linestyle='--', color=colors['text'], alpha=0.5)
    
    # Formato y etiquetas
    ax_hist.set_title('Distribución de Ganancias/Pérdidas', fontsize=14, fontweight='bold', color=colors['text'])
    ax_hist.set_xlabel(f'P&L ({currency})', fontsize=12, color=colors['text'])
    ax_hist.set_ylabel('Frecuencia', fontsize=12, color=colors['text'])
    
    # 3. Gráfico de dispersión del P&L por operación - Ahora en la segunda fila, segunda columna
    ax_scatter = fig.add_subplot(gs[1, 1])
    
    # Dibujar gráfico de dispersión con colores basados en ganancias/pérdidas
    scatter = sns.scatterplot(
        x=range(len(df_trade_metrics)),
        y=df_trade_metrics["net_profit_loss"],
        hue=df_trade_metrics["net_profit_loss"] > 0,
        palette={True: colors['profit'], False: colors['loss']},
        s=70, alpha=0.7, ax=ax_scatter,
        edgecolor=colors['text'], linewidth=0.5,
        legend=False
    )
    
    # Línea de cero
    ax_scatter.axhline(0, linestyle='--', color=colors['text'], alpha=0.5)
    
    # Formato y etiquetas
    ax_scatter.set_title('Rendimiento por Operación', fontsize=14, fontweight='bold', color=colors['text'])
    ax_scatter.set_xlabel('Operación #', fontsize=12, color=colors['text'])
    ax_scatter.set_ylabel(f'P&L ({currency})', fontsize=12, color=colors['text'])
    
    # Configuración final de la figura
    plt.suptitle(
        f"{strategy_info.get('strategy_name', 'Trading Strategy')} | {strategy_info.get('symbol', '')} {strategy_info.get('timeframe', '')}",
        fontsize=16, fontweight='bold', color=colors['text'], y=1.02
    )
    
    # Guardar si se proporciona una ruta
    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f"Dashboard guardado como {save_path}")
    
    return fig

def calculate_backtest_metrics(df_trade_metrics, initial_capital):
    """
    Calcula las métricas básicas del backtest a partir del DataFrame de trades.
    
    Args:
        df_trade_metrics: DataFrame con las métricas de trades
        initial_capital: Capital inicial
    
    Returns:
        dict: Diccionario con las métricas calculadas
    """
    metrics = {}
    
    # Total de operaciones
    metrics['total_trades'] = len(df_trade_metrics)
    
    # Operaciones ganadoras y perdedoras
    metrics['winning_trades'] = sum(df_trade_metrics['net_profit_loss'] > 0)
    metrics['losing_trades'] = sum(df_trade_metrics['net_profit_loss'] <= 0)
    
    # Porcentaje de operaciones rentables
    metrics['percent_profitable'] = metrics['winning_trades'] / metrics['total_trades'] * 100 if metrics['total_trades'] > 0 else 0
    
    # Beneficio bruto y neto
    metrics['gross_profit'] = df_trade_metrics[df_trade_metrics['net_profit_loss'] > 0]['net_profit_loss'].sum()
    metrics['gross_loss'] = df_trade_metrics[df_trade_metrics['net_profit_loss'] <= 0]['net_profit_loss'].sum()
    metrics['net_profit'] = df_trade_metrics['net_profit_loss'].sum()
    
    # ROI
    metrics['ROI'] = (metrics['net_profit'] / initial_capital) * 100
    
    # Factor de beneficio
    if metrics['gross_loss'] != 0:
        metrics['profit_factor'] = abs(metrics['gross_profit'] / metrics['gross_loss'])
    else:
        metrics['profit_factor'] = float('inf') if metrics['gross_profit'] > 0 else 0
    
    # Ratio ganador/perdedor
    if metrics['losing_trades'] > 0:
        metrics['win_loss_ratio'] = metrics['winning_trades'] / metrics['losing_trades']
    else:
        metrics['win_loss_ratio'] = float('inf') if metrics['winning_trades'] > 0 else 0
    
    # Expectativa
    metrics['expectancy'] = metrics['net_profit'] / metrics['total_trades'] if metrics['total_trades'] > 0 else 0
    
    # Máximo drawdown (si no se proporciona, calculamos una aproximación)
    if 'cumulative_capital' in df_trade_metrics.columns:
        # Calcular drawdown como porcentaje desde el pico
        cumulative = df_trade_metrics['cumulative_capital'].values
        max_so_far = np.maximum.accumulate(cumulative)
        drawdown = (cumulative - max_so_far) / max_so_far * 100
        metrics['max_drawdown_pct'] = abs(np.min(drawdown)) if len(drawdown) > 0 else 0
        metrics['max_drawdown'] = abs(np.min(cumulative - max_so_far)) if len(cumulative) > 0 else 0
        metrics['avg_drawdown'] = abs(np.mean(cumulative - max_so_far)) if len(cumulative) > 0 else 0
    else:
        # Si no hay columna de capital acumulado, asignamos valores estimados
        metrics['max_drawdown_pct'] = 0
        metrics['max_drawdown'] = 0 
        metrics['avg_drawdown'] = 0
    
    # Ratios de rendimiento (solo placeholders, requieren cálculos más complejos)
    metrics['sharpe_ratio'] = 'N/A'  # Requiere retornos diarios
    metrics['sortino_ratio'] = 'N/A'  # Requiere retornos diarios y desviación de rendimientos negativos
    metrics['recovery_factor'] = 'N/A'  # Requiere periodo de tiempo
    
    return metrics

def visualize_performance(strategy, df_trade_metrics, save_path=None):
    """
    Función principal para generar el dashboard de rendimiento.
    Esta función será llamada desde dashboard_manager.py
    
    Args:
        strategy: Objeto de estrategia
        df_trade_metrics: DataFrame con métricas de trades
        save_path: Ruta opcional para guardar el gráfico
    
    Returns:
        fig: Figura de matplotlib generada
    """
    fig = create_performance_dashboard(strategy, df_trade_metrics, save_path=save_path)
    return fig