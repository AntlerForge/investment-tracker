"""
Flask web application for Risk Portfolio System Dashboard.

Provides a web interface to:
- View portfolio holdings and risk evaluation
- Update holdings and baseline values
- Trigger new risk evaluations
- View historical risk scores
"""

from flask import Flask, render_template, request, jsonify, send_from_directory
from pathlib import Path
import yaml
import json
import subprocess
import sys
import time
from datetime import datetime
from typing import Dict, Any, Optional, List
import logging

app = Flask(__name__)
app.config['SECRET_KEY'] = 'risk-portfolio-dashboard-secret-key'
app.config['DEBUG'] = False  # Disable debug mode to prevent reloader issues

# Set up paths
PROJECT_ROOT = Path(__file__).parent

# Import StateManager for shared state access (after PROJECT_ROOT is defined)
try:
    scripts_dir = PROJECT_ROOT / "scripts"
    if str(scripts_dir) not in sys.path:
        sys.path.insert(0, str(scripts_dir))
    from state_manager import StateManager
    state_manager = StateManager(PROJECT_ROOT)
except ImportError as e:
    print(f"Warning: Could not import StateManager: {e}")
    state_manager = None
CONFIG_DIR = PROJECT_ROOT / "config"
REPORTS_DIR = PROJECT_ROOT / "reports" / "daily"
HISTORY_DIR = PROJECT_ROOT / "data" / "history"
LOGS_DIR = PROJECT_ROOT / "logs"

# Ensure directories exist
REPORTS_DIR.mkdir(parents=True, exist_ok=True)
HISTORY_DIR.mkdir(parents=True, exist_ok=True)
LOGS_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def load_portfolio_config() -> Dict[str, Any]:
    """Load portfolio configuration from YAML."""
    config_path = CONFIG_DIR / "portfolio.yaml"
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)


def save_portfolio_config(config: Dict[str, Any]):
    """Save portfolio configuration to YAML."""
    config_path = CONFIG_DIR / "portfolio.yaml"
    # Create backup
    backup_path = CONFIG_DIR / f"portfolio_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.yaml"
    if config_path.exists():
        import shutil
        shutil.copy(config_path, backup_path)
    
    with open(config_path, 'w') as f:
        yaml.dump(config, f, default_flow_style=False, sort_keys=False)
    
    logger.info(f"Portfolio config saved. Backup: {backup_path}")


def load_latest_report() -> Optional[Dict[str, Any]]:
    """Load the latest risk evaluation report."""
    today = datetime.now().strftime('%Y-%m-%d')
    report_path = REPORTS_DIR / f"{today}_risk_report.md"
    
    if not report_path.exists():
        # Try to find the most recent report
        reports = sorted(REPORTS_DIR.glob("*_risk_report.md"), reverse=True)
        if reports:
            report_path = reports[0]
        else:
            return None
    
    with open(report_path, 'r') as f:
        content = f.read()
    
    # Parse risk score from markdown
    risk_score = None
    risk_level = None
    for line in content.split('\n'):
        if 'Risk Score:' in line:
            import re
            match = re.search(r'(\d+)\s*/\s*100\s*\(([^)]+)\)', line)
            if match:
                risk_score = int(match.group(1))
                risk_level = match.group(2)
                break
    
    # Parse basic info from markdown
    report_data = {
        "date": report_path.stem.split('_')[0],
        "content": content,
        "html_path": report_path.with_suffix('.html').name,
        "risk_score": risk_score,
        "risk_level": risk_level
    }
    
    return report_data


def load_risk_history() -> list:
    """Load risk score history from CSV."""
    csv_path = HISTORY_DIR / "risk_scores.csv"
    if not csv_path.exists():
        return []
    
    history = []
    with open(csv_path, 'r') as f:
        lines = f.readlines()
        if len(lines) > 1:  # Skip header
            for line in lines[1:]:
                parts = line.strip().split(',')
                if len(parts) >= 4:
                    history.append({
                        "date": parts[0],
                        "risk_score": int(parts[1]),
                        "portfolio_value": float(parts[2]),
                        "portfolio_change_pct": float(parts[3])
                    })
    
    return sorted(history, key=lambda x: x["date"], reverse=True)


def calculate_portfolio_pnl(portfolio_config: Dict[str, Any]) -> Dict[str, Any]:
    """Calculate current portfolio values and P&L."""
    try:
        # Import required functions
        from scripts.fetch_market_data import clear_cache, _cache, fetch_all_prices, fetch_fx_rate
        from scripts.portfolio_logic import get_position_value, calculate_pnl, evaluate_position_rules, aggregate_portfolio_metrics, Action
        import time
        # Import StateManager lazily to avoid circular imports
        from scripts.state_manager import StateManager as ScriptStateManager
        
        holdings = portfolio_config.get("holdings", {})

        # Try to load the latest per-holding analysis summaries from shared state
        analysis_summaries_by_ticker: Dict[str, str] = {}
        try:
            sm = ScriptStateManager(PROJECT_ROOT)
            current_state = sm.load_state()
            state_holdings = current_state.get("portfolio", {}).get("holdings", [])
            for pos in state_holdings:
                ticker = pos.get("ticker")
                summary = pos.get("analysis_summary")
                if ticker and summary:
                    analysis_summaries_by_ticker[str(ticker)] = str(summary)
        except Exception as e:
            logger.warning(f"Could not load analysis summaries from state: {e}")
        
        # AGGRESSIVE cache clearing - clear multiple times to ensure it's gone
        
        # Clear cache multiple times with delays to ensure it's completely cleared
        for i in range(3):
            clear_cache()
            time.sleep(0.1)
        
        # Also manually clear the cache dict to be absolutely sure
        _cache.clear()
        
        logger.info(f"AGGRESSIVE cache clear completed. Cache size: {len(_cache)}")
        
        # Fetch FX rate (force fresh - bypass cache)
        fx_rate = fetch_fx_rate("USD", "GBP", force_refresh=True) or 0.79
        logger.info(f"FX Rate (USD->GBP): {fx_rate:.4f}")
        
        # Fetch all prices (fresh, no cache) - force_refresh bypasses cache
        symbols = [h.get("symbol", ticker) for ticker, h in holdings.items()]
        prices = fetch_all_prices(symbols, force_refresh=True)
        
        # Log fetched prices for debugging
        logger.info(f"Fetched prices: {dict((k, f'${v:.2f}' if v else None) for k, v in prices.items())}")
        
        # Calculate positions
        positions = []
        for ticker, holding in holdings.items():
            symbol = holding.get("symbol", ticker)
            shares = holding.get("shares", 0.0)
            baseline_value_gbp = holding.get("baseline_value_gbp", 0.0)
            
            # Determine currency
            if ".L" in symbol:
                currency = "GBP"
            else:
                currency = "USD"
            
            price = prices.get(symbol)
            current_value_gbp = get_position_value(symbol, shares, price, currency, fx_rate)
            
            # Debug logging for price calculations
            if ticker == "NVDA":  # Log NVDA specifically for debugging
                logger.info(f"NVDA: price=${price:.2f}, shares={shares:.8f}, currency={currency}, fx_rate={fx_rate:.4f}, value_gbp=£{current_value_gbp:.2f}")
            
            # Calculate P&L
            pnl = calculate_pnl(baseline_value_gbp, current_value_gbp)
            
            # Calculate action recommendation
            rules = portfolio_config.get("rules", {})
            take_profit_pct = rules.get("take_profit_pct", 40.0)
            cut_loss_pct = rules.get("cut_loss_pct", -25.0)
            action = evaluate_position_rules(
                baseline_value_gbp, current_value_gbp, take_profit_pct, cut_loss_pct
            )
            
            # Determine action reason
            action_reason = ""
            if pnl["change_pct"] >= take_profit_pct:
                action_reason = f"Take profit: +{pnl['change_pct']:.1f}%"
            elif pnl["change_pct"] <= cut_loss_pct:
                action_reason = f"Stop loss: {pnl['change_pct']:.1f}%"
            else:
                action_reason = "Within normal range"
            
            positions.append({
                "ticker": ticker,
                "symbol": symbol,
                "baseline_value_gbp": baseline_value_gbp,
                "current_value_gbp": current_value_gbp,
                "change_gbp": pnl["change_gbp"],
                "change_pct": pnl["change_pct"],
                "action": action.value if hasattr(action, 'value') else str(action),
                "action_reason": action_reason,
                # Attach the latest analysis summary from the last evaluation, if available
                "analysis_summary": analysis_summaries_by_ticker.get(ticker)
            })
        
        # Calculate totals (current baseline)
        totals = aggregate_portfolio_metrics(positions)
        
        # Calculate totals against original experiment baseline
        original_baseline_values = portfolio_config.get("original_baseline_values", {})
        original_baseline_total = sum(original_baseline_values.values())
        current_total = totals.get("total_current_value", 0.0)
        original_pnl_gbp = current_total - original_baseline_total
        original_pnl_pct = (original_pnl_gbp / original_baseline_total * 100) if original_baseline_total > 0 else 0.0
        
        totals["original_baseline_total"] = original_baseline_total
        totals["original_pnl_gbp"] = original_pnl_gbp
        totals["original_pnl_pct"] = original_pnl_pct

        # Baseline ages in days (current vs original)
        # Config semantics:
        # - baseline_date / original_baseline_date: experiment start
        # - current_baseline_date: date the current baseline values were locked
        original_baseline_date_str = str(
            portfolio_config.get("original_baseline_date", portfolio_config.get("baseline_date", "")) or ""
        )
        current_baseline_date_str = str(
            portfolio_config.get("current_baseline_date", original_baseline_date_str) or ""
        )
        today = datetime.now().date()

        def _age_days(date_str: str) -> int:
            try:
                # Expect ISO YYYY-MM-DD
                d = datetime.strptime(date_str.split("T")[0], "%Y-%m-%d").date()
                return max((today - d).days, 0)
            except Exception:
                return 0

        totals["current_baseline_age_days"] = _age_days(current_baseline_date_str)
        totals["original_baseline_age_days"] = _age_days(original_baseline_date_str)
        logger.info(
            f"Baseline ages (current/original): "
            f"{totals['current_baseline_age_days']} / {totals['original_baseline_age_days']}"
        )
        
        # Create a dictionary mapping tickers to their position data for easy lookup
        positions_by_ticker = {pos["ticker"]: pos for pos in positions}
        
        return {
            "positions": positions,
            "positions_by_ticker": positions_by_ticker,
            "totals": totals
        }
    except Exception as e:
        logger.error(f"Error calculating portfolio P&L: {e}", exc_info=True)
        return {"positions": [], "totals": {}}


@app.route('/')
def index():
    """Main dashboard page - reads from shared state."""
    # Load state from the shared state file
    if state_manager:
        state = state_manager.load_state()
        
        portfolio_data = state.get("portfolio", {})
        holdings = portfolio_data.get("holdings", [])
        totals = portfolio_data.get("totals", {})
        
        recommendations = state.get("recommendations", {})
        sell_recommendations = recommendations.get("sell", [])
        buy_recommendations = recommendations.get("buy", [])
        
        risk_assessment = state.get("risk_assessment", {})
        risk_score = risk_assessment.get("risk_score", 0)
        risk_level = risk_assessment.get("risk_level", "Unknown")
        risk_signals = risk_assessment.get("signals", {})
        risk_missing_market_inputs = risk_assessment.get("missing_market_inputs", [])
        risk_worst_position_pnl_pct = risk_assessment.get("worst_position_pnl_pct")
        
        last_updated = state.get("last_updated", "Never")
        system_status = state.get("system_status", "unknown")
    else:
        # Fallback if state manager not available
        holdings = []
        totals = {}
        sell_recommendations = []
        buy_recommendations = []
        risk_score = 0
        risk_level = "Unknown"
        risk_signals = {}
        risk_missing_market_inputs = []
        risk_worst_position_pnl_pct = None
        last_updated = "Never"
        system_status = "error"
    
    # Still load config and reports for display
    portfolio_config = load_portfolio_config()
    latest_report = load_latest_report()
    history = load_risk_history()[:30]  # Last 30 days
    
    # Calculate portfolio P&L for template (needed for holdings table)
    portfolio_pnl = calculate_portfolio_pnl(portfolio_config)
    
    # AGGRESSIVE cache-control headers to prevent browser caching
    response = app.make_response(render_template('dashboard.html',
                         portfolio=portfolio_config,
                         portfolio_pnl=portfolio_pnl,
                         latest_report=latest_report,
                         history=history,
                         holdings=holdings,
                         totals=totals,
                         sell_recommendations=sell_recommendations,
                         buy_recommendations=buy_recommendations,
                         risk_score=risk_score,
                         risk_level=risk_level,
                         risk_signals=risk_signals,
                         risk_missing_market_inputs=risk_missing_market_inputs,
                         risk_worst_position_pnl_pct=risk_worst_position_pnl_pct,
                         last_updated=last_updated,
                         system_status=system_status))
    # Set multiple cache-busting headers
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    response.headers['Last-Modified'] = datetime.now().strftime('%a, %d %b %Y %H:%M:%S GMT')
    response.headers['ETag'] = str(int(time.time() * 1000))  # Unique ETag every time
    return response


@app.route('/api/portfolio', methods=['GET'])
def get_portfolio():
    """Get current portfolio data from state."""
    if state_manager:
        state = state_manager.load_state()
        return jsonify(state.get("portfolio", {}))
    return jsonify(load_portfolio_config())


@app.route('/api/portfolio', methods=['POST'])
def update_portfolio():
    """Update portfolio configuration."""
    try:
        data = request.json
        
        # Validate required fields
        if 'holdings' not in data:
            return jsonify({"error": "Missing 'holdings' field"}), 400
        
        # Load current config to preserve structure
        current_config = load_portfolio_config()
        
        # Update holdings
        if 'holdings' in data:
            current_config['holdings'] = data['holdings']
        
        # Update rules if provided
        if 'rules' in data:
            current_config['rules'] = data['rules']
        
        # Update baseline date if provided
        if 'baseline_date' in data:
            current_config['baseline_date'] = data['baseline_date']
        
        # Save configuration
        save_portfolio_config(current_config)
        
        return jsonify({"success": True, "message": "Portfolio updated successfully"})
    
    except Exception as e:
        logger.error(f"Error updating portfolio: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@app.route('/api/holding/<ticker>', methods=['PUT'])
def update_holding(ticker: str):
    """Update a specific holding."""
    try:
        data = request.json
        portfolio_config = load_portfolio_config()
        
        if ticker not in portfolio_config.get('holdings', {}):
            return jsonify({"error": f"Holding '{ticker}' not found"}), 404
        
        # Update the holding
        for key, value in data.items():
            if key in portfolio_config['holdings'][ticker]:
                portfolio_config['holdings'][ticker][key] = value
        
        save_portfolio_config(portfolio_config)
        
        return jsonify({"success": True, "message": f"Holding '{ticker}' updated"})
    
    except Exception as e:
        logger.error(f"Error updating holding: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@app.route('/api/holding', methods=['POST'])
def add_holding():
    """Add a new holding."""
    try:
        data = request.json
        
        required_fields = ['ticker', 'symbol', 'shares', 'baseline_value_gbp']
        for field in required_fields:
            if field not in data:
                return jsonify({"error": f"Missing required field: {field}"}), 400
        
        portfolio_config = load_portfolio_config()
        ticker = data['ticker']
        
        if ticker in portfolio_config.get('holdings', {}):
            return jsonify({"error": f"Holding '{ticker}' already exists"}), 400
        
        # Add new holding
        portfolio_config.setdefault('holdings', {})[ticker] = {
            "symbol": data['symbol'],
            "shares": float(data['shares']),
            "baseline_value_gbp": float(data['baseline_value_gbp']),
            "type": data.get('type', 'equity'),
            "risk_bucket": data.get('risk_bucket', 'unknown')
        }
        
        save_portfolio_config(portfolio_config)
        
        return jsonify({"success": True, "message": f"Holding '{ticker}' added"})
    
    except Exception as e:
        logger.error(f"Error adding holding: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@app.route('/api/holding/<ticker>', methods=['DELETE'])
def delete_holding(ticker: str):
    """Delete a holding."""
    try:
        portfolio_config = load_portfolio_config()
        
        if ticker not in portfolio_config.get('holdings', {}):
            return jsonify({"error": f"Holding '{ticker}' not found"}), 404
        
        del portfolio_config['holdings'][ticker]
        save_portfolio_config(portfolio_config)
        
        return jsonify({"success": True, "message": f"Holding '{ticker}' deleted"})
    
    except Exception as e:
        logger.error(f"Error deleting holding: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@app.route('/api/evaluate', methods=['POST'])
def trigger_evaluation():
    """Trigger a new risk evaluation."""
    try:
        if state_manager:
            state_manager.update_status("running")
        
        # Run the evaluation script in background
        script_path = PROJECT_ROOT / "scripts" / "evaluate_risk.py"
        venv_python = PROJECT_ROOT / ".venv" / "bin" / "python3"
        
        if venv_python.exists():
            python_cmd = str(venv_python)
        else:
            python_cmd = sys.executable
        
        # Run in background (non-blocking)
        subprocess.Popen(
            [python_cmd, str(script_path)],
            cwd=str(PROJECT_ROOT)
        )
        
        return jsonify({
            "success": True,
            "message": "Evaluation started"
        })
    
    except Exception as e:
        logger.error(f"Error running evaluation: {e}", exc_info=True)
        if state_manager:
            state_manager.update_status("error")
        return jsonify({"error": str(e)}), 500


@app.route('/api/report/latest')
def get_latest_report():
    """Get the latest risk report."""
    report = load_latest_report()
    if report:
        return jsonify(report)
    else:
        return jsonify({"error": "No report found"}), 404


@app.route('/api/history')
def get_history():
    """Get risk score history."""
    history = load_risk_history()
    return jsonify(history)


@app.route('/api/buy-recommendations')
def get_buy_recommendations():
    """Get buy recommendations based on current portfolio."""
    try:
        # Import required functions
        from scripts.fetch_market_data import clear_cache
        from scripts.buy_recommendations import generate_buy_recommendations
        from scripts.recommendation_formatter import format_recommendations_for_discussion
        
        # Force fresh calculation - clear cache first
        clear_cache()
        
        portfolio_config = load_portfolio_config()
        # Calculate fresh P&L with current prices (cache already cleared above)
        portfolio_pnl = calculate_portfolio_pnl(portfolio_config)
        
        # Calculate available funds from sell recommendations using FRESH data
        available_funds = 0.0
        sell_recommendations = []
        positions = portfolio_pnl.get("positions", [])
        
        logger.info(f"Buy recommendations: Processing {len(positions)} positions from fresh P&L calculation")
        
        for pos in positions:
            action = pos.get("action", "HOLD")
            ticker = pos.get("ticker", "Unknown")
            current_value = pos.get("current_value_gbp", 0.0)
            change_pct = pos.get("change_pct", 0.0)
            
            # Log for debugging
            if action in ["SELL", "REDUCE"]:
                logger.info(f"  {ticker}: {action} - Current: £{current_value:.2f}, P&L: {change_pct:+.2f}%")
            
            if action in ["SELL", "REDUCE"]:
                sell_recommendations.append(pos)
                if action == "SELL":
                    available_funds += current_value
                elif action == "REDUCE":
                    available_funds += current_value * 0.5
        
        logger.info(f"Buy recommendations: Found {len(sell_recommendations)} sell recommendations, available funds: £{available_funds:.2f}")
        
        # Load buy signal config
        signals_config_path = CONFIG_DIR / "signals.yaml"
        buy_config = {}
        if signals_config_path.exists():
            with open(signals_config_path, 'r') as f:
                signals_config = yaml.safe_load(f)
                buy_config = signals_config.get("buy_signals", {})
        
        # Generate buy recommendations
        buy_recommendations = []
        try:
            buy_recommendations = generate_buy_recommendations(
                available_funds=available_funds,
                watchlist=buy_config.get("watchlist"),
                buy_config=buy_config
            )
        except Exception as e:
            logger.error(f"Error generating buy recommendations: {e}", exc_info=True)
        
        # Format for discussion
        recommendations_text = ""
        try:
            recommendations_text = format_recommendations_for_discussion(
                sell_recommendations=sell_recommendations,
                buy_recommendations=buy_recommendations,
                available_funds=available_funds,
                portfolio_value=portfolio_pnl.get("totals", {}).get("total_current_value", 0.0)
            )
        except Exception as e:
            logger.error(f"Error formatting recommendations: {e}", exc_info=True)
        
        return jsonify({
            "sell_recommendations": sell_recommendations,
            "buy_recommendations": buy_recommendations,
            "available_funds": available_funds,
            "recommendations_text": recommendations_text
        })
    
    except Exception as e:
        logger.error(f"Error getting buy recommendations: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@app.route('/reports/<path:filename>')
def serve_report(filename):
    """Serve report files."""
    return send_from_directory(REPORTS_DIR, filename)


if __name__ == '__main__':
    # Disable reloader completely to avoid cache issues
    import os
    import sys
    # Prevent Python from writing .pyc files
    sys.dont_write_bytecode = True
    os.environ['FLASK_ENV'] = 'production'
    os.environ['FLASK_DEBUG'] = '0'
    os.environ['PYTHONDONTWRITEBYTECODE'] = '1'
    # Force no reloader - use werkzeug directly with explicit parameters
    from werkzeug.serving import run_simple
    # CRITICAL: use_reloader MUST be False, and we need to prevent any file watching
    run_simple(
        '127.0.0.1', 
        5001, 
        app, 
        use_reloader=False, 
        use_debugger=False, 
        threaded=True,
        processes=1
    )

