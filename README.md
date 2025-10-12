# Generative AI Backtesting Framework

Framework de backtesting para estrategias de trading algorítmico con soporte para múltiples mercados (Crypto, Futures, Stocks) y futura integración de agentes de IA generativa para operaciones mediante lenguaje natural.

## 🎯 Visión del Proyecto

Este proyecto está diseñado en dos fases:

**Fase 1 (Actual):** Framework robusto de backtesting con métricas avanzadas, visualizaciones y soporte multi-mercado.

**Fase 2 (Futura):** Integración de agentes de IA generativa que permitan realizar operaciones de compra/venta mediante lenguaje natural, automatizando la toma de decisiones basándose en análisis de datos históricos y patrones de mercado.

## ✨ Características

### Funcionalidades Actuales (Fase 1)

- ✅ **Multi-Mercado:** Soporte completo para Crypto, Futures y Stocks
- ✅ **Sistema de Tipos Robusto:** Validación automática con Pydantic
- ✅ **Métricas Avanzadas:**
  - MAE (Maximum Adverse Excursion)
  - MFE (Maximum Favorable Excursion)
  - Sharpe Ratio, Sortino Ratio
  - Profit Factor, Win Rate
  - Drawdown máximo y promedio
  - Y muchas más...
- ✅ **Visualización Profesional:** Dashboards interactivos con gráficos de rendimiento
- ✅ **Preparación de Datos:** Limpieza y transformación automática
- ✅ **Gestión de Posiciones:** Sistema completo de position management
- ⚠️ **Motor de Backtest:** En desarrollo y optimización continua

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

### Ejemplo Básico: Crear una Estrategia

```python
from models.enums import SignalType, MarketType
from models.markets.crypto_market import CryptoMarketDefinition
from strategies.base_strategy import BaseStrategy
from utils.timeframe import Timeframe
import pandas as pd

# 1. Crear tu estrategia personalizada
class MyBreakoutStrategy(BaseStrategy):
    def generate_signals(self, df: pd.DataFrame):
        """Genera señales de compra/venta basadas en breakouts"""
        signals = []

        # Tu lógica de estrategia aquí
        # Ejemplo: Breakout de SMA 20
        df['SMA_20'] = df['close'].rolling(20).mean()

        for i in range(len(df)):
            if df['close'].iloc[i] > df['SMA_20'].iloc[i]:
                signals.append({
                    'type': SignalType.LONG,
                    'timestamp': df.index[i],
                    'price': df['close'].iloc[i]
                })

        return signals

# 2. Configurar y ejecutar backtest
strategy = MyBreakoutStrategy(
    market=MarketType.CRYPTO,
    symbol="BTC",
    strategy_name="breakout_sma20",
    timeframe=Timeframe.H1,
    initial_capital=10000
)

# 3. Ejecutar backtest
results = strategy.run_backtest(data)

# 4. Visualizar resultados
strategy.plot_results()
strategy.generate_dashboard()
```

### Métricas Disponibles

```python
# Obtener métricas del backtest
metrics = results.get_metrics()

print(f"Profit Factor: {metrics['profit_factor']}")
print(f"Sharpe Ratio: {metrics['sharpe_ratio']}")
print(f"Win Rate: {metrics['win_rate']}%")
print(f"Max Drawdown: {metrics['max_drawdown']}%")
```

## 📚 Documentación

- **[Documentación Completa](docs/CLAUDE.md)** - Guía detallada del framework
- **[Diccionario de Datos](docs/data_dictionary.md)** - Estructura de datos y modelos
- **[Plan de Refactorización](docs/REFACTORING_PLAN.md)** - Roadmap técnico
- **[Resumen Fase 1](docs/FASE1_RESUMEN.md)** - Estado actual del proyecto

## 🏗️ Estado del Proyecto

**Versión Actual**: `0.1.0` (En desarrollo activo)

### Fase 1: Framework de Backtesting (En progreso)
- ✅ Arquitectura modular con Pydantic
- ✅ Soporte multi-mercado (Crypto, Futures)
- ✅ Sistema de métricas completo (30+ métricas)
- ✅ Visualizaciones y dashboards interactivos
- ✅ Gestión de posiciones y trades
- ⚠️ Motor de backtest (optimización continua)
- ⏳ Cobertura de tests (en expansión)

### Fase 2: Integración IA Generativa (Planificado)
- 🔮 Investigación de arquitectura de agentes
- 🔮 Diseño de API conversacional
- 🔮 Integración con LLMs (GPT-4, Claude, etc.)
- 🔮 Sistema de toma de decisiones autónomo
- 🔮 Generación automática de estrategias

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
