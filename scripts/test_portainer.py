import urllib.request
import ssl
import json
import os

# Portainer Connection Details
PORTAINER_URL = os.environ.get("PORTAINER_URL", "https://192.168.1.50:9443")

def get_portainer_api_key():
    # 1. Try environment variable
    key = os.environ.get("PORTAINER_API_KEY")
    if key:
        return key

    # 2. Try loading from homelab-spec.md
    spec_path = os.path.join(os.path.dirname(__file__), "..", ".agents", "references", "homelab-spec.md")
    if os.path.exists(spec_path):
        try:
            with open(spec_path, "r") as f:
                for line in f:
                    if "Portainer API Key:" in line:
                        # Extract the key between backticks
                        parts = line.split("`")
                        if len(parts) >= 3:
                            return parts[1].strip()
        except Exception as e:
            print(f"Warning: Failed to read key from spec file: {e}")
    return None

def test_connection():
    api_key = get_portainer_api_key()
    if not api_key:
        print("\n[Error] Portainer API key not found. Please set PORTAINER_API_KEY environment variable or verify homelab-spec.md.")
        return False

    # Bypass self-signed certificate verification (common in homelabs)
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    print(f"Connecting to Portainer at: {PORTAINER_URL}...")
    
    # Portainer API Key authentication uses the X-API-Key header
    headers = {
        "X-API-Key": api_key,
        "Accept": "application/json"
    }


    # Test by listing endpoints (environments)
    endpoints_url = f"{PORTAINER_URL.rstrip('/')}/api/endpoints"
    req = urllib.request.Request(endpoints_url, headers=headers)
    
    try:
        with urllib.request.urlopen(req, context=ctx) as response:
            if response.status == 200:
                data = json.loads(response.read().decode())
                print("\n[Success] Connected to Portainer API successfully!")
                print(f"Retrieved {len(data)} environments/endpoints:\n")
                for item in data:
                    print(f" - ID: {item.get('Id')}, Name: {item.get('Name')}, URL: {item.get('URL')}, Status: {'Running' if item.get('Status') == 1 else 'Down/Unknown'}")
                return True
            else:
                print(f"\n[Failed] Received status code {response.status}")
                return False
    except Exception as e:
        print(f"\n[Error] Could not connect to Portainer API: {e}")
        return False

if __name__ == "__main__":
    test_connection()
