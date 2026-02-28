# Design Doc: Skill /refine-strategy

**Fecha:** 2026-02-28
**Autor:** Conversación colaborativa usuario + Claude
**Estado:** Aprobado

## Visión

Skill de validación, refinamiento y catalogación de estrategias de trading. Paso natural después de `/create-strategy`. No es un optimizador de parámetros — es un **proceso de comprensión** que acompaña al trader a entender por qué su estrategia funciona o falla, en qué contextos rinde, y cómo mejorarla con cambios mínimos y fundamentados.

**Filosofía:** "La historia no se repite, pero rima." No descartamos estrategias que funcionan en contextos específicos — las catalogamos, etiquetamos y conectamos.

**Flujo:** De grande a pequeño. Validar antes de optimizar. Entender antes de cambiar.

## Conexión con /create-strategy

```
/create-strategy              /refine-strategy
┌──────────────────┐          ┌────────────────────────────┐
│ FASE 0: Edge     │          │ Lee spec + strategy memory │
│ FASE 1: Spec     │─────────►│ FASE 0: Quality Gates      │
│ FASE 2: Código   │          │ FASE 1: Visual Diagnosis   │
│         + test   │          │ FASE 2: Refinamiento       │
└──────────────────┘          │ FASE 3: Optimización       │
        ▲                     │ Actualiza memoria          │
        │                     └────────────────────────────┘
        │                              │
        └──────────────────────────────┘
         Si el edge necesita rediseño fundamental
         → volver a /create-strategy
```

El **puente** es el spec (`docs/strategies/{nombre}-spec.md`) y la strategy memory.

## Tono: Mentor, no checklist

La skill NO es un validador frío de métricas. Es un **compañero de trading** que:

- **Explica el POR QUÉ** en términos de trading, no solo números
  - No: "PF = 0.9, falla G2"
  - Sí: "Tu PF está en 0.9 — por cada dólar que arriesgas recuperas 90 centavos. Antes de ajustar parámetros, ¿el problema está en las entradas o en las salidas?"
- **Hace preguntas reflexivas** para que el trader piense
- **Conecta hallazgos** entre gates, fases y estrategias previas
- **Ofrece perspectiva** antes de cada decisión, con trade-offs claros
- **Lee la memoria** para aportar contexto histórico: "Esto lo vimos antes en X estrategia..."

## Arquitectura

### FASE 0 — Quality Gates (Automatizadas)

Se ejecutan al inicio. Son un **diagnóstico**, no un rechazo. Cada gate genera un reporte con explicación en contexto de trading.

| Gate | Métrica | Umbral | Si falla |
|------|---------|--------|----------|
| G1: Actividad | Trades/año | M5: 100+ · H1: 50+ · D1: 20+ | ¿Edge de baja frecuencia legítima o lógica que filtra demasiado? |
| G2: Rentabilidad | PF > 1.0 AND expectancy > 0 | Ambos | Si fallan ambos → problema fundamental. Si falla uno → investigar sesgo |
| G3: Perfil de contexto | Regime profiling | NO es gate de rechazo | Cataloga en qué contextos funciona/falla (ver Regime Profiling) |
| G3b: Context Intelligence | Agente investigador | Auto si anomalía extrema | Investiga qué pasó en el mundo real durante períodos anómalos |
| G4: Coherencia | WR vs Avg Win/Loss | Ratio coherente | WR alto + avg_win << avg_loss → problema de salidas |
| G5: Riesgo | Recovery Factor > 1.0 | RF = ROI / MaxDD | Si falla → priorizar gestión de riesgo en Fase 2 |

#### G3 — Quantitative Regime Profiling

Dividir el período en ventanas (trimestres o segmentos de N trades). Para cada ventana:

**Características de mercado:**
- Volatilidad: ATR normalizado, percentil de ATR
- Tendencia: pendiente de SMA, distancia precio-SMA
- Actividad: volumen relativo vs media

**Performance de la estrategia:**
- PF, expectancy, win rate, avg P&L por ventana

**Output:** Tabla de contextos con etiquetas:
```
| Período | Volatilidad | Tendencia | PF  | Etiqueta |
|---------|-------------|-----------|-----|----------|
| Q1 2025 | Alta        | Alcista   | 2.3 | Óptimo   |
| Q2 2025 | Baja        | Lateral   | 0.7 | Débil    |
```

Esto alimenta la visión futura de agentes que matchean estrategias con regímenes de mercado.

#### G3b — Context Intelligence Agent

Cuando G3 detecta anomalías, se lanza un agente para investigar qué pasó en el mundo real.

**Invocación automática** (sin preguntar):
- Volatilidad en percentil >95
- Drawdown >2x el MaxDD histórico
- PF colapsa de >1.5 a <0.5 entre períodos
- Período con 0 trades cuando debería tener actividad
- Movimiento de precio >3 desviaciones estándar

**Sugerir al trader** (preguntar antes):
- Cambios moderados de régimen sin causa obvia
- Períodos interesantes pero no extremos

El agente busca noticias financieras, eventos macro, cambios regulatorios y eventos geopolíticos para el activo en el período detectado. Retorna un mini-reporte de 3-5 puntos clave.

**Output:** Anotación de contexto en el Regime Profile + lessons.md si la dinámica es reutilizable.

Ejemplo: "CL abril 2020 — COVID destruyó demanda de crudo, futuros a precio negativo por primera vez. Cisne negro, no fallo de estrategia."

### FASE 1 — Diagnóstico Visual

1. `runner.plot_trades()` — ¿Las señales están donde el spec dice?
2. `runner.plot_dashboards()` — ¿Patrones anómalos en distribuciones/heatmaps?
3. **Edge Decay Check:**
   - Expectancy rolling (ventana de 20-50 trades)
   - Graficar a lo largo del tiempo
   - Detectar: ¿estable, mejora, decae, o cíclico?
   - Si decae → edge posiblemente agotado
   - Si cíclico → confirma dependencia de régimen (conecta con G3)

**Preguntas reflexivas:**
- ¿Las señales aparecen donde esperas?
- ¿Hay clusters de pérdidas en períodos específicos?
- ¿El decay es preocupante o esperado por el régimen?

### FASE 2 — Refinamiento de Lógica

Orden estricto: **Entradas → Salidas → Filtros → Sizing**

Cada sub-fase:
1. Identificar problema específico (de la visual o las gates)
2. Proponer cambio mínimo
3. Re-correr backtest
4. Comparar métricas antes/después
5. Validar visualmente

**2a. Entradas** — ¿Timing correcto? ¿Falsos breakouts? ¿Falta confirmación?
**2b. Salidas** — ¿Cortando profits? ¿Stops ajustados/sueltos? ¿Parciales?
**2c. Filtros** — ¿Contextos donde no debería operar? (conecta con G3)
**2d. Sizing** — ¿Position sizing adecuado? ¿DCA calibrado?

### Robustness Test (entre Fase 2 y Fase 3)

Antes de optimizar, verificar que la configuración actual no es frágil:

- Para cada parámetro clave: variar ±10% y ±20%, re-correr backtest
- Si ±10% destruye rentabilidad → señal de curve-fitting
- Visualizar: tabla de sensibilidad por parámetro
- Solo pasar a Fase 3 si la estrategia es robusta

### FASE 3 — Optimización Paramétrica

Solo llegar aquí si:
- Gates entendidas (no necesariamente todas pasadas, pero sí comprendidas)
- Lógica refinada y validada visualmente
- Robustness test pasado

Proceso:
1. Definir rangos para parámetros sensibles
2. Grid search con `ParameterOptimizer`
3. Verificar que el óptimo no está en borde del rango
4. Comparar con pre-optimización
5. Re-validar visualmente

## Sistema de Memoria

### Estructura de archivos

```
docs/strategy_memory/
├── INDEX.md                      ← Índice centralizado (~200 líneas)
│                                    Se lee siempre al inicio
├── strategies/
│   ├── btc_pugilanime.md         ← Detalle de una estrategia
│   ├── es_momentum.md            ← Otra estrategia
│   └── ...
└── lessons.md                    ← Dinámicas de mercado cross-strategy
```

### INDEX.md — Índice comprimido

```markdown
# Strategy Memory Index

## Estrategias activas

### BTCPugilanime v2.2 | CRYPTO BTC M5 | Tendencia (breakout-pullback)
- **Edge:** Sesgo alcista BTC, pullbacks a EMA en tendencia
- **Régimen óptimo:** Alta vol + tendencia alcista (PF 2.3)
- **Régimen débil:** Baja vol + lateral (PF 0.7)
- **Métricas:** PF 1.5 | RF 1.4 | WR 45% | MaxDD -12% | 120 trades/año
- **Última versión:** v2.2 (2026-03-01)
- **Detalle:** strategies/btc_pugilanime.md
```

### strategies/{nombre}.md — Detalle por estrategia

Contiene:
- Edge y descripción
- Regime Profile (tabla por período)
- Changelog versionado (contexto → cambio → resultado → lección)
- Robustness table (última versión)
- Edge Decay status

### lessons.md — Dinámicas de mercado

NO son lecciones técnicas de parámetros. Son observaciones sobre **dinámicas de mercado de orden superior** que trascienden estrategias individuales:

```markdown
## Acumulación con volatilidad creciente
Cuando ATR semanal crece >20% y precio retestea SMA200 sin romperla,
los pullbacks a EMAs rápidas ofrecen entradas de alta calidad.
El mercado está absorbiendo oferta.
**Observado en:** BTCPugi Q1 2025, Q4 2025

## Compresión de volatilidad post-impulso
Después de un rally >30%, la volatilidad se comprime.
Los breakouts generan falsos positivos frecuentes.
**Observado en:** BTCPugi Q2 2025 (PF 0.7)
```

### Flujo de memoria en la skill

```
/refine-strategy
    │
    ├── 1. Leer INDEX.md → contexto global
    ├── 2. Leer strategies/{nombre}.md → historial de esta estrategia
    ├── 3. Leer lessons.md → dinámicas de mercado conocidas
    │
    ├── 4. Ejecutar FASES 0-3
    │
    └── 5. Actualizar memoria:
           ├── Append changelog en strategies/{nombre}.md
           ├── Actualizar métricas en INDEX.md
           └── Si hay dinámica nueva → append en lessons.md
```

## Control de versiones

Cada ciclo de refinamiento:
1. Bump versión en docstring del `.py` y en el spec
2. Documenta en changelog: **contexto** (qué problema) + **cambio** (qué se hizo) + **resultado** (métricas antes/después) + **lección** (dinámica de mercado aprendida)
3. Git commit: `refine(strategy): {nombre} v{X.Y} — {descripción corta}`

## Implementación futura de memoria

La estructura markdown es migrable:
- **Fase actual:** Archivos `.md` en git (funcional desde día 1)
- **Fase futura:** PostgreSQL para métricas + queries exactos
- **Fase posterior:** Vector store (pgvector/Chroma) para búsqueda semántica sobre lessons.md y changelogs
