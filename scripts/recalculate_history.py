#!/usr/bin/env python3
"""
Recalculate history CSV from saved state files.

This script:
1. Reads all state_*.json files from the history directory
2. Extracts portfolio values and risk scores
3. Calculates change percentages against both baselines
4. Creates a clean history CSV with one entry per date (latest evaluation)
"""

import json
import sys
from pathlib import Path
from datetime import datetime
from collections import defaultdict
from typing import Dict, Any, List

# Add scripts directory to path
scripts_dir = Path(__file__).parent
project_root = scripts_dir.parent
sys.path.insert(0, str(scripts_dir))
sys.path.insert(0, str(project_root))

def load_portfolio_config() -> Dict[str, Any]:
    """Load portfolio configuration."""
    config_path = project_root / "config" / "portfolio.yaml"
    import yaml
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

def recalculate_history():
    """Recalculate history CSV from state files."""
    history_dir = project_root / "data" / "history"
    csv_path = history_dir / "risk_scores.csv"
    
    # Load portfolio config for baseline values
    portfolio_config = load_portfolio_config()
    original_baseline_total = get_original_baseline_total(portfolio_config)
    current_baseline_total = get_current_baseline_total(portfolio_config)
    
    print(f"Original baseline total: £{original_baseline_total:.2f}")
    print(f"Current baseline total: £{current_baseline_total:.2f}")
    
    # Find all state files
    state_files = sorted(history_dir.glob("state_*.json"))
    print(f"\nFound {len(state_files)} state files")
    
    # Group by date (YYYY-MM-DD), keeping only the latest evaluation for each date
    daily_data = {}
    
    for state_file in state_files:
        try:
            with open(state_file, 'r') as f:
                state = json.load(f)
            
            # Extract date from timestamp
            last_updated = state.get("last_updated", "")
            if not last_updated:
                continue
                
            # Parse timestamp
            dt = datetime.fromisoformat(last_updated.replace('Z', '+00:00'))
            date_str = dt.strftime("%Y-%m-%d")
            
            # Get portfolio data
            portfolio = state.get("portfolio", {})
            totals = portfolio.get("totals", {})
            portfolio_value = totals.get("total_value_gbp", 0.0)
            
            # Get risk assessment
            risk_assessment = state.get("risk_assessment", {})
            risk_score = risk_assessment.get("risk_score", 0)
            
            # Calculate change percentages
            # Use current baseline for portfolio_change_pct (as stored in CSV)
            current_change_pct = totals.get("total_pnl_pct", 0.0)
            
            # Store or update if this is a later evaluation for the same date
            if date_str not in daily_data or dt > daily_data[date_str]["timestamp"]:
                daily_data[date_str] = {
                    "timestamp": dt,
                    "date": date_str,
                    "risk_score": risk_score,
                    "portfolio_value": portfolio_value,
                    "portfolio_change_pct": current_change_pct
                }
                
        except Exception as e:
            print(f"Error processing {state_file.name}: {e}")
            continue
    
    # Sort by date
    sorted_entries = sorted(daily_data.values(), key=lambda x: x["date"])
    
    print(f"\nRecalculated {len(sorted_entries)} history entries:")
    for entry in sorted_entries:
        print(f"  {entry['date']}: £{entry['portfolio_value']:.2f} (risk: {entry['risk_score']}, change: {entry['portfolio_change_pct']:.2f}%)")
    
    # Write new CSV
    print(f"\nWriting to {csv_path}")
    with open(csv_path, 'w') as f:
        f.write("date,risk_score,portfolio_value_gbp,portfolio_change_pct\n")
        for entry in sorted_entries:
            f.write(
                f"{entry['date']},"
                f"{entry['risk_score']},"
                f"{entry['portfolio_value']:.2f},"
                f"{entry['portfolio_change_pct']:.2f}\n"
            )
    
    print("✓ History CSV recalculated successfully!")

if __name__ == "__main__":
    recalculate_history()





