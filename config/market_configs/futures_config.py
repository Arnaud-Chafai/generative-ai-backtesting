"""
Configuración de futuros CME.

Cada activo define sus costos en unidades naturales (ticks, dólares fijos).
`get_futures_config()` devuelve un dict compatible con BacktestEngine,
pasando slippage_ticks directamente (el engine lo aplica como valor fijo).
"""

FUTURES_CONFIG = {
    "CME": {
        "ES": {  # S&P 500 E-mini
            "tick_size": 0.25,
            "tick_value": 12.50,
            "contract_size": 50,
            "slippage_ticks": 1,
            "exchange_fee": 1.39,  # USD por contrato (CME exchange fee)
            "price_precision": 2,
            "currency": "USD",
        },
        "NQ": {  # Nasdaq-100 E-mini
            "tick_size": 0.25,
            "tick_value": 5.00,
            "contract_size": 20,
            "slippage_ticks": 1,
            "exchange_fee": 1.39,  # USD por contrato (CME exchange fee)
            "price_precision": 2,
            "currency": "USD",
        },
        "GC": {  # Gold Futures (COMEX)
            "tick_size": 0.10,
            "tick_value": 10.00,
            "contract_size": 100,  # 100 onzas troy
            "slippage_ticks": 1,
            "exchange_fee": 1.60,  # USD por contrato (COMEX exchange fee)
            "price_precision": 2,
            "currency": "USD",
        },
        "CL": {  # Crude Oil Futures (NYMEX)
            "tick_size": 0.01,
            "tick_value": 10.00,
            "contract_size": 1000,  # 1000 barriles
            "slippage_ticks": 2,
            "exchange_fee": 1.50,  # USD por contrato (NYMEX exchange fee)
            "price_precision": 2,
            "currency": "USD",
        },
    }
}


def get_futures_config(exchange: str, symbol: str) -> dict:
    """
    Devuelve configuración de futuros compatible con BacktestEngine.

    El slippage se pasa como slippage_ticks (valor fijo). El engine
    lo aplica como: price ± (slippage_ticks * tick_size).

    El exchange_fee se convierte de USD fijo a ratio usando contract_size
    y un precio de referencia conservador.

    Args:
        exchange: Nombre del exchange (e.g., "CME")
        symbol: Símbolo del futuro (e.g., "ES", "CL")

    Returns:
        dict con keys: tick_size, slippage_ticks, exchange_fee,
        price_precision, contract_size, currency, quote_currency

    Raises:
        ValueError: Si no existe configuración para ese exchange/symbol
    """
    if exchange not in FUTURES_CONFIG or symbol not in FUTURES_CONFIG[exchange]:
        raise ValueError(f"No se ha definido configuración para {symbol} en {exchange}")

    raw = FUTURES_CONFIG[exchange][symbol]

    return {
        "tick_size": raw["tick_size"],
        "tick_value": raw["tick_value"],
        "slippage_ticks": raw["slippage_ticks"],
        "exchange_fee": raw["exchange_fee"],
        "price_precision": raw["price_precision"],
        "contract_size": raw["contract_size"],
        "currency": raw["currency"],
        "quote_currency": raw["currency"],
    }
