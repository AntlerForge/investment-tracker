"""
Main entry point for daily risk evaluation.

This script orchestrates the entire risk evaluation workflow:
1. Load configuration files
2. Fetch market data
3. Evaluate signals
4. Compute risk scores
5. Generate reports
"""

import argparse
import sys
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import yaml

# Add scripts directory to path for imports
scripts_dir = Path(__file__).parent
project_root = scripts_dir.parent
sys.path.insert(0, str(scripts_dir))
sys.path.insert(0, str(project_root))

# Try relative imports first, then absolute
try:
    from fetch_market_data import (
        fetch_stock_price,
        fetch_fx_rate,
        fetch_macro_indicator,
        fetch_all_prices,
        fetch_insider_trades,
        fetch_options_activity
    )
    from portfolio_logic import (
        calculate_pnl,
        evaluate_position_rules,
        get_position_value,
        aggregate_portfolio_metrics,
        apply_signal_adjustments,
        Action
    )
    from signals_engine import (
        evaluate_macro_signals,
        evaluate_sector_signals,
        evaluate_stock_signals,
        compute_risk_score,
        get_risk_level
    )
    from buy_recommendations import generate_buy_recommendations
    from recommendation_formatter import format_recommendations_for_discussion, save_recommendations_to_file
    from report_generator import (
        generate_markdown_report,
        generate_html_report,
        save_history_entry
    )
    from state_manager import StateManager
except ImportError:
    # Fallback to absolute imports
    from scripts.fetch_market_data import (
        fetch_stock_price,
        fetch_fx_rate,
        fetch_macro_indicator,
        fetch_all_prices,
        fetch_insider_trades,
        fetch_options_activity
    )
    from scripts.portfolio_logic import (
        calculate_pnl,
        evaluate_position_rules,
        get_position_value,
        aggregate_portfolio_metrics,
        apply_signal_adjustments,
        Action
    )
    from scripts.signals_engine import (
        evaluate_macro_signals,
        evaluate_sector_signals,
        evaluate_stock_signals,
        compute_risk_score,
        get_risk_level
    )
    from scripts.report_generator import (
        generate_markdown_report,
        generate_html_report,
        save_history_entry
    )


def setup_logging(log_dir: Path, evaluation_date: datetime) -> logging.Logger:
    """Set up logging to file and console."""
    log_file = log_dir / f"eval_{evaluation_date.strftime('%Y-%m-%d')}.log"
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    return logging.getLogger(__name__)


def _summarise_signals(signals: Dict[str, Any]) -> str:
    """
    Create a short text summary of a signals dict (macro / sector / stock).
    This is deterministic and purely rule-based – no AI.
    """
    if not signals:
        return "No specific signals were triggered."

    positive_keys: List[str] = []
    negative_keys: List[str] = []

    for key, value in signals.items():
        # Treat True / positive numbers as positive, False / negative as negative
        if isinstance(value, (int, float)):
            if value > 0:
                positive_keys.append(key)
            elif value < 0:
                negative_keys.append(key)
        elif isinstance(value, bool):
            if value:
                positive_keys.append(key)
        # Ignore other types for this simple summary

    parts: List[str] = []
    if positive_keys:
        parts.append(
            f"Constructive signals: {', '.join(sorted(positive_keys))}."
        )
    if negative_keys:
        parts.append(
            f"Caution signals: {', '.join(sorted(negative_keys))}."
        )

    if not parts:
        return "Signals are mostly neutral with no strong positives or negatives."

    return " ".join(parts)


def build_position_summary(
    pos: Dict[str, Any],
    macro_signals: Dict[str, Any],
    sector_signals: Dict[str, Any],
    stock_signals: Dict[str, Any]
) -> str:
    """
    Build a ~250-word style summary for a single holding.

    The goal is to provide a rich but deterministic narrative that explains:
    - Baseline vs current value and P&L
    - Risk bucket and action
    - Macro / sector / stock-level context
    """
    ticker = pos.get("ticker", "")
    symbol = pos.get("symbol", ticker)
    baseline = float(pos.get("baseline_value_gbp", 0.0) or 0.0)
    current = float(pos.get("current_value_gbp", 0.0) or 0.0)
    change_gbp = float(pos.get("change_gbp", 0.0) or 0.0)
    change_pct = float(pos.get("change_pct", 0.0) or 0.0)
    risk_bucket = str(pos.get("risk_bucket", "unknown"))
    action = str(pos.get("action", "HOLD"))
    action_reason = str(pos.get("action_reason", "") or "").strip()

    direction_prefix = "+" if change_gbp >= 0 else ""
    pct_prefix = "+" if change_pct >= 0 else ""

    # Core valuation and rule context
    intro = (
        f"{ticker} ({symbol}) is currently valued at £{current:.2f} "
        f"against a baseline of £{baseline:.2f}, giving a mark-to-market "
        f"change of {direction_prefix}£{change_gbp:.2f} "
        f"({pct_prefix}{change_pct:.2f}%). "
    )

    bucket_text = (
        f"It sits in the '{risk_bucket}' risk bucket, which reflects how much "
        f"volatility and drawdown we are prepared to tolerate for this position. "
    )

    if action_reason:
        action_text = (
            f"The current rule-based action is **{action}** {action_reason}. "
        )
    else:
        action_text = (
            f"The current rule-based action is **{action}**, with the position "
            f"remaining inside the normal tolerance band for now. "
        )

    # Macro, sector and stock signal summaries
    macro_text = (
        "From a macro perspective, the broader market backdrop is interpreted "
        "through indicators such as VIX, credit spreads and key index levels. "
        f"{_summarise_signals(macro_signals)} "
    )

    sector_text = (
        "Sector-level signals capture whether the immediate ecosystem around "
        f"{ticker} is trending risk-on or risk-off relative to the wider market. "
        f"{_summarise_signals(sector_signals)} "
    )

    stock_text = (
        "At the stock level, the engine folds together insider activity, options "
        "flows and other micro signals into a single risk-adjusted tilt. "
        f"{_summarise_signals(stock_signals)} "
    )

    forward_look = (
        "Taken together, this keeps the emphasis on medium to high risk and "
        "high potential reward, while staying anchored to explicit rules rather "
        "than intuition. The summary should be read as a snapshot, updated each "
        "time a fresh evaluation is run rather than a standing recommendation. "
    )

    # Join everything into one long paragraph suitable for a hover tooltip
    summary = (
        intro
        + bucket_text
        + action_text
        + macro_text
        + sector_text
        + stock_text
        + forward_look
    )

    return summary


def load_config(config_path: str) -> Dict[str, Any]:
    """
    Load portfolio configuration from YAML file.
    
    Args:
        config_path: Path to portfolio.yaml
        
    Returns:
        Dictionary containing portfolio configuration
    """
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)


def load_signals(signals_path: str) -> Dict[str, Any]:
    """
    Load signals configuration from YAML file.
    
    Args:
        signals_path: Path to signals.yaml
        
    Returns:
        Dictionary containing signals configuration
    """
    with open(signals_path, 'r') as f:
        return yaml.safe_load(f)


def main():
    """
    Main entry point for risk evaluation.
    
    Orchestrates the full evaluation workflow and generates reports.
    """
    parser = argparse.ArgumentParser(description="Evaluate portfolio risk")
    parser.add_argument(
        "--config",
        type=str,
        default="config/portfolio.yaml",
        help="Path to portfolio configuration file"
    )
    parser.add_argument(
        "--signals",
        type=str,
        default="config/signals.yaml",
        help="Path to signals configuration file"
    )
    parser.add_argument(
        "--date",
        type=str,
        default=None,
        help="Evaluation date (YYYY-MM-DD). Defaults to today."
    )
    
    args = parser.parse_args()
    
    # Determine evaluation date
    if args.date:
        evaluation_date = datetime.strptime(args.date, "%Y-%m-%d")
    else:
        evaluation_date = datetime.now()
    
    # Set up paths (use project_root from imports if available, otherwise calculate)
    if 'project_root' not in locals():
        project_root = Path(__file__).parent.parent
    config_path = project_root / args.config
    signals_path = project_root / args.signals
    reports_dir = project_root / "reports" / "daily"
    history_dir = project_root / "data" / "history"
    logs_dir = project_root / "logs"
    
    # Ensure directories exist
    reports_dir.mkdir(parents=True, exist_ok=True)
    history_dir.mkdir(parents=True, exist_ok=True)
    logs_dir.mkdir(parents=True, exist_ok=True)
    
    # Set up logging
    logger = setup_logging(logs_dir, evaluation_date)
    logger.info(f"Starting risk evaluation for {evaluation_date.strftime('%Y-%m-%d')}")
    
    try:
        # Load configurations
        logger.info("Loading configurations...")
        portfolio_config = load_config(config_path)
        signals_config = load_signals(signals_path)
        
        holdings = portfolio_config.get("holdings", {})
        rules = portfolio_config.get("rules", {})
        take_profit_pct = rules.get("take_profit_pct", 40.0)
        cut_loss_pct = rules.get("cut_loss_pct", -25.0)
        
        # Fetch market data
        logger.info("Fetching market data...")
        data_quality_warnings = []
        
        # CRITICAL: Clear cache to ensure fresh data
        from fetch_market_data import clear_cache
        clear_cache()
        logger.info("Cleared price cache to ensure fresh data")
        
        # Fetch FX rate (GBP/USD) - force fresh
        fx_rate = fetch_fx_rate("USD", "GBP", force_refresh=True)
        if fx_rate is None:
            logger.warning("Failed to fetch GBP/USD rate, using default 0.79")
            fx_rate = 0.79
            data_quality_warnings.append("FX rate unavailable, using default")
        else:
            logger.info(f"FX Rate (USD->GBP): {fx_rate:.4f}")
        
        # Fetch stock prices - force fresh with cache cleared
        symbols = [h.get("symbol", ticker) for ticker, h in holdings.items()]
        prices = fetch_all_prices(symbols, force_refresh=True)
        
        # Log fetched prices for debugging
        logger.info(f"Fetched prices: {dict((k, f'${v:.2f}' if v else None) for k, v in prices.items())}")
        
        # Check for missing prices
        missing_prices = [s for s, p in prices.items() if p is None]
        if missing_prices:
            logger.warning(f"Missing prices for: {missing_prices}")
            data_quality_warnings.append(f"Missing prices for: {', '.join(missing_prices)}")
        
        # Fetch macro indicators
        market_data = {}
        macro_indicators = ["VIX", "HYG", "QQQ", "US10Y"]
        for indicator in macro_indicators:
            value = fetch_macro_indicator(indicator)
            market_data[indicator] = value
            if value is None:
                logger.warning(f"Failed to fetch {indicator}")
                data_quality_warnings.append(f"{indicator} data unavailable")
        
        # Fetch previous day data for sector signals
        # For divergence detection, we need previous day prices
        previous_date = evaluation_date - timedelta(days=1)
        nvda_prev = fetch_stock_price("NVDA", previous_date)
        qqq_prev = fetch_macro_indicator("QQQ", previous_date)
        sox_prev = fetch_macro_indicator("SOX", previous_date)
        
        market_data["NVDA"] = prices.get("NVDA")
        market_data["NVDA_prev"] = nvda_prev
        market_data["QQQ"] = market_data.get("QQQ")
        market_data["QQQ_prev"] = qqq_prev
        market_data["SOX"] = fetch_macro_indicator("SOX")  # Semiconductor index
        market_data["SOX_prev"] = sox_prev
        
        # Calculate positions
        logger.info("Calculating positions...")
        positions = []
        
        for ticker, holding in holdings.items():
            symbol = holding.get("symbol", ticker)
            shares = holding.get("shares", 0.0)
            baseline_value_gbp = holding.get("baseline_value_gbp", 0.0)
            risk_bucket = holding.get("risk_bucket", "unknown")
            
            # Determine currency
            if ".L" in symbol:
                currency = "GBP"
            else:
                currency = "USD"
            
            price = prices.get(symbol)
            current_value_gbp = get_position_value(symbol, shares, price, currency, fx_rate)
            
            # Debug logging for key positions
            if ticker in ["NVDA", "AML", "SMCI"]:
                logger.info(f"{ticker}: price=${price:.2f} {currency}, shares={shares:.8f}, fx_rate={fx_rate:.4f}, value_gbp=£{current_value_gbp:.2f}, baseline=£{baseline_value_gbp:.2f}")
            
            # Calculate P&L
            pnl = calculate_pnl(baseline_value_gbp, current_value_gbp)
            
            # Evaluate base action from rules
            base_action = evaluate_position_rules(
                baseline_value_gbp, current_value_gbp, take_profit_pct, cut_loss_pct
            )
            
            # Get stock signals
            insider_trades = fetch_insider_trades(symbol)
            options_activity = fetch_options_activity(symbol)
            stock_signals = evaluate_stock_signals(
                symbol, insider_trades, options_activity,
                signals_config.get("stock_level", {})
            )
            
            # Apply signal adjustments
            signals_dict = {
                "macro": {},  # Will be filled later
                "sector": {},  # Will be filled later
                "stock": stock_signals
            }
            final_action = apply_signal_adjustments(base_action, signals_dict, risk_bucket)
            
            # Determine action reason
            action_reason = ""
            if pnl["change_pct"] >= take_profit_pct:
                action_reason = f"(take profit: +{pnl['change_pct']:.1f}%)"
            elif pnl["change_pct"] <= cut_loss_pct:
                action_reason = f"(stop loss: {pnl['change_pct']:.1f}%)"
            
            positions.append({
                "ticker": ticker,
                "symbol": symbol,
                "shares": shares,
                "baseline_value_gbp": baseline_value_gbp,
                "current_value_gbp": current_value_gbp,
                "change_gbp": pnl["change_gbp"],
                "change_pct": pnl["change_pct"],
                "action": final_action.value,
                "action_reason": action_reason,
                "risk_bucket": risk_bucket
            })
        
        # Aggregate portfolio metrics
        portfolio_metrics = aggregate_portfolio_metrics(positions)
        
        # Evaluate signals
        logger.info("Evaluating signals...")
        macro_signals = evaluate_macro_signals(
            market_data, signals_config.get("macro", {})
        )
        sector_signals = evaluate_sector_signals(
            market_data, signals_config.get("sector", {})
        )
        
        # Collect all stock signals
        all_stock_signals = {}
        for pos in positions:
            symbol = pos["symbol"]
            insider_trades = fetch_insider_trades(symbol)
            options_activity = fetch_options_activity(symbol)
            all_stock_signals[symbol] = evaluate_stock_signals(
                symbol, insider_trades, options_activity,
                signals_config.get("stock_level", {})
            )
        
        # Compute risk score
        # Also incorporate position-level drawdown and data completeness so the score is more informative.
        worst_position_pnl_pct = None
        try:
            if positions:
                worst_position_pnl_pct = min(p.get("change_pct", 0.0) for p in positions)
        except Exception:
            worst_position_pnl_pct = None

        # Track missing market inputs that would suppress macro/sector signal evaluation
        required_market_keys = ["VIX", "HYG", "QQQ", "US10Y", "NVDA", "SOX", "NVDA_prev", "QQQ_prev", "SOX_prev"]
        missing_market_inputs = [k for k in required_market_keys if market_data.get(k) is None]

        risk_score = compute_risk_score(
            macro_signals,
            sector_signals,
            all_stock_signals,
            portfolio_metrics["total_change_pct"],
            worst_position_pnl_pct=worst_position_pnl_pct,
            missing_market_inputs=missing_market_inputs
        )
        risk_level = get_risk_level(risk_score)
        
        logger.info(f"Risk score: {risk_score}/100 ({risk_level})")
        
        # Update positions with signal-adjusted actions and build per-holding notes
        sell_recommendations: List[Dict[str, Any]] = []
        for pos in positions:
            symbol = pos["symbol"]
            stock_signals_for_symbol = all_stock_signals.get(symbol, {})

            signals_dict = {
                "macro": macro_signals,
                "sector": sector_signals,
                "stock": stock_signals_for_symbol
            }
            base_action = Action(pos["action"])
            final_action = apply_signal_adjustments(
                base_action, signals_dict, pos["risk_bucket"]
            )
            pos["action"] = final_action.value

            # Build a deterministic analysis summary for this holding
            try:
                pos["analysis_summary"] = build_position_summary(
                    pos,
                    macro_signals=macro_signals,
                    sector_signals=sector_signals,
                    stock_signals=stock_signals_for_symbol
                )
            except Exception as e:
                # If anything goes wrong, don't break the evaluation – just log and continue
                logger.warning(
                    f"Could not build analysis summary for {pos.get('ticker')}: {e}",
                    exc_info=True
                )
                pos["analysis_summary"] = (
                    "Summary unavailable due to an internal error while building the note."
                )
            
            # Collect sell recommendations
            if final_action.value in ["SELL", "REDUCE"]:
                sell_recommendations.append(pos)
        
        # Calculate available funds from sell recommendations
        available_funds = 0.0
        for rec in sell_recommendations:
            if rec["action"] == "SELL":
                available_funds += rec.get("current_value_gbp", 0.0)
            elif rec["action"] == "REDUCE":
                # For REDUCE, assume 50% of position is sold
                available_funds += rec.get("current_value_gbp", 0.0) * 0.5
        
        # Generate buy recommendations based on available funds
        logger.info("Generating buy recommendations...")
        buy_config = signals_config.get("buy_signals", {})
        buy_recommendations = []
        if available_funds > 0 or buy_config.get("watchlist"):
            try:
                buy_recommendations = generate_buy_recommendations(
                    available_funds=available_funds,
                    watchlist=buy_config.get("watchlist"),
                    buy_config=buy_config
                )
                logger.info(f"Generated {len(buy_recommendations)} buy recommendations")
            except Exception as e:
                logger.warning(f"Error generating buy recommendations: {e}", exc_info=True)
        
        # Format recommendations for discussion
        recommendations_text = format_recommendations_for_discussion(
            sell_recommendations=sell_recommendations,
            buy_recommendations=buy_recommendations,
            available_funds=available_funds,
            portfolio_value=portfolio_metrics["total_current_value"]
        )
        
        # Save recommendations to file
        recommendations_file = save_recommendations_to_file(
            recommendations_text,
            str(reports_dir),
            evaluation_date
        )
        logger.info(f"Saved recommendations to: {recommendations_file}")
        
        # Generate reports
        logger.info("Generating reports...")
        markdown_report = generate_markdown_report(
            evaluation_date,
            portfolio_config,
            positions,
            portfolio_metrics,
            risk_score,
            risk_level,
            macro_signals,
            sector_signals,
            market_data,
            data_quality_warnings,
            buy_recommendations=buy_recommendations,
            available_funds=available_funds
        )
        
        # Save markdown report
        report_filename = f"{evaluation_date.strftime('%Y-%m-%d')}_risk_report.md"
        report_path = reports_dir / report_filename
        with open(report_path, 'w') as f:
            f.write(markdown_report)
        logger.info(f"Saved markdown report: {report_path}")
        
        # Generate and save HTML report
        html_report = generate_html_report(markdown_report)
        html_filename = f"{evaluation_date.strftime('%Y-%m-%d')}_risk_report.html"
        html_path = reports_dir / html_filename
        with open(html_path, 'w') as f:
            f.write(html_report)
        logger.info(f"Saved HTML report: {html_path}")
        
        # Update dashboard symlink
        dashboard_path = project_root / "reports" / "dashboards" / "latest.html"
        dashboard_path.parent.mkdir(parents=True, exist_ok=True)
        if dashboard_path.exists() or dashboard_path.is_symlink():
            try:
                dashboard_path.unlink()
            except Exception as e:
                logger.warning(f"Could not remove existing symlink: {e}")
        try:
            dashboard_path.symlink_to(html_path.relative_to(dashboard_path.parent.parent))
        except Exception as e:
            logger.warning(f"Could not create symlink: {e}. You can manually link the latest report.")
        
        # Save history entry
        save_history_entry(
            history_dir,
            evaluation_date,
            risk_score,
            portfolio_metrics["total_current_value"],
            portfolio_metrics["total_change_pct"]
        )
        
        # Save system state for dashboard and CLI access
        logger.info("Saving system state...")
        state_manager = StateManager(project_root)
        
        # Prepare portfolio data for state
        portfolio_state = {
            "holdings": positions,
            "totals": {
                "total_value_gbp": portfolio_metrics["total_current_value"],
                "total_baseline_value": portfolio_metrics["total_baseline_value"],
                "total_pnl_gbp": portfolio_metrics["total_change_gbp"],
                "total_pnl_pct": portfolio_metrics["total_change_pct"],
                "available_funds": available_funds,
                "fx_rate": fx_rate
            }
        }
        
        risk_assessment_state = {
            "risk_score": risk_score,
            "risk_level": risk_level,
            "worst_position_pnl_pct": worst_position_pnl_pct,
            "missing_market_inputs": missing_market_inputs,
            "signals": {
                "macro": macro_signals,
                "sector": sector_signals,
                "stock": all_stock_signals
            }
        }
        
        state_manager.save_state(
            portfolio_data=portfolio_state,
            buy_recommendations=buy_recommendations,
            sell_recommendations=sell_recommendations,
            risk_assessment=risk_assessment_state,
            system_status="idle"
        )
        logger.info("System state saved successfully")
        
        logger.info("Risk evaluation completed successfully")
        print(f"\n✅ Risk evaluation completed!")
        print(f"📊 Risk Score: {risk_score}/100 ({risk_level})")
        print(f"💰 Portfolio Change: {portfolio_metrics['total_change_pct']:.2f}%")
        print(f"📄 Reports saved to: {reports_dir}")
        
    except Exception as e:
        logger.error(f"Error during evaluation: {e}", exc_info=True)
        print(f"❌ Error: {e}", file=sys.stderr)
        # Update state to error status
        try:
            state_manager = StateManager(project_root)
            state_manager.update_status("error")
        except:
            pass
        sys.exit(1)


if __name__ == "__main__":
    main()

