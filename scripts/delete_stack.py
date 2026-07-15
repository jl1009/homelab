import argparse
import ssl
import sys
import urllib.request
import json
from urllib.error import HTTPError

def get_ssl_context():
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx

def find_stack_by_name(base_url, headers, stack_name):
    url = f"{base_url.rstrip('/')}/api/stacks"
    req = urllib.request.Request(url, headers=headers)
    ctx = get_ssl_context()
    try:
        with urllib.request.urlopen(req, context=ctx) as response:
            if response.status == 200:
                stacks = json.loads(response.read().decode())
                for stack in stacks:
                    if stack.get("Name") == stack_name:
                        return stack.get("Id"), stack.get("EndpointId")
    except Exception as e:
        print(f"[Error] Failed to query stacks: {e}")
    return None, None

def delete_stack(base_url, api_key, stack_name):
    headers = {
        "X-API-Key": api_key,
        "Accept": "application/json"
    }
    
    print(f"Finding stack '{stack_name}' in Portainer...")
    stack_id, endpoint_id = find_stack_by_name(base_url, headers, stack_name)
    
    if not stack_id:
        print(f"[Info] Stack '{stack_name}' not found. No deletion needed.")
        return
        
    print(f"Found Stack ID: {stack_id}, Endpoint ID: {endpoint_id}. Deleting...")
    delete_url = f"{base_url.rstrip('/')}/api/stacks/{stack_id}?endpointId={endpoint_id}"
    req = urllib.request.Request(delete_url, headers=headers, method="DELETE")
    
    try:
        with urllib.request.urlopen(req, context=get_ssl_context()) as response:
            # Portainer returns 204 No Content on successful deletion
            if response.status in [200, 204]:
                print(f"[Success] Stack '{stack_name}' deleted successfully.")
            else:
                print(f"[Warning] Delete request returned status code: {response.status}")
    except HTTPError as e:
        print(f"[Error] Failed to delete stack. HTTP Status: {e.code}")
        try:
            error_data = json.loads(e.read().decode())
            print(f"Details: {error_data}")
        except:
            print(f"Raw Response: {e.read().decode()}")
        sys.exit(1)
    except Exception as e:
        print(f"[Error] Unexpected error during deletion: {e}")
        sys.exit(1)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Delete a Portainer Stack by Name")
    parser.add_argument("--url", required=True, help="Portainer URL (e.g., https://192.168.1.49:9442)")
    parser.add_argument("--api-key", required=True, help="Portainer API Key")
    parser.add_argument("--stack-name", required=True, help="Name of the stack to delete")
    args = parser.parse_args()
    delete_stack(args.url, args.api_key, args.stack_name)
