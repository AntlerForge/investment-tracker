"""
Multi-Factor Buy Recommendation Engine v2

Focus: Medium/High Risk, High Reward opportunities
Approach: Multi-factor analysis combining early signals, technical indicators, and risk/reward metrics

Key Principles:
1. Early signals only (7-14 days for insider/congressional trades)
2. Multi-factor scoring (not just insider trading)
3. Medium/high risk, high reward focus
4. Technical confirmation required
"""

import requests
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
import logging
import sys
import importlib.util
from pathlib import Path

# Use Any for BeautifulSoup to avoid NameError if import fails
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

# Add scripts directory to path
scripts_dir = Path(__file__).parent
sys.path.insert(0, str(scripts_dir))

try:
    from fetch_market_data import fetch_all_prices, fetch_fx_rate, fetch_macro_indicator
except ImportError:
    logger.warning("Could not import fetch_market_data functions")
    fetch_all_prices = None
    fetch_fx_rate = None
    fetch_macro_indicator = None

# Import existing functions from buy_recommendations module
# Use importlib to avoid circular dependency
buy_rec_path = scripts_dir / "buy_recommendations.py"
if buy_rec_path.exists():
    try:
        spec = importlib.util.spec_from_file_location("buy_recommendations", buy_rec_path)
        buy_rec_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(buy_rec_module)
        
        fetch_congressional_trades = buy_rec_module.fetch_congressional_trades
        fetch_insider_trades_sec = buy_rec_module.fetch_insider_trades_sec
        fetch_institutional_holdings = buy_rec_module.fetch_institutional_holdings
    except Exception as e:
        logger.warning(f"Could not import from buy_recommendations: {e}")
        fetch_congressional_trades = None
        fetch_insider_trades_sec = None
        fetch_institutional_holdings = None
else:
    logger.warning("Could not find buy_recommendations.py, some functions may not work")
    fetch_congressional_trades = None
    fetch_insider_trades_sec = None
    fetch_institutional_holdings = None


def get_technical_indicators(symbol: str, lookback_days: int = 60) -> Dict[str, Any]:
    """
    Get comprehensive technical indicators for a symbol.
    
    Returns:
        Dictionary with technical indicators:
        - rsi: RSI (14-day)
        - momentum_5d, momentum_10d, momentum_20d: Price momentum
        - volume_ratio: Current volume vs 20-day average
        - above_ma20, above_ma50: Price vs moving averages
        - ma20, ma50: Moving average values
        - price_change_5d, price_change_20d: Percentage changes
        - volatility: 20-day volatility
        - support_level: Recent low (potential support)
        - resistance_level: Recent high (potential resistance)
    """
    if not YFINANCE_AVAILABLE:
        return {}
    
    try:
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period=f"{lookback_days}d", interval="1d")
        
        if hist.empty or len(hist) < 20:
            return {}
        
        current_price = hist['Close'].iloc[-1]
        
        # RSI calculation
        delta = hist['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        current_rsi = rsi.iloc[-1] if not rsi.empty else None
        
        # Moving averages
        ma_20 = hist['Close'].rolling(window=20).mean().iloc[-1] if len(hist) >= 20 else None
        ma_50 = hist['Close'].rolling(window=50).mean().iloc[-1] if len(hist) >= 50 else None
        
        # Momentum
        price_5d_ago = hist['Close'].iloc[-6] if len(hist) >= 6 else None
        price_10d_ago = hist['Close'].iloc[-11] if len(hist) >= 11 else None
        price_20d_ago = hist['Close'].iloc[-21] if len(hist) >= 21 else None
        
        momentum_5d = ((current_price - price_5d_ago) / price_5d_ago * 100) if price_5d_ago else None
        momentum_10d = ((current_price - price_10d_ago) / price_10d_ago * 100) if price_10d_ago else None
        momentum_20d = ((current_price - price_20d_ago) / price_20d_ago * 100) if price_20d_ago else None
        
        # Volume analysis
        avg_volume = hist['Volume'].rolling(window=20).mean().iloc[-1] if len(hist) >= 20 else None
        current_volume = hist['Volume'].iloc[-1]
        volume_ratio = (current_volume / avg_volume) if avg_volume and avg_volume > 0 else None
        
        # Volatility (20-day standard deviation of returns)
        returns = hist['Close'].pct_change()
        volatility = returns.rolling(window=20).std().iloc[-1] * 100 if len(hist) >= 20 else None
        
        # Support and resistance levels (recent lows and highs)
        support_level = hist['Low'].rolling(window=20).min().iloc[-1] if len(hist) >= 20 else None
        resistance_level = hist['High'].rolling(window=20).max().iloc[-1] if len(hist) >= 20 else None
        
        # Price changes
        price_change_5d = momentum_5d
        price_change_20d = momentum_20d
        
        return {
            "rsi": current_rsi,
            "momentum_5d": momentum_5d,
            "momentum_10d": momentum_10d,
            "momentum_20d": momentum_20d,
            "volume_ratio": volume_ratio,
            "above_ma20": (current_price > ma_20) if ma_20 else None,
            "above_ma50": (current_price > ma_50) if ma_50 else None,
            "ma20": ma_20,
            "ma50": ma_50,
            "current_price": current_price,
            "price_change_5d": price_change_5d,
            "price_change_20d": price_change_20d,
            "volatility": volatility,
            "support_level": support_level,
            "resistance_level": resistance_level,
            "distance_to_support": ((current_price - support_level) / support_level * 100) if support_level else None,
            "distance_to_resistance": ((resistance_level - current_price) / current_price * 100) if resistance_level else None
        }
    except Exception as e:
        logger.debug(f"Could not get technical indicators for {symbol}: {e}")
        return {}


def get_analyst_data(symbol: str) -> Dict[str, Any]:
    """
    Get analyst ratings and price targets.
    
    Returns:
        Dictionary with analyst data:
        - target_price: Average target price
        - upside_pct: Upside potential percentage
        - recommendation: Analyst recommendation
    """
    if not YFINANCE_AVAILABLE:
        return {}
    
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info
        
        current_price = info.get('currentPrice') or info.get('regularMarketPrice')
        target_price = info.get('targetMeanPrice') or info.get('targetHighPrice')
        
        upside_pct = None
        if current_price and target_price and target_price > 0:
            upside_pct = ((target_price - current_price) / current_price) * 100
        
        recommendation = info.get('recommendationKey', '').upper()
        
        return {
            "target_price": target_price,
            "upside_pct": upside_pct,
            "recommendation": recommendation,
            "current_price": current_price
        }
    except Exception as e:
        logger.debug(f"Could not get analyst data for {symbol}: {e}")
        return {}


def evaluate_multi_factor_signals(
    symbol: str,
    congressional_trades: List[Dict[str, Any]],
    insider_trades: List[Dict[str, Any]],
    technical_indicators: Dict[str, Any],
    analyst_data: Dict[str, Any],
    market_data: Dict[str, Optional[float]],
    buy_config: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Evaluate multi-factor buy signals with detailed scoring.
    
    Factors:
    1. Early Signals (30 points max)
       - Recent insider buying (last 7-14 days) - 15 points
       - Recent congressional buying (last 7-14 days) - 15 points
    
    2. Technical Indicators (30 points max)
       - Momentum (5d, 10d, 20d) - 10 points
       - RSI oversold/neutral - 5 points
       - Volume surge - 5 points
       - Price vs moving averages - 5 points
       - Breakout patterns - 5 points
    
    3. Risk/Reward Metrics (25 points max)
       - Upside potential (analyst targets) - 10 points
       - Volatility (medium/high risk) - 5 points
       - Support/resistance levels - 5 points
       - Recent price action - 5 points
    
    4. Market Conditions (15 points max)
       - VIX levels - 5 points
       - Sector momentum - 5 points
       - Market timing - 5 points
    
    Returns:
        Dictionary with detailed signal breakdown and total score
    """
    signals = {
        "early_signals": {
            "recent_insider_buying": False,
            "recent_congressional_buying": False,
            "insider_details": {},
            "congressional_details": {},
            "score": 0,
            "max_score": 30
        },
        "technical_signals": {
            "momentum": None,
            "rsi_signal": None,
            "volume_surge": False,
            "ma_alignment": None,
            "breakout": False,
            "score": 0,
            "max_score": 30
        },
        "risk_reward": {
            "upside_potential": None,
            "volatility": None,
            "support_level": None,
            "recent_action": None,
            "score": 0,
            "max_score": 25
        },
        "market_conditions": {
            "vix_signal": None,
            "sector_momentum": None,
            "timing": None,
            "score": 0,
            "max_score": 15
        },
        "total_score": 0,
        "max_total_score": 100,
        "reasons": [],
        "risk_level": "UNKNOWN",
        "reward_potential": "UNKNOWN"
    }
    
    # ===== 1. EARLY SIGNALS (30 points) =====
    #
    # We distinguish between:
    # - data_lookback_days: how far back we fetch/consider data
    # - focus_days: window for "fresh" signals that get full weight
    #
    # Older signals are still considered but down‑weighted based on staleness.
    data_lookback_days = buy_config.get("early_signal_data_days", buy_config.get("early_signal_days", 90))
    focus_days = buy_config.get("early_signal_focus_days", 21)
    now = datetime.now()
    cutoff_date = now - timedelta(days=data_lookback_days)
    
    recent_insider_buys = [
        t for t in insider_trades 
        if t.get("transaction_type") == "buy" 
        and t.get("date") and t.get("date") >= cutoff_date
    ]
    
    if recent_insider_buys:
        signals["early_signals"]["recent_insider_buying"] = True
        
        # Calculate total value
        total_value = sum(t.get("value", 0) or 0 for t in recent_insider_buys)
        total_shares = sum(t.get("shares", 0) or 0 for t in recent_insider_buys)
        
        # Score based on recency and size
        days_ago_list = [(now - t.get("date")).days for t in recent_insider_buys if t.get("date")]
        most_recent_days = min(days_ago_list) if days_ago_list else data_lookback_days
        
        # Recency weighting:
        # - <= focus_days → full weight
        # - focus_days .. data_lookback_days → linearly down‑weight to 20%
        if most_recent_days <= focus_days:
            recency_weight = 1.0
        else:
            span = max(1, data_lookback_days - focus_days)
            recency_weight = max(0.2, 1.0 - (most_recent_days - focus_days) / span)
        base_recency_points = 15.0
        recency_score = base_recency_points * recency_weight
        
        # Size bonus (larger purchases = more conviction)
        # Cap contribution so very large programmes (e.g. Elon/TSLA) don't dominate
        size_bonus = 0.0
        if total_value > 0:
            scaled = min(total_value, 25_000_000)  # treat anything above $25m as max for scoring
            size_bonus = 5.0 * (scaled / 25_000_000)
        
        # Cluster bonus (multiple insiders)
        cluster_bonus = 3 if len(recent_insider_buys) >= 2 else 0
        
        insider_score = min(15, recency_score + size_bonus + cluster_bonus)
        signals["early_signals"]["score"] += insider_score
        
        signals["early_signals"]["insider_details"] = {
            "count": len(recent_insider_buys),
            "total_value_usd": total_value,
            "total_shares": total_shares,
            "most_recent_days_ago": most_recent_days,
            "insiders": [t.get("insider", "Unknown") for t in recent_insider_buys[:3]]
        }
        
        signals["reasons"].append(
            f"Recent insider buying: {len(recent_insider_buys)} transaction(s) in last {most_recent_days} days, "
            f"${total_value:,.0f} value"
        )
    
    # Recent congressional buying (same data/lookback logic as insiders)
    recent_congressional_buys = [
        t for t in congressional_trades
        if t.get("transaction_type") == "buy"
        and t.get("ticker", "").upper() == symbol.upper()
        and t.get("date") and t.get("date") >= cutoff_date
    ]
    
    if recent_congressional_buys:
        signals["early_signals"]["recent_congressional_buying"] = True
        
        days_ago = [(now - t.get("date")).days for t in recent_congressional_buys if t.get("date")]
        most_recent_days = min(days_ago) if days_ago else data_lookback_days
        
        if most_recent_days <= focus_days:
            recency_weight = 1.0
        else:
            span = max(1, data_lookback_days - focus_days)
            recency_weight = max(0.2, 1.0 - (most_recent_days - focus_days) / span)
        base_recency_points = 15.0
        recency_score = base_recency_points * recency_weight
        cluster_bonus = 5 if len(recent_congressional_buys) >= 2 else 0
        
        congressional_score = min(15, recency_score + cluster_bonus)
        signals["early_signals"]["score"] += congressional_score
        
        signals["early_signals"]["congressional_details"] = {
            "count": len(recent_congressional_buys),
            "most_recent_days_ago": most_recent_days,
            "traders": [t.get("senator", "Unknown") for t in recent_congressional_buys[:3]]
        }
        
        signals["reasons"].append(
            f"Recent congressional buying: {len(recent_congressional_buys)} trade(s) in last {most_recent_days} days"
        )
    
    # ===== 2. TECHNICAL INDICATORS (30 points) =====
    
    rsi = technical_indicators.get("rsi")
    momentum_5d = technical_indicators.get("momentum_5d")
    momentum_10d = technical_indicators.get("momentum_10d")
    momentum_20d = technical_indicators.get("momentum_20d")
    volume_ratio = technical_indicators.get("volume_ratio")
    above_ma20 = technical_indicators.get("above_ma20")
    above_ma50 = technical_indicators.get("above_ma50")
    current_price = technical_indicators.get("current_price")
    ma20 = technical_indicators.get("ma20")
    
    # Momentum scoring (10 points)
    momentum_score = 0
    if momentum_5d and momentum_5d > 0:
        momentum_score += 3  # Positive 5-day momentum
    if momentum_10d and momentum_10d > 0:
        momentum_score += 3  # Positive 10-day momentum
    if momentum_20d and momentum_20d > -5:  # Not too negative
        momentum_score += 4  # Reasonable 20-day momentum
    
    signals["technical_signals"]["momentum"] = {
        "5d": momentum_5d,
        "10d": momentum_10d,
        "20d": momentum_20d
    }
    signals["technical_signals"]["score"] += min(10, momentum_score)
    
    # RSI scoring (5 points) - oversold or neutral is good for entry
    if rsi:
        if 30 <= rsi <= 50:  # Oversold to neutral - good entry
            rsi_score = 5
            signals["technical_signals"]["rsi_signal"] = "oversold_entry"
        elif 50 < rsi <= 70:  # Neutral to overbought - still okay
            rsi_score = 3
            signals["technical_signals"]["rsi_signal"] = "neutral"
        else:
            rsi_score = 0
            signals["technical_signals"]["rsi_signal"] = "extreme"
        signals["technical_signals"]["score"] += rsi_score
    
    # Volume surge (5 points)
    if volume_ratio and volume_ratio > 1.5:  # 50% above average
        signals["technical_signals"]["volume_surge"] = True
        volume_score = min(5, (volume_ratio - 1.5) * 2)  # Up to 5 points
        signals["technical_signals"]["score"] += volume_score
        signals["reasons"].append(f"Volume surge: {volume_ratio:.1f}x average")
    
    # Moving average alignment (5 points)
    if above_ma20 and above_ma50:
        signals["technical_signals"]["ma_alignment"] = "bullish"
        signals["technical_signals"]["score"] += 5
    elif above_ma20:
        signals["technical_signals"]["ma_alignment"] = "neutral"
        signals["technical_signals"]["score"] += 3
    elif current_price and ma20:
        # Price below MA20 but close - potential bounce
        pct_below = ((ma20 - current_price) / ma20) * 100
        if pct_below < 5:  # Within 5% of MA20
            signals["technical_signals"]["ma_alignment"] = "near_support"
            signals["technical_signals"]["score"] += 2
    
    # Breakout detection (5 points)
    if current_price and technical_indicators.get("resistance_level"):
        resistance = technical_indicators.get("resistance_level")
        if current_price > resistance * 0.98:  # Within 2% of resistance
            signals["technical_signals"]["breakout"] = True
            signals["technical_signals"]["score"] += 5
            signals["reasons"].append("Near breakout level")
    
    # ===== 3. RISK/REWARD METRICS (25 points) =====
    
    # Upside potential (10 points)
    upside_pct = analyst_data.get("upside_pct")
    if upside_pct:
        signals["risk_reward"]["upside_potential"] = upside_pct
        if upside_pct > 30:  # 30%+ upside
            upside_score = 10
        elif upside_pct > 20:  # 20-30% upside
            upside_score = 7
        elif upside_pct > 10:  # 10-20% upside
            upside_score = 5
        else:
            upside_score = 2
        signals["risk_reward"]["score"] += upside_score
        signals["reasons"].append(f"Analyst upside: {upside_pct:.1f}%")
    
    # Volatility (5 points) - medium/high volatility for high reward
    volatility = technical_indicators.get("volatility")
    if volatility:
        signals["risk_reward"]["volatility"] = volatility
        if 20 <= volatility <= 50:  # Medium-high volatility
            signals["risk_reward"]["score"] += 5
        elif volatility > 50:  # Very high volatility
            signals["risk_reward"]["score"] += 3
        elif volatility < 20:  # Low volatility
            signals["risk_reward"]["score"] += 1
    
    # Support level (5 points)
    distance_to_support = technical_indicators.get("distance_to_support")
    if distance_to_support is not None:
        signals["risk_reward"]["support_level"] = distance_to_support
        if 0 <= distance_to_support <= 5:  # Near support
            signals["risk_reward"]["score"] += 5
        elif 5 < distance_to_support <= 10:  # Close to support
            signals["risk_reward"]["score"] += 3
        signals["reasons"].append(f"Support: {distance_to_support:.1f}% away")
    
    # Recent price action (5 points)
    price_change_5d = technical_indicators.get("price_change_5d")
    if price_change_5d:
        signals["risk_reward"]["recent_action"] = price_change_5d
        if -5 <= price_change_5d <= 5:  # Consolidation
            signals["risk_reward"]["score"] += 5
        elif price_change_5d > 5:  # Strong momentum
            signals["risk_reward"]["score"] += 3
        elif price_change_5d < -10:  # Oversold bounce potential
            signals["risk_reward"]["score"] += 4
    
    # ===== 4. MARKET CONDITIONS (15 points) =====
    
    # VIX levels (5 points)
    vix = market_data.get("VIX")
    if vix:
        signals["market_conditions"]["vix_signal"] = vix
        if vix < 15:  # Low volatility - good entry
            signals["market_conditions"]["score"] += 5
        elif vix < 20:  # Moderate volatility
            signals["market_conditions"]["score"] += 3
        else:  # High volatility - be cautious
            signals["market_conditions"]["score"] += 1
    
    # Sector momentum (5 points) - would need sector data
    # Placeholder for now
    
    # Market timing (5 points) - based on overall market conditions
    if vix and vix < 20:
        signals["market_conditions"]["timing"] = "favorable"
        signals["market_conditions"]["score"] += 5
    
    # ===== CALCULATE TOTAL SCORE =====
    signals["total_score"] = (
        signals["early_signals"]["score"] +
        signals["technical_signals"]["score"] +
        signals["risk_reward"]["score"] +
        signals["market_conditions"]["score"]
    )
    
    # ===== DETERMINE RISK LEVEL AND REWARD POTENTIAL =====
    volatility_val = volatility or 0
    upside_val = upside_pct or 0
    
    if volatility_val > 40 or (volatility_val > 25 and upside_val > 30):
        signals["risk_level"] = "HIGH"
    elif volatility_val > 20 or upside_val > 20:
        signals["risk_level"] = "MEDIUM-HIGH"
    else:
        signals["risk_level"] = "MEDIUM"
    
    if upside_val > 30:
        signals["reward_potential"] = "VERY HIGH"
    elif upside_val > 20:
        signals["reward_potential"] = "HIGH"
    elif upside_val > 10:
        signals["reward_potential"] = "MODERATE"
    else:
        signals["reward_potential"] = "LOW"
    
    return signals


def generate_multi_factor_recommendations(
    available_funds: float,
    watchlist: Optional[List[str]] = None,
    buy_config: Dict[str, Any] = None
) -> List[Dict[str, Any]]:
    """
    Generate multi-factor buy recommendations.
    
    Focus: Medium/High Risk, High Reward opportunities
    """
    if buy_config is None:
        buy_config = {}
    
    recommendations = []
    
    # Clear cache
    from fetch_market_data import clear_cache
    clear_cache()
    logger.info("Starting multi-factor buy recommendation generation")
    
    # Get symbols to evaluate
    symbols_to_evaluate = set()
    
    # Add watchlist symbols
    if watchlist:
        symbols_to_evaluate.update([s.upper() for s in watchlist])
    
    # Determine early‑signal data window
    early_data_days = buy_config.get("early_signal_data_days", buy_config.get("early_signal_days", 90))
    
    # Fetch recent congressional trades (for early signals)
    if fetch_congressional_trades:
        congressional_trades = fetch_congressional_trades(
            lookback_days=early_data_days
        )
        for trade in congressional_trades:
            if trade.get("transaction_type") == "buy":
                symbols_to_evaluate.add(trade.get("ticker", "").upper())
    else:
        congressional_trades = []
    
    # If no symbols, use a focused watchlist of high-volatility, high-reward stocks
    if not symbols_to_evaluate:
        default_watchlist = [
            "NVDA", "AMD", "TSLA", "META", "AMZN", "GOOGL", "MSFT", "AAPL",
            "SMCI", "ARM", "AVGO", "MU", "INTC", "QCOM", "NFLX", "PLTR"
        ]
        symbols_to_evaluate.update(default_watchlist)
        logger.info(f"Using default watchlist: {', '.join(symbols_to_evaluate)}")
    
    # Fetch market data
    market_data = {}
    if fetch_macro_indicator:
        try:
            vix = fetch_macro_indicator("VIX")
            if vix is not None:
                market_data["VIX"] = vix
        except Exception as e:
            logger.warning(f"Could not fetch VIX: {e}")
    
    # Fetch prices
    prices = {}
    if fetch_all_prices:
        try:
            prices = fetch_all_prices(list(symbols_to_evaluate), force_refresh=True)
        except Exception as e:
            logger.warning(f"Could not fetch prices: {e}")
    
    # Fetch FX rate
    fx_rate = 0.79
    if fetch_fx_rate:
        try:
            fx_rate = fetch_fx_rate("USD", "GBP", force_refresh=True) or 0.79
        except Exception as e:
            logger.warning(f"Could not fetch FX rate: {e}")
    
    # Evaluate each symbol
    for symbol in symbols_to_evaluate:
        if not symbol:
            continue
        
        current_price = prices.get(symbol)
        if not current_price:
            continue
        
        logger.info(f"Evaluating {symbol}...")
        
        # Fetch data
        insider_trades = []
        if fetch_insider_trades_sec:
            insider_trades = fetch_insider_trades_sec(
                symbol, 
                lookback_days=early_data_days
            )
        
        technical_indicators = get_technical_indicators(symbol)
        analyst_data = get_analyst_data(symbol)
        
        # Evaluate multi-factor signals
        signals = evaluate_multi_factor_signals(
            symbol, congressional_trades, insider_trades, technical_indicators,
            analyst_data, market_data, buy_config
        )
        
        # Filter: Must have at least some early signal OR strong technical + risk/reward
        min_score = buy_config.get("min_score_to_show", 25)
        early_score = signals["early_signals"]["score"]
        tech_score = signals["technical_signals"]["score"]
        risk_reward_score = signals["risk_reward"]["score"]
        
        # Require either:
        # 1. Early signal (insider/congressional) OR
        # 2. Strong technical + risk/reward (15+ points each)
        has_early_signal = early_score > 0
        has_strong_technical = tech_score >= 15 and risk_reward_score >= 15
        
        if signals["total_score"] < min_score and not (has_early_signal or has_strong_technical):
            continue
        
        # Determine recommendation level
        total_score = signals["total_score"]
        thresholds = buy_config.get("confidence_thresholds", {})
        strong_buy_threshold = thresholds.get("strong_buy", 60)
        buy_threshold = thresholds.get("buy", 40)
        
        if total_score >= strong_buy_threshold:
            recommendation = "STRONG BUY"
        elif total_score >= buy_threshold:
            recommendation = "BUY"
        else:
            recommendation = "CONSIDER"
        
        # Calculate price in GBP
        if ".L" in symbol:
            current_price_gbp = current_price
        else:
            current_price_gbp = current_price * fx_rate
        
        # Calculate insider buying value
        insider_buying_value_gbp = 0.0
        if signals["early_signals"]["recent_insider_buying"]:
            total_value_usd = signals["early_signals"]["insider_details"].get("total_value_usd", 0)
            insider_buying_value_gbp = total_value_usd * fx_rate
        
        # Build recommendation
        rec = {
            "symbol": symbol,
            "recommendation": recommendation,
            "total_score": total_score,
            "max_score": 100,
            "score_breakdown": {
                "early_signals": signals["early_signals"]["score"],
                "technical": signals["technical_signals"]["score"],
                "risk_reward": signals["risk_reward"]["score"],
                "market_conditions": signals["market_conditions"]["score"]
            },
            "factors": {
                "early_signals": signals["early_signals"],
                "technical": signals["technical_signals"],
                "risk_reward": signals["risk_reward"],
                "market_conditions": signals["market_conditions"]
            },
            "risk_level": signals["risk_level"],
            "reward_potential": signals["reward_potential"],
            "reasons": signals["reasons"],
            "current_price": current_price,
            "current_price_gbp": current_price_gbp,
            "insider_buying_value_gbp": insider_buying_value_gbp,
            "upside_potential_pct": analyst_data.get("upside_pct"),
            "volatility": technical_indicators.get("volatility"),
            "rsi": technical_indicators.get("rsi"),
            "momentum_5d": technical_indicators.get("momentum_5d")
        }
        
        recommendations.append(rec)
    
    # Sort by total score
    recommendations.sort(key=lambda x: x["total_score"], reverse=True)
    
    # Calculate suggested allocations
    if available_funds > 0 and recommendations:
        total_score_sum = sum(r["total_score"] for r in recommendations)
        for rec in recommendations:
            allocation_pct = rec["total_score"] / total_score_sum if total_score_sum > 0 else 0
            rec["suggested_allocation_gbp"] = available_funds * allocation_pct
            if rec.get("current_price_gbp"):
                rec["suggested_shares"] = int(rec["suggested_allocation_gbp"] / rec["current_price_gbp"])
            else:
                rec["suggested_shares"] = None
    else:
        for rec in recommendations:
            rec["suggested_allocation_gbp"] = 0.0
            rec["suggested_shares"] = None
    
    logger.info(f"Generated {len(recommendations)} multi-factor recommendations")
    return recommendations

