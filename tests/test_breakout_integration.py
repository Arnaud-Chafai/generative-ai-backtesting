"""
Test de integración para el notebook breakout.ipynb
Ejecuta la estrategia completa y verifica que los resultados son correctos.
"""

import pytest
import pandas as pd
from datetime import datetime, time, timedelta
from strategies.base_strategy import BaseStrategy
from models.enums import SignalType, OrderType, MarketType
from utils.timeframe import Timeframe
from core.executor import execute_backtest


class AmericanOpenTripleBuyStrategy(BaseStrategy):
    """
    Estrategia que compra 3 veces al día a horarios fijos y vende 1 hora después.
    Copiada del notebook breakout.ipynb para testing.
    """
    def __init__(self, market, symbol, strategy_name, timeframe, exchange,
                 initial_capital=1000.0, slippage=True, fees=True,
                 volume_pct=0.1):
        super().__init__(market, symbol, strategy_name, timeframe, exchange, initial_capital, slippage, fees)

        self.volume_pct = volume_pct
        self.buy_times = [time(15, 30), time(15, 45), time(16, 0)]
        self.sell_time_by_day = {}
        self.buys_by_day = {}

    def generate_signals(self) -> None:
        df = self.market_data.copy()
        df = df.sort_index()

        for i in range(len(df)):
            row = df.iloc[i]
            timestamp = df.index[i]
            current_date = timestamp.date()
            current_time = timestamp.time()
            close = row["Close"]

            # Verifica si toca hacer una compra (3 horarios fijos por día)
            if current_time in self.buy_times:
                self.buys_by_day.setdefault(current_date, [])
                if len(self.buys_by_day[current_date]) < 3:
                    self.create_crypto_signal(
                        signal_type=SignalType.BUY,
                        order_type=OrderType.MARKET,
                        volume_pct=self.volume_pct,
                        timestamp=timestamp,
                        price=close
                    )
                    self.buys_by_day[current_date].append(timestamp)

                    # Si es la 3ra compra, agenda la venta 1 hora después
                    if len(self.buys_by_day[current_date]) == 3:
                        self.sell_time_by_day[current_date] = timestamp + timedelta(hours=1)

            # Ejecutar venta si es hora
            if current_date in self.sell_time_by_day:
                sell_time = self.sell_time_by_day[current_date]
                if timestamp >= sell_time:
                    self.create_crypto_signal(
                        signal_type=SignalType.SELL,
                        order_type=OrderType.MARKET,
                        volume_pct=self.volume_pct * 3,
                        timestamp=timestamp,
                        price=close
                    )
                    # Limpiar para que no vuelva a vender ese día
                    del self.sell_time_by_day[current_date]
                    del self.buys_by_day[current_date]


@pytest.mark.integration
@pytest.mark.slow
def test_breakout_notebook_execution():
    """
    Test de integración: Ejecuta la estrategia completa del notebook
    y verifica que produce resultados válidos.

    Requiere: data/laboratory_data/BTC/Timeframe.M5.csv
    """
    try:
        # Ejecutar el backtest igual que en el notebook
        strategy, df_metrics = execute_backtest(
            strategy_type=AmericanOpenTripleBuyStrategy,
            market=MarketType.CRYPTO,
            exchange="Binance",
            symbol="BTC",
            timeframe=Timeframe.M5,
            strategy_name="PremarketReentryShort_BTC_M15",
            initial_capital=1000.0,
            fees=True,
            slippage=True,
            strategy_params={
                "volume_pct": 0.1
            },
            number_visualisation=20,
            interval_hours=24,
            show_dashboard=False
        )

        # ============================================
        # Verificaciones del DataFrame de métricas
        # ============================================

        # 1. El DataFrame no debe estar vacío
        assert len(df_metrics) > 0, "El DataFrame de métricas está vacío"
        print(f"✅ Total de trades: {len(df_metrics)}")

        # 2. Verificar columnas esperadas
        expected_columns = [
            'entry_timestamp', 'exit_timestamp', 'market', 'exchange', 'symbol',
            'entry_price', 'exit_price', 'usdt_amount', 'fees', 'slippage_cost',
            'gross_profit_loss', 'net_profit_loss', 'cumulative_capital'
        ]
        for col in expected_columns:
            assert col in df_metrics.columns, f"Falta la columna: {col}"
        print(f"✅ Todas las columnas esperadas presentes")

        # 3. Verificar tipos de datos básicos
        assert df_metrics['entry_timestamp'].dtype == 'datetime64[ns]'
        assert df_metrics['exit_timestamp'].dtype == 'datetime64[ns]'
        assert pd.api.types.is_numeric_dtype(df_metrics['entry_price'])
        assert pd.api.types.is_numeric_dtype(df_metrics['exit_price'])
        print(f"✅ Tipos de datos correctos")

        # 4. Verificar que todos los trades tienen precios válidos
        assert (df_metrics['entry_price'] > 0).all(), "Hay precios de entrada <= 0"
        assert (df_metrics['exit_price'] > 0).all(), "Hay precios de salida <= 0"
        print(f"✅ Todos los precios son válidos (> 0)")

        # 5. Verificar que exit_timestamp > entry_timestamp
        time_diff = (df_metrics['exit_timestamp'] - df_metrics['entry_timestamp']).dt.total_seconds()
        assert (time_diff > 0).all(), "Hay trades con exit antes de entry"
        print(f"✅ Todas las salidas son después de las entradas")

        # 6. Verificar market y exchange
        assert (df_metrics['market'] == 'Crypto').all()
        assert (df_metrics['exchange'] == 'Binance').all()
        assert (df_metrics['symbol'] == 'BTC').all()
        print(f"✅ Market, exchange y symbol correctos")

        # 7. Verificar que hay fees y slippage (si están activadas)
        assert (df_metrics['fees'] >= 0).all(), "Hay fees negativas"
        assert (df_metrics['slippage_cost'] >= 0).all(), "Hay slippage negativo"
        print(f"✅ Fees y slippage son no negativos")

        # ============================================
        # Verificaciones de la estrategia
        # ============================================

        # 8. Verificar que la estrategia generó señales
        assert len(strategy.signals) > 0, "La estrategia no generó señales"
        print(f"✅ Señales generadas: {len(strategy.signals)}")

        # 9. Verificar que hay señales BUY y SELL
        buy_signals = [s for s in strategy.signals if s.signal_type == SignalType.BUY]
        sell_signals = [s for s in strategy.signals if s.signal_type == SignalType.SELL]

        assert len(buy_signals) > 0, "No hay señales de compra"
        assert len(sell_signals) > 0, "No hay señales de venta"
        print(f"✅ Señales BUY: {len(buy_signals)}, SELL: {len(sell_signals)}")

        # 10. Verificar ratio de señales (debe haber ~3 BUY por cada SELL)
        buy_sell_ratio = len(buy_signals) / len(sell_signals) if len(sell_signals) > 0 else 0
        assert 2.5 <= buy_sell_ratio <= 3.5, f"Ratio BUY/SELL inesperado: {buy_sell_ratio:.2f}"
        print(f"✅ Ratio BUY/SELL: {buy_sell_ratio:.2f} (esperado ~3.0)")

        # ============================================
        # Verificaciones de capital
        # ============================================

        # 11. Verificar capital inicial
        initial_capital = 1000.0
        assert strategy.initial_capital == initial_capital
        print(f"✅ Capital inicial: ${initial_capital}")

        # 12. Verificar capital acumulado (debe ser coherente)
        final_capital = df_metrics['cumulative_capital'].iloc[-1]
        assert final_capital > 0, "Capital final es negativo o cero"
        print(f"✅ Capital final: ${final_capital:.2f}")

        # 13. Calcular retorno total
        total_return = ((final_capital - initial_capital) / initial_capital) * 100
        print(f"✅ Retorno total: {total_return:.2f}%")

        # ============================================
        # Verificaciones de métricas
        # ============================================

        # 14. Verificar que net_profit_loss = gross_profit_loss - fees - slippage
        calculated_net = df_metrics['gross_profit_loss'] - df_metrics['fees'] - df_metrics['slippage_cost']
        net_diff = abs(df_metrics['net_profit_loss'] - calculated_net)
        assert (net_diff < 0.01).all(), "Cálculo de net_profit_loss incorrecto"
        print(f"✅ Cálculo de net_profit_loss correcto")

        # 15. Verificar que hay métricas adicionales (MAE, MFE, etc.)
        if 'MAE' in df_metrics.columns:
            assert (df_metrics['MAE'] >= 0).all(), "MAE negativo"
            print(f"✅ MAE promedio: {df_metrics['MAE'].mean():.2f}%")

        if 'MFE' in df_metrics.columns:
            assert (df_metrics['MFE'] >= 0).all(), "MFE negativo"
            print(f"✅ MFE promedio: {df_metrics['MFE'].mean():.2f}%")

        # ============================================
        # Resumen final
        # ============================================
        print("\n" + "="*60)
        print("RESUMEN DEL TEST DE INTEGRACIÓN")
        print("="*60)
        print(f"✅ Total de trades ejecutados: {len(df_metrics)}")
        print(f"✅ Señales generadas: {len(strategy.signals)} (BUY: {len(buy_signals)}, SELL: {len(sell_signals)})")
        print(f"✅ Capital inicial: ${initial_capital:.2f}")
        print(f"✅ Capital final: ${final_capital:.2f}")
        print(f"✅ Retorno total: {total_return:.2f}%")
        print(f"✅ Trades ganadores: {(df_metrics['net_profit_loss'] > 0).sum()}")
        print(f"✅ Trades perdedores: {(df_metrics['net_profit_loss'] < 0).sum()}")
        print(f"✅ Win rate: {(df_metrics['net_profit_loss'] > 0).mean() * 100:.2f}%")
        print("="*60)

    except FileNotFoundError as e:
        pytest.skip(f"Archivo de datos no encontrado: {e}")
    except Exception as e:
        pytest.fail(f"Error durante la ejecución del backtest: {e}")


@pytest.mark.integration
def test_strategy_with_minimal_data():
    """
    Test más simple que verifica solo la generación de señales
    sin ejecutar el backtest completo.
    """
    # Este test podríamos ejecutarlo con datos de prueba
    pytest.skip("Pendiente: crear datos de prueba mínimos")
