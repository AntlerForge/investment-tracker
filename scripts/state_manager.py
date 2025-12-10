import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class StateManager:
    """
    Manages the central state of the Risk Portfolio System.
    Acts as the single source of truth for both the Dashboard and the CLI.
    """
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.data_dir = project_root / "data"
        self.state_file = self.data_dir / "system_state.json"
        self.history_dir = self.data_dir / "history"
        
        # Ensure directories exist
        self.data_dir.mkdir(exist_ok=True)
        self.history_dir.mkdir(exist_ok=True)
        
    def save_state(self, 
                  portfolio_data: Dict[str, Any], 
                  buy_recommendations: list, 
                  sell_recommendations: list,
                  risk_assessment: Dict[str, Any],
                  system_status: str = "idle") -> Path:
        """
        Save the current system state to a JSON file.
        """
        state = {
            "last_updated": datetime.now().isoformat(),
            "system_status": system_status,
            "portfolio": portfolio_data,
            "recommendations": {
                "buy": buy_recommendations,
                "sell": sell_recommendations
            },
            "risk_assessment": risk_assessment,
            "meta": {
                "version": "1.0",
                "environment": "production"
            }
        }
        
        try:
            # Write to temp file first then rename for atomic write
            temp_file = self.state_file.with_suffix('.tmp')
            with open(temp_file, 'w') as f:
                json.dump(state, f, indent=2, default=str)
            temp_file.rename(self.state_file)
            
            logger.info(f"System state saved to {self.state_file}")
            
            # Also save a history snapshot
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            history_file = self.history_dir / f"state_{timestamp}.json"
            with open(history_file, 'w') as f:
                json.dump(state, f, indent=2, default=str)
                
            return self.state_file
            
        except Exception as e:
            logger.error(f"Failed to save state: {e}")
            raise

    def load_state(self) -> Dict[str, Any]:
        """
        Load the latest system state.
        """
        if not self.state_file.exists():
            logger.warning("No state file found. Returning empty state.")
            return self._get_empty_state()
            
        try:
            with open(self.state_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load state: {e}")
            return self._get_empty_state()

    def _get_empty_state(self) -> Dict[str, Any]:
        """Return a default empty state structure."""
        return {
            "last_updated": None,
            "system_status": "unknown",
            "portfolio": {"totals": {}, "holdings": []},
            "recommendations": {"buy": [], "sell": []},
            "risk_assessment": {},
            "meta": {"version": "1.0"}
        }

    def update_status(self, status: str):
        """Quickly update just the system status field."""
        state = self.load_state()
        state["system_status"] = status
        state["last_updated"] = datetime.now().isoformat()
        
        try:
            with open(self.state_file, 'w') as f:
                json.dump(state, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Failed to update status: {e}")


