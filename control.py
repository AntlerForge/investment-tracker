#!/usr/bin/env python3
import sys
import os
import json
import argparse
import subprocess
from pathlib import Path
from typing import Dict, Any

# Setup paths
current_dir = Path(__file__).resolve().parent
sys.path.insert(0, str(current_dir / "scripts"))
from state_manager import StateManager

class ControlInterface:
    def __init__(self):
        self.project_root = current_dir
        self.state_manager = StateManager(self.project_root)

    def get_status(self):
        """Print current system status and key metrics."""
        state = self.state_manager.load_state()
        
        status = state.get("system_status", "unknown")
        updated = state.get("last_updated", "never")
        
        print(f"\n=== Risk Portfolio System Status ===")
        print(f"Status: {status.upper()}")
        print(f"Last Updated: {updated}")
        print(f"====================================")
        
        if "portfolio" in state and "totals" in state["portfolio"]:
            totals = state["portfolio"]["totals"]
            val = totals.get("total_value_gbp", 0)
            pnl_pct = totals.get("total_pnl_pct", 0)
            funds = totals.get("available_funds", 0)
            
            print(f"\nPortfolio Value: £{val:,.2f}")
            print(f"Total P&L:       {pnl_pct:+.2f}%")
            print(f"Available Funds: £{funds:,.2f}")
            
        if "recommendations" in state:
            buys = state["recommendations"].get("buy", [])
            sells = state["recommendations"].get("sell", [])
            print(f"\nActive Recommendations:")
            print(f"  SELL: {len(sells)}")
            print(f"  BUY:  {len(buys)}")
            
    def run_evaluation(self):
        """Trigger a full risk evaluation run."""
        print("Triggering risk evaluation...")
        script_path = self.project_root / "scripts" / "evaluate_risk.py"
        
        # Activate venv if it exists
        venv_python = self.project_root / ".venv" / "bin" / "python3"
        if venv_python.exists():
            python_exe = str(venv_python)
        else:
            python_exe = sys.executable
        
        try:
            # Run the evaluation script (no --force arg needed, it always clears cache)
            process = subprocess.Popen(
                [python_exe, str(script_path)],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                cwd=str(self.project_root)
            )
            
            # Stream output
            print("Running...")
            for line in process.stdout:
                print(f"  {line.strip()}")
                
            process.wait()
            
            if process.returncode == 0:
                print("\n✓ Evaluation complete.")
                self.get_status()
            else:
                print(f"\n✗ Evaluation failed (code {process.returncode})")
                
        except Exception as e:
            print(f"Error running evaluation: {e}")
            import traceback
            traceback.print_exc()

    def show_json(self):
        """Dump the full state as JSON."""
        print(json.dumps(self.state_manager.load_state(), indent=2))

def main():
    parser = argparse.ArgumentParser(description="Control Interface for Risk Portfolio System")
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")
    
    # Status command
    subparsers.add_parser("status", help="Show system status and summary")
    
    # Run command
    subparsers.add_parser("run", help="Run full risk evaluation")
    
    # JSON command
    subparsers.add_parser("json", help="Output full state as JSON")
    
    args = parser.parse_args()
    
    interface = ControlInterface()
    
    if args.command == "status":
        interface.get_status()
    elif args.command == "run":
        interface.run_evaluation()
    elif args.command == "json":
        interface.show_json()
    else:
        parser.print_help()

if __name__ == "__main__":
    main()

