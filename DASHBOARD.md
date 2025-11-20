# Web Dashboard Guide

## Overview

The Risk Portfolio System includes a web-based dashboard that provides:

- **Portfolio Management**: View and edit holdings, shares, and baseline values
- **Risk Evaluation**: Trigger new evaluations and view results
- **Historical Tracking**: View risk score history with charts
- **Report Viewing**: Access latest risk reports directly from the dashboard

## Starting the Dashboard

### Option 1: Using the startup script

```bash
cd risk-portfolio-system
./start_dashboard.sh
```

### Option 2: Manual start

```bash
cd risk-portfolio-system
source .venv/bin/activate  # Activate virtual environment
pip install flask  # If not already installed
python app.py
```

The dashboard will be available at: **http://localhost:5001**

## Features

### 1. Portfolio Holdings Table

- View all holdings with current configuration
- **Edit**: Click the ✏️ icon to edit a holding
- **Delete**: Click the 🗑️ icon to delete a holding
- **Quick Edit**: Double-click on shares or baseline value cells to edit inline
- **Add New**: Click "+ Add Holding" button to add a new position

### 2. Risk Summary

- View the latest evaluation date
- Quick link to the full report
- Risk score display (when available)

### 3. Run Evaluation

- Click "Run Evaluation" button to trigger a new risk assessment
- The evaluation runs in the background (may take 1-2 minutes)
- Page automatically refreshes when complete

### 4. Risk History Chart

- Visual chart showing risk scores over time
- Last 30 days of data displayed
- Interactive Chart.js visualization

### 5. Latest Report Preview

- Quick preview of the most recent risk report
- Link to view full HTML report in new tab

## API Endpoints

The dashboard uses a REST API. You can also interact with it programmatically:

### Get Portfolio
```bash
GET /api/portfolio
```

### Update Portfolio
```bash
POST /api/portfolio
Content-Type: application/json

{
  "holdings": { ... },
  "rules": { ... }
}
```

### Update Single Holding
```bash
PUT /api/holding/<ticker>
Content-Type: application/json

{
  "shares": 100.0,
  "baseline_value_gbp": 5000.0
}
```

### Add Holding
```bash
POST /api/holding
Content-Type: application/json

{
  "ticker": "AAPL",
  "symbol": "AAPL",
  "shares": 10.0,
  "baseline_value_gbp": 1500.0,
  "type": "equity",
  "risk_bucket": "core-ai"
}
```

### Delete Holding
```bash
DELETE /api/holding/<ticker>
```

### Trigger Evaluation
```bash
POST /api/evaluate
```

### Get Latest Report
```bash
GET /api/report/latest
```

### Get History
```bash
GET /api/history
```

## Configuration Backup

When you update holdings through the dashboard, the system automatically creates a backup of your `portfolio.yaml` file in the `config/` directory with a timestamp:

```
config/portfolio_backup_20251119_185530.yaml
```

This ensures you can always revert changes if needed.

## Troubleshooting

### Dashboard won't start

1. **Check Flask is installed:**
   ```bash
   pip install flask
   ```

2. **Check virtual environment is activated:**
   ```bash
   source .venv/bin/activate
   ```

3. **Check port 5000 is available:**
   ```bash
   lsof -i :5000  # macOS/Linux
   ```

### Changes not saving

- Check browser console for errors (F12)
- Verify you have write permissions to the `config/` directory
- Check the Flask console output for error messages

### Evaluation fails

- Check that all dependencies are installed: `pip install -r requirements.txt`
- Verify the evaluation script works: `python scripts/evaluate_risk.py`
- Check logs in `logs/` directory

## Security Notes

⚠️ **Important**: The dashboard runs in development mode by default and is accessible to anyone on your network. For production use:

1. Add authentication
2. Use HTTPS
3. Restrict access to localhost only
4. Set a proper `SECRET_KEY` in `app.py`

## Customization

### Change Port

Edit `app.py`:
```python
app.run(debug=True, host='0.0.0.0', port=8080)  # Change 5000 to your port
```

### Change Host

To only allow localhost access:
```python
app.run(debug=True, host='127.0.0.1', port=5000)
```

### Disable Debug Mode

For production:
```python
app.run(debug=False, host='127.0.0.1', port=5000)
```

