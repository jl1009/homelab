import os
import ssl
import json
import urllib.request
import urllib.error
from typing import Optional, Union, Any

def get_ssl_context(verify: bool = False) -> ssl.SSLContext:
    """Create an SSL context. If verify is False, disable hostname checking and cert validation."""
    ctx = ssl.create_default_context()
    if not verify:
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
    return ctx

def get_portainer_api_key(spec_path: Optional[str] = None) -> Optional[str]:
    """Resolve the Portainer API key, checking environment first, then homelab-spec.md."""
    key = os.environ.get("PORTAINER_API_KEY")
    if key:
        return key

    # Resolve default path to spec file relative to this script if not provided
    if not spec_path:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        spec_path = os.path.abspath(os.path.join(script_dir, "..", ".agents", "references", "homelab-spec.md"))

    if os.path.exists(spec_path):
        try:
            with open(spec_path, "r") as f:
                for line in f:
                    if "Portainer API Key:" in line:
                        parts = line.split("`")
                        if len(parts) >= 3:
                            return parts[1].strip()
        except Exception as e:
            # Propagate warning but don't crash
            print(f"Warning: Failed to read key from spec file: {e}")
    return None

def make_portainer_request(
    base_url: str,
    endpoint: str,
    api_key: str,
    method: str = "GET",
    payload: Optional[dict] = None,
    verify_ssl: bool = False
) -> Optional[Union[dict, list]]:
    """Send a request to the Portainer API and return the JSON response.
    
    Raises RuntimeError on HTTP errors or connection failures.
    """
    clean_base = base_url.rstrip("/")
    clean_endpoint = endpoint.lstrip("/")
    url = f"{clean_base}/{clean_endpoint}"
    
    headers = {
        "X-API-Key": api_key,
        "Accept": "application/json"
    }
    
    data = None
    if payload is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(payload).encode("utf-8")
        
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    ctx = get_ssl_context(verify=verify_ssl)
    
    try:
        with urllib.request.urlopen(req, context=ctx) as response:
            status = response.status
            # Status 204 has no content (common for deletes)
            if status == 204:
                return {}
            
            body = response.read().decode("utf-8")
            if not body:
                return {}
            return json.loads(body)
            
    except urllib.error.HTTPError as e:
        # Read the error body if available to give detailed messages
        try:
            raw_err = e.read().decode("utf-8")
            error_data = json.loads(raw_err)
            detail = error_data.get("message", error_data.get("details", raw_err))
        except Exception:
            detail = "Could not parse error response"
        raise RuntimeError(f"HTTP {e.code}: {e.reason}. Details: {detail}") from e
    except urllib.error.URLError as e:
        raise RuntimeError(f"Network error connecting to Portainer API: {e.reason}") from e
    except Exception as e:
        raise RuntimeError(f"Unexpected error making API request: {e}") from e
