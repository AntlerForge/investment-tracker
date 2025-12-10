# Multi-Factor Buy Recommendation Engine v2

## Overview

The new recommendation engine provides a comprehensive multi-factor analysis focused on **medium/high risk, high reward** opportunities. It combines early signals, technical indicators, risk/reward metrics, and market conditions to generate actionable buy recommendations.

## Key Improvements

### 1. Early Signal Focus
- **Insider buying**: Only considers trades from last **7-14 days** (not months ago)
- **Congressional buying**: Only considers trades from last **7-14 days**
- Emphasizes **recent activity** as early indicators of potential price movements

### 2. Multi-Factor Scoring System

The engine evaluates four factor categories (100 points total):

#### Early Signals (30 points max)
- Recent insider buying (last 14 days): Up to 15 points
  - Recency bonus: More recent = higher score
  - Size bonus: Larger purchases = more conviction
  - Cluster bonus: Multiple insiders = stronger signal
- Recent congressional buying (last 14 days): Up to 15 points
  - Recency bonus
  - Cluster bonus (multiple senators)

#### Technical Indicators (30 points max)
- **Momentum** (10 points): 5d, 10d, 20d price momentum
- **RSI** (5 points): Oversold/neutral conditions for entry
- **Volume surge** (5 points): Unusual volume activity
- **Moving average alignment** (5 points): Price vs MA20/MA50
- **Breakout patterns** (5 points): Near resistance levels

#### Risk/Reward Metrics (25 points max)
- **Upside potential** (10 points): Analyst price targets
- **Volatility** (5 points): Medium/high volatility for high reward
- **Support levels** (5 points): Distance to support
- **Recent price action** (5 points): Consolidation or momentum

#### Market Conditions (15 points max)
- **VIX levels** (5 points): Low volatility = good entry
- **Sector momentum** (5 points): Sector recovery signals
- **Market timing** (5 points): Overall market conditions

### 3. Risk/Reward Classification

Each recommendation includes:
- **Risk Level**: HIGH, MEDIUM-HIGH, or MEDIUM
- **Reward Potential**: VERY HIGH, HIGH, MODERATE, or LOW

Based on volatility and upside potential metrics.

### 4. Enhanced Dashboard Display

The dashboard now shows:
- **Multi-factor score breakdown** by category
- **Risk and reward badges** for quick assessment
- **Detailed signal breakdown** with expandable details
- **All factors visible** in a comprehensive table

## Recommendation Levels

- **STRONG BUY** (60+ points): Strong multi-factor alignment
- **BUY** (40-59 points): Good multi-factor signals
- **CONSIDER** (25-39 points): Some positive factors

## Configuration

Settings in `config/signals.yaml`:

```yaml
buy_signals:
  early_signal_days: 14  # Only consider trades from last 14 days
  min_score_to_show: 25  # Minimum total score to show
  confidence_thresholds:
    strong_buy: 60
    buy: 40
    consider: 25
```

## Usage

The system automatically uses v2 engine when generating recommendations. It evaluates:
1. Stocks with recent insider/congressional activity
2. High-volatility stocks from default watchlist
3. Stocks with strong technical + risk/reward signals

## Benefits

1. **Early signals**: Focuses on recent activity, not stale data
2. **Multi-factor**: Not just insider trading - combines multiple signals
3. **Risk/reward focus**: Specifically targets medium/high risk, high reward opportunities
4. **Transparency**: Shows exactly why each recommendation was made
5. **Actionable**: Clear scoring breakdown helps prioritize opportunities




