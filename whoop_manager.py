import os
import json
import logging
import requests
from datetime import datetime
import pytz

logger = logging.getLogger(__name__)

TOKEN_FILE = "whoop_token.json"
TOKEN_URL = "https://api.prod.whoop.com/oauth/oauth2/token"
API_BASE = "https://api.prod.whoop.com/developer/v2"

def _get_whoop_tokens():
    if not os.path.exists(TOKEN_FILE):
        return None
    try:
        with open(TOKEN_FILE, "r") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error reading whoop tokens: {e}")
        return None

def _save_whoop_tokens(tokens):
    try:
        with open(TOKEN_FILE, "w") as f:
            json.dump(tokens, f)
    except Exception as e:
        logger.error(f"Error saving whoop tokens: {e}")

def _refresh_whoop_token(refresh_token):
    client_id = os.environ.get("WHOOP_CLIENT_ID")
    client_secret = os.environ.get("WHOOP_CLIENT_SECRET")
    if not client_id or not client_secret:
        logger.error("Missing WHOOP_CLIENT_ID or WHOOP_CLIENT_SECRET")
        return None

    data = {
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
        "client_id": client_id,
        "client_secret": client_secret
    }
    
    try:
        response = requests.post(TOKEN_URL, data=data)
        response.raise_for_status()
        new_tokens = response.json()
        _save_whoop_tokens(new_tokens)
        return new_tokens.get("access_token")
    except Exception as e:
        logger.error(f"Error refreshing whoop token: {e}")
        return None

def _make_whoop_request(endpoint: str, params: dict = None):
    tokens = _get_whoop_tokens()
    if not tokens or "access_token" not in tokens:
        return {"error": "Whoop is not authenticated. Please run whoop_auth.py first."}

    access_token = tokens["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}
    
    try:
        url = f"{API_BASE}/{endpoint}"
        response = requests.get(url, headers=headers, params=params)
        
        # Handle token expiration (usually 401 Unauthorized)
        if response.status_code == 401 and "refresh_token" in tokens:
            logger.info("Whoop token expired, attempting refresh...")
            new_access_token = _refresh_whoop_token(tokens["refresh_token"])
            if new_access_token:
                headers["Authorization"] = f"Bearer {new_access_token}"
                response = requests.get(url, headers=headers, params=params)
                
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"Whoop API request failed: {e}")
        return {"error": str(e)}

def get_whoop_data() -> str:
    """Fetch the latest recovery, sleep, and cycle data from Whoop."""
    # 1. Get latest recovery
    recovery_data = _make_whoop_request("recovery", params={"limit": 1})
    if "error" in recovery_data:
        return f"Failed to fetch Whoop data: {recovery_data['error']}"
        
    # 2. Get latest cycle (contains strain)
    cycle_data = _make_whoop_request("cycle", params={"limit": 1})
    
    # 3. Get latest sleep
    sleep_data = _make_whoop_request("activity/sleep", params={"limit": 1})
    
    lines = ["📊 **Whoop Daily Report:**\n"]
    
    # Parse Recovery
    if recovery_data and "records" in recovery_data and len(recovery_data["records"]) > 0:
        rec = recovery_data["records"][0]
        score = rec.get("score", {})
        recovery_score = score.get("recovery_score", "Unknown")
        rhr = score.get("resting_heart_rate", "Unknown")
        hrv = score.get("hrv_rmssd_milli", "Unknown")
        lines.append(f"- **Recovery**: {recovery_score}% (RHR: {rhr} bpm, HRV: {hrv} ms)")
    else:
        lines.append("- **Recovery**: No data available for today.")
        
    # Parse Strain
    if cycle_data and "records" in cycle_data and len(cycle_data["records"]) > 0:
        cyc = cycle_data["records"][0]
        score = cyc.get("score", {})
        strain = score.get("strain", "Unknown")
        lines.append(f"- **Day Strain**: {strain}")
    else:
        lines.append("- **Day Strain**: No data available.")
        
    # Parse Sleep
    if sleep_data and "records" in sleep_data and len(sleep_data["records"]) > 0:
        slp = sleep_data["records"][0]
        score = slp.get("score", {})
        perf = score.get("sleep_performance_percentage", "Unknown")
        lines.append(f"- **Sleep Performance**: {perf}%")
    else:
        lines.append("- **Sleep Performance**: No data available.")
        
    return "\n".join(lines)
