"""
Format buy/sell recommendations in a readable format for AI discussion.

Creates structured, easy-to-read recommendation summaries that can be
discussed in chat before execution.
"""

from typing import Dict, List, Any
from datetime import datetime


def format_recommendations_for_discussion(
    sell_recommendations: List[Dict[str, Any]],
    buy_recommendations: List[Dict[str, Any]],
    available_funds: float,
    portfolio_value: float
) -> str:
    """
    Format recommendations in a readable format for AI discussion.
    
    Args:
        sell_recommendations: List of sell recommendations
        buy_recommendations: List of buy recommendations
        available_funds: Funds available from sales
        portfolio_value: Current portfolio value
        
    Returns:
        Formatted string ready for discussion
    """
    output = []
    output.append("=" * 80)
    output.append("PORTFOLIO RECOMMENDATIONS - DISCUSSION FORMAT")
    output.append("=" * 80)
    output.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    output.append(f"Current Portfolio Value: £{portfolio_value:,.2f}")
    output.append("")
    
    # SELL RECOMMENDATIONS
    if sell_recommendations:
        output.append("─" * 80)
        output.append("SELL RECOMMENDATIONS")
        output.append("─" * 80)
        output.append("")
        
        total_sell_value = 0.0
        
        for i, rec in enumerate(sell_recommendations, 1):
            ticker = rec.get("ticker", "Unknown")
            symbol = rec.get("symbol", ticker)
            action = rec.get("action", "SELL")
            reason = rec.get("action_reason", "")
            current_value = rec.get("current_value_gbp", 0.0)
            change_pct = rec.get("change_pct", 0.0)
            
            total_sell_value += current_value
            
            output.append(f"{i}. {ticker} ({symbol})")
            output.append(f"   Action: {action}")
            output.append(f"   Current Value: £{current_value:,.2f}")
            output.append(f"   P&L: {change_pct:+.2f}%")
            output.append(f"   Reason: {reason}")
            output.append("")
        
        output.append(f"Total Funds from Sales: £{total_sell_value:,.2f}")
        output.append("")
    else:
        output.append("─" * 80)
        output.append("SELL RECOMMENDATIONS: None")
        output.append("─" * 80)
        output.append("")
    
    # BUY RECOMMENDATIONS
    if buy_recommendations:
        output.append("─" * 80)
        output.append("BUY RECOMMENDATIONS")
        output.append("─" * 80)
        output.append(f"Available Funds: £{available_funds:,.2f}")
        output.append("")
        
        for i, rec in enumerate(buy_recommendations, 1):
            symbol = rec.get("symbol", "Unknown")
            recommendation = rec.get("recommendation", "CONSIDER")
            confidence = rec.get("confidence_score", 0)
            reasons = rec.get("reasons", [])
            suggested_allocation = rec.get("suggested_allocation_gbp", 0.0)
            congressional_cluster = rec.get("congressional_cluster", 0)
            insider_buying = rec.get("insider_buying", False)
            
            output.append(f"{i}. {symbol} - {recommendation}")
            output.append(f"   Confidence Score: {confidence}/100")
            output.append(f"   Suggested Allocation: £{suggested_allocation:,.2f}")
            output.append("")
            output.append("   Signals:")
            if congressional_cluster > 0:
                output.append(f"   • {congressional_cluster} Congressional buy(s)")
            if insider_buying:
                output.append("   • Insider buying detected")
            for reason in reasons:
                if reason not in ["Congressional buy", "Insider buying"]:
                    output.append(f"   • {reason}")
            output.append("")
    else:
        output.append("─" * 80)
        output.append("BUY RECOMMENDATIONS: None")
        output.append("─" * 80)
        output.append("")
        output.append("No strong buy signals detected at this time.")
        output.append("")
    
    # SUMMARY
    output.append("=" * 80)
    output.append("SUMMARY")
    output.append("=" * 80)
    output.append(f"Sell Actions: {len(sell_recommendations)}")
    output.append(f"Buy Opportunities: {len(buy_recommendations)}")
    output.append(f"Funds Available: £{available_funds:,.2f}")
    output.append("")
    output.append("Review these recommendations and discuss before executing trades.")
    output.append("=" * 80)
    
    return "\n".join(output)


def save_recommendations_to_file(
    recommendations_text: str,
    output_dir: str,
    date: datetime = None
) -> str:
    """
    Save recommendations to a text file for easy reading.
    
    Args:
        recommendations_text: Formatted recommendations text
        output_dir: Directory to save file
        date: Date for filename (defaults to today)
        
    Returns:
        Path to saved file
    """
    from pathlib import Path
    
    if date is None:
        date = datetime.now()
    
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    filename = f"recommendations_{date.strftime('%Y-%m-%d_%H-%M-%S')}.txt"
    filepath = output_path / filename
    
    with open(filepath, 'w') as f:
        f.write(recommendations_text)
    
    return str(filepath)

