# Modulo: config/market_configs

Configuraciones estaticas de mercados: tick size, fees, slippage y precision de precios por exchange y simbolo. Consumidos por las clases en `config/markets/`.

## Archivos

### crypto_config.py
Configuracion de activos crypto por exchange.

```python
from config.market_configs.crypto_config import get_crypto_config

config = get_crypto_config("Binance", "BTC")
# → {"tick_size": 0.01, "exchange_fee": 0.001, "slippage": 0.0002, "price_precision": 2}
```

**Exchanges definidos:** Binance, Kucoin
**Simbolos:** BTC, ETH

### futures_config.py
Configuracion de futuros por exchange.

```python
from config.market_configs.futures_config import get_futures_config

config = get_futures_config("CME", "ES")
# → {"tick_size": 0.25, "exchange_fee": 0.0002, "slippage": 0.00005, ...}
```

**Exchanges definidos:** CME
**Simbolos:** ES (S&P 500), NQ (Nasdaq-100), GC (Gold)

**Nota:** No tiene consumidor activo (futures_market.py fue eliminado).

## Relacion con config/markets/

```
config/market_configs/          config/markets/
├── crypto_config.py  ──────►  ├── crypto_market.py (CryptoMarketDefinition)
└── futures_config.py  ✗       └── (sin consumidor)
```

`CryptoMarketDefinition.get_config()` llama internamente a `get_crypto_config()`.

## Como agregar un nuevo exchange/simbolo

Agregar entrada al diccionario correspondiente:

```python
# En crypto_config.py
CRYPTO_CONFIG = {
    "Binance": {
        "SOL": {
            "tick_size": 0.01,
            "exchange_fee": 0.001,
            "slippage": 0.0003,
            "price_precision": 2,
        },
        # ...
    }
}
```
