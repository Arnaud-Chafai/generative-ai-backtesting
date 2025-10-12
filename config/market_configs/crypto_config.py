CRYPTO_CONFIG = {
    "Binance": {
        "BTC": {
            "tick_size": 0.01,
            "exchange_fee": 0.001,  # 0.1% en Binance
            "slippage": 0.0002,  # 0.02% de slippage estimado
            "price_precision": 2,
        },
        "ETH": {
            "tick_size": 0.01,
            "exchange_fee": 0.001,
            "slippage": 0.0002,
            "price_precision": 2,
        }
    },
    "Kucoin": {
        "BTC": {
            "tick_size": 0.0001,  # 🔹 Kucoin permite más precisión en BTC
            "exchange_fee": 0.0008,  # 🔹 0.08% de fee en Kucoin
            "slippage": 0.0003,  # 🔹 Slippage ligeramente mayor en Kucoin
            "price_precision": 4,  # 🔹 Más decimales en precios
        },
        "ETH": {
            "tick_size": 0.0001,
            "exchange_fee": 0.0008,
            "slippage": 0.0003,
            "price_precision": 4,
        }
    }
}

def get_crypto_config(exchange: str, symbol: str):
    """ Devuelve la configuración del activo cripto según el exchange o lanza un error si no está definido. """
    if exchange not in CRYPTO_CONFIG or symbol not in CRYPTO_CONFIG[exchange]:
        raise ValueError(f"⚠ No se ha definido configuración para {symbol} en {exchange}")
    return CRYPTO_CONFIG[exchange][symbol]
