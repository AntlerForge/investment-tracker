# Quick Start Guide

## Step 1: Install Dependencies

```bash
cd risk-portfolio-system

# Create a virtual environment (recommended)
python3 -m venv .venv

# Activate it
source .venv/bin/activate

# Install required packages
pip install -r requirements.txt
```

## Step 2: Run Your First Evaluation

You can run the system immediately - no API keys needed for basic functionality!

```bash
# Make sure you're in the project directory and venv is activated
python scripts/evaluate_risk.py
```

Or use the convenience script:

```bash
./tools/run_daily.sh
```

## Step 3: View Your Reports

After running, check the generated reports:

```bash
# View the latest markdown report
cat reports/daily/$(date +%Y-%m-%d)_risk_report.md

# Or open the HTML report in your browser
open reports/dashboards/latest.html  # macOS
# xdg-open reports/dashboards/latest.html  # Linux
```

## What You'll Get

1. **Markdown Report** (`reports/daily/YYYY-MM-DD_risk_report.md`)
   - Risk score and summary
   - Triggered signals
   - Suggested actions (SELL/REDUCE/HOLD)
   - Holdings P&L table

2. **HTML Report** (`reports/daily/YYYY-MM-DD_risk_report.html`)
   - Same content, nicely formatted
   - Also available at `reports/dashboards/latest.html`

3. **Log File** (`logs/eval_YYYY-MM-DD.log`)
   - Detailed execution log
   - Data fetching details
   - Any warnings or errors

4. **History CSV** (`data/history/risk_scores.csv`)
   - Daily risk scores
   - Portfolio values
   - Change percentages

## Example Output

When you run the script, you'll see:

```
Starting risk evaluation for 2025-11-19
Loading configurations...
Fetching market data...
Calculating positions...
Evaluating signals...
Risk score: 45/100 (Moderate)
Generating reports...
Saved markdown report: reports/daily/2025-11-19_risk_report.md
Saved HTML report: reports/daily/2025-11-19_risk_report.html

✅ Risk evaluation completed!
📊 Risk Score: 45/100 (Moderate)
💰 Portfolio Change: -2.34%
📄 Reports saved to: reports/daily
```

## Customizing

### Adjust Risk Thresholds

Edit `config/signals.yaml` to change:
- VIX warning/critical levels
- NVDA divergence thresholds
- Other signal parameters

### Update Portfolio Holdings

Edit `config/portfolio.yaml` to:
- Add/remove holdings
- Update share counts
- Adjust baseline values

### Change Rules

Edit `config/portfolio.yaml` rules section:
- `take_profit_pct`: When to take profit (default: 40%)
- `cut_loss_pct`: When to cut losses (default: -25%)

## Scheduling Daily Runs

To run automatically at 19:30 UK time every weekday:

### macOS/Linux (cron)

```bash
# Edit crontab
crontab -e

# Add this line (adjust path):
30 19 * * 1-5 cd /path/to/risk-portfolio-system && ./tools/run_daily.sh >> logs/cron.log 2>&1
```

### macOS (launchd)

Create `~/Library/LaunchAgents/com.riskportfolio.daily.plist`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.riskportfolio.daily</string>
    <key>ProgramArguments</key>
    <array>
        <string>/path/to/risk-portfolio-system/tools/run_daily.sh</string>
    </array>
    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key>
        <integer>19</integer>
        <key>Minute</key>
        <integer>30</integer>
        <key>Weekday</key>
        <integer>1</integer>
    </dict>
</dict>
</plist>
```

Then load it:
```bash
launchctl load ~/Library/LaunchAgents/com.riskportfolio.daily.plist
```

## Troubleshooting

### "Module not found" errors
- Make sure virtual environment is activated: `source .venv/bin/activate`
- Reinstall dependencies: `pip install -r requirements.txt`

### "No data available" warnings
- This is normal - the system will flag missing data but continue
- Check your internet connection
- Some data may be unavailable outside market hours

### Reports not generating
- Check `logs/eval_YYYY-MM-DD.log` for errors
- Ensure `reports/daily/` directory exists and is writable

## Next Steps

1. **Review your first report** - Check the generated markdown/HTML
2. **Adjust thresholds** - Modify `config/signals.yaml` based on your risk tolerance
3. **Update holdings** - Keep `config/portfolio.yaml` in sync with your actual portfolio
4. **Schedule daily runs** - Set up automation for 19:30 UK time
5. **Monitor history** - Track risk scores over time in `data/history/risk_scores.csv`

## Need Help?

- Check `IMPLEMENTATION.md` for technical details
- Review `AGENT_NOTES.md` for system behavior rules
- Check log files in `logs/` for detailed execution information

