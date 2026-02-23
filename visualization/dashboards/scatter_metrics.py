import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

from visualization.theme import apply_dashboard_style

def visualize_metrics_vs_mae(df_trade_metrics, save_path=None):
    """
    Genera gráficos de dispersión mostrando la relación entre:
    - MAE vs MFE
    - MAE vs Risk-Reward Ratio
    - MAE vs Profit Efficiency
    - MAE vs Trade Volatility
    """
    colors = apply_dashboard_style()

    required_metrics = ['MAE', 'MFE', 'risk_reward_ratio', 'profit_efficiency', 'trade_volatility']
    missing_metrics = [m for m in required_metrics if m not in df_trade_metrics.columns]
    if missing_metrics:
        print(f"❌ Faltan las siguientes métricas: {', '.join(missing_metrics)}")
        return None

    fig, axes = plt.subplots(2, 2, figsize=(12, 8), gridspec_kw={'wspace': 0.3, 'hspace': 0.3})

    # 1. MAE vs MFE
    scatter = sns.scatterplot(
        x='MAE',
        y='MFE',
        data=df_trade_metrics,
        hue='net_profit_loss',
        palette='RdBu',
        s=70,
        alpha=0.7,
        linewidth=0.5,
        edgecolor='black',  # Borde negro
        ax=axes[0, 0]
    )
    sns.regplot(x='MAE', y='MFE', data=df_trade_metrics, scatter=False, ci=None,
                color=colors['text'], line_kws={"alpha": 0.7, "lw": 2}, ax=axes[0, 0])
    axes[0, 0].set_title('MAE vs MFE')
    legend = axes[0, 0].legend(
        title="Net Profit/Loss",
        bbox_to_anchor=(1.3, 1),
        loc="upper left",
        borderaxespad=0,
        frameon=True  
    )

    # 2. MAE vs Risk-Reward Ratio
    scatter = sns.scatterplot(
        x='MAE',
        y='risk_reward_ratio',
        data=df_trade_metrics,
        hue='net_profit_loss',
        palette='RdBu',
        s=70,
        alpha=0.7,
        linewidth=0.5,
        edgecolor='black',
        ax=axes[0, 1]
    )
    sns.regplot(x='MAE', y='risk_reward_ratio', data=df_trade_metrics, scatter=False,
                ci=None, color=colors['text'], line_kws={"alpha": 0.7, "lw": 2}, ax=axes[0, 1])
    axes[0, 1].set_title('MAE vs Risk-Reward Ratio')
    scatter.legend_.remove()

    # 3. MAE vs Profit Efficiency
    scatter = sns.scatterplot(
        x='MAE',
        y='profit_efficiency',
        data=df_trade_metrics,
        hue='net_profit_loss',
        palette='RdBu',
        s=70,
        alpha=0.7,
        linewidth=0.5,
        edgecolor='black',
        ax=axes[1, 0]
    )
    sns.regplot(x='MAE', y='profit_efficiency', data=df_trade_metrics, scatter=False,
                ci=None, color=colors['text'], line_kws={"alpha": 0.7, "lw": 2}, ax=axes[1, 0])
    axes[1, 0].set_title('MAE vs Profit Efficiency')
    scatter.legend_.remove()

    # 4. MAE vs Trade Volatility
    scatter = sns.scatterplot(
        x='MAE',
        y='trade_volatility',
        data=df_trade_metrics,
        hue='net_profit_loss',
        palette='RdBu',
        s=70,
        alpha=0.7,
        linewidth=0.5,
        edgecolor='black',
        ax=axes[1, 1]
    )
    sns.regplot(x='MAE', y='trade_volatility', data=df_trade_metrics, scatter=False,
                ci=None, color=colors['text'], line_kws={"alpha": 0.7, "lw": 2}, ax=axes[1, 1])
    axes[1, 1].set_title('MAE vs Trade Volatility')
    scatter.legend_.remove()

    plt.suptitle(
        "Relación de MAE con Otras Métricas",
        fontsize=14, fontweight='bold', color=colors['text'], y=0.98
    )
    plt.tight_layout(rect=[0, 0, 0.75, 0.95])  

    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f"📊 Gráfico guardado como {save_path}")

    return fig


def visualize_metrics_vs_mfe(df_trade_metrics, save_path=None):
    """
    Genera gráficos de dispersión mostrando la relación entre:
    - MFE vs MAE
    - MFE vs Risk-Reward Ratio
    - MFE vs Profit Efficiency
    - MFE vs Trade Volatility
    """
    colors = apply_dashboard_style()
    required_metrics = ['MFE', 'MAE', 'risk_reward_ratio', 'profit_efficiency', 'trade_volatility']
    missing_metrics = [m for m in required_metrics if m not in df_trade_metrics.columns]
    if missing_metrics:
        print(f"❌ Faltan las siguientes métricas: {', '.join(missing_metrics)}")
        return None

    fig, axes = plt.subplots(2, 2, figsize=(12, 8), gridspec_kw={'wspace': 0.3, 'hspace': 0.3})

    # 1. MFE vs MAE
    scatter = sns.scatterplot(
        x='MFE',
        y='MAE',
        data=df_trade_metrics,
        hue='net_profit_loss',
        palette='RdBu',
        linewidth=0.5,
        edgecolor='black',
        s=70,
        alpha=0.7,
        ax=axes[0, 0]
    )
    sns.regplot(x='MFE', y='MAE', data=df_trade_metrics, scatter=False, ci=None,
                color=colors['text'], line_kws={"alpha": 0.7, "lw": 2}, ax=axes[0, 0])
    axes[0, 0].set_title('MFE vs MAE')
    legend = axes[0, 0].legend(
        title="Net Profit/Loss",
        bbox_to_anchor=(1.3, 1),
        loc="upper left",
        borderaxespad=0,
        frameon=True  
    )

    # 2. MFE vs Risk-Reward Ratio
    scatter = sns.scatterplot(
        x='MFE',
        y='risk_reward_ratio',
        data=df_trade_metrics,
        hue='net_profit_loss',
        palette='RdBu',
        linewidth=0.5,
        edgecolor='black',
        s=70,
        alpha=0.7,
        ax=axes[0, 1]
    )
    sns.regplot(x='MFE', y='risk_reward_ratio', data=df_trade_metrics, scatter=False,
                ci=None, color=colors['text'], line_kws={"alpha": 0.7, "lw": 2}, ax=axes[0, 1])
    axes[0, 1].set_title('MFE vs Risk-Reward Ratio')
    scatter.legend_.remove()

    # 3. MFE vs Profit Efficiency
    scatter = sns.scatterplot(
        x='MFE',
        y='profit_efficiency',
        data=df_trade_metrics,
        hue='net_profit_loss',
        palette='RdBu',
        linewidth=0.5,
        edgecolor='black',
        s=70,
        alpha=0.7,
        ax=axes[1, 0]
    )
    sns.regplot(x='MFE', y='profit_efficiency', data=df_trade_metrics, scatter=False,
                ci=None, color=colors['text'], line_kws={"alpha": 0.7, "lw": 2}, ax=axes[1, 0])
    axes[1, 0].set_title('MFE vs Profit Efficiency')
    scatter.legend_.remove()

    # 4. MFE vs Trade Volatility
    scatter = sns.scatterplot(
        x='MFE',
        y='trade_volatility',
        data=df_trade_metrics,
        hue='net_profit_loss',
        palette='RdBu',
        linewidth=0.5,
        edgecolor='black',
        s=70,
        alpha=0.7,
        ax=axes[1, 1]
    )
    sns.regplot(x='MFE', y='trade_volatility', data=df_trade_metrics, scatter=False,
                ci=None, color=colors['text'], line_kws={"alpha": 0.7, "lw": 2}, ax=axes[1, 1])
    axes[1, 1].set_title('MFE vs Trade Volatility')
    scatter.legend_.remove()

    plt.suptitle(
        "Relación de MFE con Otras Métricas",
        fontsize=14, fontweight='bold', color=colors['text'], y=0.98
    )
    plt.tight_layout(rect=[0, 0, 0.75, 0.95])  
    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f"📊 Gráfico guardado como {save_path}")

    return fig


def visualize_metrics_vs_risk_reward(df_trade_metrics, save_path=None):
    """
    Genera gráficos de dispersión mostrando la relación entre:
    - Risk-Reward Ratio vs MAE
    - Risk-Reward Ratio vs MFE
    - Risk-Reward Ratio vs Profit Efficiency
    - Risk-Reward Ratio vs Trade Volatility
    """
    colors = apply_dashboard_style()
    required_metrics = ['risk_reward_ratio', 'MAE', 'MFE', 'profit_efficiency', 'trade_volatility']
    missing_metrics = [m for m in required_metrics if m not in df_trade_metrics.columns]
    if missing_metrics:
        print(f"❌ Faltan las siguientes métricas: {', '.join(missing_metrics)}")
        return None

    fig, axes = plt.subplots(2, 2, figsize=(12, 8), gridspec_kw={'wspace': 0.3, 'hspace': 0.3})

    # 1. Risk-Reward Ratio vs MAE
    scatter = sns.scatterplot(
        x='risk_reward_ratio',
        y='MAE',
        data=df_trade_metrics,
        hue='net_profit_loss',
        palette='RdBu',
        linewidth=0.5,
        edgecolor='black',
        s=70,
        alpha=0.7,
        ax=axes[0, 0]
    )
    sns.regplot(x='risk_reward_ratio', y='MAE', data=df_trade_metrics, scatter=False,
                ci=None, color=colors['text'], line_kws={"alpha": 0.7, "lw": 2}, ax=axes[0, 0])
    axes[0, 0].set_title('Risk-Reward Ratio vs MAE')
    legend = axes[0, 0].legend(
        title="Net Profit/Loss",
        bbox_to_anchor=(1.3, 1),
        loc="upper left",
        borderaxespad=0,
        frameon=True  
    )

    # 2. Risk-Reward Ratio vs MFE
    scatter = sns.scatterplot(
        x='risk_reward_ratio',
        y='MFE',
        data=df_trade_metrics,
        hue='net_profit_loss',
        palette='RdBu',
        linewidth=0.5,
        edgecolor='black',
        s=70,
        alpha=0.7,
        ax=axes[0, 1]
    )
    sns.regplot(x='risk_reward_ratio', y='MFE', data=df_trade_metrics, scatter=False,
                ci=None, color=colors['text'], line_kws={"alpha": 0.7, "lw": 2}, ax=axes[0, 1])
    axes[0, 1].set_title('Risk-Reward Ratio vs MFE')
    scatter.legend_.remove()

    # 3. Risk-Reward Ratio vs Profit Efficiency
    scatter = sns.scatterplot(
        x='risk_reward_ratio',
        y='profit_efficiency',
        data=df_trade_metrics,
        hue='net_profit_loss',
        palette='RdBu',
        linewidth=0.5,
        edgecolor='black',
        s=70,
        alpha=0.7,
        ax=axes[1, 0]
    )
    sns.regplot(x='risk_reward_ratio', y='profit_efficiency', data=df_trade_metrics, scatter=False,
                ci=None, color=colors['text'], line_kws={"alpha": 0.7, "lw": 2}, ax=axes[1, 0])
    axes[1, 0].set_title('Risk-Reward Ratio vs Profit Efficiency')
    scatter.legend_.remove()

    # 4. Risk-Reward Ratio vs Trade Volatility
    scatter = sns.scatterplot(
        x='risk_reward_ratio',
        y='trade_volatility',
        data=df_trade_metrics,
        hue='net_profit_loss',
        palette='RdBu',
        linewidth=0.5,
        edgecolor='black',
        s=70,
        alpha=0.7,
        ax=axes[1, 1]
    )
    sns.regplot(x='risk_reward_ratio', y='trade_volatility', data=df_trade_metrics, scatter=False,
                ci=None, color=colors['text'], line_kws={"alpha": 0.7, "lw": 2}, ax=axes[1, 1])
    axes[1, 1].set_title('Risk-Reward Ratio vs Trade Volatility')
    scatter.legend_.remove()

    plt.suptitle(
        "Relación de Risk-Reward Ratio con Otras Métricas",
        fontsize=14, fontweight='bold', color=colors['text'], y=0.98
    )
    plt.tight_layout(rect=[0, 0, 0.75, 0.95])  
    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f"📊 Gráfico guardado como {save_path}")

    return fig


def visualize_metrics_vs_volatility(df_trade_metrics, save_path=None):
    """
    Genera gráficos de dispersión mostrando la relación entre:
    - Trade Volatility vs MAE
    - Trade Volatility vs MFE
    - Trade Volatility vs Risk-Reward Ratio
    - Trade Volatility vs Profit Efficiency
    """
    colors = apply_dashboard_style()
    required_metrics = ['trade_volatility', 'MAE', 'MFE', 'risk_reward_ratio', 'profit_efficiency']
    missing_metrics = [m for m in required_metrics if m not in df_trade_metrics.columns]
    if missing_metrics:
        print(f"❌ Faltan las siguientes métricas: {', '.join(missing_metrics)}")
        return None

    fig, axes = plt.subplots(2, 2, figsize=(12, 8), gridspec_kw={'wspace': 0.3, 'hspace': 0.3})

    # 1. Trade Volatility vs MAE
    scatter = sns.scatterplot(
        x='trade_volatility',
        y='MAE',
        data=df_trade_metrics,
        hue='net_profit_loss',
        palette='RdBu',
        linewidth=0.5,
        edgecolor='black',
        s=70,
        alpha=0.7,
        ax=axes[0, 0]
    )
    sns.regplot(x='trade_volatility', y='MAE', data=df_trade_metrics, scatter=False,
                ci=None, color=colors['text'], line_kws={"alpha": 0.7, "lw": 2}, ax=axes[0, 0])
    axes[0, 0].set_title('Trade Volatility vs MAE')
    legend = axes[0, 0].legend(
        title="Net Profit/Loss",
        bbox_to_anchor=(1.3, 1),
        loc="upper left",
        borderaxespad=0,
        frameon=True  
    )

    # 2. Trade Volatility vs MFE
    scatter = sns.scatterplot(
        x='trade_volatility',
        y='MFE',
        data=df_trade_metrics,
        hue='net_profit_loss',
        palette='RdBu',
        linewidth=0.5,
        edgecolor='black',
        s=70,
        alpha=0.7,
        ax=axes[0, 1]
    )
    sns.regplot(x='trade_volatility', y='MFE', data=df_trade_metrics, scatter=False,
                ci=None, color=colors['text'], line_kws={"alpha": 0.7, "lw": 2}, ax=axes[0, 1])
    axes[0, 1].set_title('Trade Volatility vs MFE')
    scatter.legend_.remove()

    # 3. Trade Volatility vs Risk-Reward Ratio
    scatter = sns.scatterplot(
        x='trade_volatility',
        y='risk_reward_ratio',
        data=df_trade_metrics,
        hue='net_profit_loss',
        palette='RdBu',
        linewidth=0.5,
        edgecolor='black',
        s=70,
        alpha=0.7,
        ax=axes[1, 0]
    )
    sns.regplot(x='trade_volatility', y='risk_reward_ratio', data=df_trade_metrics, scatter=False,
                ci=None, color=colors['text'], line_kws={"alpha": 0.7, "lw": 2}, ax=axes[1, 0])
    axes[1, 0].set_title('Trade Volatility vs Risk-Reward Ratio')
    scatter.legend_.remove()

    # 4. Trade Volatility vs Profit Efficiency
    scatter = sns.scatterplot(
        x='trade_volatility',
        y='profit_efficiency',
        data=df_trade_metrics,
        hue='net_profit_loss',
        palette='RdBu',
        linewidth=0.5,
        edgecolor='black',
        s=70,
        alpha=0.7,
        ax=axes[1, 1]
    )
    sns.regplot(x='trade_volatility', y='profit_efficiency', data=df_trade_metrics, scatter=False,
                ci=None, color=colors['text'], line_kws={"alpha": 0.7, "lw": 2}, ax=axes[1, 1])
    axes[1, 1].set_title('Trade Volatility vs Profit Efficiency')
    scatter.legend_.remove()

    plt.suptitle(
        "Relación de Trade Volatility con Otras Métricas",
        fontsize=14, fontweight='bold', color=colors['text'], y=0.98
    )
    plt.tight_layout(rect=[0, 0, 0.75, 0.95])  
    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f"📊 Gráfico guardado como {save_path}")

    return fig


def visualize_metrics_vs_profit_efficiency(df_trade_metrics, save_path=None):
    """
    Genera gráficos de dispersión mostrando la relación entre:
    - Profit Efficiency vs MAE
    - Profit Efficiency vs MFE
    - Profit Efficiency vs Risk-Reward Ratio
    - Profit Efficiency vs Trade Volatility
    """
    colors = apply_dashboard_style()
    required_metrics = ['profit_efficiency', 'MAE', 'MFE', 'risk_reward_ratio', 'trade_volatility']
    missing_metrics = [m for m in required_metrics if m not in df_trade_metrics.columns]
    if missing_metrics:
        print(f"❌ Faltan las siguientes métricas: {', '.join(missing_metrics)}")
        return None

    fig, axes = plt.subplots(2, 2, figsize=(12, 8), gridspec_kw={'wspace': 0.3, 'hspace': 0.3})

    # 1. Profit Efficiency vs MAE
    scatter = sns.scatterplot(
        x='profit_efficiency',
        y='MAE',
        data=df_trade_metrics,
        hue='net_profit_loss',
        palette='RdBu',
        linewidth=0.5,
        edgecolor='black',
        s=70,
        alpha=0.7,
        ax=axes[0, 0]
    )
    sns.regplot(x='profit_efficiency', y='MAE', data=df_trade_metrics, scatter=False,
                ci=None, color=colors['text'], line_kws={"alpha": 0.7, "lw": 2}, ax=axes[0, 0])
    axes[0, 0].set_title('Profit Efficiency vs MAE')
    legend = axes[0, 0].legend(
        title="Net Profit/Loss",
        bbox_to_anchor=(1.3, 1),
        loc="upper left",
        borderaxespad=0,
        frameon=True  
    )

    # 2. Profit Efficiency vs MFE
    scatter = sns.scatterplot(
        x='profit_efficiency',
        y='MFE',
        data=df_trade_metrics,
        hue='net_profit_loss',
        palette='RdBu',
        linewidth=0.5,
        edgecolor='black',
        s=70,
        alpha=0.7,
        ax=axes[0, 1]
    )
    sns.regplot(x='profit_efficiency', y='MFE', data=df_trade_metrics, scatter=False,
                ci=None, color=colors['text'], line_kws={"alpha": 0.7, "lw": 2}, ax=axes[0, 1])
    axes[0, 1].set_title('Profit Efficiency vs MFE')
    scatter.legend_.remove()

    # 3. Profit Efficiency vs Risk-Reward Ratio
    scatter = sns.scatterplot(
        x='profit_efficiency',
        y='risk_reward_ratio',
        data=df_trade_metrics,
        hue='net_profit_loss',
        palette='RdBu',
        linewidth=0.5,
        edgecolor='black',
        s=70,
        alpha=0.7,
        ax=axes[1, 0]
    )
    sns.regplot(x='profit_efficiency', y='risk_reward_ratio', data=df_trade_metrics, scatter=False,
                ci=None, color=colors['text'], line_kws={"alpha": 0.7, "lw": 2}, ax=axes[1, 0])
    axes[1, 0].set_title('Profit Efficiency vs Risk-Reward Ratio')
    scatter.legend_.remove()

    # 4. Profit Efficiency vs Trade Volatility
    scatter = sns.scatterplot(
        x='profit_efficiency',
        y='trade_volatility',
        data=df_trade_metrics,
        hue='net_profit_loss',
        palette='RdBu',
        linewidth=0.5,
        edgecolor='black',
        s=70,
        alpha=0.7,
        ax=axes[1, 1]
    )
    sns.regplot(x='profit_efficiency', y='trade_volatility', data=df_trade_metrics, scatter=False,
                ci=None, color=colors['text'], line_kws={"alpha": 0.7, "lw": 2}, ax=axes[1, 1])
    axes[1, 1].set_title('Profit Efficiency vs Trade Volatility')
    scatter.legend_.remove()

    plt.suptitle(
        "Relación de Profit Efficiency con Otras Métricas",
        fontsize=14, fontweight='bold', color=colors['text'], y=0.98
    )
    plt.tight_layout(rect=[0, 0, 0.75, 0.95])  
    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f"📊 Gráfico guardado como {save_path}")

    return fig
