# MT5 Backtesting Framework

Framework de backtesting para estrategias de trading algorítmico con soporte para múltiples mercados (Crypto, Futures, Stocks).

## Características

- ✅ Soporte para múltiples mercados (Crypto, Futures, Stocks)
- ✅ Sistema de tipos con Pydantic (validación automática)
- ✅ Métricas detalladas (MAE, MFE, Sharpe, Profit Factor, etc.)
- ✅ Visualización avanzada con dashboards
- ✅ Preparación y transformación de datos
- ⚠️ Motor de backtest simplificado (en desarrollo)

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

## Estructura del Proyecto

```
backtesting/
├── models/          # Modelos de datos (Pydantic)
├── config/          # Configuraciones por mercado
├── strategies/      # Estrategias de trading
├── data/            # Carga y preparación de datos
├── core/            # Motor de backtest (en desarrollo)
├── metrics/         # Cálculo de métricas
├── visualization/   # Dashboards y gráficos
├── utils/           # Utilidades
├── notebooks/       # Notebooks de análisis
├── tests/           # Tests unitarios
└── docs/            # Documentación
```

## Uso Rápido

```python
from models.enums import SignalType, MarketType
from models.markets.crypto_market import CryptoMarketDefinition
from strategies.base_strategy import BaseStrategy
from utils.timeframe import Timeframe

# Crear estrategia
class MyStrategy(BaseStrategy):
    def generate_signals(self):
        # Tu lógica de estrategia aquí
        pass

# Ejecutar backtest
strategy = MyStrategy(
    market=MarketType.CRYPTO,
    symbol="BTC",
    strategy_name="my_strategy",
    timeframe=Timeframe.H1
)
```

## Documentación

Ver `docs/CLAUDE.md` para documentación completa.

## Estado del Proyecto

**Versión**: 0.1.0 (En desarrollo activo)

### Fase Actual: Refactorización
- ✅ Reorganización de estructura de carpetas
- ✅ Actualización de imports (79% completo)
- ⏳ Motor de backtest simplificado (próximamente)
- ⏳ Tests unitarios (próximamente)

Ver `docs/REFACTORING_PLAN.md` para más detalles del plan de refactorización.

## Licencia

MIT
