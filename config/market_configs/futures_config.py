FUTURES_CONFIG = {
    "CME": {  # Chicago Mercantile Exchange
        "ES": {  # S&P 500 E-mini
            "tick_size": 0.25,
            "exchange_fee": 0.0002,
            "slippage": 0.00005,
            "price_precision": 2,
            "contract_size": 50,
            "leverage": 1,
        },
        "NQ": {  # Nasdaq-100 E-mini
            "tick_size": 0.25,
            "exchange_fee": 0.0002,
            "slippage": 0.00005,
            "price_precision": 2,
            "contract_size": 20,  # $20 multiplicador
            "leverage": 1,
        },
        "GC": {  # Gold Futures
            "tick_size": 0.10,  # $10 por tick
            "exchange_fee": 0.0003,
            "slippage": 0.0001,
            "price_precision": 1,
            "contract_size": 100,  # 100 onzas troy
            "leverage": 1,
        }
    }
}

def get_futures_config(exchange: str, symbol: str):
    """
    Devuelve la configuración del futuro según el exchange o lanza un error si no está definido.

    Args:
        exchange: Nombre del exchange (ej: "Binance", "Bybit", "CME")
        symbol: Símbolo del futuro (ej: "BTCUSDT", "ES", "NQ")

    Returns:
        dict: Configuración del futuro con tick_size, fees, slippage, etc.

    Raises:
        ValueError: Si no existe configuración para ese exchange/symbol
    """
    if exchange not in FUTURES_CONFIG or symbol not in FUTURES_CONFIG[exchange]:
        raise ValueError(f"⚠ No se ha definido configuración para {symbol} en {exchange}")
    return FUTURES_CONFIG[exchange][symbol]
