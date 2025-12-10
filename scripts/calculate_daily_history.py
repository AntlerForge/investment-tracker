#!/usr/bin/env python3
"""
Calculate daily portfolio history from baseline dates.

This script:
1. Calculates portfolio value for each trading day since baseline dates
2. Uses Friday's value for weekends (markets closed)
3. Generates a complete daily history CSV
"""

import sys
import yaml
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import pandas as pd

# Add scripts directory to path
scripts_dir = Path(__file__).parent
project_root = scripts_dir.parent
sys.path.insert(0, str(scripts_dir))
sys.path.insert(0, str(project_root))

def load_portfolio_config() -> Dict[str, Any]:
    """Load portfolio configuration."""
    config_path = project_root / "config" / "portfolio.yaml"
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)

def get_original_baseline_total(portfolio_config: Dict[str, Any]) -> float:
    """Calculate original baseline total."""
    original_baseline_values = portfolio_config.get("original_baseline_values", {})
    return sum(original_baseline_values.values())

def get_current_baseline_total(portfolio_config: Dict[str, Any]) -> float:
    """Calculate current baseline total from holdings."""
    holdings = portfolio_config.get("holdings", {})
    total = 0.0
    for ticker, holding in holdings.items():
        total += holding.get("baseline_value_gbp", 0.0)
    return total

def is_weekend(date: datetime) -> bool:
    """Check if date is a weekend."""
    return date.weekday() >= 5  # Saturday = 5, Sunday = 6

def get_last_trading_day(date: datetime) -> datetime:
    """Get the last trading day (Friday if weekend, otherwise the date itself)."""
    if is_weekend(date):
        # Go back to Friday
        days_back = date.weekday() - 4  # Saturday = 1 day, Sunday = 2 days
        return date - timedelta(days=days_back)
    return date

def fetch_historical_price(symbol: str, date: datetime) -> Optional[float]:
    """Fetch historical price for a symbol on a specific date."""
    try:
        from fetch_market_data import fetch_stock_price, fetch_fx_rate
        
        # For macro indicators, we might need different handling
        # For now, focus on stocks
        price = fetch_stock_price(symbol, date)
        return price
    except Exception as e:
        print(f"  Warning: Could not fetch {symbol} for {date.strftime('%Y-%m-%d')}: {e}")
        return None

def calculate_portfolio_value_for_date(
    portfolio_config: Dict[str, Any],
    date: datetime,
    use_original_holdings: bool = False
) -> Optional[float]:
    """
    Calculate portfolio value for a specific date.
    
    Args:
        portfolio_config: Portfolio configuration
        date: Date to calculate for
        use_original_holdings: If True, use original baseline holdings (for original baseline chart)
    """
    try:
        from fetch_market_data import fetch_fx_rate
        from portfolio_logic import get_position_value
        
        # Get holdings - use original if specified, otherwise current
        if use_original_holdings:
            # For original baseline, we need to reconstruct original holdings
            # This is complex - for now, use current holdings but track against original baseline
            holdings = portfolio_config.get("holdings", {})
        else:
            holdings = portfolio_config.get("holdings", {})
        
        # Get FX rate for the date
        fx_rate = fetch_fx_rate("USD", "GBP", date) or 0.79
        
        total_value = 0.0
        
        for ticker, holding in holdings.items():
            symbol = holding.get("symbol", ticker)
            shares = holding.get("shares", 0.0)
            
            # Determine currency
            if ".L" in symbol:
                currency = "GBP"
            else:
                currency = "USD"
            
            # Fetch price for this date
            price = fetch_historical_price(symbol, date)
            
            if price is None:
                # If we can't get price, return None to indicate missing data
                return None
            
            # Calculate position value
            position_value = get_position_value(symbol, shares, price, currency, fx_rate)
            total_value += position_value
        
        return total_value
        
    except Exception as e:
        print(f"  Error calculating portfolio value for {date.strftime('%Y-%m-%d')}: {e}")
        return None

def calculate_daily_history():
    """Calculate daily portfolio history from baseline dates."""
    portfolio_config = load_portfolio_config()
    original_baseline_date = datetime.strptime(portfolio_config.get("baseline_date", "2025-10-13"), "%Y-%m-%d")
    current_baseline_total = get_current_baseline_total(portfolio_config)
    original_baseline_total = get_original_baseline_total(portfolio_config)
    
    # Determine current baseline date - use first evaluation date or today
    # For now, use the first state file date or Nov 20, 2025
    current_baseline_date = datetime(2025, 11, 20)  # First evaluation date
    
    print(f"Original baseline date: {original_baseline_date.strftime('%Y-%m-%d')} (£{original_baseline_total:.2f})")
    print(f"Current baseline date: {current_baseline_date.strftime('%Y-%m-%d')} (£{current_baseline_total:.2f})")
    
    # Start from original baseline date, go to today
    end_date = datetime.now()
    current_date = original_baseline_date
    
    history_entries = []
    last_trading_day_value = None
    
    print(f"\nCalculating daily history from {original_baseline_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}...")
    
    while current_date <= end_date:
        # For weekends, use last trading day's value
        if is_weekend(current_date):
            if last_trading_day_value is not None:
                # Use Friday's value for weekend
                portfolio_value = last_trading_day_value["portfolio_value"]
                risk_score = last_trading_day_value["risk_score"]
                change_pct = last_trading_day_value["change_pct"]
            else:
                # Skip if we don't have a previous value yet
                current_date += timedelta(days=1)
                continue
        else:
            # Calculate portfolio value for this trading day
            portfolio_value = calculate_portfolio_value_for_date(portfolio_config, current_date)
            
            if portfolio_value is None:
                # If we can't calculate, use last known value
                if last_trading_day_value is not None:
                    portfolio_value = last_trading_day_value["portfolio_value"]
                    risk_score = last_trading_day_value["risk_score"]
                    change_pct = last_trading_day_value["change_pct"]
                else:
                    # Skip if we don't have any value yet
                    current_date += timedelta(days=1)
                    continue
            else:
                # Calculate change percentage against current baseline
                change_pct = ((portfolio_value - current_baseline_total) / current_baseline_total * 100) if current_baseline_total > 0 else 0.0
                # Risk score would need to be calculated, but for now use 0 or get from state files
                risk_score = 0
        
        # Store this day's value
        date_str = current_date.strftime("%Y-%m-%d")
        history_entries.append({
            "date": date_str,
            "risk_score": risk_score,
            "portfolio_value": portfolio_value,
            "portfolio_change_pct": change_pct
        })
        
        # Update last trading day value if this is a trading day
        if not is_weekend(current_date):
            last_trading_day_value = {
                "portfolio_value": portfolio_value,
                "risk_score": risk_score,
                "change_pct": change_pct
            }
        
        current_date += timedelta(days=1)
    
    # Also check state files for actual risk scores on evaluation dates
    history_dir = project_root / "data" / "history"
    state_files = sorted(history_dir.glob("state_*.json"))
    
    # Create a map of dates to risk scores from state files
    risk_scores_by_date = {}
    for state_file in state_files:
        try:
            import json
            with open(state_file, 'r') as f:
                state = json.load(f)
            last_updated = state.get("last_updated", "")
            if last_updated:
                dt = datetime.fromisoformat(last_updated.replace('Z', '+00:00'))
                date_str = dt.strftime("%Y-%m-%d")
                risk_assessment = state.get("risk_assessment", {})
                risk_score = risk_assessment.get("risk_score", 0)
                risk_scores_by_date[date_str] = risk_score
        except:
            pass
    
    # Update risk scores from state files
    for entry in history_entries:
        if entry["date"] in risk_scores_by_date:
            entry["risk_score"] = risk_scores_by_date[entry["date"]]
    
    print(f"\nGenerated {len(history_entries)} daily history entries")
    
    # Write to CSV
    csv_path = history_dir / "risk_scores.csv"
    print(f"\nWriting to {csv_path}")
    
    with open(csv_path, 'w') as f:
        f.write("date,risk_score,portfolio_value_gbp,portfolio_change_pct\n")
        for entry in history_entries:
            f.write(
                f"{entry['date']},"
                f"{entry['risk_score']},"
                f"{entry['portfolio_value']:.2f},"
                f"{entry['portfolio_change_pct']:.2f}\n"
            )
    
    print("✓ Daily history CSV generated successfully!")
    print(f"\nSample entries (first 5 and last 5):")
    for entry in history_entries[:5]:
        print(f"  {entry['date']}: £{entry['portfolio_value']:.2f} ({entry['portfolio_change_pct']:.2f}%)")
    print("  ...")
    for entry in history_entries[-5:]:
        print(f"  {entry['date']}: £{entry['portfolio_value']:.2f} ({entry['portfolio_change_pct']:.2f}%)")

if __name__ == "__main__":
    calculate_daily_history()





