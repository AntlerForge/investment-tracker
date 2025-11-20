"""
Market data fetching module.

Handles fetching of:
- Stock prices
- FX rates (GBP/USD)
- Macro indicators (VIX, HYG, QQQ, US10Y)
- Optional: insider trades, options activity
"""

import os
import json
import time
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from pathlib import Path
import logging

try:
    import yfinance as yf
    YFINANCE_AVAILABLE = True
except ImportError:
    YFINANCE_AVAILABLE = False
    logging.warning("yfinance not available. Install with: pip install yfinance")

logger = logging.getLogger(__name__)

# Simple in-memory cache with TTL
_cache: Dict[str, tuple[float, Any]] = {}
_cache_ttl = 1 * 60  # 1 minute default (reduced for more frequent updates, yfinance has 15-20min delay anyway)

def clear_cache():
    """Clear the entire price cache. Use this to force fresh data fetches."""
    global _cache
    _cache.clear()
    logger.debug("Price cache cleared")


def _get_cache_key(prefix: str, *args) -> str:
    """Generate cache key from prefix and arguments."""
    return f"{prefix}:{':'.join(str(a) for a in args)}"


def _get_cached(key: str) -> Optional[Any]:
    """Get value from cache if not expired."""
    if key in _cache:
        timestamp, value = _cache[key]
        if time.time() - timestamp < _cache_ttl:
            return value
        del _cache[key]
    return None


def _set_cache(key: str, value: Any):
    """Store value in cache."""
    _cache[key] = (time.time(), value)


def _fetch_with_yfinance(symbol: str, date: Optional[datetime] = None) -> Optional[float]:
    """Fetch price using yfinance."""
    if not YFINANCE_AVAILABLE:
        return None
    
    try:
        ticker = yf.Ticker(symbol)
        
        if date:
            # Historical data
            end_date = date + timedelta(days=1)
            hist = ticker.history(start=date, end=end_date, interval="1d")
            if not hist.empty:
                price = float(hist['Close'].iloc[-1])
        else:
            # Latest data
            info = ticker.info
            if 'currentPrice' in info and info['currentPrice'] is not None:
                price = float(info['currentPrice'])
            elif 'regularMarketPrice' in info and info['regularMarketPrice'] is not None:
                price = float(info['regularMarketPrice'])
            else:
                # Fallback to recent history
                hist = ticker.history(period="1d", interval="1d")
                if not hist.empty:
                    price = float(hist['Close'].iloc[-1])
                else:
                    return None
        
        # Handle UK stocks (.L suffix) - yfinance returns prices in pence for LSE stocks
        # Convert pence to pounds by dividing by 100
        if symbol.endswith('.L'):
            # UK stocks on LSE are quoted in pence, convert to pounds
            price = price / 100.0
            logger.debug(f"Converted {symbol} price from pence to pounds: {price}")
        
        return price
        
    except Exception as e:
        logger.warning(f"Failed to fetch {symbol} with yfinance: {e}")
    
    return None


def fetch_stock_price(symbol: str, date: Optional[datetime] = None, force_refresh: bool = False) -> Optional[float]:
    """
    Fetch current or historical stock price for a given symbol.
    
    Args:
        symbol: Stock ticker symbol (e.g., "NVDA", "AML.L")
        date: Optional date for historical price. Defaults to latest.
        force_refresh: If True, bypass cache and fetch fresh data
        
    Returns:
        Price in native currency, or None if unavailable
    """
    cache_key = _get_cache_key("price", symbol, date.isoformat() if date else "latest")
    
    # Only check cache if not forcing refresh
    if not force_refresh:
        cached = _get_cached(cache_key)
        if cached is not None:
            return cached
    
    # Fetch fresh price
    price = _fetch_with_yfinance(symbol, date)
    if price is not None:
        _set_cache(cache_key, price)
    
    return price


def fetch_fx_rate(base_currency: str, target_currency: str, date: Optional[datetime] = None, force_refresh: bool = False) -> Optional[float]:
    """
    Fetch foreign exchange rate.
    
    Args:
        base_currency: Base currency code (e.g., "USD")
        target_currency: Target currency code (e.g., "GBP")
        date: Optional date for historical rate. Defaults to latest.
        force_refresh: If True, bypass cache and fetch fresh data
        
    Returns:
        Exchange rate (target/base), or None if unavailable
    """
    if base_currency == target_currency:
        return 1.0
    
    # For GBP/USD, we fetch GBPUSD=X
    if base_currency == "USD" and target_currency == "GBP":
        pair = "GBPUSD=X"
        inverse = True
    elif base_currency == "GBP" and target_currency == "USD":
        pair = "GBPUSD=X"
        inverse = False
    else:
        # Try generic pair format
        pair = f"{target_currency}{base_currency}=X"
        inverse = False
    
    cache_key = _get_cache_key("fx", pair, date.isoformat() if date else "latest")
    
    # Only check cache if not forcing refresh
    if not force_refresh:
        cached = _get_cached(cache_key)
        if cached is not None:
            return 1.0 / cached if inverse else cached
    
    # Fetch fresh rate
    rate = _fetch_with_yfinance(pair, date)
    if rate is not None:
        result = 1.0 / rate if inverse else rate
        _set_cache(cache_key, result)
        return result
    
    return None


def fetch_macro_indicator(indicator_name: str, date: Optional[datetime] = None) -> Optional[float]:
    """
    Fetch macro economic indicator value.
    
    Supported indicators:
    - VIX (volatility index)
    - HYG (high yield bond ETF)
    - QQQ (NASDAQ ETF)
    - US10Y (10-year Treasury yield)
    
    Args:
        indicator_name: Name of the indicator
        date: Optional date for historical value. Defaults to latest.
        
    Returns:
        Indicator value, or None if unavailable
    """
    # Map indicator names to symbols
    symbol_map = {
        "VIX": "^VIX",
        "HYG": "HYG",
        "QQQ": "QQQ",
        "US10Y": "^TNX",  # 10-year Treasury yield
    }
    
    symbol = symbol_map.get(indicator_name.upper())
    if not symbol:
        logger.warning(f"Unknown indicator: {indicator_name}")
        return None
    
    cache_key = _get_cache_key("macro", indicator_name, date.isoformat() if date else "latest")
    cached = _get_cached(cache_key)
    if cached is not None:
        return cached
    
    value = _fetch_with_yfinance(symbol, date)
    if value is not None:
        _set_cache(cache_key, value)
    
    return value


def fetch_all_prices(symbols: List[str], date: Optional[datetime] = None, force_refresh: bool = False) -> Dict[str, Optional[float]]:
    """
    Fetch prices for multiple symbols in batch.
    
    Args:
        symbols: List of stock ticker symbols
        date: Optional date for historical prices. Defaults to latest.
        force_refresh: If True, clear cache before fetching
        
    Returns:
        Dictionary mapping symbol to price (or None if unavailable)
    """
    if force_refresh:
        # Clear cache for these specific symbols
        for symbol in symbols:
            cache_key = _get_cache_key("price", symbol, date.isoformat() if date else "latest")
            if cache_key in _cache:
                del _cache[cache_key]
    
    results = {}
    for symbol in symbols:
        results[symbol] = fetch_stock_price(symbol, date, force_refresh=force_refresh)
        # Small delay to avoid rate limiting
        time.sleep(0.1)
    return results


def select_data_source(data_sources_config: Dict[str, Any]) -> str:
    """
    Select appropriate data source based on configuration and availability.
    
    Args:
        data_sources_config: Configuration from data_sources.yaml
        
    Returns:
        Selected provider name (e.g., "alphavantage", "yfinance")
    """
    # For now, always use yfinance as it's free and available
    # In the future, can check for API keys and select accordingly
    if YFINANCE_AVAILABLE:
        return "yfinance"
    
    # Check for Alpha Vantage API key
    if os.getenv("ALPHAVANTAGE_API_KEY"):
        return "alphavantage"
    
    return "yfinance"  # Default fallback


def fetch_insider_trades(symbol: str, lookback_days: int = 14) -> List[Dict[str, Any]]:
    """
    Fetch recent insider trading activity for a symbol.
    
    Args:
        symbol: Stock ticker symbol
        lookback_days: Number of days to look back
        
    Returns:
        List of insider trade records (may be empty if data unavailable)
    """
    # Insider trading data requires paid APIs or web scraping
    # For now, return empty list - can be extended later
    logger.debug(f"Insider trades not yet implemented for {symbol}")
    return []


def fetch_options_activity(symbol: str) -> Dict[str, Any]:
    """
    Fetch options activity metrics for a symbol.
    
    Args:
        symbol: Stock ticker symbol
        
    Returns:
        Dictionary with options metrics (put/call ratios, volume, etc.)
        Returns empty dict if data unavailable
    """
    # Options data requires paid APIs or complex web scraping
    # For now, return empty dict - can be extended later
    logger.debug(f"Options activity not yet implemented for {symbol}")
    return {}

