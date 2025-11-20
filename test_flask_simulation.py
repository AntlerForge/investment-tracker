#!/usr/bin/env python3
"""
Test that simulates exactly what the Flask app does when you click "Run Evaluation".
This will help us find the bug.
"""
import sys
import subprocess
from pathlib import Path

# Add scripts to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "scripts"))

def simulate_flask_after_evaluation():
    """Simulate what Flask app does after evaluation completes"""
    print("=" * 70)
    print("SIMULATING: Flask app behavior after evaluation")
    print("=" * 70)
    
    from fetch_market_data import clear_cache, fetch_all_prices, fetch_fx_rate
    from portfolio_logic import get_position_value, calculate_pnl, evaluate_position_rules
    from portfolio_logic import aggregate_portfolio_metrics
    import yaml
    
    # Step 1: Clear cache (like Flask app does after evaluation)
    clear_cache()
    print("✓ Step 1: Cleared cache (like Flask app does)")
    
    # Step 2: Load portfolio config
    with open(project_root / "config" / "portfolio.yaml", 'r') as f:
        portfolio_config = yaml.safe_load(f)
    print("✓ Step 2: Loaded portfolio config")
    
    # Step 3: Calculate P&L (like Flask app does)
    holdings = portfolio_config.get("holdings", {})
    
    # Fetch FX rate
    fx_rate = fetch_fx_rate("USD", "GBP") or 0.79
    print(f"✓ Step 3a: FX Rate: {fx_rate:.4f}")
    
    # Fetch prices
    symbols = [h.get("symbol", ticker) for ticker, h in holdings.items()]
    prices = fetch_all_prices(symbols, force_refresh=True)
    print(f"✓ Step 3b: Fetched {len(prices)} prices")
    
    # Calculate positions (like calculate_portfolio_pnl does)
    positions = []
    for ticker, holding in holdings.items():
        symbol = holding.get("symbol", ticker)
        shares = holding.get("shares", 0.0)
        baseline_value_gbp = holding.get("baseline_value_gbp", 0.0)
        
        currency = "GBP" if ".L" in symbol else "USD"
        price = prices.get(symbol)
        current_value_gbp = get_position_value(symbol, shares, price, currency, fx_rate)
        pnl = calculate_pnl(baseline_value_gbp, current_value_gbp)
        
        rules = portfolio_config.get("rules", {})
        take_profit_pct = rules.get("take_profit_pct", 40.0)
        cut_loss_pct = rules.get("cut_loss_pct", -25.0)
        action = evaluate_position_rules(
            baseline_value_gbp, current_value_gbp, take_profit_pct, cut_loss_pct
        )
        
        positions.append({
            "ticker": ticker,
            "current_value_gbp": current_value_gbp,
            "change_gbp": pnl["change_gbp"],
            "change_pct": pnl["change_pct"],
            "action": action.value
        })
        
        if ticker == "NVDA":
            print(f"\n  NVDA Calculation:")
            print(f"    Price: ${price:.2f} {currency}")
            print(f"    Shares: {shares:.8f}")
            print(f"    Current Value: £{current_value_gbp:.2f}")
            print(f"    Baseline: £{baseline_value_gbp:.2f}")
            print(f"    P&L: £{pnl['change_gbp']:+.2f} ({pnl['change_pct']:+.2f}%)")
    
    totals = aggregate_portfolio_metrics(positions)
    print(f"\n✓ Step 3c: Calculated {len(positions)} positions")
    print(f"  Total Current Value: £{totals.get('total_current_value', 0):.2f}")
    
    return positions

def main():
    print("\n" + "=" * 70)
    print("TESTING: What Flask app sees after evaluation")
    print("=" * 70 + "\n")
    
    # First, run an evaluation (like clicking the button)
    print("Step 0: Running evaluation script...")
    script_path = project_root / "scripts" / "evaluate_risk.py"
    venv_python = project_root / ".venv" / "bin" / "python"
    
    if venv_python.exists():
        python_cmd = str(venv_python)
    else:
        python_cmd = sys.executable
    
    result = subprocess.run(
        [python_cmd, str(script_path)],
        cwd=str(project_root),
        capture_output=True,
        text=True,
        timeout=120
    )
    
    if result.returncode != 0:
        print(f"❌ Evaluation failed: {result.stderr}")
        return
    
    print("✓ Evaluation completed\n")
    
    # Now simulate what Flask app does
    positions = simulate_flask_after_evaluation()
    
    # Check NVDA
    nvda_pos = next((p for p in positions if p["ticker"] == "NVDA"), None)
    if nvda_pos:
        print(f"\n" + "=" * 70)
        print("RESULT: What Flask app would show for NVDA")
        print("=" * 70)
        print(f"Current Value: £{nvda_pos['current_value_gbp']:.2f}")
        print(f"P&L: £{nvda_pos['change_gbp']:+.2f} ({nvda_pos['change_pct']:+.2f}%)")
        print(f"Action: {nvda_pos['action']}")
        
        if nvda_pos['current_value_gbp'] > 200:
            print(f"\n❌ BUG CONFIRMED: Value is too high!")
            print(f"   Should be around £132-138, but showing £{nvda_pos['current_value_gbp']:.2f}")
        else:
            print(f"\n✓ Value looks correct")

if __name__ == "__main__":
    main()

