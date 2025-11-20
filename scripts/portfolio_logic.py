"""
Portfolio calculation and logic module.

Handles:
- P&L calculations vs baseline
- Position-level rule evaluation (+40% / -25%)
- Portfolio aggregation
- Action recommendations
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class Action(Enum):
    """Recommended action for a position."""
    HOLD = "HOLD"
    SELL = "SELL"
    REDUCE = "REDUCE"
    CONSIDER_BUY = "CONSIDER_BUY"


def calculate_pnl(
    baseline_value: float,
    current_value: float
) -> Dict[str, float]:
    """
    Calculate profit and loss metrics for a position.
    
    Args:
        baseline_value: Baseline value in GBP
        current_value: Current value in GBP
        
    Returns:
        Dictionary with:
        - change_gbp: Absolute change in GBP
        - change_pct: Percentage change
    """
    if baseline_value == 0:
        return {"change_gbp": 0.0, "change_pct": 0.0}
    
    change_gbp = current_value - baseline_value
    change_pct = (change_gbp / baseline_value) * 100.0
    
    return {
        "change_gbp": change_gbp,
        "change_pct": change_pct
    }


def evaluate_position_rules(
    baseline_value: float,
    current_value: float,
    take_profit_pct: float = 40.0,
    cut_loss_pct: float = -25.0
) -> Action:
    """
    Evaluate position-level rules and return recommended action.
    
    Rules:
    - If gain >= take_profit_pct: SELL
    - If loss <= cut_loss_pct: SELL
    - Otherwise: HOLD
    
    Args:
        baseline_value: Baseline value in GBP
        current_value: Current value in GBP
        take_profit_pct: Take profit threshold (default 40.0)
        cut_loss_pct: Stop loss threshold (default -25.0)
        
    Returns:
        Recommended Action
    """
    if baseline_value == 0:
        return Action.HOLD
    
    pnl = calculate_pnl(baseline_value, current_value)
    change_pct = pnl["change_pct"]
    
    if change_pct >= take_profit_pct:
        return Action.SELL
    elif change_pct <= cut_loss_pct:
        return Action.SELL
    else:
        return Action.HOLD


def get_position_value(
    symbol: str,
    shares: float,
    price: Optional[float],
    currency: str,
    fx_rate: float
) -> float:
    """
    Calculate position value in GBP.
    
    Args:
        symbol: Stock ticker symbol
        shares: Number of shares held
        price: Current price in native currency (None if unavailable)
        currency: Native currency of the position
        fx_rate: GBP/USD exchange rate (if position is USD)
        
    Returns:
        Position value in GBP, or 0.0 if price unavailable
    """
    if price is None:
        logger.warning(f"Price unavailable for {symbol}, returning 0.0")
        return 0.0
    
    value_native = shares * price
    
    # Convert to GBP if needed
    if currency.upper() == "USD":
        return value_native * fx_rate
    elif currency.upper() == "GBP":
        return value_native
    else:
        # Assume GBP for unknown currencies
        logger.warning(f"Unknown currency {currency} for {symbol}, assuming GBP")
        return value_native


def calculate_portfolio_value(
    holdings: Dict[str, Dict[str, Any]], 
    prices: Dict[str, Optional[float]], 
    fx_rate: float
) -> float:
    """
    Calculate total portfolio value in GBP.
    
    Args:
        holdings: Dictionary of holdings with shares and symbols
        prices: Dictionary mapping symbols to prices (in native currency)
        fx_rate: GBP/USD exchange rate (if needed for USD positions)
        
    Returns:
        Total portfolio value in GBP
    """
    total = 0.0
    
    for ticker, holding in holdings.items():
        symbol = holding.get("symbol", ticker)
        shares = holding.get("shares", 0.0)
        
        # Determine currency from symbol or default
        if ".L" in symbol:
            currency = "GBP"
        else:
            currency = "USD"
        
        price = prices.get(symbol)
        position_value = get_position_value(symbol, shares, price, currency, fx_rate)
        total += position_value
    
    return total


def aggregate_portfolio_metrics(
    positions: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Aggregate portfolio-level metrics from individual positions.
    
    Args:
        positions: List of position dictionaries with P&L data
        
    Returns:
        Dictionary with aggregated metrics:
        - total_baseline_value
        - total_current_value
        - total_change_gbp
        - total_change_pct
    """
    total_baseline = sum(p.get("baseline_value_gbp", 0.0) for p in positions)
    total_current = sum(p.get("current_value_gbp", 0.0) for p in positions)
    
    change_gbp = total_current - total_baseline
    change_pct = (change_gbp / total_baseline * 100.0) if total_baseline > 0 else 0.0
    
    return {
        "total_baseline_value": total_baseline,
        "total_current_value": total_current,
        "total_change_gbp": change_gbp,
        "total_change_pct": change_pct
    }


def apply_signal_adjustments(
    base_action: Action,
    signals: Dict[str, Any],
    risk_bucket: str
) -> Action:
    """
    Adjust base action based on macro/sector/stock signals.
    
    Args:
        base_action: Base action from position rules
        signals: Dictionary of triggered signals
        risk_bucket: Risk bucket of the position (e.g., "high-beta-ai")
        
    Returns:
        Adjusted Action recommendation
    """
    # If already SELL, don't downgrade
    if base_action == Action.SELL:
        return base_action
    
    # Check for critical macro signals
    macro_signals = signals.get("macro", {})
    if macro_signals.get("vix_critical", False):
        # VIX > 25: de-risk all
        if risk_bucket in ["high-beta-ai", "crypto-beta"]:
            return Action.SELL
        else:
            return Action.REDUCE
    
    # Check for high-beta sell signals
    if macro_signals.get("vix_warning", False) and risk_bucket in ["high-beta-ai", "crypto-beta"]:
        if base_action == Action.HOLD:
            return Action.REDUCE
    
    # Check for sector signals affecting AI stocks
    sector_signals = signals.get("sector", {})
    if sector_signals.get("nvda_divergence", False) and risk_bucket in ["core-ai", "high-beta-ai"]:
        if base_action == Action.HOLD:
            return Action.REDUCE
    
    # Check for stock-specific signals
    stock_signals = signals.get("stock", {})
    if stock_signals.get("critical_insider_selling", False):
        return Action.SELL
    elif stock_signals.get("warning_insider_selling", False):
        if base_action == Action.HOLD:
            return Action.REDUCE
    
    return base_action

