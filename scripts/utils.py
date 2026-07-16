import os
import ssl
import json
import urllib.request
import urllib.error
from typing import Optional, Union, Any, List, Dict, Tuple

def get_ssl_context(verify: bool = False) -> ssl.SSLContext:
    """Create an SSL context. If verify is False, disable hostname checking and cert validation."""
    ctx = ssl.create_default_context()
    if not verify:
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
    return ctx

def get_portainer_api_key(spec_path: Optional[str] = None, device_name: Optional[str] = None) -> Optional[str]:
    """Resolve the Portainer API key, checking environment first, then homelab-spec.json."""
    key = os.environ.get("PORTAINER_API_KEY")
    if key:
        return key

    # Resolve default path to spec file relative to this script if not provided
    if not spec_path:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        spec_path = os.path.abspath(os.path.join(script_dir, "..", ".agents", "references", "homelab-spec.json"))

    if os.path.exists(spec_path):
        try:
            with open(spec_path, "r") as f:
                specs = json.load(f)
            
            if device_name and device_name in specs.get("devices", {}):
                return specs["devices"][device_name].get("credentials", {}).get("portainer_api_key")
            
            # If no device specified or not found, try to find the first valid API key as a fallback
            for dev_data in specs.get("devices", {}).values():
                k = dev_data.get("credentials", {}).get("portainer_api_key")
                if k and k != "[API_KEY_FAILED_TO_GENERATE]":
                    return k
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

def get_endpoint_id(base_url: str, api_key: str) -> int:
    """Retrieve the ID of the first active endpoint/environment in Portainer."""
    data = make_portainer_request(base_url, "/api/endpoints", api_key)
    if isinstance(data, list) and data:
        return data[0].get("Id")
    raise RuntimeError("No active Portainer environments found.")

def parse_env_file(env_file_path: str) -> List[Dict[str, str]]:
    """Parse a local .env file into the JSON structure expected by Portainer API."""
    env_vars: List[Dict[str, str]] = []
    try:
        with open(env_file_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, val = line.split('=', 1)
                    val = val.strip()
                    if (val.startswith('"') and val.endswith('"')) or (val.startswith("'") and val.endswith("'")):
                        val = val[1:-1]
                    env_vars.append({"name": key.strip(), "value": val})
    except Exception as e:
        raise RuntimeError(f"Error reading env file: {e}") from e
    return env_vars

def find_stack_by_name(base_url: str, api_key: str, stack_name: str) -> Tuple[Optional[int], Optional[int]]:
    """Search for a stack by its name in Portainer. Returns (stack_id, endpoint_id)."""
    try:
        stacks = make_portainer_request(base_url, "/api/stacks", api_key)
        if isinstance(stacks, list):
            for stack in stacks:
                if stack.get("Name") == stack_name:
                    return stack.get("Id"), stack.get("EndpointId")
    except Exception as e:
        print(f"[Warning] Failed to query stacks: {e}")
    return None, None

