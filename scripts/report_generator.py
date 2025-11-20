"""
Report generation module.

Generates markdown and HTML reports with portfolio analysis, risk scores, and recommendations.
"""

from typing import Dict, List, Any, Optional
from datetime import datetime
from pathlib import Path
import logging

try:
    import matplotlib
    matplotlib.use('Agg')  # Non-interactive backend
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    logging.warning("matplotlib not available. Charts will be skipped.")

logger = logging.getLogger(__name__)


def generate_markdown_report(
    evaluation_date: datetime,
    portfolio_config: Dict[str, Any],
    positions: List[Dict[str, Any]],
    portfolio_metrics: Dict[str, Any],
    risk_score: int,
    risk_level: str,
    macro_signals: Dict[str, Any],
    sector_signals: Dict[str, Any],
    market_data: Dict[str, Optional[float]],
    data_quality_warnings: List[str],
    buy_recommendations: Optional[List[Dict[str, Any]]] = None,
    available_funds: float = 0.0
) -> str:
    """
    Generate markdown risk report.
    
    Args:
        evaluation_date: Date of evaluation
        portfolio_config: Portfolio configuration
        positions: List of position dictionaries with P&L and actions
        portfolio_metrics: Aggregated portfolio metrics
        risk_score: Risk score (0-100)
        risk_level: Risk level string
        macro_signals: Macro signals dictionary
        sector_signals: Sector signals dictionary
        market_data: Market data dictionary
        data_quality_warnings: List of data quality warnings
        
    Returns:
        Markdown report as string
    """
    baseline_date = portfolio_config.get("baseline_date", "Unknown")
    currency = portfolio_config.get("currency", "GBP")
    
    report = []
    report.append(f"# Daily Risk Report — {evaluation_date.strftime('%d %b %Y')} ({evaluation_date.strftime('%H:%M')} UK)")
    report.append(f"Baseline: {baseline_date} • Currency: {currency}")
    report.append("")
    
    # Data quality warnings
    if data_quality_warnings:
        report.append("## ⚠️ Data Quality Warnings")
        for warning in data_quality_warnings:
            report.append(f"- ⚠ {warning}")
        report.append("")
    
    # Summary
    report.append("## 🔍 Summary")
    report.append(f"- **Risk Score:** {risk_score} / 100 ({risk_level})")
    report.append(f"- **Overall P&L vs Baseline:** {portfolio_metrics['total_change_pct']:.2f}%")
    report.append(f"- **Total Portfolio Value:** {currency} {portfolio_metrics['total_current_value']:.2f}")
    report.append("")
    
    # Triggered signals
    report.append("## 📊 Triggered Signals")
    
    # Macro signals
    macro_items = []
    if macro_signals.get("vix_critical"):
        macro_items.append(f"VIX Critical (≥25): {market_data.get('VIX', 'N/A')}")
    elif macro_signals.get("vix_warning"):
        macro_items.append(f"VIX Warning (≥20): {market_data.get('VIX', 'N/A')}")
    if macro_signals.get("credit_stress"):
        macro_items.append("Credit Stress (HYG declining)")
    if macro_signals.get("yield_spike"):
        macro_items.append(f"Yield Spike: {market_data.get('US10Y', 'N/A')}%")
    
    if macro_items:
        report.append("**Macro Signals:**")
        for item in macro_items:
            report.append(f"- {item}")
    else:
        report.append("**Macro Signals:** None")
    
    # Sector signals
    sector_items = []
    if sector_signals.get("nvda_divergence"):
        sector_items.append("NVDA Divergence (NVDA dropping while QQQ flat)")
    if sector_signals.get("semi_momentum_negative"):
        sector_items.append("Semiconductor Momentum Negative")
    
    if sector_items:
        report.append("**Sector Signals:**")
        for item in sector_items:
            report.append(f"- {item}")
    else:
        report.append("**Sector Signals:** None")
    
    report.append("")
    
    # Suggested actions
    report.append("## ✅ Suggested Actions")
    
    sell_positions = [p for p in positions if p.get("action") == "SELL"]
    reduce_positions = [p for p in positions if p.get("action") == "REDUCE"]
    hold_positions = [p for p in positions if p.get("action") == "HOLD"]
    
    if sell_positions:
        report.append("**SELL:**")
        for pos in sell_positions:
            ticker = pos.get("ticker", "Unknown")
            reason = pos.get("action_reason", "")
            report.append(f"- {ticker} {reason}")
    
    if reduce_positions:
        report.append("**REDUCE:**")
        for pos in reduce_positions:
            ticker = pos.get("ticker", "Unknown")
            reason = pos.get("action_reason", "")
            report.append(f"- {ticker} {reason}")
    
    if hold_positions:
        report.append("**HOLD:**")
        tickers = [p.get("ticker", "Unknown") for p in hold_positions]
        report.append(f"- {', '.join(tickers)}")
    
    report.append("")
    
    # Buy Recommendations
    if buy_recommendations:
        report.append("## 💰 Buy Recommendations")
        if available_funds > 0:
            report.append(f"**Available Funds from Sales:** £{available_funds:,.2f}")
        report.append("")
        report.append("| Symbol | Recommendation | Confidence | Suggested Allocation | Signals |")
        report.append("|--------|---------------|------------|---------------------|---------|")
        
        for rec in buy_recommendations[:10]:  # Top 10
            symbol = rec.get("symbol", "Unknown")
            recommendation = rec.get("recommendation", "CONSIDER")
            confidence = rec.get("confidence_score", 0)
            allocation = rec.get("suggested_allocation_gbp", 0.0)
            reasons = rec.get("reasons", [])
            signals = "; ".join(reasons[:2])  # First 2 reasons
            
            report.append(
                f"| {symbol} | {recommendation} | {confidence}/100 | "
                f"£{allocation:,.2f} | {signals} |"
            )
        report.append("")
    
    # Holdings P&L table
    report.append("## 📊 Holdings P&L")
    report.append("| Holding | Start (£) | Current (£) | Change (£) | Change (%) | Action |")
    report.append("|---------|----------:|------------:|-----------:|-----------:|--------|")
    
    for pos in positions:
        ticker = pos.get("ticker", "Unknown")
        baseline = pos.get("baseline_value_gbp", 0.0)
        current = pos.get("current_value_gbp", 0.0)
        change_gbp = pos.get("change_gbp", 0.0)
        change_pct = pos.get("change_pct", 0.0)
        action = pos.get("action", "HOLD")
        
        report.append(
            f"| {ticker} | {baseline:.2f} | {current:.2f} | "
            f"{change_gbp:+.2f} | {change_pct:+.2f}% | {action} |"
        )
    
    # Total row
    total_baseline = portfolio_metrics.get("total_baseline_value", 0.0)
    total_current = portfolio_metrics.get("total_current_value", 0.0)
    total_change_gbp = portfolio_metrics.get("total_change_gbp", 0.0)
    total_change_pct = portfolio_metrics.get("total_change_pct", 0.0)
    
    report.append(
        f"| **TOTAL** | **{total_baseline:.2f}** | **{total_current:.2f}** | "
        f"**{total_change_gbp:+.2f}** | **{total_change_pct:+.2f}%** | |"
    )
    report.append("")
    
    # Risk indicators
    report.append("## 📈 Risk Indicators")
    
    vix = market_data.get("VIX")
    if vix is not None:
        report.append(f"- **VIX:** {vix:.2f} (Warning threshold: 20, Critical: 25)")
    
    hyg = market_data.get("HYG")
    qqq = market_data.get("QQQ")
    if hyg is not None and qqq is not None:
        report.append(f"- **HYG:** {hyg:.2f}, **QQQ:** {qqq:.2f}")
    
    us10y = market_data.get("US10Y")
    if us10y is not None:
        report.append(f"- **US10Y:** {us10y:.2f}%")
    
    report.append("")
    report.append(f"---")
    report.append(f"*Report generated at {evaluation_date.strftime('%Y-%m-%d %H:%M:%S')}*")
    
    return "\n".join(report)


def generate_html_report(
    markdown_content: str,
    chart_path: Optional[str] = None
) -> str:
    """
    Convert markdown report to HTML with styling.
    
    Args:
        markdown_content: Markdown report content
        chart_path: Optional path to chart image
        
    Returns:
        HTML report as string
    """
    # Simple markdown to HTML conversion (basic)
    html = []
    html.append("<!DOCTYPE html>")
    html.append("<html><head>")
    html.append('<meta charset="UTF-8">')
    html.append('<meta name="viewport" content="width=device-width, initial-scale=1.0">')
    html.append("<title>Risk Portfolio Report</title>")
    html.append("<style>")
    html.append("""
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            line-height: 1.6;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }
        .container {
            background: white;
            padding: 30px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        h1 { color: #333; border-bottom: 3px solid #4CAF50; padding-bottom: 10px; }
        h2 { color: #555; margin-top: 30px; }
        table {
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
        }
        th, td {
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }
        th {
            background-color: #4CAF50;
            color: white;
        }
        tr:hover { background-color: #f5f5f5; }
        .warning { color: #ff9800; }
        .critical { color: #f44336; }
        .positive { color: #4CAF50; }
        .negative { color: #f44336; }
        ul { margin: 10px 0; }
        li { margin: 5px 0; }
        img { max-width: 100%; height: auto; margin: 20px 0; }
    """)
    html.append("</style>")
    html.append("</head><body>")
    html.append('<div class="container">')
    
    # Convert markdown to HTML (simplified)
    lines = markdown_content.split("\n")
    in_table = False
    
    for line in lines:
        if line.startswith("# "):
            html.append(f"<h1>{line[2:]}</h1>")
        elif line.startswith("## "):
            html.append(f"<h2>{line[3:]}</h2>")
        elif line.startswith("|") and "---" not in line:
            if not in_table:
                html.append("<table>")
                in_table = True
            cells = [c.strip() for c in line.split("|")[1:-1]]
            tag = "th" if "**" in line else "td"
            html.append("<tr>")
            for cell in cells:
                cell_html = cell.replace("**", "<strong>").replace("<strong>", "</strong>", 1) if "**" in cell else cell
                html.append(f"<{tag}>{cell_html}</{tag}>")
            html.append("</tr>")
        elif line.startswith("|") and "---" in line:
            continue
        elif in_table and not line.startswith("|"):
            html.append("</table>")
            in_table = False
        elif line.startswith("- "):
            html.append(f"<li>{line[2:]}</li>")
        elif line.strip():
            html.append(f"<p>{line}</p>")
        else:
            html.append("<br>")
    
    if in_table:
        html.append("</table>")
    
    # Add chart if available
    if chart_path and Path(chart_path).exists():
        html.append(f'<img src="{chart_path}" alt="Portfolio Chart">')
    
    html.append("</div>")
    html.append("</body></html>")
    
    return "\n".join(html)


def save_history_entry(
    history_path: Path,
    evaluation_date: datetime,
    risk_score: int,
    portfolio_value: float,
    portfolio_change_pct: float
):
    """
    Append entry to risk_scores.csv history file.
    
    Args:
        history_path: Path to history directory
        evaluation_date: Date of evaluation
        risk_score: Risk score
        portfolio_value: Total portfolio value
        portfolio_change_pct: Portfolio change percentage
    """
    csv_path = history_path / "risk_scores.csv"
    
    # Create CSV with header if it doesn't exist
    if not csv_path.exists():
        with open(csv_path, "w") as f:
            f.write("date,risk_score,portfolio_value_gbp,portfolio_change_pct\n")
    
    # Append entry
    with open(csv_path, "a") as f:
        f.write(
            f"{evaluation_date.strftime('%Y-%m-%d')},"
            f"{risk_score},"
            f"{portfolio_value:.2f},"
            f"{portfolio_change_pct:.2f}\n"
        )

