# Buy Recommendation System

## Overview

The buy recommendation system analyzes multiple data sources to provide intelligent buy recommendations based on:

1. **Congressional/Senate Trading Data** - Tracks when senators and representatives buy stocks
2. **Insider Trading (SEC Form 4)** - Corporate insider buying activity
3. **Regulatory Filings (SEC 13F)** - Institutional holdings changes
4. **Market Indicators** - VIX levels, sector momentum, etc.
5. **Technical Signals** - Oversold conditions, momentum shifts

## How It Works

### 1. Sell Recommendations Trigger Buy Analysis

When the system recommends selling positions (due to take-profit or stop-loss triggers), it:
- Calculates available funds from the sales
- Automatically generates buy recommendations based on those funds
- Matches buy opportunities to available capital

### 2. Signal Evaluation

Each potential buy is scored based on:
- **Congressional Cluster Buys** (2+ senators buying same stock) = +30 confidence
- **Single Congressional Buy** = +15 confidence
- **Insider Buying** = +20 confidence
- **Low VIX** (<15) = +10 confidence (good entry conditions)
- **Sector Recovery** = Variable (future enhancement)

### 3. Recommendation Levels

- **STRONG BUY** (50+ confidence): Multiple strong signals aligned
- **BUY** (30-49 confidence): Good signals present
- **CONSIDER** (15-29 confidence): Some positive signals

### 4. Allocation Suggestions

The system suggests how to allocate available funds:
- Proportional to confidence scores
- Higher confidence = larger suggested allocation
- Includes suggested number of shares based on current price

## Output Formats

### 1. Dashboard Display

The web dashboard shows:
- Buy opportunities table with symbols, recommendations, confidence scores
- Current prices and suggested allocations
- Signal explanations
- Discussion-format text for AI review

### 2. Discussion Format (Text File)

When you run an evaluation, a text file is created in `reports/` with format:

```
================================================================================
PORTFOLIO RECOMMENDATIONS - DISCUSSION FORMAT
================================================================================
Generated: 2024-01-15 14:30:00
Current Portfolio Value: £50,000.00

────────────────────────────────────────────────────────────────────────────────
SELL RECOMMENDATIONS
────────────────────────────────────────────────────────────────────────────────

1. NVDA (NVDA)
   Action: SELL
   Current Value: £15,000.00
   P&L: +45.00%
   Reason: Take profit: +45.0%

Total Funds from Sales: £15,000.00

────────────────────────────────────────────────────────────────────────────────
BUY RECOMMENDATIONS
────────────────────────────────────────────────────────────────────────────────
Available Funds: £15,000.00

1. AAPL - STRONG BUY
   Confidence Score: 65/100
   Suggested Allocation: £7,500.00
   
   Signals:
   • 3 Congressional buy(s)
   • Insider buying detected
   • Low volatility (VIX: 12.5) - good entry conditions

2. MSFT - BUY
   Confidence Score: 35/100
   Suggested Allocation: £4,500.00
   
   Signals:
   • 2 Congressional buy(s)
   • Low volatility (VIX: 12.5) - good entry conditions
```

This format is designed to be **easy for AI to read** so you can:
- Copy/paste into chat
- Discuss recommendations with AI
- Get additional analysis before buying

## Configuration

Edit `config/signals.yaml` to customize buy signals:

```yaml
buy_signals:
  congressional:
    cluster_threshold: 2  # Number of senators buying same stock
    lookback_days: 30
    min_confidence: 15
  insider_buying:
    lookback_days: 30
    min_confidence: 20
  market_conditions:
    vix_low_threshold: 15.0  # VIX below this = good entry
    vix_confidence: 10
  confidence_thresholds:
    strong_buy: 50
    buy: 30
    consider: 15
  watchlist: []  # Empty = evaluate all Congressional trades
                 # Or specify: ["AAPL", "MSFT", "GOOGL"]
```

## Data Sources

### Currently Implemented

- **Market Data**: yfinance (prices, VIX)
- **FX Rates**: yfinance (USD/GBP conversion)

### Needs API Keys (Placeholder Ready)

1. **QuiverQuant API** (Congressional Trading)
   - Sign up at: https://www.quiverquant.com/
   - Add API key to `.env`: `QUIVERQUANT_API_KEY=your_key`
   - Update `buy_recommendations.py` to load from `.env`

2. **SEC EDGAR** (Insider Trading)
   - Options:
     - sec-api.io (paid, easy integration)
     - Direct EDGAR scraping (free, more complex)
     - finnhub API (has insider trading endpoint)

3. **13F Filings** (Institutional Holdings)
   - Same options as SEC EDGAR

## Usage

### Via Dashboard

1. Click "Run Evaluation" to generate recommendations
2. View "Buy Recommendations" section
3. Click "Refresh" to reload recommendations
4. Review discussion-format text in the section

### Via Command Line

```bash
cd risk-portfolio-system
source .venv/bin/activate
python scripts/evaluate_risk.py
```

This will:
- Generate sell recommendations
- Calculate available funds
- Generate buy recommendations
- Save discussion-format file to `reports/recommendations_YYYY-MM-DD_HH-MM-SS.txt`

### Reading Recommendations in Chat

1. Open the recommendations text file
2. Copy the entire content
3. Paste into chat: "Here are my buy recommendations. Can you analyze these and help me decide?"
4. AI can read the structured format and provide analysis

## Future Enhancements

- [ ] Real-time Congressional trading data integration
- [ ] SEC Form 4 insider trading integration
- [ ] 13F institutional holdings tracking
- [ ] Technical indicator integration (RSI, MACD, etc.)
- [ ] Sector momentum analysis
- [ ] Risk-adjusted allocation (consider portfolio risk buckets)
- [ ] Historical performance tracking of recommendations

## Notes

- Recommendations are **suggestions only** - always do your own research
- Data sources may have delays (especially free tiers)
- Congressional trading data requires API key for real-time updates
- The system focuses on **early indicators** - Congressional and insider trades often precede public moves

