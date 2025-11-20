# Adding Dashboard to macOS Applications

## Quick Setup

1. **Copy the launcher script:**
   ```bash
   cp "Risk Portfolio Dashboard.command" ~/Applications/
   ```

2. **Or drag and drop:**
   - Open Finder
   - Navigate to the `risk-portfolio-system` folder
   - Drag `Risk Portfolio Dashboard.command` to your Applications folder

3. **Double-click to launch:**
   - Open Applications folder
   - Double-click "Risk Portfolio Dashboard.command"
   - The dashboard will start and open in your browser automatically

## What the Script Does

- ✅ Checks if the server is already running
- ✅ Starts the server if needed
- ✅ Opens the dashboard in your default browser
- ✅ Handles virtual environment setup
- ✅ Installs Flask if missing

## First Time Setup

Before using the launcher, make sure you've set up the project:

```bash
cd risk-portfolio-system
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

After that, you can use the launcher script from Applications.

## Stopping the Server

The server runs in the background. To stop it:

```bash
lsof -ti:5001 | xargs kill
```

Or use Activity Monitor to find and quit the Python process.

## Troubleshooting

### "Virtual environment not found"
- Make sure you've created the virtual environment first
- Run the setup commands above

### "Port already in use"
- Another instance might be running
- Kill it with: `lsof -ti:5001 | xargs kill`
- Or change the port in the script (edit `PORT=5001`)

### Script won't run
- Make sure it's executable: `chmod +x "Risk Portfolio Dashboard.command"`
- Right-click → Get Info → Check "Open with" is set to Terminal

