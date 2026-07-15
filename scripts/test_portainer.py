import os
import sys
from utils import get_portainer_api_key, make_portainer_request

PORTAINER_URL = os.environ.get("PORTAINER_URL", "https://192.168.1.50:9443")

def test_connection() -> bool:
    """Test the Portainer API connection by listing endpoints (environments).
    
    Returns True if successful, False otherwise.
    """
    api_key = get_portainer_api_key()
    if not api_key:
        print("\n[Error] Portainer API key not found. Please set PORTAINER_API_KEY environment variable or verify homelab-spec.md.")
        return False

    print(f"Connecting to Portainer at: {PORTAINER_URL}...")
    
    try:
        data = make_portainer_request(PORTAINER_URL, "/api/endpoints", api_key)
        if isinstance(data, list):
            print("\n[Success] Connected to Portainer API successfully!")
            print(f"Retrieved {len(data)} environments/endpoints:\n")
            for item in data:
                status_str = "Running" if item.get("Status") == 1 else "Down/Unknown"
                print(f" - ID: {item.get('Id')}, Name: {item.get('Name')}, URL: {item.get('URL')}, Status: {status_str}")
            return True
        else:
            print("\n[Failed] Did not receive a valid list of endpoints from Portainer.")
            return False
    except Exception as e:
        print(f"\n[Error] Could not connect to Portainer API: {e}")
        return False

if __name__ == "__main__":
    success = test_connection()
    if not success:
        sys.exit(1)
