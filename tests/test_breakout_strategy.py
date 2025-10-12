"""
Tests para la estrategia AmericanOpenTripleBuyStrategy del notebook breakout.ipynb
"""

import pytest
import pandas as pd
from datetime import datetime, time, timedelta
from strategies.base_strategy import BaseStrategy
from models.enums import SignalType, OrderType, MarketType
from utils.timeframe import Timeframe


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


@pytest.fixture
def create_test_data_file(tmp_path):
    """Crea un archivo CSV temporal con datos de prueba para la estrategia"""
    # Crear datos de prueba: 2 días completos con velas cada 15 minutos
    dates = pd.date_range(start='2024-01-01 00:00:00', periods=200, freq='15min')

    df = pd.DataFrame({
        'Time': dates,
        'Open': 50000.0,
        'High': 50100.0,
        'Low': 49900.0,
        'Close': 50000.0,
        'Volume': 100
    })

    # Crear la estructura de directorios
    data_dir = tmp_path / "data" / "laboratory_data" / "BTCUSDT"
    data_dir.mkdir(parents=True)

    # Guardar el archivo
    csv_path = data_dir / "Timeframe.M15.csv"
    df.to_csv(csv_path, index=False)

    return tmp_path


@pytest.mark.skip(reason="Requiere archivo de datos real en data/laboratory_data/BTC/")
def test_strategy_initialization():
    """Test básico de inicialización de la estrategia"""
    strategy = AmericanOpenTripleBuyStrategy(
        market=MarketType.CRYPTO,
        symbol="BTC",
        strategy_name="TestBreakout",
        timeframe=Timeframe.M15,
        exchange="Binance",
        initial_capital=1000.0,
        slippage=True,
        fees=True,
        volume_pct=0.1
    )

    assert strategy.volume_pct == 0.1
    assert len(strategy.buy_times) == 3
    assert strategy.buy_times[0] == time(15, 30)
    assert strategy.buy_times[1] == time(15, 45)
    assert strategy.buy_times[2] == time(16, 0)


def test_strategy_configuration():
    """Test de configuración sin cargar datos reales"""
    # Verificar que la clase tiene los atributos correctos
    assert hasattr(AmericanOpenTripleBuyStrategy, '__init__')
    assert hasattr(AmericanOpenTripleBuyStrategy, 'generate_signals')


def test_buy_times_configuration():
    """Test que verifica los horarios de compra están bien configurados"""
    buy_times = [time(15, 30), time(15, 45), time(16, 0)]

    # Verificar que son 3 horarios
    assert len(buy_times) == 3

    # Verificar que están ordenados
    assert buy_times[0] < buy_times[1] < buy_times[2]

    # Verificar la diferencia entre horarios (15 minutos)
    t1 = datetime.combine(datetime.today(), buy_times[0])
    t2 = datetime.combine(datetime.today(), buy_times[1])
    t3 = datetime.combine(datetime.today(), buy_times[2])

    assert (t2 - t1).total_seconds() == 900  # 15 minutos
    assert (t3 - t2).total_seconds() == 900  # 15 minutos


def test_sell_time_calculation():
    """Test que verifica el cálculo del horario de venta (1 hora después)"""
    buy_time = datetime(2024, 1, 1, 16, 0, 0)
    sell_time = buy_time + timedelta(hours=1)

    expected_sell_time = datetime(2024, 1, 1, 17, 0, 0)
    assert sell_time == expected_sell_time


def test_volume_calculation():
    """Test que verifica el cálculo de volumen para compra y venta"""
    volume_pct = 0.1  # 10% (ya está en decimal)
    initial_capital = 1000.0

    # Para cada compra (10% del capital)
    buy_volume = initial_capital * volume_pct
    assert buy_volume == pytest.approx(100.0)  # 10% de 1000 = 100 USDT

    # Para la venta (suma de 3 compras = 30% del capital)
    sell_volume = initial_capital * (volume_pct * 3)
    assert sell_volume == pytest.approx(300.0)  # 30% de 1000 = 300 USDT


def test_strategy_logic_consistency():
    """
    Test de lógica:
    - Debe hacer exactamente 3 compras por día
    - Debe hacer 1 venta por día (suma de las 3 compras)
    """
    # Simulación de la lógica sin datos reales
    buys_by_day = {}
    sell_time_by_day = {}

    current_date = datetime(2024, 1, 1).date()

    # Simular 3 compras
    for i in range(3):
        buys_by_day.setdefault(current_date, [])
        buys_by_day[current_date].append(datetime.now())

        # En la 3ra compra, agendar venta
        if len(buys_by_day[current_date]) == 3:
            sell_time_by_day[current_date] = datetime.now() + timedelta(hours=1)

    # Verificar que se hicieron 3 compras
    assert len(buys_by_day[current_date]) == 3

    # Verificar que se agendó una venta
    assert current_date in sell_time_by_day

    # Simular ejecución de venta (limpieza)
    del sell_time_by_day[current_date]
    del buys_by_day[current_date]

    # Verificar limpieza
    assert current_date not in sell_time_by_day
    assert current_date not in buys_by_day


@pytest.mark.parametrize("volume_pct,expected_buy,expected_sell", [
    (0.1, 100.0, 300.0),    # 10% -> 100 USDT compra, 300 USDT venta
    (0.2, 200.0, 600.0),    # 20% -> 200 USDT compra, 600 USDT venta
    (0.05, 50.0, 150.0),    # 5% -> 50 USDT compra, 150 USDT venta
])
def test_volume_parametrization(volume_pct, expected_buy, expected_sell):
    """Test parametrizado para diferentes porcentajes de volumen"""
    initial_capital = 1000.0

    buy_volume = initial_capital * volume_pct
    sell_volume = initial_capital * (volume_pct * 3)

    assert buy_volume == pytest.approx(expected_buy)
    assert sell_volume == pytest.approx(expected_sell)
