#!/usr/bin/env python3
"""
Test script to reproduce and verify the evaluation cache issue.
This simulates exactly what happens when you click "Run Evaluation".
"""
import sys
import subprocess
from pathlib import Path

# Add scripts to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "scripts"))

def test_refresh_flow():
    """Test what happens when Refresh button is clicked (works correctly)"""
    print("=" * 70)
    print("TEST 1: Refresh Flow (This works correctly)")
    print("=" * 70)
    
    from fetch_market_data import clear_cache, fetch_all_prices, fetch_fx_rate
    from portfolio_logic import get_position_value, calculate_pnl
    import yaml
    
    # Clear cache
    clear_cache()
    print("✓ Cache cleared")
    
    # Load portfolio
    with open(project_root / "config" / "portfolio.yaml", 'r') as f:
        portfolio_config = yaml.safe_load(f)
    
    holdings = portfolio_config.get("holdings", {})
    nvda = holdings.get("NVDA")
    
    if not nvda:
        print("❌ NVDA not found in portfolio")
        return None
    
    # Fetch fresh data
    fx_rate = fetch_fx_rate("USD", "GBP") or 0.79
    prices = fetch_all_prices(["NVDA"], force_refresh=True)
    nvda_price = prices.get("NVDA")
    
    # Calculate value
    shares = nvda.get("shares", 0.0)
    baseline = nvda.get("baseline_value_gbp", 0.0)
    current_value = get_position_value("NVDA", shares, nvda_price, "USD", fx_rate)
    pnl = calculate_pnl(baseline, current_value)
    
    print(f"NVDA Price: ${nvda_price:.2f}")
    print(f"FX Rate: {fx_rate:.4f}")
    print(f"Shares: {shares:.8f}")
    print(f"Current Value: £{current_value:.2f}")
    print(f"Baseline: £{baseline:.2f}")
    print(f"P&L: £{pnl['change_gbp']:+.2f} ({pnl['change_pct']:+.2f}%)")
    
    return {
        "price": nvda_price,
        "value": current_value,
        "pnl_pct": pnl['change_pct']
    }

def test_evaluation_flow():
    """Test what happens when Run Evaluation button is clicked (this breaks)"""
    print("\n" + "=" * 70)
    print("TEST 2: Evaluation Flow (This breaks - shows wrong numbers)")
    print("=" * 70)
    
    from fetch_market_data import clear_cache
    import yaml
    
    # Clear cache before evaluation (like Flask app does)
    clear_cache()
    print("✓ Cache cleared before evaluation")
    
    # Run evaluation script (like Flask app does)
    script_path = project_root / "scripts" / "evaluate_risk.py"
    venv_python = project_root / ".venv" / "bin" / "python"
    
    if venv_python.exists():
        python_cmd = str(venv_python)
    else:
        python_cmd = sys.executable
    
    print(f"Running evaluation script: {script_path}")
    result = subprocess.run(
        [python_cmd, str(script_path)],
        cwd=str(project_root),
        capture_output=True,
        text=True,
        timeout=120
    )
    
    if result.returncode != 0:
        print(f"❌ Evaluation failed: {result.stderr}")
        return None
    
    print("✓ Evaluation completed")
    
    # Clear cache after evaluation (like Flask app does)
    clear_cache()
    print("✓ Cache cleared after evaluation")
    
    # Now check what the report says vs what fresh data says
    from datetime import datetime
    today = datetime.now().strftime('%Y-%m-%d')
    report_path = project_root / "reports" / "daily" / f"{today}_risk_report.md"
    
    if not report_path.exists():
        print(f"❌ Report not found: {report_path}")
        return None
    
    # Parse NVDA data from report
    with open(report_path, 'r') as f:
        report_content = f.read()
    
    # Find NVDA line in report
    nvda_line = None
    for line in report_content.split('\n'):
        if 'NVDA' in line and ('£' in line or 'Current Value' in line or 'P&L' in line):
            nvda_line = line.strip()
            break
    
    print(f"\nReport shows: {nvda_line}")
    
    # Now fetch fresh data to compare
    from fetch_market_data import fetch_all_prices, fetch_fx_rate
    from portfolio_logic import get_position_value, calculate_pnl
    
    with open(project_root / "config" / "portfolio.yaml", 'r') as f:
        portfolio_config = yaml.safe_load(f)
    
    holdings = portfolio_config.get("holdings", {})
    nvda = holdings.get("NVDA")
    
    fx_rate = fetch_fx_rate("USD", "GBP") or 0.79
    prices = fetch_all_prices(["NVDA"], force_refresh=True)
    nvda_price = prices.get("NVDA")
    
    shares = nvda.get("shares", 0.0)
    baseline = nvda.get("baseline_value_gbp", 0.0)
    current_value = get_position_value("NVDA", shares, nvda_price, "USD", fx_rate)
    pnl = calculate_pnl(baseline, current_value)
    
    print(f"\nFresh data shows:")
    print(f"  Price: ${nvda_price:.2f}")
    print(f"  Current Value: £{current_value:.2f}")
    print(f"  P&L: £{pnl['change_gbp']:+.2f} ({pnl['change_pct']:+.2f}%)")
    
    return {
        "report_line": nvda_line,
        "fresh_price": nvda_price,
        "fresh_value": current_value,
        "fresh_pnl_pct": pnl['change_pct']
    }

def main():
    print("\n" + "=" * 70)
    print("REPRODUCING THE BUG: Testing Refresh vs Evaluation Flow")
    print("=" * 70 + "\n")
    
    # Test 1: Refresh flow (works)
    refresh_result = test_refresh_flow()
    
    # Test 2: Evaluation flow (breaks)
    eval_result = test_evaluation_flow()
    
    # Compare results
    print("\n" + "=" * 70)
    print("COMPARISON")
    print("=" * 70)
    
    if refresh_result and eval_result:
        print(f"\nRefresh flow value: £{refresh_result['value']:.2f}")
        print(f"Evaluation fresh value: £{eval_result['fresh_value']:.2f}")
        
        diff = abs(refresh_result['value'] - eval_result['fresh_value'])
        if diff > 1.0:
            print(f"\n❌ BUG CONFIRMED: Values differ by £{diff:.2f}")
            print(f"   Refresh shows: £{refresh_result['value']:.2f}")
            print(f"   After eval shows: £{eval_result['fresh_value']:.2f}")
            print(f"\n   This is the bug - evaluation is corrupting the data!")
        else:
            print(f"\n✓ Values match (difference: £{diff:.2f})")
    
    print("\n" + "=" * 70)

if __name__ == "__main__":
    main()

