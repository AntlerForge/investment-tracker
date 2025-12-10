# Setting Up Regulatory Data Sources for Buy Recommendations

The buy recommendation system focuses on **regulatory and early indicators** - data that shows what politicians, insiders, and institutions are doing before the general public knows.

## Required API Keys

### 1. QuiverQuant API (Congressional Trading) - **RECOMMENDED**

**What it provides:**
- Real-time Congressional/Senate stock trades
- Which politicians are buying/selling which stocks
- Transaction dates and amounts
- This is the PRIMARY signal source

**How to get it:**
1. Sign up at: https://www.quiverquant.com/
2. Get your API key from the dashboard
3. Add to `.env` file:
   ```
   QUIVERQUANT_API_KEY=your_api_key_here
   ```

**Free tier:** Limited but usually enough for personal use

### 2. Finnhub API (Insider Trading) - **RECOMMENDED**

**What it provides:**
- SEC Form 4 insider trading data
- Corporate executives buying/selling their own stock
- Transaction details (shares, price, date)

**How to get it:**
1. Sign up at: https://finnhub.io/
2. Get your free API key
3. Add to `.env` file:
   ```
   FINNHUB_API_KEY=your_api_key_here
   ```

**Free tier:** 60 calls/minute - plenty for this use case

### 3. SEC API (13F Filings) - **OPTIONAL**

**What it provides:**
- Institutional holdings (hedge funds, pension funds)
- What "smart money" is buying/selling
- Quarterly 13F filings

**Options:**
- **sec-api.io** (paid, easiest)
- **Direct SEC EDGAR scraping** (free, complex)
- **WhaleWisdom.com scraping** (free, rate-limited)

## How It Works

Once API keys are set up, the system will:

1. **Fetch Congressional trades** - See which senators/representatives are buying
2. **Fetch insider trades** - See which corporate executives are buying
3. **Fetch institutional holdings** - See which institutions are increasing positions
4. **Generate recommendations** - Only show stocks with actual regulatory signals

## Recommendation Logic

**Stocks are ONLY recommended if they have:**
- Congressional/Senate buys (2+ senators = strong signal)
- Insider buying (corporate executives buying)
- Institutional buying (13F filings showing increased holdings)

**No generic recommendations** - if there's no regulatory signal, the stock won't appear.

## Testing

After adding API keys to `.env`:

1. Restart the Flask server
2. Click "Run Evaluation" in the dashboard
3. Check the "Buy Recommendations" section
4. You should see stocks with actual Congressional/insider signals

## Troubleshooting

**No recommendations showing:**
- Check API keys are in `.env` file
- Check server logs for API errors
- Verify API keys are valid (test with curl or Postman)

**"Congressional trading data not available":**
- Add `QUIVERQUANT_API_KEY` to `.env`
- Restart server

**"Insider trading data not available":**
- Add `FINNHUB_API_KEY` to `.env`
- Restart server


