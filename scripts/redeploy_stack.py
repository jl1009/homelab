import argparse
import sys
import json
from typing import Optional, List, Dict
from utils import make_portainer_request

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

def find_stack_by_name(base_url: str, api_key: str, stack_name: str):
    """Find a stack ID and endpoint ID by stack name."""
    stacks = make_portainer_request(base_url, "/api/stacks", api_key)
    if isinstance(stacks, list):
        for stack in stacks:
            if stack.get("Name") == stack_name:
                return stack.get("Id"), stack.get("EndpointId")
    return None, None

def redeploy_stack(base_url: str, api_key: str, stack_name: str, env_file: Optional[str] = None):
    """Trigger a pull and redeployment of an existing Git-backed stack on Portainer."""
    print(f"Finding stack '{stack_name}' in Portainer...")
    stack_id, endpoint_id = find_stack_by_name(base_url, api_key, stack_name)
    if not stack_id:
        raise RuntimeError(f"Stack '{stack_name}' not found.")
    
    print(f"Found Stack ID: {stack_id}, Endpoint ID: {endpoint_id}. Redeploying...")
    
    env_vars = parse_env_file(env_file) if env_file else []
    
    payload = {
        "env": env_vars,
        "Env": env_vars,
        "prune": True,
        "pullImage": True,
    }
    
    redeploy_endpoint = f"/api/stacks/{stack_id}/git/redeploy?endpointId={endpoint_id}"
    
    resp = make_portainer_request(base_url, redeploy_endpoint, api_key, method="PUT", payload=payload)
    print(f"[Success] Stack '{stack_name}' redeployed successfully!")
    if resp:
        print(f"Details: {json.dumps(resp, indent=2)}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Redeploy a Portainer Stack from Git")
    parser.add_argument("--url", required=True, help="Portainer URL")
    parser.add_argument("--api-key", required=True, help="Portainer API Key")
    parser.add_argument("--stack-name", required=True, help="Stack Name")
    parser.add_argument("--env-file", help="Path to env file")
    args = parser.parse_args()
    
    try:
        redeploy_stack(args.url, args.api_key, args.stack_name, args.env_file)
    except Exception as e:
        print(f"[Error] {e}")
        sys.exit(1)
