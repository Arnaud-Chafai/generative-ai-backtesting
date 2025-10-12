# 📋 PROYECTO MT5_Framework - Guía Completa

**Fecha última actualización**: 2025-10-11 23:45
**Estado**: ✅ **FASE 1 COMPLETADA AL 100%** - Todos los tests pasando

---

## 🎯 RESUMEN EJECUTIVO

Este es un **framework de backtesting** para estrategias de trading algorítmico.

### Características principales:
- ✅ Soporte para múltiples mercados (Crypto, Futures, Stocks)
- ✅ Sistema de tipos con Pydantic (validación automática)
- ✅ Métricas detalladas (MAE, MFE, Sharpe, Profit Factor, etc.)
- ✅ Visualización avanzada con dashboards
- ✅ Preparación y transformación de datos
- ⚠️ Motor de backtest simplificado (en desarrollo)

---

## 📂 ESTRUCTURA ACTUAL

```
backtesting/
│
├── 📁 models/                              # Modelos de datos (Pydantic)
│   ├── enums.py                            # ✅ SignalType, MarketType, OrderType, etc.
│   ├── signals.py                          # ✅ StrategySignal
│   │
│   ├── markets/                            # Definiciones de mercado
│   │   ├── __init__.py
│   │   ├── base_market.py                  # BaseMarketDefinition
│   │   ├── crypto_market.py                # ✅ CryptoMarketDefinition
│   │   └── futures_market.py               # FuturesMarketDefinition
│   │
│   └── trades/                             # Modelos de trades
│       ├── __init__.py
│       ├── base_trade.py                   # Trade base
│       ├── crypto_trade.py                 # ✅ CryptoTrade
│       └── futures_trade.py                # FuturesTrade
│
├── 📁 config/                              # Configuraciones
│   └── market_configs/
│       └── crypto_config.py                # ✅ Configuración de exchanges
│
├── 📁 strategies/                          # Estrategias de trading
│   ├── __init__.py
│   └── base_strategy.py                    # ⚠️ BaseStrategy (imports a actualizar)
│
├── 📁 data/                                # Carga y preparación de datos
│   ├── loaders/
│   │   └── data_provider.py                # ⚠️ CSV/MT5 loaders (imports a actualizar)
│   │
│   └── preparation/
│       ├── data_transformer.py             # ⚠️ DataTransformer (imports a actualizar)
│       └── data_cleaner.py                 # ⚠️ DataCleaner (imports a actualizar)
│
├── 📁 core/                                # ⚠️ VACÍO - Motor de backtest a implementar
│   # Aquí irá:
│   # - backtest_engine.py
│   # - position_manager.py
│   # - metrics_calculator.py
│
├── 📁 metrics/                             # Cálculo de métricas
│   ├── trade_metrics.py                    # ⚠️ TradeMetricsCalculator (imports a actualizar)
│   └── portfolio_metrics.py                # ⚠️ BacktestMetrics (imports a actualizar)
│
├── 📁 visualization/                       # Visualización de resultados
│   ├── chart_plotter.py                    # ⚠️ ChartVisualizer (imports a actualizar)
│   ├── dashboard_manager.py                # ⚠️ DashboardManager (imports a actualizar)
│   └── dashboards/                         # ⚠️ Dashboards individuales (imports a actualizar)
│       ├── performance_dashboard.py
│       ├── scatter_metrics.py
│       ├── metrics_boxplot.py
│       ├── metrics_distribution.py
│       ├── temporal_heatmaps.py
│       └── week_month_barchart.py
│
├── 📁 utils/                               # Utilidades
│   └── timeframe.py                        # ✅ Timeframe, prepare_datetime_data
│
├── 📁 notebooks/                           # Notebooks de análisis
│   ├── breakout.ipynb                      # ⚠️ Estrategia breakout (imports a actualizar)
│   ├── strategy.ipynb                      # ⚠️ Análisis de estrategias
│   └── research_backtest.ipynb             # ⚠️ Investigación
│
├── 📁 outputs/                             # Resultados generados
│   ├── dashboards/                         # Gráficos PNG
│   └── df_trade_metrics.csv                # Métricas exportadas
│
├── 📁 docs/                                # Documentación
│   ├── CLAUDE.md                           # ⭐ ESTE DOCUMENTO
│   ├── REFACTORING_PLAN.md                 # Plan de refactorización
│   └── data_dictionary.md                  # Diccionario de datos
│
└── 📁 tests/                               # ⚠️ VACÍO - Tests a crear
    # Aquí irán:
    # - test_models/
    # - test_core/
    # - test_strategies/
```

---

## 🚀 ESTADO DE LA REORGANIZACIÓN

### ✅ FASE 1 COMPLETADA AL 100%

#### 1. Estructura de carpetas reorganizada
- ✅ Modelos consolidados en `models/`
- ✅ Configuraciones en `config/market_configs/`
- ✅ Estrategias en `strategies/`
- ✅ Datos en `data/loaders/` y `data/preparation/`
- ✅ Métricas en `metrics/`
- ✅ Visualización en `visualization/`
- ✅ Tests en `tests/` (carpeta creada)
- ✅ Docs en `docs/`

#### 2. Archivos movidos y actualizados (16 archivos)
- ✅ `models/enums.py` - Todos los Enums consolidados
- ✅ `models/signals.py` - StrategySignal
- ✅ `models/markets/crypto_market.py` - CryptoMarketDefinition
- ✅ `models/markets/futures_market.py` - FuturesMarketDefinition ⭐ NUEVO
- ✅ `models/trades/base_trade.py` - Imports actualizados
- ✅ `models/trades/crypto_trade.py` - CryptoTrade
- ✅ `models/trades/futures_trade.py` - FuturesTrade con imports actualizados
- ✅ `config/market_configs/crypto_config.py` - Configuración Crypto
- ✅ `config/market_configs/futures_config.py` - Configuración Futures ⭐ NUEVO
- ✅ `utils/timeframe.py` - Timeframe utils
- ✅ `strategies/base_strategy.py` - Imports actualizados
- ✅ `data/loaders/data_provider.py` - Imports actualizados
- ✅ `data/preparation/data_transformer.py` - Imports actualizados
- ✅ `data/preparation/data_cleaner.py` - Imports actualizados
- ✅ `metrics/trade_metrics.py` - Imports actualizados
- ✅ `metrics/portfolio_metrics.py` - Imports actualizados
- ✅ `visualization/` - Todos los archivos actualizados (8 archivos)

#### 3. Notebooks
- ✅ `notebooks/breakout.ipynb` - Imports actualizados con advertencias
- ❌ Notebooks antiguos eliminados (strategy.ipynb, research_backtest.ipynb, research_notebook.ipynb)
- **Resultado**: Un solo notebook principal limpio y funcional

#### 4. Dependencias
- ✅ `requirements.txt` actualizado con versiones compatibles Python 3.13
- ✅ Todas las dependencias instaladas y funcionando
- ✅ pytest y pytest-cov añadidos

#### 5. Testing y Verificación
- ✅ Script `test_imports.py` creado
- ✅ **8/8 tests pasando** (100% éxito)
- ✅ No hay imports circulares
- ✅ No hay errores de sintaxis
- ✅ Todas las configuraciones funcionando

### 🔜 Próximo: FASE 2 - Motor de Backtest Simplificado
- Crear motor de backtest en `core/backtest_engine.py`
- Implementar `core/position_manager.py`
- Crear tests unitarios básicos
- Migrar lógica desde `backtest_signal_runner.py`

---

## 📝 GUÍA DE IMPORTS (NUEVA ESTRUCTURA)

### ✅ Imports correctos desde cualquier módulo:

```python
# Enums y tipos básicos
from models.enums import SignalType, MarketType, OrderType, CurrencyType
from models.enums import ExchangeName, SignalStatus, SignalPositionSide
from models.signals import StrategySignal

# Modelos de mercado
from models.markets.base_market import BaseMarketDefinition
from models.markets.crypto_market import CryptoMarketDefinition
from models.markets.futures_market import FuturesMarketDefinition

# Modelos de trades
from models.trades.base_trade import Trade
from models.trades.crypto_trade import CryptoTrade
from models.trades.futures_trade import FuturesTrade

# Configuraciones
from config.market_configs.crypto_config import get_crypto_config

# Utilidades
from utils.timeframe import Timeframe, prepare_datetime_data

# Estrategias
from strategies.base_strategy import BaseStrategy

# Data loading y preparación
from data.loaders.data_provider import CSVDataProvider, MT5BacktestDataProvider
from data.preparation.data_transformer import DataTransformer

# Métricas
from metrics.trade_metrics import TradeMetricsCalculator
from metrics.portfolio_metrics import BacktestMetrics

# Visualización
from visualization.chart_plotter import ChartVisualizer
from visualization.dashboard_manager import DashboardManager
```

### ❌ Imports antiguos (NO USAR):

```python
# ❌ ANTES (formato antiguo):
from backtest_strategy_definition.properties.strategy_definition_properties import SignalType
from utils.crypto_config import get_crypto_config
from utils.timeframe_definition import Timeframe
from backtest_market_definition.properties.crypto_market_definition_properties import CryptoMarketDefinition
from backtest_trade_definition.properties.crypto_trade import CryptoTrade

# ✅ AHORA (formato nuevo):
from models.enums import SignalType
from config.market_configs.crypto_config import get_crypto_config
from utils.timeframe import Timeframe
from models.markets.crypto_market import CryptoMarketDefinition
from models.trades.crypto_trade import CryptoTrade
```

---

## 🔧 PRÓXIMOS PASOS

### **FASE 1: Actualizar Imports** 🔥 EN PROGRESO
**Objetivo**: Corregir todos los imports para que usen la nueva estructura

1. [⏳] Actualizar imports en archivos Python (14 archivos)
2. [⏳] Actualizar imports en notebooks (3 archivos)
3. [⏳] Verificar que no hay imports circulares
4. [⏳] Testear con un notebook simple

### **FASE 2: Crear Motor de Backtest** (Siguiente)
**Objetivo**: Implementar `core/backtest_engine.py`

- Crear `BacktestEngine` simplificado
- Usar clases existentes (`CryptoTrade`, `CryptoMarketDefinition`)
- Implementar lógica LONG/SHORT
- Calcular P&L con fees y slippage

### **FASE 3: Tests Unitarios**
**Objetivo**: Crear suite de tests

- Tests para modelos (`CryptoTrade`, `StrategySignal`)
- Tests para motor de backtest
- Tests para métricas
- Cobertura >70%

### **FASE 4: Simplificar y Documentar**
**Objetivo**: Mejorar calidad del código

- Simplificar métricas (eliminar duplicados)
- Optimizar loops (evitar `.iterrows()`)
- Crear notebooks tutoriales
- Documentación completa

---

## 🎯 OBJETIVOS DE LA REFACTORIZACIÓN

### Objetivos principales:
1. ✅ **Simplicidad**: Código fácil de entender y mantener
2. ✅ **Robustez**: Tests que validen cálculos correctos
3. ✅ **Escalabilidad**: Fácil añadir nuevos mercados/estrategias
4. ✅ **Funcionalidad**: Mantener todo lo que ya funciona
5. ✅ **Documentación**: Ejemplos claros de uso

### Métricas de éxito:
- [ ] Tests unitarios con >70% cobertura
- [ ] Reducción de código duplicado en ~30%
- [ ] Notebook funcional end-to-end en <100 líneas
- [ ] Documentación completa de API pública

---

## 📊 PROGRESO GENERAL

### Checklist de reorganización:
- [✅] **Fase 0**: Preparación (estructura de carpetas) - **COMPLETADA**
- [✅] **Fase 1**: Actualización de imports - **COMPLETADA 100%**
- [⏳] **Fase 2**: Motor de backtest - **PENDIENTE**
- [ ] **Fase 3**: Tests unitarios
- [ ] **Fase 4**: Simplificación y documentación
- [ ] **Fase 5**: Limpieza final

**Progreso actual**: ~30% completado (2 de 6 fases)

---

## 🚧 NOTAS IMPORTANTES

### ⚠️ Estado Actual:
- ✅ **FASE 1 COMPLETADA** - Imports actualizados y funcionando
- ✅ Notebook `breakout.ipynb` listo para usar (con advertencias sobre módulos antiguos)
- ⚠️ La carpeta `core/` está vacía (motor a implementar en **FASE 2**)
- ⚠️ El módulo `backtest_executor/` sigue funcionando pero será deprecado en FASE 2

### ✅ Listo para usar:
- ✅ Todos los imports actualizados y funcionando
- ✅ Config functions (crypto + futures) operativas
- ✅ Modelos y enums funcionando correctamente
- ✅ Visualización y métricas operativas
- ✅ Test suite de imports completa (test_imports.py)

### 📋 Siguientes Pasos:
- 🔜 **FASE 2**: Crear motor de backtest simplificado en `core/`
- 🔜 Implementar `BacktestEngine` y `PositionManager`
- 🔜 Crear tests unitarios básicos
- 🔜 Validar que resultados coinciden con versión antigua

---

## 📚 DOCUMENTOS DE REFERENCIA

### En `docs/`:
- **`CLAUDE.md`** ⭐ - **ESTE DOCUMENTO** (Guía maestra)
- `REFACTORING_PLAN.md` - Plan detallado de refactorización
- `data_dictionary.md` - Diccionario de datos

### En `notebooks/`:
- `breakout.ipynb` - Ejemplo de estrategia completa (actualizar imports)
- `strategy.ipynb` - Análisis de estrategias
- `research_backtest.ipynb` - Investigación y pruebas

---

## ❓ FAQ

### ¿Cuál es la nueva estructura de imports?
Todos los imports ahora usan rutas relativas desde la raíz del proyecto:
- `models/` para enums, signals, markets, trades
- `config/` para configuraciones
- `utils/` para utilidades
- `strategies/` para estrategias
- `data/` para loaders y preparación
- `metrics/` para cálculo de métricas
- `visualization/` para gráficos y dashboards

### ¿Qué archivos tienen imports rotos?
17 archivos en total (14 Python + 3 notebooks). Ver sección "Estado de la reorganización" arriba.

### ¿Cuándo estará listo el motor de backtest?
Se implementará en Fase 2, después de completar la actualización de imports.

### ¿Cómo añadir un nuevo mercado (ej: Stocks)?
1. Crear `models/markets/stocks_market.py` (heredar de `BaseMarketDefinition`)
2. Crear `models/trades/stocks_trade.py` (heredar de `Trade`)
3. Crear `config/market_configs/stocks_config.py`
4. Usar en estrategias igual que Crypto/Futures

---

## 📞 AYUDA Y SOPORTE

Si tienes dudas:
1. Lee primero este documento (CLAUDE.md)
2. Revisa REFACTORING_PLAN.md para plan detallado
3. Consulta ejemplos en `notebooks/` (después de actualizar imports)
4. Revisa el código en `models/` para entender la estructura

---

**Última actualización**: 2025-10-11 23:45
**Autor**: Usuario + Claude
**Versión**: 2.1 (FASE 1 COMPLETADA - Imports funcionando al 100%)
