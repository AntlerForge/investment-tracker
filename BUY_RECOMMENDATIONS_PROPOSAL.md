# Buy Recommendations Feature Proposal

## Current State

The system currently only provides:
- **SELL** recommendations (take profit +40%, stop loss -25%)
- **HOLD** recommendations
- **REDUCE** recommendations (based on risk signals)

**Missing:**
- Buy recommendations
- Senate/Congressional trading data
- Market research integration
- Buy signal evaluation

## Proposed Buy Recommendation System

### 1. Data Sources to Integrate

#### Senate Trading Data
- **Source**: quiverquant.com API (free tier available) or web scraping
- **Data**: Recent Congressional trades (Senate/House)
- **Signals**: 
  - Senators buying specific stocks
  - Cluster buys (multiple senators buying same stock)
  - Timing (buying after dips, before earnings, etc.)

#### Market Indicators for Buy Signals
- **VIX drops** (fear subsiding)
- **Sector momentum** (sectors recovering)
- **Insider buying** (corporate insiders buying)
- **Options activity** (unusual call buying)
- **Technical indicators** (RSI oversold, support levels)

### 2. Buy Recommendation Logic

#### Entry Signals
- **Senate cluster buys**: 2+ senators buying same stock
- **VIX < 15**: Low volatility, good entry conditions
- **Sector recovery**: Sector index recovering from dip
- **Insider buying**: Corporate insiders buying (opposite of selling)
- **Oversold conditions**: RSI < 30, significant pullback

#### Risk-Adjusted Recommendations
- **High confidence**: Multiple signals align (Senate + insider + technical)
- **Medium confidence**: 2 signals align
- **Low confidence**: Single signal

### 3. Implementation Plan

1. **Create `buy_recommendations.py` module**
   - Fetch Senate trading data
   - Evaluate buy signals
   - Generate buy recommendations with confidence scores

2. **Add to `signals.yaml`**
   - Buy signal thresholds
   - Senate trading parameters
   - Entry criteria

3. **Update dashboard**
   - "Buy Opportunities" section
   - Show recommended stocks with reasons
   - Confidence scores
   - Link to Senate trading data

4. **Integration with existing system**
   - When positions are sold, suggest buy opportunities
   - Track cash available for deployment
   - Show allocation suggestions

## Questions for You

1. **Senate trading data**: Do you want to use quiverquant.com API (requires free account) or scrape from public sources?

2. **Buy criteria**: What factors matter most to you?
   - Senate trades
   - Insider buying
   - Technical indicators
   - Sector momentum
   - All of the above?

3. **Watchlist**: Should the system:
   - Only recommend stocks you already own (re-entry)?
   - Recommend new stocks based on signals?
   - Both?

4. **Integration**: Should buy recommendations:
   - Appear in the daily report?
   - Be a separate dashboard section?
   - Trigger alerts when strong signals appear?

## Next Steps

If you want this feature, I can:
1. Create the buy recommendation engine
2. Integrate Senate trading data source
3. Add buy signals to the dashboard
4. Include buy recommendations in daily reports

Would you like me to implement this?

