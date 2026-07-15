import argparse
import sys
from typing import Tuple, Optional
from utils import make_portainer_request

def find_stack_by_name(base_url: str, api_key: str, stack_name: str) -> Tuple[Optional[int], Optional[int]]:
    """Search for a stack by its name in Portainer.
    
    Returns a tuple of (stack_id, endpoint_id), or (None, None) if not found.
    """
    try:
        stacks = make_portainer_request(base_url, "/api/stacks", api_key)
        if isinstance(stacks, list):
            for stack in stacks:
                if stack.get("Name") == stack_name:
                    return stack.get("Id"), stack.get("EndpointId")
    except Exception as e:
        print(f"[Warning] Failed to query stacks: {e}")
    return None, None

def delete_stack(base_url: str, api_key: str, stack_name: str) -> None:
    """Find a stack by name and delete it from Portainer.
    
    Raises RuntimeError on API failure.
    """
    print(f"Finding stack '{stack_name}' in Portainer...")
    stack_id, endpoint_id = find_stack_by_name(base_url, api_key, stack_name)
    
    if not stack_id:
        print(f"[Info] Stack '{stack_name}' not found. No deletion needed.")
        return
        
    print(f"Found Stack ID: {stack_id}, Endpoint ID: {endpoint_id}. Deleting...")
    delete_endpoint = f"/api/stacks/{stack_id}?endpointId={endpoint_id}"
    
    # A successful delete request returns 204 No Content, which make_portainer_request handles
    make_portainer_request(base_url, delete_endpoint, api_key, method="DELETE")
    print(f"[Success] Stack '{stack_name}' deleted successfully.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Delete a Portainer Stack by Name")
    parser.add_argument("--url", required=True, help="Portainer URL (e.g., https://192.168.1.49:9442)")
    parser.add_argument("--api-key", required=True, help="Portainer API Key")
    parser.add_argument("--stack-name", required=True, help="Name of the stack to delete")
    args = parser.parse_args()
    
    try:
        delete_stack(args.url, args.api_key, args.stack_name)
    except Exception as e:
        print(f"[Error] Failed to delete stack: {e}")
        sys.exit(1)
