# Risk-Aware Portfolio System

A local, Cursor-managed system for daily risk evaluation and portfolio monitoring.

## Overview

This system runs locally and evaluates your portfolio daily at 19:30 UK time, generating risk reports and trade recommendations based on configurable rules and signals.

## Quick Start

1. **Install dependencies:**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. **Configure environment:**
   ```bash
   cp .env.example .env
   # Edit .env with your API keys
   ```

3. **Run daily evaluation:**
   ```bash
   ./tools/run_daily.sh
   # Or manually:
   python scripts/evaluate_risk.py --config config/portfolio.yaml --signals config/signals.yaml
   ```

4. **Start web dashboard (optional):**
   ```bash
   ./start_dashboard.sh
   # Then open http://localhost:5001 in your browser
   ```

## Project Structure

```
risk-portfolio-system/
├── app.py           # Flask web dashboard application
├── templates/       # HTML templates for dashboard
├── static/          # CSS and JavaScript for dashboard
├── config/          # Configuration files (portfolio, signals, schedule)
├── scripts/         # Python evaluation and data fetching scripts
├── data/           # Raw data, history, and cache
├── reports/        # Daily reports and dashboards
├── logs/           # Evaluation logs
└── tools/          # Utility scripts and shell wrappers
```

## Configuration

- `config/portfolio.yaml` - Portfolio holdings and baseline values
- `config/signals.yaml` - Risk signal thresholds and rules
- `config/schedule.yaml` - Evaluation schedule settings
- `config/data_sources.yaml` - Data source configuration

## Daily Workflow

1. Load portfolio baseline and current holdings
2. Fetch live market data (prices, indicators)
3. Evaluate macro, sector, and stock-level signals
4. Compute risk score (0-100)
5. Generate markdown and HTML reports
6. Output explicit BUY/SELL/HOLD recommendations

## Web Dashboard

The system includes a web-based dashboard for managing your portfolio:

- **View and edit holdings** - Update shares, baseline values, and risk buckets
- **Trigger evaluations** - Run new risk assessments from the browser
- **View reports** - Access latest risk reports and history
- **Interactive charts** - Visualize risk scores over time

Start the dashboard:
```bash
./start_dashboard.sh
```

Then open http://localhost:5000 in your browser.

See `DASHBOARD.md` for detailed dashboard documentation.

## Safety Rules

- **Never executes trades** - only generates recommendations
- **Never modifies baseline** without explicit "Lock in new baseline" instruction
- **Flags missing data** and degrades gracefully
- **Deterministic outputs** based on configured rules

See `AGENT_NOTES.md` for detailed operational guidelines.

