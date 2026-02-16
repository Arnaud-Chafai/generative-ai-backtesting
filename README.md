# Backtesting Framework

Framework de backtesting para estrategias de trading algoritmico en crypto. Motor de ejecucion con soporte para multiples entradas (DCA), 30+ metricas, 10 dashboards de analisis y optimizacion de parametros.

## Uso rapido

```python
from strategies.examples.breakout_simple import BreakoutSimple
from core.backtest_runner import BacktestRunner

# Crear estrategia y ejecutar
strategy = BreakoutSimple(symbol="BTC", exchange="Binance", lookback_period=20)
runner = BacktestRunner(strategy)
runner.run()

# Resultados
runner.print_summary()
runner.plot_trades()        # chart interactivo de velas
runner.plot_dashboards()    # 10 dashboards de analisis
```

## Descargar datos

```python
from data.loaders.data_provider import CcxtDataProvider

provider = CcxtDataProvider(symbol="BTC/USDT", timeframe="5m", start_date="2024-01-01")
provider.save_to_csv()  # guarda en data/raw_data/BTCUSDT_5m.csv
```

## Optimizar parametros

```python
from optimization import ParameterOptimizer

optimizer = ParameterOptimizer(
    strategy_class=BreakoutSimple, market_data=df,
    symbol='BTC', exchange='Binance'
)
results = optimizer.optimize(
    param_ranges={'lookback_period': [10, 20, 30, 50], 'position_size_pct': [0.3, 0.5, 0.7]},
    metric='sharpe_ratio'
)
best = optimizer.get_best_params(min_trades=20)
```

## Crear una estrategia

```python
from strategies.base_strategy import BaseStrategy
from models.enums import SignalType, MarketType
from utils.timeframe import Timeframe

class MiEstrategia(BaseStrategy):
    def __init__(self, mi_param: int = 20, **kwargs):
        super().__init__(
            market=MarketType.CRYPTO, symbol=kwargs.get('symbol', 'BTC'),
            strategy_name="Mi_Estrategia", timeframe=kwargs.get('timeframe', Timeframe.H1),
            exchange=kwargs.get('exchange', 'Binance'), **kwargs
        )
        self.mi_param = mi_param

    def generate_simple_signals(self):
        signals = []
        df = self.market_data
        for i in range(self.mi_param, len(df)):
            if condicion_compra:
                signals.append(self.create_simple_signal(
                    SignalType.BUY, df.index[i], df['Close'].iloc[i], 0.5
                ))
            elif condicion_venta:
                signals.append(self.create_simple_signal(
                    SignalType.SELL, df.index[i], df['Close'].iloc[i], 1.0
                ))
        return signals
```

## Estructura del proyecto

```
backtesting/
├── core/                    Motor de backtest + orquestador
├── models/                  Enums (SignalType) y TradingSignal
├── config/
│   ├── market_configs/      Fees, slippage, tick_size por exchange
│   └── markets/             Clases de definicion de mercados
├── data/
│   ├── loaders/             CSV, MT5, ccxt (Binance)
│   └── preparation/         DataCleaner + DataTransformer
├── metrics/                 30+ metricas (trade + portfolio)
├── strategies/              BaseStrategy + ejemplos
├── optimization/            Grid Search + visualizacion 3D
├── visualization/           Charts de velas + 10 dashboards
├── utils/                   Timeframe enum
├── tests/                   pytest
└── notebooks/               Ejemplos interactivos
```

Cada modulo tiene un `CLAUDE.md` con documentacion detallada. Ver [CLAUDE.md](CLAUDE.md) para el indice completo.

## Metricas disponibles

**Por trade:** MAE, MFE, duration_bars, bars_in_profit/loss, profit_efficiency, risk_reward_ratio, trade_volatility, trade_drawdown

**Portfolio:** Sharpe ratio, Sortino ratio, Profit Factor, Max Drawdown, Recovery Factor, Expectancy, ROI, Win Rate

**Operacionales:** Total fees, slippage cost, avg fee per trade, costs as % of profit

## Dashboards

10 dashboards disponibles via `runner.plot_dashboards()`:

`performance`, `time_chart`, `temporal`, `metrics_distribution`, `metrics_boxplot`, `mae_scatter`, `mfe_scatter`, `risk_reward_scatter`, `volatility_scatter`, `profit_efficiency_scatter`

## Instalacion

```bash
python -m venv .venv
source .venv/Scripts/activate   # Windows
pip install -r requirements.txt
pip install ccxt                # opcional, para descargar datos de Binance
```

## Estado

| Fase | Descripcion | Estado |
|------|-------------|--------|
| 1-2 | Motor de backtest + metricas | Completado |
| 3 | Visualizacion (charts + 10 dashboards) | Completado |
| 4a | Optimizador Grid Search + viz 3D | Completado |
| 4b | Random Search + Bayesian | Pendiente |
| 5 | Mas estrategias | Pendiente |

---

Proyecto educativo y de investigacion. No constituye asesoramiento financiero.
