import matplotlib.pyplot as plt
import os
import seaborn as sns
import numpy as np

# 1️⃣ Importar los módulos estándar de visualización:
from visualization.dashboards.performance_dashboard import visualize_performance
from visualization.dashboards.temporal_heatmaps import visualize_temporal_heatmap
from visualization.dashboards.metrics_distribution import visualize_metrics_distribution
from visualization.dashboards.metrics_boxplot import visualize_metrics_boxplot

# 2️⃣ Importar visualizaciones tipo scatter desde scatter_metrics.py:
from visualization.dashboards.scatter_metrics import (
    visualize_metrics_vs_mae,
    visualize_metrics_vs_mfe,
    visualize_metrics_vs_risk_reward,
    visualize_metrics_vs_volatility,
    visualize_metrics_vs_profit_efficiency
)

# 3️⃣ Importar función time_chart desde week_month_barchart.py
from visualization.dashboards.week_month_barchart import time_chart

# 4️⃣ Lista ordenada de módulos
MODULE_ORDER = [
    "performance",         # Requiere strategy - PRIMERO
    "time_chart",          # Análisis temporal (día y mes)
    "temporal",            # Requiere strategy
    "metrics_distribution", # Requiere strategy
    "metrics_boxplot",     # Requiere strategy
    "mae_scatter",         # Scatter plots
    "mfe_scatter",
    "risk_reward_scatter",
    "volatility_scatter",
    "profit_efficiency_scatter",
]

# Mapeo de módulos a funciones
MODULE_FUNCTIONS = {
    "performance": visualize_performance,
    "time_chart": time_chart,
    "temporal": visualize_temporal_heatmap,
    "metrics_distribution": visualize_metrics_distribution,
    "metrics_boxplot": visualize_metrics_boxplot,
    "mae_scatter": visualize_metrics_vs_mae,
    "mfe_scatter": visualize_metrics_vs_mfe,
    "risk_reward_scatter": visualize_metrics_vs_risk_reward,
    "volatility_scatter": visualize_metrics_vs_volatility,
    "profit_efficiency_scatter": visualize_metrics_vs_profit_efficiency,
}

# Módulos que NO requieren strategy
NON_STRATEGY_MODULES = [
    "mae_scatter",
    "mfe_scatter",
    "risk_reward_scatter",
    "volatility_scatter",
    "profit_efficiency_scatter",
    "time_chart"
]

def create_dashboard(strategy, df_trade_metrics, modules=None, output_folder="dashboards", show=True):
    """
    Crea y muestra los dashboards seleccionados, en el orden definido.
    
    Args:
        strategy: Objeto de estrategia.
        df_trade_metrics: DataFrame con métricas de trades.
        modules: Lista de módulos a incluir. (Si es None, usa todos los disponibles).
        output_folder: Carpeta donde guardar los dashboards.
        show: Si es True, muestra los gráficos generados.
        
    Returns:
        dict: Diccionario con las figuras generadas {nombre_modulo: figura}.
    """
    # Asegurar que el directorio exista
    os.makedirs(output_folder, exist_ok=True)
    
    # Si no se especifican módulos, usar todos
    if modules is None:
        modules = MODULE_ORDER
    
    # Validar los módulos seleccionados
    valid_modules = []
    for module in MODULE_ORDER:  # Usar el orden predefinido
        if module in modules and module in MODULE_FUNCTIONS:
            valid_modules.append(module)
    
    invalid_modules = [m for m in modules if m not in MODULE_FUNCTIONS]
    if invalid_modules:
        print(f"⚠️ Módulos inválidos ignorados: {invalid_modules}")
    
    # Diccionario para guardar las figuras
    figures = {}
    
    # Crear y guardar cada dashboard
    for module in valid_modules:
        try:
            print(f"🔹 Generando {module}...")
            
            # Definir dónde se guardará la figura
            save_path = os.path.join(output_folder, f"{module}_dashboard.png")
            
            # Obtener la función de visualización
            visualization_func = MODULE_FUNCTIONS[module]
            
            # Generar el gráfico
            if module in NON_STRATEGY_MODULES:
                # Si la función NO requiere strategy
                fig = visualization_func(df_trade_metrics, save_path=save_path)
            else:
                # Si la función requiere strategy
                fig = visualization_func(strategy, df_trade_metrics, save_path=save_path)
            
            # Guardar la figura
            figures[module] = fig
            
        except Exception as e:
            print(f"⚠️ Error en {module}: {e}")
            import traceback
            traceback.print_exc()
    
    # Mostrar los gráficos juntos si se solicita
    if show and figures:
        for module in valid_modules:
            if module in figures and figures[module] is not None:
                # Copiar número de figura y mostrar sin sobrescribir la original
                fig_num = figures[module].number
                plt.figure(fig_num)
        
        plt.show()
    
    # Mensaje final
    if figures:
        print(f"✅ {len(figures)} dashboards generados: {', '.join(figures.keys())}")
    else:
        print("⚠️ No se generó ningún dashboard.")
    
    return figures

def create_time_analysis_dashboard(df_trade_metrics, output_folder="dashboards", show=True):
    """
    Crea y muestra un dashboard específico de análisis temporal (día de semana y mes en un mismo lienzo).
    
    Args:
        df_trade_metrics: DataFrame con métricas de trades.
        output_folder: Carpeta donde guardar los dashboards.
        show: Si es True, muestra los gráficos generados.
        
    Returns:
        fig: Figura combinada generada.
    """
    os.makedirs(output_folder, exist_ok=True)
    
    try:
        print("🔹 Generando análisis temporal...")
        
        # Generar el gráfico
        save_path = os.path.join(output_folder, "time_chart_dashboard.png")
        fig = time_chart(df_trade_metrics, save_path=save_path)
        
        # Mostrar si se solicita
        if show and fig is not None:
            plt.figure(fig.number)
            plt.show()
        
        print("✅ Análisis temporal completado")
        return fig
        
    except Exception as e:
        print(f"⚠️ Error en el análisis temporal: {e}")
        import traceback
        traceback.print_exc()
        return None