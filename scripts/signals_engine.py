"""
Signals evaluation engine.

Evaluates macro, sector, and stock-level signals based on configured thresholds.
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


def check_nvda_divergence(
    nvda_change_pct: float,
    qqq_change_pct: float,
    threshold_pct: float = -5.0,
    flat_band_pct: float = 1.0
) -> bool:
    """
    Check if NVDA is diverging from QQQ.
    
    Divergence occurs when:
    - NVDA drops by more than threshold_pct
    - QQQ is within flat_band_pct (relatively flat)
    
    Args:
        nvda_change_pct: NVDA percentage change
        qqq_change_pct: QQQ percentage change
        threshold_pct: NVDA drop threshold (default -5.0)
        flat_band_pct: QQQ flat band threshold (default 1.0)
        
    Returns:
        True if divergence detected, False otherwise
    """
    nvda_dropping = nvda_change_pct <= threshold_pct
    qqq_flat = abs(qqq_change_pct) <= flat_band_pct
    
    return nvda_dropping and qqq_flat


def evaluate_macro_signals(
    market_data: Dict[str, Optional[float]],
    signal_config: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Evaluate macro-level risk signals.
    
    Signals evaluated:
    - VIX level (volatility)
    - Credit spreads (HYG vs QQQ)
    - Yield spikes (US10Y)
    
    Args:
        market_data: Dictionary with VIX, HYG, QQQ, US10Y values
        signal_config: Macro signal configuration from signals.yaml
        
    Returns:
        Dictionary of triggered signals with severity levels
    """
    signals = {
        "vix_warning": False,
        "vix_critical": False,
        "credit_stress": False,
        "yield_spike": False
    }
    
    # VIX evaluation
    vix = market_data.get("VIX")
    if vix is not None:
        vix_config = signal_config.get("vix", {})
        sell_high_beta_above = vix_config.get("sell_high_beta_above", 20.0)
        de_risk_all_above = vix_config.get("de_risk_all_above", 25.0)
        
        if vix >= de_risk_all_above:
            signals["vix_critical"] = True
        elif vix >= sell_high_beta_above:
            signals["vix_warning"] = True
    
    # Credit spread evaluation (HYG vs QQQ)
    hyg = market_data.get("HYG")
    qqq = market_data.get("QQQ")
    
    if hyg is not None and qqq is not None:
        # For simplicity, we check if HYG dropped significantly
        # In a full implementation, we'd compare HYG and QQQ changes
        credit_config = signal_config.get("credit_spreads", {})
        hyg_drop_threshold = credit_config.get("hyg_drop_threshold_pct", -1.0)
        
        # Note: This is simplified - we'd need historical data for proper comparison
        # For now, we'll flag if HYG is very low relative to typical range
        if hyg < 70:  # Simplified threshold
            signals["credit_stress"] = True
    
    # Yield spike evaluation
    us10y = market_data.get("US10Y")
    if us10y is not None:
        yields_config = signal_config.get("yields", {})
        spike_bps = yields_config.get("ten_year_spike_bps", 15)
        
        # Note: This would require comparing to previous day's value
        # For now, we'll use a simplified check
        if us10y > 5.0:  # Simplified threshold (5% yield)
            signals["yield_spike"] = True
    
    return signals


def evaluate_sector_signals(
    market_data: Dict[str, Optional[float]],
    signal_config: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Evaluate sector-level risk signals.
    
    Signals evaluated:
    - NVDA divergence (NVDA vs QQQ)
    - Semiconductor momentum (SOX index)
    
    Args:
        market_data: Dictionary with NVDA, QQQ, SOX values
        signal_config: Sector signal configuration from signals.yaml
        
    Returns:
        Dictionary of triggered sector signals
    """
    signals = {
        "nvda_divergence": False,
        "semi_momentum_negative": False
    }
    
    # NVDA divergence
    nvda_price = market_data.get("NVDA")
    qqq_price = market_data.get("QQQ")
    nvda_prev = market_data.get("NVDA_prev")
    qqq_prev = market_data.get("QQQ_prev")
    
    if all(x is not None for x in [nvda_price, qqq_price, nvda_prev, qqq_prev]):
        if nvda_prev > 0 and qqq_prev > 0:
            nvda_change = ((nvda_price - nvda_prev) / nvda_prev) * 100.0
            qqq_change = ((qqq_price - qqq_prev) / qqq_prev) * 100.0
            
            nvda_config = signal_config.get("nvda_divergence", {})
            threshold = nvda_config.get("nvda_drop_pct", -5.0)
            flat_band = nvda_config.get("qqq_flat_band_pct", 1.0)
            
            signals["nvda_divergence"] = check_nvda_divergence(
                nvda_change, qqq_change, threshold, flat_band
            )
    
    # Semiconductor momentum
    sox_price = market_data.get("SOX")
    sox_prev = market_data.get("SOX_prev")
    
    if sox_price is not None and sox_prev is not None and sox_prev > 0:
        sox_change = ((sox_price - sox_prev) / sox_prev) * 100.0
        
        semi_config = signal_config.get("semi_momentum", {})
        drop_threshold = semi_config.get("daily_drop_threshold_pct", -2.0)
        
        if sox_change <= drop_threshold:
            signals["semi_momentum_negative"] = True
    
    return signals


def evaluate_stock_signals(
    symbol: str,
    insider_trades: List[Dict[str, Any]],
    options_activity: Dict[str, Any],
    signal_config: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Evaluate stock-level risk signals.
    
    Signals evaluated:
    - Insider selling clusters
    - Options activity (put/call ratios)
    
    Args:
        symbol: Stock ticker symbol
        insider_trades: List of recent insider trades
        options_activity: Options activity metrics
        signal_config: Stock-level signal configuration from signals.yaml
        
    Returns:
        Dictionary of triggered stock-level signals
    """
    signals = {
        "warning_insider_selling": False,
        "critical_insider_selling": False,
        "options_warning": False,
        "options_critical": False
    }
    
    # Insider selling evaluation
    if insider_trades:
        insider_config = signal_config.get("insider_selling", {})
        warning_cluster = insider_config.get("severity_levels", {}).get("warning_cluster", 2)
        critical_cluster = insider_config.get("severity_levels", {}).get("critical_cluster", 3)
        
        # Count selling transactions
        selling_count = sum(1 for trade in insider_trades if trade.get("transaction_type") == "Sell")
        
        if selling_count >= critical_cluster:
            signals["critical_insider_selling"] = True
        elif selling_count >= warning_cluster:
            signals["warning_insider_selling"] = True
    
    # Options activity evaluation
    if options_activity:
        options_config = signal_config.get("options_activity", {})
        watchlist = options_config.get("watchlist", [])
        
        if symbol in watchlist:
            put_volume_mult = options_activity.get("put_volume_multiplier", 1.0)
            warning_mult = options_config.get("put_volume_multiplier_warning", 2.0)
            critical_mult = options_config.get("put_volume_multiplier_critical", 3.0)
            
            if put_volume_mult >= critical_mult:
                signals["options_critical"] = True
            elif put_volume_mult >= warning_mult:
                signals["options_warning"] = True
    
    return signals


def compute_risk_score(
    macro_signals: Dict[str, Any],
    sector_signals: Dict[str, Any],
    stock_signals: Dict[str, Dict[str, Any]],
    portfolio_pnl_pct: float
) -> int:
    """
    Compute composite risk score (0-100).
    
    Args:
        macro_signals: Dictionary of macro signals
        sector_signals: Dictionary of sector signals
        stock_signals: Dictionary mapping symbols to their stock signals
        portfolio_pnl_pct: Overall portfolio P&L percentage
        
    Returns:
        Risk score from 0 (low risk) to 100 (critical risk)
    """
    score = 0
    
    # Macro signals (0-40 points)
    if macro_signals.get("vix_critical"):
        score += 25
    elif macro_signals.get("vix_warning"):
        score += 15
    
    if macro_signals.get("credit_stress"):
        score += 10
    
    if macro_signals.get("yield_spike"):
        score += 5
    
    # Sector signals (0-20 points)
    if sector_signals.get("nvda_divergence"):
        score += 10
    
    if sector_signals.get("semi_momentum_negative"):
        score += 10
    
    # Stock signals (0-30 points)
    for symbol, signals in stock_signals.items():
        if signals.get("critical_insider_selling"):
            score += 15
        elif signals.get("warning_insider_selling"):
            score += 8
        
        if signals.get("options_critical"):
            score += 10
        elif signals.get("options_warning"):
            score += 5
    
    # Portfolio P&L adjustment (0-10 points)
    if portfolio_pnl_pct <= -20:
        score += 10
    elif portfolio_pnl_pct <= -10:
        score += 5
    
    # Cap at 100
    return min(score, 100)


def get_risk_level(risk_score: int) -> str:
    """
    Convert numeric risk score to human-readable level.
    
    Args:
        risk_score: Risk score (0-100)
        
    Returns:
        Risk level string: "Low", "Moderate", "Elevated", "High", "Critical"
    """
    if risk_score >= 80:
        return "Critical"
    elif risk_score >= 60:
        return "High"
    elif risk_score >= 40:
        return "Elevated"
    elif risk_score >= 20:
        return "Moderate"
    else:
        return "Low"

