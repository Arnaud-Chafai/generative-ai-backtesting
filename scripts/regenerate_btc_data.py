"""
Regenerar datos BTC sin Heikin Ashi.

Descarga BTC/USDT 5m desde Binance (2021-03-26 a hoy),
limpia, enriquece con indicadores y exporta a laboratory_data/BTC/.

Uso:
    python scripts/regenerate_btc_data.py
"""
import sys
import os

# Añadir raíz del proyecto al path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.loaders.data_provider import CcxtDataProvider
from data.preparation.data_cleaner import DataCleaner
from data.preparation.data_transformer import DataTransformer
from utils.timeframe import Timeframe


# ── 1. Descargar datos crudos desde Binance ─────────────────────────
print("=" * 60)
print("PASO 1: Descargando BTC/USDT 5m desde Binance...")
print("=" * 60)

provider = CcxtDataProvider(
    symbol="BTC/USDT",
    timeframe="5m",
    start_date="2021-03-26",
)
df_raw = provider.get_all_data()
print(f"✓ {len(df_raw)} velas descargadas")
print(f"  Rango: {df_raw.index.min()} → {df_raw.index.max()}")

# Guardar raw por si acaso
os.makedirs("data/raw_data", exist_ok=True)
provider.save_to_csv("data/raw_data/BTCUSDT_5m.csv")

# ── 2. Limpiar ──────────────────────────────────────────────────────
print("\n" + "=" * 60)
print("PASO 2: Limpiando datos...")
print("=" * 60)

cleaner = DataCleaner()
df_clean = cleaner.clean_data(df_raw)
print(f"✓ {len(df_clean)} filas después de limpieza")

# ── 3. Transformar SIN Heikin Ashi ──────────────────────────────────
print("\n" + "=" * 60)
print("PASO 3: Enriqueciendo datos (SIN Heikin Ashi)...")
print("=" * 60)

transformer = DataTransformer(df_clean)
enriched_data = transformer.prepare_data(
    timeframes=[Timeframe.M5, Timeframe.M15, Timeframe.H1, Timeframe.H4],
    ema_periods=[9, 20, 50, 200],
    volatility_periods=[5, 10],
    pct_change_periods=[1, 5],
    volume_periods=[5, 10],
    cumulative_volume_periods=[5, 10],
    obp_range=10,
    heikin_ashi=False,  # ← CLAVE: sin Heikin Ashi
)

# ── 4. Exportar a laboratory_data/BTC/ ──────────────────────────────
print("\n" + "=" * 60)
print("PASO 4: Exportando a laboratory_data/BTC/...")
print("=" * 60)

output_dir = "data/laboratory_data/BTC"
transformer.export_dataframes_to_csv(enriched_data, output_dir)

# Verificación: mostrar que los precios son reales (sin decimales HA)
for tf, df in enriched_data.items():
    sample_open = df['Open'].iloc[10]
    print(f"  {tf} → Open sample: {sample_open} ({len(df)} filas)")

print("\n" + "=" * 60)
print("✓ COMPLETADO — Datos regenerados sin Heikin Ashi")
print("=" * 60)
