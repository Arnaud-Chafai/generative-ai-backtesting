"""Execute Backtest - Función wrapper compatible con notebooks antiguos"""
from typing import Type, Tuple, Optional
import pandas as pd

from strategies.base_strategy import BaseStrategy
from models.enums import MarketType
from utils.timeframe import Timeframe
from core.backtest_engine import BacktestEngine
from metrics.trade_metrics import TradeMetricsCalculator


def execute_backtest(
    strategy_type: Type[BaseStrategy],
    market: MarketType,
    exchange: str,
    symbol: str,
    timeframe: Timeframe,
    strategy_name: str,
    initial_capital: float = 1000.0,
    fees: bool = True,
    slippage: bool = True,
    strategy_params: Optional[dict] = None,
    number_visualisation: int = 20,
    interval_hours: int = 24,
    show_dashboard: bool = False
) -> Tuple[BaseStrategy, pd.DataFrame]:
    """
    Ejecuta un backtest completo usando el nuevo motor.

    Args:
        strategy_type: Clase de la estrategia
        market: Tipo de mercado (CRYPTO, FUTURES, etc.)
        exchange: Exchange (ej: "Binance")
        symbol: Símbolo del activo (ej: "BTC")
        timeframe: Timeframe de los datos
        strategy_name: Nombre de la estrategia
        initial_capital: Capital inicial
        fees: Activar fees
        slippage: Activar slippage
        strategy_params: Parámetros adicionales de la estrategia
        number_visualisation: (No usado aún)
        interval_hours: (No usado aún)
        show_dashboard: (No usado aún)

    Returns:
        Tuple[BaseStrategy, pd.DataFrame]: (estrategia con señales, métricas de trades)
    """
    strategy_params = strategy_params or {}

    # 1. Crear instancia de la estrategia
    strategy = strategy_type(
        market=market,
        symbol=symbol,
        strategy_name=strategy_name,
        timeframe=timeframe,
        exchange=exchange,
        initial_capital=initial_capital,
        slippage=slippage,
        fees=fees,
        **strategy_params
    )

    # 2. Generar señales
    print(f"[*] Generando señales para {strategy_name}...")
    strategy.generate_signals()
    print(f"[OK] {len(strategy.signals)} señales generadas\n")

    # 3. Ejecutar backtest con el motor
    print(f"[*] Ejecutando backtest...")
    engine = BacktestEngine(initial_capital=initial_capital)
    completed_trades, df_basic = engine.run(strategy.signals)

    if df_basic.empty:
        print("[!] No se completaron trades")
        return strategy, pd.DataFrame()

    # 4. Calcular métricas avanzadas
    print(f"[*] Calculando métricas avanzadas...")
    metrics_calculator = TradeMetricsCalculator(
        initial_capital=initial_capital,
        market_data=strategy.market_data,
        timeframe=strategy.timeframe
    )
    df_metrics = metrics_calculator.create_trade_metrics_df(df_basic)

    print(f"[OK] Backtest completado: {len(completed_trades)} trades\n")

    # TODO: Implementar visualización si show_dashboard=True

    return strategy, df_metrics
