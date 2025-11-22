# Generative AI Backtesting Framework

Framework de backtesting para estrategias de trading algorítmico con soporte para múltiples mercados (Crypto, Futures, Stocks) y futura integración de agentes de IA generativa para operaciones mediante lenguaje natural.

## 🎯 Visión del Proyecto

Este proyecto está diseñado en dos fases:

**Fase 1 (Actual):** Framework robusto de backtesting con métricas avanzadas, visualizaciones y soporte multi-mercado.

**Fase 2 (Futura):** Integración de agentes de IA generativa que permitan realizar operaciones de compra/venta mediante lenguaje natural, automatizando la toma de decisiones basándose en análisis de datos históricos y patrones de mercado.

## ✨ Características

### Funcionalidades Actuales (Fase 1-3 Completas)

- ✅ **Motor de Backtest Robusto:** 280 líneas limpias, optimizado y funcional
- ✅ **Soporte Multi-Mercado:** Crypto (con extensión futura a Futures y Stocks)
- ✅ **Sistema de Tipos:** Validación con Pydantic, enums robustos
- ✅ **30+ Métricas Avanzadas:**
  - Por Trade: MAE, MFE, Profit Efficiency, Risk/Reward
  - Portfolio: Sharpe, Sortino, Profit Factor, Max Drawdown
  - Operacionales: Fees, Slippage, Win Rate, etc.
- ✅ **Visualización Completa:**
  - Gráficos de velas con entrada/salida marcadas
  - 10 dashboards interactivos (performance, scatter plots, heatmaps)
  - Análisis temporal por día/mes
  - Distribuciones y boxplots de métricas
- ✅ **Preparación de Datos:** Limpieza y transformación automática
- ✅ **Notebook Interactivo:** Ejemplo completo con flujo end-to-end

### Roadmap Fase 2 (IA Generativa)

- 🔮 Agentes conversacionales para análisis de mercado
- 🔮 Sistema de decisión autónomo basado en LLMs
- 🔮 Generación de estrategias mediante lenguaje natural
- 🔮 Optimización automática de parámetros con IA
- 🔮 Análisis predictivo con modelos generativos

## Instalación

### Requisitos previos

- Python 3.10 o superior
- uv (gestor de paquetes)

### Instalación con uv

```bash
# Crear entorno virtual
uv venv

# Activar entorno virtual
source .venv/Scripts/activate  # Windows
source .venv/bin/activate       # Linux/Mac

# Instalar dependencias
uv pip install -e .

# Para desarrollo (incluye pytest, black, ruff)
uv pip install -e ".[dev]"
```

## 📁 Estructura del Proyecto

```
backtesting/
├── 📦 models/              # Modelos de datos con Pydantic
│   ├── markets/            # Definiciones de mercados (Crypto, Futures)
│   ├── trades/             # Modelos de trades por tipo de mercado
│   ├── signals.py          # Señales de trading
│   └── enums.py            # Enumeraciones del sistema
├── ⚙️ config/              # Configuraciones por mercado
│   └── market_configs/     # Configs específicas (fees, leverage, etc.)
├── 🎯 strategies/          # Estrategias de trading
│   └── base_strategy.py    # Clase base para estrategias personalizadas
├── 📊 data/                # Gestión de datos
│   ├── loaders/            # Carga de datos desde fuentes
│   └── preparation/        # Limpieza y transformación
├── 🚀 core/                # Motor de backtest
│   ├── backtest_engine.py  # Engine principal
│   ├── executor.py         # Ejecución de trades
│   └── position_manager.py # Gestión de posiciones
├── 📈 metrics/             # Métricas de rendimiento
│   ├── portfolio_metrics.py # Métricas de portafolio
│   └── trade_metrics.py    # Métricas por trade
├── 📉 visualization/       # Visualización y dashboards
│   ├── dashboards/         # Dashboards especializados
│   ├── chart_plotter.py    # Gráficos de trades
│   └── dashboard_manager.py # Gestión de dashboards
├── 🛠️ utils/              # Utilidades generales
├── 📓 notebooks/           # Análisis exploratorios
├── 🧪 tests/               # Suite de tests
└── 📚 docs/                # Documentación técnica
```

## 🚀 Uso Rápido

### Flujo Completo en 10 Líneas

```python
from strategies.examples.breakout_simple import BreakoutSimple
from core.backtest_runner import BacktestRunner
from utils.timeframe import Timeframe

# 1. Configurar estrategia
strategy = BreakoutSimple(
    symbol="BTC",
    timeframe=Timeframe.M5,
    exchange="Binance",
    lookback_period=20,
    position_size_pct=0.25,
    initial_capital=1000.0
)

# 2. Ejecutar backtest completo
runner = BacktestRunner(strategy)
runner.run()

# 3. Ver resumen de métricas
runner.print_summary()

# 4. Visualizar trades en gráficos
runner.plot_trades(interval_hours=24, number_visualisation=5)

# 5. Generar dashboards de análisis
runner.plot_dashboards(
    modules=['performance', 'metrics_boxplot', 'mae_scatter', 'mfe_scatter'],
    show=True
)

# 6. Acceder a datos brutos
df_trades = runner.metrics.trade_metrics_df
all_metrics = runner.metrics.all_metrics
```

### Crear tu Propia Estrategia

```python
from strategies.base_strategy import BaseStrategy
from models.simple_signals import TradingSignal
from models.enums import SignalType
from utils.timeframe import Timeframe

class MyStrategy(BaseStrategy):
    def generate_simple_signals(self):
        """Genera señales de trading"""
        signals = []
        df = self.market_data

        # Implementa tu lógica aquí
        df['SMA_20'] = df['close'].rolling(20).mean()

        for i in range(20, len(df)):
            if df['close'].iloc[i] > df['SMA_20'].iloc[i]:
                signals.append(TradingSignal(
                    timestamp=df.index[i],
                    signal_type=SignalType.BUY,
                    price=df['close'].iloc[i]
                ))

        return signals

# Usar tu estrategia
strategy = MyStrategy(
    symbol="BTC",
    timeframe=Timeframe.H1,
    exchange="Binance",
    initial_capital=5000
)
runner = BacktestRunner(strategy)
runner.run()
```

## 📚 Documentación

- **[Roadmap Técnico](CLAUDE.md)** - Planeación y visión del proyecto
- **[Resumen Fase 3](docs/FASE3_RESUMEN.md)** - Visualización y dashboards (ACTUAL)
- **[Diccionario de Datos](docs/data_dictionary.md)** - Estructura de datos
- **[API Reference](#)** - Documentación de APIs (próximamente)

## 🏗️ Estado del Proyecto

**Versión Actual**: `0.3.0` (Fase 4a Completada)

### Fase 1: Framework de Backtesting ✅ COMPLETADO
- ✅ Arquitectura modular con Pydantic
- ✅ Motor de backtest (280 líneas optimizadas)
- ✅ Sistema de métricas completo (30+ métricas)
- ✅ Soporte Crypto (extensible a Futures/Stocks)
- ✅ Gestión de posiciones y trades

### Fase 2: Sistema de Visualización ✅ COMPLETADO
- ✅ Visualización de trades con candles
- ✅ 10 dashboards interactivos
- ✅ Scatter plots y análisis temporal
- ✅ Distribuciones y boxplots
- ✅ Notebook ejemplo funcional

### Fase 3: Optimización de Parámetros ✅ PARCIALMENTE (v1.0)

#### Completado:
- ✅ Grid Search automático
- ✅ Inyección de datos (200x más rápido)
- ✅ Validación inteligente de parámetros
- ✅ Filtro anti-fantasma (min_trades)
- ✅ Barra de progreso con tqdm
- ✅ Export a CSV
- ✅ 7 tests comprensivos
- ✅ Documentación OPTIMIZER_GUIDE.md

#### Próximo (v1.5):
- ⏳ Random Search (espacios grandes)
- ⏳ Bayesian Optimization (más inteligente)
- ⏳ Walk-Forward Testing (v2.0)
- ⏳ Multiprocessing (paralelizar)

### Fase 4: Comparación de Estrategias (SIGUIENTE)
- ⏳ Comparador de estrategias
- ⏳ Análisis de sensibilidad
- ⏳ Backtesting robusto multi-período

### Fase 5: Integración IA Generativa (FUTURO)
- 🔮 Agentes conversacionales para análisis
- 🔮 Generación de estrategias con LLMs
- 🔮 Optimización con IA
- 🔮 Sistema de toma de decisiones autónomo

## 🤝 Contribuciones

Las contribuciones son bienvenidas! Este proyecto está en desarrollo activo y cualquier ayuda es apreciada.

### Áreas de Interés
- Optimización del motor de backtest
- Nuevas estrategias de ejemplo
- Mejoras en visualizaciones
- Tests y documentación
- Ideas para integración con IA generativa

## 📝 Licencia

MIT License - Ver archivo LICENSE para más detalles.

## 🔗 Enlaces

- **Repositorio:** [github.com/Arnaud-Chafai/generative-ai-backtesting](https://github.com/Arnaud-Chafai/generative-ai-backtesting)
- **Issues:** [Reportar problemas o sugerencias](https://github.com/Arnaud-Chafai/generative-ai-backtesting/issues)

---

**Nota:** Este es un proyecto educativo y de investigación. No constituye asesoramiento financiero. Úsalo bajo tu propia responsabilidad.
