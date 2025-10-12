#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test script to verify that all imports work correctly after refactoring.
This tests the new import structure without requiring full dependencies.
"""

print("=" * 60)
print("TESTING PHASE 1: Import Structure Verification")
print("=" * 60)

# Test 1: Basic enums
print("\n[1/8] Testing models.enums...")
try:
    from models.enums import (
        SignalType, MarketType, OrderType, CurrencyType,
        ExchangeName, SignalStatus, SignalPositionSide
    )
    print("[OK] models.enums - PASSED")
    print(f"   - SignalType: {list(SignalType)[:3]}")
    print(f"   - MarketType: {list(MarketType)}")
except Exception as e:
    print(f"[FAIL] models.enums - FAILED: {e}")

# Test 2: Signals
print("\n[2/8] Testing models.signals...")
try:
    from models.signals import StrategySignal
    print("[OK] models.signals - PASSED")
    print(f"   - StrategySignal class loaded")
except Exception as e:
    print(f"[FAIL] models.signals - FAILED: {e}")

# Test 3: Market definitions
print("\n[3/8] Testing models.markets...")
try:
    from models.markets.crypto_market import CryptoMarketDefinition
    from models.markets.futures_market import FuturesMarketDefinition
    print("[OK] models.markets - OK")
    print(f"   - CryptoMarketDefinition loaded")
    print(f"   - FuturesMarketDefinition loaded")
except Exception as e:
    print(f"[FAIL] models.markets - FAILED: {e}")

# Test 4: Trade definitions
print("\n[4/8] Testing models.trades...")
try:
    from models.trades.crypto_trade import CryptoTrade
    from models.trades.futures_trade import FuturesTrade
    print("[OK] models.trades - OK")
    print(f"   - CryptoTrade loaded")
    print(f"   - FuturesTrade loaded")
except Exception as e:
    print(f"[FAIL] models.trades - FAILED: {e}")

# Test 5: Config
print("\n[5/8] Testing config.market_configs...")
try:
    from config.market_configs.crypto_config import get_crypto_config, CRYPTO_CONFIG
    from config.market_configs.futures_config import get_futures_config, FUTURES_CONFIG
    print("[OK] config.market_configs - OK")
    print(f"   - Crypto exchanges: {list(CRYPTO_CONFIG.keys())}")
    print(f"   - Futures exchanges: {list(FUTURES_CONFIG.keys())}")
except Exception as e:
    print(f"[FAIL] config.market_configs - FAILED: {e}")

# Test 6: Utilities
print("\n[6/8] Testing utils.timeframe...")
try:
    from utils.timeframe import Timeframe, prepare_datetime_data
    print("[OK] utils.timeframe - OK")
    print(f"   - Available timeframes: {[t.name for t in Timeframe][:5]}")
except Exception as e:
    print(f"[FAIL] utils.timeframe - FAILED: {e}")

# Test 7: Strategies
print("\n[7/8] Testing strategies.base_strategy...")
try:
    from strategies.base_strategy import BaseStrategy
    print("[OK] strategies.base_strategy - OK")
    print(f"   - BaseStrategy class loaded")
except Exception as e:
    print(f"[FAIL] strategies.base_strategy - FAILED: {e}")

# Test 8: Data loaders
print("\n[8/8] Testing data.loaders...")
try:
    from data.loaders.data_provider import CSVDataProvider, MT5BacktestDataProvider
    print("[OK] data.loaders - OK")
    print(f"   - CSVDataProvider loaded")
    print(f"   - MT5BacktestDataProvider loaded")
except Exception as e:
    print(f"[FAIL] data.loaders - FAILED: {e}")

# Test 9: Verification of crypto config function
print("\n" + "=" * 60)
print("BONUS TEST: Config Functions")
print("=" * 60)

try:
    from config.market_configs.crypto_config import get_crypto_config
    config = get_crypto_config("Binance", "BTC")
    print("\n[OK] Crypto config function works!")
    print(f"   BTC on Binance config:")
    print(f"   - tick_size: {config['tick_size']}")
    print(f"   - exchange_fee: {config['exchange_fee']}")
    print(f"   - slippage: {config['slippage']}")
except Exception as e:
    print(f"[FAIL] Crypto config function - FAILED: {e}")

try:
    from config.market_configs.futures_config import get_futures_config
    config = get_futures_config("Binance", "BTCUSDT")
    print("\n[OK] Futures config function works!")
    print(f"   BTCUSDT on Binance config:")
    print(f"   - tick_size: {config['tick_size']}")
    print(f"   - exchange_fee: {config['exchange_fee']}")
    print(f"   - contract_size: {config['contract_size']}")
except Exception as e:
    print(f"[FAIL] Futures config function - FAILED: {e}")

print("\n" + "=" * 60)
print("TEST COMPLETED")
print("=" * 60)
