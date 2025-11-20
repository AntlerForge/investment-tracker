"""
Buy recommendation engine.

Evaluates buy signals from multiple sources:
- Congressional/Senate trading data
- Insider trading (SEC Form 4)
- Regulatory filings (SEC 13F)
- Market indicators
- Technical signals
"""

import requests
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import logging
import time
import sys
import json
from pathlib import Path

# Use Any for BeautifulSoup to avoid NameError if import fails or during type checking
BeautifulSoup = Any

try:
    from bs4 import BeautifulSoup as BS
    BeautifulSoup = BS
except ImportError:
    pass

try:
    import yfinance as yf
    YFINANCE_AVAILABLE = True
except ImportError:
    YFINANCE_AVAILABLE = False
    logging.warning("yfinance not available. Technical indicators will be limited.")

logger = logging.getLogger(__name__)

# Add scripts directory to path for imports
scripts_dir = Path(__file__).parent
sys.path.insert(0, str(scripts_dir))

try:
    from fetch_market_data import fetch_all_prices, fetch_fx_rate, fetch_macro_indicator
except ImportError:
    logger.warning("Could not import fetch_market_data functions")
    fetch_all_prices = None
    fetch_fx_rate = None
    fetch_macro_indicator = None


def fetch_congressional_trades(lookback_days: int = 30) -> List[Dict[str, Any]]:
    """
    Fetch recent Congressional/Senate stock trades.
    
    Sources (in priority order):
    1. QuiverQuant API (if API key available)
    2. CapitolTrades.com scraping (free, public data)
    3. SEC EDGAR scraping (free, but slower)
    
    Args:
        lookback_days: Number of days to look back
        
    Returns:
        List of trade dictionaries with:
        - ticker: Stock symbol
        - transaction_type: "buy" or "sell"
        - amount: Transaction amount
        - date: Transaction date
        - senator: Senator/Representative name
        - disclosure_date: When disclosed
    """
    trades = []
    
    # Try QuiverQuant API if available
    import os
    from dotenv import load_dotenv
    load_dotenv()
    api_key = os.getenv("QUIVERQUANT_API_KEY")
    
    if api_key:
        try:
            url = "https://api.quiverquant.com/beta/live/congresstrading"
            headers = {"Authorization": f"Bearer {api_key}"}
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                data = response.json()
                cutoff_date = datetime.now() - timedelta(days=lookback_days)
                for trade in data:
                    trade_date_str = trade.get("TransactionDate", "")
                    try:
                        trade_date = datetime.strptime(trade_date_str, "%Y-%m-%d")
                        if trade_date >= cutoff_date:
                            trades.append({
                                "ticker": trade.get("Ticker", "").upper(),
                                "transaction_type": trade.get("Transaction", "").lower(),
                                "amount": trade.get("Amount", 0),
                                "date": trade_date,
                                "senator": trade.get("Representative", ""),
                                "disclosure_date": trade.get("DisclosureDate", "")
                            })
                    except (ValueError, TypeError):
                        continue
                logger.info(f"Fetched {len(trades)} Congressional trades from QuiverQuant (last {lookback_days} days)")
                return trades
        except Exception as e:
            logger.warning(f"QuiverQuant API failed: {e}")
    
    # Fallback: Try CapitolTrades.com (public data, no API key needed)
    try:
        trades = fetch_capitoltrades_data(lookback_days)
        if trades:
            logger.info(f"Fetched {len(trades)} Congressional trades from CapitolTrades")
            return trades
    except Exception as e:
        logger.debug(f"CapitolTrades scraping failed: {e}")
    
    logger.info("Congressional trading data not available - add QUIVERQUANT_API_KEY to .env or enable scraping")
    return trades


def fetch_capitoltrades_data(lookback_days: int = 30) -> List[Dict[str, Any]]:
    """
    Fetch Congressional trades from free public sources.
    
    Tries multiple free sources in order:
    1. House Stock Watcher API (if available)
    2. Senate Stock Watcher API (if available)  
    3. CapitolTrades.com scraping (fallback)
    
    All of these are free public data sources.
    """
    trades = []
    cutoff_date = datetime.now() - timedelta(days=lookback_days)
    
    # Try House Stock Watcher (free public API)
    try:
        house_trades = _fetch_house_stock_watcher(cutoff_date)
        trades.extend(house_trades)
        if house_trades:
            logger.info(f"Fetched {len(house_trades)} trades from House Stock Watcher")
    except Exception as e:
        logger.debug(f"House Stock Watcher failed: {e}")
    
    # Try Senate Stock Watcher (free public API)
    try:
        senate_trades = _fetch_senate_stock_watcher(cutoff_date)
        trades.extend(senate_trades)
        if senate_trades:
            logger.info(f"Fetched {len(senate_trades)} trades from Senate Stock Watcher")
    except Exception as e:
        logger.debug(f"Senate Stock Watcher failed: {e}")
    
    # Fallback: Try CapitolTrades scraping
    if not trades:
        try:
            capitol_trades = _scrape_capitoltrades(cutoff_date)
            trades.extend(capitol_trades)
            if capitol_trades:
                logger.info(f"Scraped {len(capitol_trades)} trades from CapitolTrades")
        except Exception as e:
            logger.debug(f"CapitolTrades scraping failed: {e}")
    
    return trades


def _fetch_house_stock_watcher(cutoff_date: datetime) -> List[Dict[str, Any]]:
    """Fetch from House Stock Watcher (housestockwatcher.com)."""
    trades = []
    try:
        # House Stock Watcher has a public API endpoint
        # Try their trades endpoint
        url = "https://housestockwatcher.com/api/trades"
        headers = {'User-Agent': 'Mozilla/5.0'}
        
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            for trade in data.get('trades', []):
                parsed = _parse_stock_watcher_trade(trade, cutoff_date, 'house')
                if parsed:
                    trades.append(parsed)
    except Exception as e:
        logger.debug(f"House Stock Watcher API error: {e}")
    
    return trades


def _fetch_senate_stock_watcher(cutoff_date: datetime) -> List[Dict[str, Any]]:
    """Fetch from Senate Stock Watcher (senatestockwatcher.com)."""
    trades = []
    try:
        # Senate Stock Watcher public API
        url = "https://senatestockwatcher.com/api/trades"
        headers = {'User-Agent': 'Mozilla/5.0'}
        
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            for trade in data.get('trades', []):
                parsed = _parse_stock_watcher_trade(trade, cutoff_date, 'senate')
                if parsed:
                    trades.append(parsed)
    except Exception as e:
        logger.debug(f"Senate Stock Watcher API error: {e}")
    
    return trades


def _parse_stock_watcher_trade(trade_data: Dict, cutoff_date: datetime, source: str) -> Optional[Dict[str, Any]]:
    """Parse trade from House/Senate Stock Watcher format."""
    try:
        # Parse date - try multiple formats
        date_str = trade_data.get('transaction_date') or trade_data.get('date') or trade_data.get('filing_date')
        if not date_str:
            return None
        
        # Try different date formats
        for fmt in ["%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%m/%d/%Y"]:
            try:
                trade_date = datetime.strptime(date_str.split('T')[0], fmt)
                break
            except ValueError:
                continue
        else:
            return None
        
        if trade_date < cutoff_date:
            return None
        
        # Check if it's a buy
        transaction_type = str(trade_data.get('transaction_type', '')).lower()
        transaction = str(trade_data.get('transaction', '')).lower()
        
        if 'buy' not in transaction_type and 'purchase' not in transaction_type and \
           'buy' not in transaction and 'purchase' not in transaction:
            return None
        
        return {
            "ticker": str(trade_data.get('ticker', '')).upper(),
            "transaction_type": "buy",
            "amount": trade_data.get('amount', 0) or trade_data.get('value', 0),
            "date": trade_date,
            "senator": trade_data.get('representative') or trade_data.get('name') or trade_data.get('politician', ''),
            "disclosure_date": trade_data.get('disclosure_date', ''),
            "source": source
        }
    except (ValueError, KeyError, TypeError) as e:
        logger.debug(f"Error parsing trade: {e}")
        return None


def _scrape_capitoltrades(cutoff_date: datetime) -> List[Dict[str, Any]]:
    """Fallback: Scrape CapitolTrades.com (basic implementation)."""
    trades = []
    try:
        from bs4 import BeautifulSoup
        
        url = "https://www.capitoltrades.com/trades"
        headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'}
        
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Look for JSON data in script tags
            scripts = soup.find_all('script', type='application/json')
            for script in scripts:
                try:
                    data = json.loads(script.string)
                    if isinstance(data, dict):
                        # Try to find trades in various possible structures
                        trade_list = data.get('trades') or data.get('data') or data.get('results', [])
                        for trade in trade_list:
                            parsed = _parse_stock_watcher_trade(trade, cutoff_date, 'capitoltrades')
                            if parsed:
                                trades.append(parsed)
                except (json.JSONDecodeError, KeyError, TypeError):
                    continue
    except ImportError:
        logger.debug("BeautifulSoup4 not available for CapitolTrades scraping")
    except Exception as e:
        logger.debug(f"CapitolTrades scraping error: {e}")
    
    return trades


def fetch_insider_trades_sec(symbol: str, lookback_days: int = 30) -> List[Dict[str, Any]]:
    """
    Fetch insider trading data from SEC EDGAR (Form 4 filings).
    
    Sources:
    1. Finnhub API (free tier available)
    2. SEC EDGAR direct scraping
    3. sec-api.io (paid, but more reliable)
    
    Args:
        symbol: Stock ticker symbol
        lookback_days: Number of days to look back
        
    Returns:
        List of insider trade records with:
        - ticker: Stock symbol
        - transaction_type: "buy" or "sell"
        - shares: Number of shares
        - price: Transaction price
        - date: Transaction date
        - insider: Insider name/title
    """
    trades = []
    
    # Try Finnhub API (free tier: 60 calls/minute)
    import os
    from dotenv import load_dotenv
    load_dotenv()
    finnhub_key = os.getenv("FINNHUB_API_KEY")
    
    if finnhub_key:
        try:
            url = f"https://finnhub.io/api/v1/stock/insider-transactions"
            params = {
                "symbol": symbol,
                "token": finnhub_key
            }
            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                cutoff_date = datetime.now() - timedelta(days=lookback_days)
                
                for transaction in data.get("data", []):
                    transaction_date_str = transaction.get("transactionDate", "")
                    try:
                        transaction_date = datetime.strptime(transaction_date_str, "%Y-%m-%d")
                        if transaction_date >= cutoff_date:
                            transaction_code = transaction.get("transactionCode", "").upper()
                            # Finnhub transaction codes for BUYS:
                            # P = Purchase, A = Acquisition, G = Gift (received), I = Discretionary
                            # S = Sale, D = Disposition, F = Payment, J = Other
                            buy_codes = ['P', 'A', 'G', 'I']
                            
                            if transaction_code in buy_codes:
                                trades.append({
                                    "ticker": symbol.upper(),
                                    "transaction_type": "buy",
                                    "shares": transaction.get("share", 0),
                                    "price": transaction.get("transactionPrice", 0),
                                    "date": transaction_date,
                                    "insider": transaction.get("name", ""),
                                    "title": transaction.get("position", ""),
                                    "transaction_code": transaction_code
                                })
                    except (ValueError, TypeError) as e:
                        logger.debug(f"Error parsing transaction date: {e}")
                        continue
                
                if trades:
                    logger.info(f"Fetched {len(trades)} insider buy transactions for {symbol} from Finnhub")
                    return trades
        except Exception as e:
            logger.debug(f"Finnhub API failed for {symbol}: {e}")
    
    # Fallback: SEC EDGAR scraping (more complex, slower)
    # Can be implemented with sec-api.io or direct EDGAR access
    logger.debug(f"Insider trading data not available for {symbol} (add FINNHUB_API_KEY to .env)")
    return trades


def fetch_institutional_holdings(symbol: str, lookback_days: int = 90) -> Dict[str, Any]:
    """
    Fetch institutional holdings changes from 13F filings.
    
    13F filings show what large institutions (hedge funds, pension funds) are buying/selling.
    This is valuable because institutions often have early information.
    
    Args:
        symbol: Stock ticker symbol
        lookback_days: Number of days to look back
        
    Returns:
        Dictionary with:
        - net_buyers: Number of institutions that increased holdings
        - net_sellers: Number of institutions that decreased holdings
        - total_institutions: Total number of institutions holding
        - recent_buyers: List of institutions that recently bought
    """
    holdings_data = {
        "net_buyers": 0,
        "net_sellers": 0,
        "total_institutions": 0,
        "recent_buyers": []
    }
    
    # 13F data requires:
    # - sec-api.io (paid, easiest)
    # - Direct SEC EDGAR scraping (free, complex)
    # - whalewisdom.com scraping (free, but rate-limited)
    
    # For now, placeholder - can be implemented
    logger.debug(f"13F institutional holdings not yet implemented for {symbol}")
    return holdings_data


def _get_technical_indicators_unused(symbol: str) -> Dict[str, Any]:
    """
    Get technical indicators for a stock using yfinance.
    
    Returns:
        Dictionary with RSI, moving averages, momentum, etc.
    """
    if not YFINANCE_AVAILABLE:
        return {}
    
    try:
        ticker = yf.Ticker(symbol)
        
        # Get historical data
        hist = ticker.history(period="6mo", interval="1d")
        if hist.empty:
            return {}
        
        # Calculate RSI (14-day)
        delta = hist['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        current_rsi = rsi.iloc[-1] if not rsi.empty else None
        
        # Moving averages
        ma_20 = hist['Close'].rolling(window=20).mean().iloc[-1] if len(hist) >= 20 else None
        ma_50 = hist['Close'].rolling(window=50).mean().iloc[-1] if len(hist) >= 50 else None
        current_price = hist['Close'].iloc[-1]
        
        # Momentum (price change over periods)
        price_5d_ago = hist['Close'].iloc[-6] if len(hist) >= 6 else None
        price_20d_ago = hist['Close'].iloc[-21] if len(hist) >= 21 else None
        
        momentum_5d = ((current_price - price_5d_ago) / price_5d_ago * 100) if price_5d_ago else None
        momentum_20d = ((current_price - price_20d_ago) / price_20d_ago * 100) if price_20d_ago else None
        
        # Volume analysis
        avg_volume = hist['Volume'].rolling(window=20).mean().iloc[-1] if len(hist) >= 20 else None
        current_volume = hist['Volume'].iloc[-1]
        volume_ratio = (current_volume / avg_volume) if avg_volume and avg_volume > 0 else None
        
        # Price vs moving averages
        above_ma20 = (current_price > ma_20) if ma_20 else None
        above_ma50 = (current_price > ma_50) if ma_50 else None
        
        return {
            "rsi": current_rsi,
            "ma_20": ma_20,
            "ma_50": ma_50,
            "current_price": current_price,
            "momentum_5d": momentum_5d,
            "momentum_20d": momentum_20d,
            "volume_ratio": volume_ratio,
            "above_ma20": above_ma20,
            "above_ma50": above_ma50
        }
    except Exception as e:
        logger.debug(f"Could not get technical indicators for {symbol}: {e}")
        return {}


def _get_analyst_data_unused(symbol: str) -> Dict[str, Any]:
    """
    Get analyst ratings and price targets from yfinance.
    
    Returns:
        Dictionary with recommendations, target price, etc.
    """
    if not YFINANCE_AVAILABLE:
        return {}
    
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info
        
        current_price = info.get('currentPrice') or info.get('regularMarketPrice')
        target_price = info.get('targetMeanPrice') or info.get('targetHighPrice')
        
        # Analyst recommendations
        recommendations = info.get('recommendationKey', '').upper()
        recommendation_mean = info.get('recommendationMean')
        
        # Calculate upside potential
        upside_pct = None
        if current_price and target_price:
            upside_pct = ((target_price - current_price) / current_price) * 100
        
        # Earnings data
        earnings_date = info.get('exDividendDate') or info.get('nextFiscalYearEnd')
        earnings_growth = info.get('earningsQuarterlyGrowth')
        
        return {
            "current_price": current_price,
            "target_price": target_price,
            "upside_pct": upside_pct,
            "recommendation": recommendations,
            "recommendation_mean": recommendation_mean,
            "earnings_growth": earnings_growth
        }
    except Exception as e:
        logger.debug(f"Could not get analyst data for {symbol}: {e}")
        return {}


def evaluate_buy_signals(
    symbol: str,
    congressional_trades: List[Dict[str, Any]],
    insider_trades: List[Dict[str, Any]],
    market_data: Dict[str, Optional[float]],
    buy_config: Dict[str, Any],
    institutional_data: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Evaluate buy signals based on REGULATORY and EARLY INDICATORS only.
    
    Focus on:
    - Congressional/Senate trading (politicians have early information)
    - Insider trading (corporate insiders know before public)
    - Institutional holdings (13F filings - smart money)
    - Market conditions (VIX for entry timing)
    
    Args:
        symbol: Stock ticker symbol
        congressional_trades: List of Congressional trades
        insider_trades: List of insider trades
        market_data: Market data dictionary
        buy_config: Buy signal configuration
        institutional_data: 13F institutional holdings data
        
    Returns:
        Dictionary with buy signals and confidence score
    """
    signals = {
        "congressional_buy": False,
        "congressional_cluster": 0,
        "insider_buying": False,
        "institutional_buying": False,
        "vix_low": False,
        "confidence_score": 0,
        "reasons": []
    }
    
    # Congressional buy signals (STRONGEST SIGNAL - politicians have early info)
    symbol_trades = [t for t in congressional_trades if t.get("ticker", "").upper() == symbol.upper()]
    buy_trades = [t for t in symbol_trades if t.get("transaction_type") == "buy"]
    
    if buy_trades:
        signals["congressional_buy"] = True
        signals["congressional_cluster"] = len(buy_trades)
        
        # Get senator names for context
        senators = [t.get("senator", "Unknown") for t in buy_trades[:3]]  # First 3
        senator_list = ", ".join(senators) if senators else "Multiple"
        
        if len(buy_trades) >= buy_config.get("congressional_cluster_threshold", 2):
            signals["confidence_score"] += 40  # Increased weight
            signals["reasons"].append(f"STRONG SIGNAL: {len(buy_trades)}+ Congressional buys ({senator_list})")
        else:
            signals["confidence_score"] += 25  # Increased weight
            signals["reasons"].append(f"Congressional buy: {senator_list} bought {symbol}")
    
    # Insider buying signals (VERY STRONG - insiders know before public)
    insider_buys = [t for t in insider_trades if t.get("transaction_type") == "buy"]
    if insider_buys:
        signals["insider_buying"] = True
        total_shares = sum(t.get("shares", 0) for t in insider_buys)
        signals["confidence_score"] += 30  # Increased weight
        signals["reasons"].append(f"Insider buying: {len(insider_buys)} transaction(s), {total_shares:,.0f} shares")
        
        # If multiple insiders buying, even stronger signal
        if len(insider_buys) >= 2:
            signals["confidence_score"] += 10
            signals["reasons"].append(f"Multiple insiders buying - strong conviction signal")
    
    # Institutional buying (13F filings - smart money)
    if institutional_data:
        net_buyers = institutional_data.get("net_buyers", 0)
        if net_buyers > 0:
            signals["institutional_buying"] = True
            signals["confidence_score"] += 20
            signals["reasons"].append(f"{net_buyers} institutions increased holdings (13F filings)")
    
    # VIX low (good entry conditions - but only if we have other signals)
    # Don't use VIX alone, only as a timing signal
    vix = market_data.get("VIX")
    vix_threshold = buy_config.get("vix_low_threshold", 15.0)
    if vix and vix < vix_threshold and signals["confidence_score"] > 0:
        signals["vix_low"] = True
        signals["confidence_score"] += 5  # Lower weight - just timing
        signals["reasons"].append(f"Low volatility (VIX: {vix:.1f}) - good entry timing")
    
    return signals


def generate_buy_recommendations(
    available_funds: float,
    watchlist: Optional[List[str]] = None,
    buy_config: Dict[str, Any] = None
) -> List[Dict[str, Any]]:
    """
    Generate buy recommendations based on available funds and signals.
    
    Args:
        available_funds: Amount available to invest (GBP)
        watchlist: Optional list of symbols to consider
        buy_config: Buy signal configuration
        
    Returns:
        List of buy recommendations with:
        - symbol: Stock ticker
        - recommendation: "STRONG BUY", "BUY", "CONSIDER"
        - confidence_score: 0-100
        - reasons: List of reasons
        - suggested_allocation: Suggested amount to invest
        - current_price: Current stock price
        - current_price_gbp: Current price in GBP
    """
    if buy_config is None:
        buy_config = {}
    
    recommendations = []
    
    # Clear cache to ensure fresh data
    from fetch_market_data import clear_cache
    clear_cache()
    logger.debug("Cleared cache in buy_recommendations")
    
    # Fetch Congressional trades
    congressional_trades = fetch_congressional_trades()
    
    # Get unique symbols from Congressional trades
    symbols_to_evaluate = set()
    if watchlist:
        symbols_to_evaluate.update([s.upper() for s in watchlist])
    
    for trade in congressional_trades:
        if trade.get("transaction_type") == "buy":
            ticker = trade.get("ticker", "").upper()
            if ticker:
                symbols_to_evaluate.add(ticker)
    
    # If no symbols from Congressional trades or watchlist, use a default watchlist
    # of popular stocks that might have signals
    if not symbols_to_evaluate:
        logger.info("No symbols from Congressional trades or watchlist. Using default watchlist.")
        # Default watchlist of commonly traded stocks
        default_watchlist = ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "AMD", "INTC"]
        symbols_to_evaluate.update(default_watchlist)
        logger.info(f"Evaluating default watchlist: {', '.join(symbols_to_evaluate)}")
    
    # Fetch market data
    market_data = {}
    if fetch_macro_indicator:
        try:
            vix = fetch_macro_indicator("VIX")
            if vix is not None:
                market_data["VIX"] = vix
        except Exception as e:
            logger.warning(f"Could not fetch VIX: {e}")
    
    # Fetch prices for all symbols - force fresh
    prices = {}
    if fetch_all_prices:
        try:
            prices = fetch_all_prices(list(symbols_to_evaluate), force_refresh=True)
        except Exception as e:
            logger.warning(f"Could not fetch prices: {e}")
    
    # Fetch FX rate - force fresh
    fx_rate = 0.79  # Default
    if fetch_fx_rate:
        try:
            fx_rate = fetch_fx_rate("USD", "GBP", force_refresh=True) or 0.79
        except Exception as e:
            logger.warning(f"Could not fetch FX rate: {e}")
    
    # Evaluate each symbol
    for symbol in symbols_to_evaluate:
        if not symbol:
            continue
        
        # Get current price first
        current_price = prices.get(symbol)
        if not current_price:
            # Skip if we can't get price data
            continue
        
        # Fetch insider trades (REGULATORY DATA)
        insider_trades = fetch_insider_trades_sec(symbol)
        
        # Fetch institutional holdings (13F filings - REGULATORY DATA)
        institutional_data = fetch_institutional_holdings(symbol)
        
        # Evaluate buy signals based ONLY on regulatory/early indicators
        signals = evaluate_buy_signals(
            symbol, congressional_trades, insider_trades, market_data, buy_config,
            institutional_data=institutional_data
        )
        
        # ONLY show stocks with actual regulatory signals (Congressional, insider, or institutional)
        # No generic recommendations
        min_confidence = buy_config.get("min_confidence_to_show", 15)
        if signals["confidence_score"] < min_confidence:
            # Skip stocks with no regulatory signals
            continue
        
        # Must have at least one of: Congressional buy, insider buy, or institutional buy
        if not (signals["congressional_buy"] or signals["insider_buying"] or signals.get("institutional_buying", False)):
            continue
        
        # Determine recommendation level
        thresholds = buy_config.get("confidence_thresholds", {})
        strong_buy_threshold = thresholds.get("strong_buy", 50)
        buy_threshold = thresholds.get("buy", 30)
        
        if signals["confidence_score"] >= strong_buy_threshold:
            recommendation = "STRONG BUY"
        elif signals["confidence_score"] >= buy_threshold:
            recommendation = "BUY"
        else:
            recommendation = "CONSIDER"
        
        # Calculate price in GBP (current_price already fetched above)
        current_price_gbp = None
        if current_price:
            # Determine currency
            if ".L" in symbol:
                currency = "GBP"
                current_price_gbp = current_price
            else:
                currency = "USD"
                current_price_gbp = current_price * fx_rate
        
        rec = {
            "symbol": symbol,
            "recommendation": recommendation,
            "confidence_score": signals["confidence_score"],
            "reasons": signals["reasons"],
            "congressional_cluster": signals["congressional_cluster"],
            "insider_buying": signals["insider_buying"],
            "institutional_buying": signals.get("institutional_buying", False),
            "vix_low": signals["vix_low"],
            "current_price": current_price,
            "current_price_gbp": current_price_gbp
        }
        
        recommendations.append(rec)
    
    # Sort by confidence score
    recommendations.sort(key=lambda x: x["confidence_score"], reverse=True)
    
    # Calculate suggested allocations
    if available_funds > 0 and recommendations:
        total_confidence = sum(r["confidence_score"] for r in recommendations)
        for rec in recommendations:
            # Allocate proportionally to confidence
            allocation_pct = rec["confidence_score"] / total_confidence if total_confidence > 0 else 0
            rec["suggested_allocation_gbp"] = available_funds * allocation_pct
            # Calculate suggested shares if price available
            if rec.get("current_price_gbp"):
                rec["suggested_shares"] = int(rec["suggested_allocation_gbp"] / rec["current_price_gbp"])
            else:
                rec["suggested_shares"] = None
    else:
        for rec in recommendations:
            rec["suggested_allocation_gbp"] = 0.0
            rec["suggested_shares"] = None
    
    return recommendations

