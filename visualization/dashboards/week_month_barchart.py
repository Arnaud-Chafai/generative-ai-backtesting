import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns
from utils.timeframe import DAYS_ORDER, MONTHS_ORDER

def time_chart(df_trade_metrics, save_path=None):
    """
    Genera un gráfico con análisis por año, mes y día de la semana en un solo lienzo.
    Las leyendas se colocan a la derecha de los gráficos.
    
    Args:
        df_trade_metrics: DataFrame con métricas de trades.
        save_path: Ruta opcional para guardar el gráfico.
        
    Returns:
        fig: Figura de Matplotlib generada.
    """
    # Verificar que las columnas necesarias existen
    required_cols = ["day_of_week", "month", "year", "net_profit_loss"]
    for col in required_cols:
        if col not in df_trade_metrics.columns:
            raise ValueError(f"La columna '{col}' no existe en el DataFrame. Asegúrate de que TradeMetricsCalculator ha procesado los datos temporales.")
    
    # Crear figura con tres paneles en disposición horizontal y espacio para leyendas
    fig = plt.figure(figsize=(18, 12))  # Ancho aumentado para dar espacio a las leyendas
    
    # Usar GridSpec para crear 3 filas y 2 columnas (3 paneles horizontales + espacio para leyendas)
    gs = plt.GridSpec(3, 2, height_ratios=[1, 1, 1], width_ratios=[4, 1], hspace=0.3, wspace=0.05)
    
    # Crear los 3 ejes para gráficos y 3 ejes para leyendas
    ax_year = fig.add_subplot(gs[0, 0])   # Panel superior (años)
    ax_year_legend = fig.add_subplot(gs[0, 1])  # Leyenda años
    
    ax_month = fig.add_subplot(gs[1, 0])  # Panel central (meses)
    ax_month_legend = fig.add_subplot(gs[1, 1])  # Leyenda meses
    
    ax_day = fig.add_subplot(gs[2, 0])    # Panel inferior (días)
    ax_day_legend = fig.add_subplot(gs[2, 1])  # Leyenda días
    
    # Desactivar ejes para las leyendas
    ax_year_legend.axis('off')
    ax_month_legend.axis('off')
    ax_day_legend.axis('off')
    
    # Colores
    colors = {
        'profit': '#006D77',  # Color para positivo (azul verdoso)
        'loss': '#E29578',    # Color para negativo (salmón)
        'text': '#333333'     # Color para texto
    }
    
    # --- GRÁFICO DE AÑOS (ARRIBA) ---
    
    # Obtener los años únicos ordenados cronológicamente
    years = sorted(df_trade_metrics["year"].unique())
    
    # Estadísticas por año
    year_stats = []
    for year in years:
        year_trades = df_trade_metrics[df_trade_metrics["year"] == year]
        
        if len(year_trades) > 0:
            win_count = len(year_trades[year_trades["net_profit_loss"] > 0])
            win_rate = win_count / len(year_trades) * 100
            net_result = year_trades["net_profit_loss"].sum()
            
            year_stats.append({
                "period": str(year),
                "trades": len(year_trades),
                "win_rate": win_rate,
                "net_result": net_result,
                "is_profitable": net_result > 0
            })
        else:
            year_stats.append({
                "period": str(year),
                "trades": 0,
                "win_rate": 0,
                "net_result": 0,
                "is_profitable": False
            })
    
    # Convertir a DataFrame
    year_df = pd.DataFrame(year_stats)
    
    # Si hay años para mostrar
    if not year_df.empty and len(year_df) > 0:
        # Dibujar gráfico de años
        y_pos_year = np.arange(len(year_df))
        bar_colors_year = [colors['profit'] if row["is_profitable"] else colors['loss'] 
                           for _, row in year_df.iterrows()]
        
        ax_year.barh(y_pos_year, year_df["net_result"], color=bar_colors_year, edgecolor="black", alpha=0.9)
        ax_year.axvline(x=0, color='black', linestyle='-', alpha=0.3)
        ax_year.set_xlabel("Resultado Neto", fontsize=12, color=colors['text'])
        ax_year.set_yticks(y_pos_year)
        ax_year.set_yticklabels(year_df["period"])
        
        # Agregar grid más ligero en ambos ejes para el gráfico de años
        ax_year.grid(axis='both', linestyle='-', alpha=0.5, color='gray')
        
                    # Añadir número de trades más cerca de las barras
        for i, row in enumerate(year_df.itertuples()):
            if row.trades > 0:
                # Cálculo de posición muy cercana a la barra
                padding = abs(row.net_result) * 0.01  # 1% del valor como padding
                padding = max(padding, 0.5)  # Un padding muy pequeño
                text_pos = row.net_result + padding if row.net_result >= 0 else row.net_result - padding
                ha = 'left' if row.net_result >= 0 else 'right'
                ax_year.text(text_pos, i, str(row.trades), ha=ha, va='center', 
                            fontsize=9, color=colors['text'], fontweight="bold")
        
        # Crear leyenda mejorada para años (solo años con trades) en panel separado
        year_handles = []
        year_labels = []
        for i, row in enumerate(year_df.itertuples()):
            if row.trades > 0:
                # Crear un parche para cada año con trades
                color = colors['profit'] if row.is_profitable else colors['loss']
                handle = plt.Rectangle((0, 0), 1, 1, color=color, edgecolor="black", alpha=0.9)
                year_handles.append(handle)
                year_labels.append(f"{row.period}: WR {row.win_rate:.1f}%")
        
        if year_handles:
            # Crear leyenda personalizada en el panel de leyenda
            legend = ax_year_legend.legend(year_handles, year_labels, loc='center', 
                                          title="Resultados por Año", 
                                          fontsize=10, 
                                          frameon=True,
                                          fancybox=True,
                                          title_fontsize=12)
            legend.get_frame().set_alpha(0.9)
            legend.get_frame().set_edgecolor('gray')
    else:
        # Si no hay datos de años, mostrar mensaje
        ax_year.text(0.5, 0.5, "No hay datos suficientes para análisis por año", 
                     ha='center', va='center', fontsize=12, color=colors['text'])
        ax_year.axis('off')
    
    ax_year.set_title("Resultado por Año", fontsize=13, fontweight="bold", color=colors['text'])
    
    # --- GRÁFICO DE MESES (CENTRO) ---
    
    # Estadísticas por mes
    month_stats = []
    for month in MONTHS_ORDER:
        month_trades = df_trade_metrics[df_trade_metrics["month"] == month]
        
        if len(month_trades) > 0:
            win_count = len(month_trades[month_trades["net_profit_loss"] > 0])
            win_rate = win_count / len(month_trades) * 100
            net_result = month_trades["net_profit_loss"].sum()
            
            month_stats.append({
                "period": month,
                "trades": len(month_trades),
                "win_rate": win_rate,
                "net_result": net_result,
                "is_profitable": net_result > 0
            })
        else:
            month_stats.append({
                "period": month,
                "trades": 0,
                "win_rate": 0,
                "net_result": 0,
                "is_profitable": False
            })
    
    # Convertir a DataFrame
    month_df = pd.DataFrame(month_stats)
    
    # Dibujar gráfico de meses
    y_pos_month = np.arange(len(month_df))
    bar_colors_month = [colors['profit'] if row["is_profitable"] else colors['loss'] 
                        for _, row in month_df.iterrows()]
    
    ax_month.barh(y_pos_month, month_df["net_result"], color=bar_colors_month, edgecolor="black", alpha=0.9)
    ax_month.axvline(x=0, color='black', linestyle='-', alpha=0.3)
    ax_month.set_xlabel("Resultado Neto", fontsize=12, color=colors['text'])
    ax_month.set_yticks(y_pos_month)
    ax_month.set_yticklabels([x[:3] for x in MONTHS_ORDER])
    
    # Agregar grid más ligero en ambos ejes para el gráfico de meses
    ax_month.grid(axis='both', linestyle='-', alpha=0.5, color='gray')
    
    # Añadir número de trades más cerca de las barras
    for i, row in enumerate(month_df.itertuples()):
        if row.trades > 0:
            # Cálculo de posición muy cercana a la barra
            padding = abs(row.net_result) * 0.01  # 1% del valor como padding
            padding = max(padding, 0.5)  # Un padding muy pequeño
            text_pos = row.net_result + padding if row.net_result >= 0 else row.net_result - padding
            ha = 'left' if row.net_result >= 0 else 'right'
            ax_month.text(text_pos, i, str(row.trades), ha=ha, va='center', 
                         fontsize=9, color=colors['text'], fontweight="bold")
    
    # Crear leyenda mejorada para meses (solo meses con trades) en panel separado
    month_handles = []
    month_labels = []
    for i, row in enumerate(month_df.itertuples()):
        if row.trades > 0:
            # Crear un parche para cada mes con trades
            color = colors['profit'] if row.is_profitable else colors['loss']
            handle = plt.Rectangle((0, 0), 1, 1, color=color, edgecolor="black", alpha=0.9)
            month_handles.append(handle)
            month_labels.append(f"{row.period[:3]}: WR {row.win_rate:.1f}%")
    
    if month_handles:
        # Crear leyenda personalizada en el panel de leyenda
        month_legend = ax_month_legend.legend(month_handles, month_labels, loc='center', 
                                          title="Resultados por Mes", 
                                          fontsize=10, 
                                          frameon=True,
                                          fancybox=True,
                                          title_fontsize=12)
        month_legend.get_frame().set_alpha(0.9)
        month_legend.get_frame().set_edgecolor('gray')
    
    ax_month.set_title("Resultado por Mes", fontsize=13, fontweight="bold", color=colors['text'])
    
    # --- GRÁFICO DE DÍAS (ABAJO) ---
    
    # Estadísticas por día
    day_stats = []
    for day in DAYS_ORDER:
        day_trades = df_trade_metrics[df_trade_metrics["day_of_week"] == day]
        
        if len(day_trades) > 0:
            win_count = len(day_trades[day_trades["net_profit_loss"] > 0])
            win_rate = win_count / len(day_trades) * 100
            net_result = day_trades["net_profit_loss"].sum()
            
            day_stats.append({
                "period": day,
                "trades": len(day_trades),
                "win_rate": win_rate,
                "net_result": net_result,
                "is_profitable": net_result > 0
            })
        else:
            day_stats.append({
                "period": day,
                "trades": 0,
                "win_rate": 0,
                "net_result": 0,
                "is_profitable": False
            })
    
    # Convertir a DataFrame
    day_df = pd.DataFrame(day_stats)
    
    # Dibujar gráfico de días
    y_pos_day = np.arange(len(day_df))
    bar_colors_day = [colors['profit'] if row["is_profitable"] else colors['loss'] 
                     for _, row in day_df.iterrows()]
    
    ax_day.barh(y_pos_day, day_df["net_result"], color=bar_colors_day, edgecolor="black", alpha=0.9)
    ax_day.axvline(x=0, color='black', linestyle='-', alpha=0.3)
    ax_day.set_xlabel("Resultado Neto", fontsize=12, color=colors['text'])
    ax_day.set_yticks(y_pos_day)
    ax_day.set_yticklabels(DAYS_ORDER)
    
    # Agregar grid más ligero en ambos ejes para el gráfico de días
    ax_day.grid(axis='both', linestyle='-', alpha=0.5, color='gray')
    
    # Añadir número de trades más cerca de las barras
    for i, row in enumerate(day_df.itertuples()):
        if row.trades > 0:
            # Cálculo de posición muy cercana a la barra
            padding = abs(row.net_result) * 0.01  # 1% del valor como padding
            padding = max(padding, 0.2)  # Un padding muy pequeño
            text_pos = row.net_result + padding if row.net_result >= 0 else row.net_result - padding
            ha = 'left' if row.net_result >= 0 else 'right'
            ax_day.text(text_pos, i, str(row.trades), ha=ha, va='center', 
                        fontsize=9, color=colors['text'], fontweight="bold")
    
    # Crear leyenda mejorada para días (solo días con trades) en panel separado
    day_handles = []
    day_labels = []
    for i, row in enumerate(day_df.itertuples()):
        if row.trades > 0:
            # Crear un parche para cada día con trades
            color = colors['profit'] if row.is_profitable else colors['loss']
            handle = plt.Rectangle((0, 0), 1, 1, color=color, edgecolor="black", alpha=0.9)
            day_handles.append(handle)
            day_labels.append(f"{row.period}: WR {row.win_rate:.1f}%")
    
    if day_handles:
        # Crear leyenda personalizada en el panel de leyenda
        day_legend = ax_day_legend.legend(day_handles, day_labels, loc='center', 
                                        title="Resultados por Día", 
                                        fontsize=10, 
                                        frameon=True,
                                        fancybox=True,
                                        title_fontsize=12)
        day_legend.get_frame().set_alpha(0.9)
        day_legend.get_frame().set_edgecolor('gray')
    
    ax_day.set_title("Resultado por Día de la Semana", fontsize=13, fontweight="bold", color=colors['text'])
    
    # Título general
    fig.suptitle("Análisis Temporal de Trading", fontsize=16, fontweight="bold")
    
    # Ajustar diseño
    plt.tight_layout(rect=[0, 0, 1, 0.95])  # Dejar espacio para el título
    
    # Guardar si se proporciona ruta
    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches="tight")
        print(f"📊 Gráfico guardado como {save_path}")
    
    return fig

def create_combined_charts(df_trade_metrics, output_folder="dashboards"):
    """
    Crea y guarda los gráficos por año, mes y día de la semana.
    
    Args:
        df_trade_metrics: DataFrame con métricas de trades.
        output_folder: Carpeta donde guardar los gráficos.
        
    Returns:
        fig: Figura combinada.
    """
    import os
    os.makedirs(output_folder, exist_ok=True)
    
    # Usar directamente time_chart que ya ha sido adaptado
    fig = time_chart(df_trade_metrics)
    
    # Guardar figura combinada
    combined_save_path = os.path.join(output_folder, "time_analysis_dashboard.png")
    plt.savefig(combined_save_path, dpi=300, bbox_inches="tight")
    print(f"📊 Dashboard combinado guardado como {combined_save_path}")
    
    return fig