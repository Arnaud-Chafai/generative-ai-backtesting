# 🎯 Parameter Optimizer - Guía Completa

## ¿Qué es el Parameter Optimizer?

El **Parameter Optimizer** es una herramienta que busca automáticamente la mejor combinación de parámetros para tu estrategia de trading usando **Grid Search**.

En lugar de probar parámetros manualmente, el optimizador:
1. ✅ Define rangos de valores a probar
2. ✅ Genera todas las combinaciones posibles
3. ✅ Ejecuta un backtest para cada combinación
4. ✅ Retorna la mejor según la métrica elegida

---

## 🚀 Inicio Rápido (5 minutos)

```python
import pandas as pd
from optimization.optimizer import ParameterOptimizer
from strategies.examples.breakout_simple import BreakoutSimple
from utils.timeframe import Timeframe

# 1. Cargar datos (UNA VEZ)
df = pd.read_csv('data/laboratory_data/BTC/Timeframe.M5.csv',
                  index_col='Time', parse_dates=['Time'])

# 2. Crear optimizador
optimizer = ParameterOptimizer(
    strategy_class=BreakoutSimple,
    market_data=df,  # ✅ Inyectar datos
    symbol='BTC',
    timeframe=Timeframe.M5,
    initial_capital=1000.0
)

# 3. Definir rangos
ranges = {
    'lookback_period': [10, 15, 20, 25, 30],
    'position_size_pct': [0.2, 0.3, 0.4]
}

# 4. Ejecutar
results = optimizer.optimize(ranges, metric='sharpe_ratio')

# 5. Obtener lo mejor
best_params = optimizer.get_best_params()
```

---

## 📊 Conceptos Clave

### Parámetros Optimizables vs Fijos

#### **Optimizables** (Lo que vamos a probar)
Estos varían en cada iteración:
```python
param_ranges = {
    'lookback_period': [10, 15, 20, 25],  # ← Varía
    'position_size_pct': [0.2, 0.3, 0.4]  # ← Varía
}
```

#### **Fijos** (No cambian)
Estos permanecen constantes:
```python
optimizer = ParameterOptimizer(
    strategy_class=BreakoutSimple,
    market_data=df,
    symbol='BTC',              # ← Fijo (no optimiza)
    timeframe=Timeframe.M5,    # ← Fijo (no optimiza)
    initial_capital=1000.0     # ← Fijo (no optimiza)
)
```

### ¿Cuándo es un parámetro optimizable?

| Tipo | Ejemplo | ¿Optimizable? | Por qué |
|------|---------|---------------|---------|
| **Input estático** | `lookback_period=20` | ✅ **SÍ** | Directamente controlable |
| **Multiplicador** | `atr_multiplier=2.0` | ✅ **SÍ** | Escala un indicador |
| **Porcentaje** | `position_size_pct=0.3` | ✅ **SÍ** | Controla riesgo |
| **Booleano** | `use_atr_stop=True` | ✅ **SÍ** | Cambia la lógica |
| **Indicador calculado** | `stop_loss = atr * 2` | ❌ **NO** | Se calcula, no se controla |
| **Métrica derivada** | `risk_reward = profit/loss` | ❌ **NO** | Resultado, no input |

**Regla de oro:** Si es un **INPUT** que la estrategia recibe en `__init__`, es optimizable.

---

## 🏗️ Arquitectura

### Flujo de Ejecución

```
┌─────────────────────────────────────────────────┐
│ 1. Cargar datos del disco (UNA SOLA VEZ)       │
│    df = pd.read_csv('data.csv')                │
└─────────────────┬───────────────────────────────┘
                  │
┌─────────────────▼───────────────────────────────┐
│ 2. Crear ParameterOptimizer                    │
│    optimizer = ParameterOptimizer(            │
│        strategy_class=MyStrategy,             │
│        market_data=df  # ✅ Inyectar         │
│    )                                           │
└─────────────────┬───────────────────────────────┘
                  │
┌─────────────────▼───────────────────────────────┐
│ 3. Generar Grid (todas las combinaciones)      │
│    5 × 4 = 20 combinaciones                    │
└─────────────────┬───────────────────────────────┘
                  │
        ┌─────────▼──────────┐
        │ Para cada combo:   │
        │  1. Crear estrategia con data inyectada
        │  2. Ejecutar backtest (rápido, sin I/O)
        │  3. Guardar resultado
        │  4. Mostrar barra de progreso
        └─────────┬──────────┘
                  │
┌─────────────────▼───────────────────────────────┐
│ 4. Retornar resultados como DataFrame          │
│    Ordenados por métrica objetivo              │
└─────────────────┬───────────────────────────────┘
                  │
┌─────────────────▼───────────────────────────────┐
│ 5. Obtener mejores parámetros                  │
│    Con filtro anti-fantasma (min_trades)      │
└─────────────────────────────────────────────────┘
```

### Inyección de Datos

**¿Por qué inyectar datos?**

```
ANTES (Lento):
Combo 1: Leer disco → 2 segundos
Combo 2: Leer disco → 2 segundos
Combo 3: Leer disco → 2 segundos
...
Total: 500 combos × 2s = 16 MINUTOS ❌

AHORA (Rápido):
Carga 1 vez: 2 segundos
Combo 1: RAM → 0.01 segundos
Combo 2: RAM → 0.01 segundos
Combo 3: RAM → 0.01 segundos
...
Total: 2s + (500 × 0.01s) = 7 SEGUNDOS ✅

MEJORA: 200x más rápido
```

---

## 📈 API Completa

### `ParameterOptimizer.__init__`

```python
optimizer = ParameterOptimizer(
    strategy_class=MyStrategy,      # Clase que hereda de BaseStrategy
    market_data=df,                 # DataFrame con OHLCV
    symbol='BTC',                   # Parámetro fijo
    timeframe=Timeframe.M5,         # Parámetro fijo
    initial_capital=1000.0,         # Parámetro fijo
    # ... más parámetros fijos
)
```

### `optimizer.optimize()`

```python
results_df = optimizer.optimize(
    param_ranges={
        'lookback_period': [10, 15, 20],
        'position_size_pct': [0.2, 0.3]
    },
    metric='sharpe_ratio',  # sharpe_ratio, roi, profit_factor, max_drawdown
    method='grid',          # Solo 'grid' en v1
    show_progress=True      # Mostrar barra de progreso
)

# Retorna: DataFrame con columnas
# [parámetros + sharpe_ratio + roi + max_drawdown + profit_factor + total_trades]
```

### `optimizer.get_best_params()`

```python
best = optimizer.get_best_params(
    metric='sharpe_ratio',  # Opcional, usa el del optimize()
    min_trades=20           # Filtro: ignorar resultados con < 20 trades
)

# Retorna: {'lookback_period': 20, 'position_size_pct': 0.3, ...}
# O None si no hay resultados válidos
```

### `optimizer.export_results()`

```python
optimizer.export_results('my_results.csv')
# Guarda DataFrame completo a CSV para análisis posterior
```

---

## 🎯 Casos de Uso

### Caso 1: Optimizar Estrategia Simple

```python
# Tengo una estrategia y quiero encontrar los mejores parámetros

df = load_data('BTC', 'M5')
optimizer = ParameterOptimizer(BreakoutSimple, df, symbol='BTC', timeframe=Timeframe.M5)

results = optimizer.optimize({
    'lookback_period': range(10, 51, 5),  # 10, 15, 20, ..., 50
    'position_size_pct': [0.1, 0.2, 0.3, 0.4, 0.5]
})

best = optimizer.get_best_params(min_trades=100)
```

### Caso 2: Comparar Dos Estrategias

```python
# Ejecutar optimizador para Strategy A
optimizer_a = ParameterOptimizer(StrategyA, df, ...)
results_a = optimizer_a.optimize({...})
best_a = optimizer_a.get_best_params()

# Ejecutar optimizador para Strategy B
optimizer_b = ParameterOptimizer(StrategyB, df, ...)
results_b = optimizer_b.optimize({...})
best_b = optimizer_b.get_best_params()

# Comparar
print(f"Estrategia A Sharpe: {best_a['sharpe_ratio']}")
print(f"Estrategia B Sharpe: {best_b['sharpe_ratio']}")
```

### Caso 3: Optimización por Múltiples Métricas

```python
# Ejecutar optimización
results = optimizer.optimize({...}, metric='sharpe_ratio')

# Obtener lo mejor por diferentes métricas
best_sharpe = optimizer.get_best_params(metric='sharpe_ratio')
best_roi = optimizer.get_best_params(metric='roi')
best_dd = optimizer.get_best_params(metric='max_drawdown', min_trades=50)
```

---

## ⚡ Performance

### Estimaciones de Tiempo

| Parámetros | Combinaciones | Tiempo |
|------------|---------------|--------|
| 2 params × (5, 5) | 25 | ~30 seg |
| 2 params × (10, 5) | 50 | ~60 seg |
| 3 params × (5, 5, 5) | 125 | ~2 min |
| 3 params × (10, 5, 5) | 250 | ~4 min |
| 4 params × (5, 5, 5, 5) | 625 | ~10 min |

**Truco:** Empieza con rangos amplios, luego refina con rangos estrechos alrededor del óptimo.

---

## 🚨 Trampa: Overfitting Fantasma

### El Problema

```python
# Resultado 1: lookback=100, trades=1, Sharpe=∞
# ↑ Sharpe infinito porque solo 1 trade ganador (pura suerte)

# Resultado 2: lookback=20, trades=300, Sharpe=1.2
# ↑ Sharpe real con 300 muestras (estadísticamente válido)
```

Sin filtro, el optimizador elegiría el Resultado 1 (engañoso).

### La Solución: `min_trades`

```python
# Requerer al menos 30 trades para considerar válido
best = optimizer.get_best_params(min_trades=30)
```

**Recomendación:** Usa `min_trades=20` mínimo para resultados robustos.

---

## 🧪 Testing

Ejecutar tests:

```bash
pytest tests/test_optimizer.py -v
```

---

## 🔮 Roadmap de Optimización

### Fase 4a: Grid Search (✅ COMPLETADO - v1.0)

```python
optimizer = ParameterOptimizer(strategy, market_data)
results = optimizer.optimize({'lookback': [10, 20, 30]})
```

**Características:**
- ✅ Grid search automático con `itertools.product`
- ✅ Inyección de datos (200x más rápido)
- ✅ Validación inteligente de parámetros
- ✅ Filtro anti-fantasma (`min_trades`)
- ✅ Barra de progreso con `tqdm`
- ✅ Export a CSV
- ✅ Tests comprensivos

**Cuando usar:** Pocos parámetros (2-3), rangos pequeños (5-10 valores)

---

### Fase 4b: Random Search + Bayesian (⏳ SIGUIENTE - v1.5)

#### Random Search
```python
# Muestreo aleatorio (más eficiente que grid)
results = optimizer.optimize(
    param_ranges={...},
    method='random',  # NEW
    n_iter=50  # Probar solo 50 combinaciones aleatorias
)
```

**Ventaja:** Para 100 parámetros × 10 valores = 10^100 combinaciones imposibles.
Random prueba solo 50 → mucho más rápido.

**Cuando usar:** Espacios grandes (>5 parámetros o >100 valores totales)

---

#### Bayesian Optimization
```python
# Usa modelos probabilísticos para buscar inteligentemente
results = optimizer.optimize(
    param_ranges={...},
    method='bayesian',  # NEW
    n_calls=50,
    random_state=42
)
```

**Cómo funciona:**
1. Comienza con búsqueda aleatoria
2. Construye modelo probabilístico de función objetivo
3. Usa el modelo para predecir dónde está el óptimo
4. Busca alrededor de esas predicciones
5. Refina iterativamente

**Ventaja:** Converge más rápido que random. ~80% mejora con 50% menos iteraciones.

**Cuando usar:** Cuando la computación es cara (backtests largos) y quieres máxima eficiencia.

**Dependencia:** `pip install scikit-optimize`

---

### Fase 4c: Walk-Forward Testing (⏳ FUTURO - v2.0)

```python
# Validación temporal: Optimizar en pasado, probar en futuro
walk_forward = WalkForwardOptimizer(strategy, market_data, window_size='1y')

# Optimizar: 2021-2022, Probar: 2022-2023
# Optimizar: 2022-2023, Probar: 2023-2024
results = walk_forward.optimize(param_ranges, metric='sharpe_ratio')
```

**Flujo:**
```
Datos: ├─ Train1 ─┤ Test1 ─┤ Train2 ─┤ Test2 ─┤
       2021    2022    2023    2024

Iter1: Opt(2021-2022) → Test(2022-2023)
Iter2: Opt(2022-2023) → Test(2023-2024)
...
```

**Ventaja:** Detecta si la optimización es válida en datos fuera de muestra.

**Cuando usar:** Validar robustez de parámetros. Evitar overfitting temporal.

---

### Fase 4d: Multiprocessing (⏳ FUTURO - v2.0)

```python
# Ejecutar backtests en paralelo
results = optimizer.optimize(
    param_ranges={...},
    method='grid',
    n_jobs=4  # Usar 4 CPU cores
)
```

**Speedup:** 4 cores = 4x más rápido (teóricamente)

**Implementación:**
- Usar `multiprocessing.Pool`
- O `joblib.Parallel` (más fácil)

**Consideraciones:**
- Overhead de procesos
- Memoria RAM (cada proceso copia datos)
- GIL en Python (threads limitados)

---

### Fase 4e: Genetic Algorithms (⏳ FUTURO - v3.0)

```python
# Evolución de parámetros
results = optimizer.optimize(
    param_ranges={...},
    method='genetic',
    population_size=20,
    generations=50
)
```

**Cómo funciona:**
1. Población inicial aleatoria
2. Selecciona mejores individuos (elitismo)
3. Crossover: combina genes de dos padres
4. Mutación: cambia genes aleatoriamente
5. Repite N generaciones

**Ventaja:** Explora espacio de búsqueda global, no solo local.

**Cuando usar:** Espacios muy complejos, multimodales.

**Dependencia:** `pip install deap`

---

## 📊 Comparación de Métodos

| Método | Velocidad | Calidad | Parámetros | Complejidad |
|--------|-----------|---------|-----------|-------------|
| Grid Search | ⭐ | ⭐⭐⭐ | 2-3 | ⭐ |
| Random Search | ⭐⭐ | ⭐⭐ | 3-5 | ⭐ |
| Bayesian | ⭐⭐⭐ | ⭐⭐⭐⭐ | 3-10 | ⭐⭐⭐ |
| Walk-Forward | ⭐ | ⭐⭐⭐⭐⭐ | 2-3 | ⭐⭐ |
| Genetic | ⭐⭐ | ⭐⭐⭐⭐ | 5+ | ⭐⭐⭐ |

---

## 🎯 Decisión: ¿Qué método elegir?

**Empezar:** Grid Search (listo hoy)
↓
**Después:** Random Search (semana 1)
↓
**Más tarde:** Bayesian si backtests son lentos
↓
**Robusto:** Walk-Forward para validar
↓
**Avanzado:** Genetic para espacios complejos

---

## 📚 Ejemplos Completos

- **Optimización básica:** `notebooks/prueba_optimizer.ipynb`
- **Visualización 3D:** `notebooks/prueba_optimizer_visualization.ipynb`

---

## 🎨 Visualización 3D de Resultados

### OptimizationPlotter

El módulo `optimization.visualizer` proporciona visualización 3D del espacio de parámetros.

```python
from optimization import OptimizationPlotter

# Después de ejecutar la optimización
plotter = OptimizationPlotter(results_df)

# Superficie 3D con mapa de color rojo → azul
plotter.plot_3d_surface(
    x_param='lookback_period',
    y_param='position_size_pct',
    metric='sharpe_ratio',
    figsize=(14, 10)
)
```

### Características

- **Superficie 3D estilo MATLAB**: Malla tridimensional con proyección en el suelo
- **Colormap rojo → azul**: Rojo = valores bajos (malos), Azul = valores altos (buenos)
- **Métricas soportadas**: `sharpe_ratio`, `roi`, `max_drawdown`, `profit_factor`, `total_trades`
- **Interactividad**: Rotación 3D para explorar desde diferentes ángulos

### Parámetros

```python
def plot_3d_surface(
    x_param: str,           # Parámetro para eje X
    y_param: str,           # Parámetro para eje Y
    metric: str,            # Métrica para eje Z
    fill_value: float = 0.0,  # Valor para rellenar huecos
    figsize: tuple = (14, 10)  # Tamaño de la figura
)
```

### Interpretación

**Superficies Planas:**
- ✅ Parámetro robusto (insensible a variaciones)
- Ejemplo: Si cambiar `lookback` de 10 a 30 no afecta el Sharpe → robusto

**Superficies con Picos:**
- ⚠️ Parámetro sensible (requiere ajuste fino)
- Ejemplo: Si solo `lookback=20` da buen Sharpe → sensible, overfitting probable

**Zonas Azules (Altas):**
- ✅ Regiones óptimas para operar
- Busca "mesetas azules" amplias (robustas) vs "picos azules" estrechos (frágiles)

---

## ❓ FAQ

**P: ¿Puedo optimizar indicadores técnicos?**
R: No directamente. Optimiza los parámetros que **controlan** los indicadores (períodos, multiplicadores, etc.).

**P: ¿Qué pasa si tengo 100 parámetros?**
R: No hagas eso. Limita a 2-3 máximo. Grid Search crece exponencialmente.

**P: ¿Es Grid Search lo mejor?**
R: Para v1 es simple y funciona. Random Search y Bayesian son más eficientes para espacios grandes.

**P: ¿Cómo evito overfitting?**
R: Usa `min_trades`, haz walk-forward testing, valida en datos fuera de muestra.

**P: ¿Puedo optimizar stops dinámicos?**
R: Sí, optimiza el **multiplicador** (ej: `atr_multiplier`), no el stop directo.

---

## 📞 Soporte

Para reportar bugs o sugerencias: `issues` en el repositorio.

---

**¡Happy optimizing! 🚀**
