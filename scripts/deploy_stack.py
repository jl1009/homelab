import argparse
import json
import ssl
import sys
import urllib.request
from urllib.error import HTTPError

def get_ssl_context():
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx

def get_endpoint_id(base_url, headers):
    endpoints_url = f"{base_url.rstrip('/')}/api/endpoints"
    req = urllib.request.Request(endpoints_url, headers=headers)
    ctx = get_ssl_context()
    
    try:
        with urllib.request.urlopen(req, context=ctx) as response:
            if response.status == 200:
                data = json.loads(response.read().decode())
                if data:
                    # In a typical homelab, the local Portainer agent is Endpoint ID 1 or 2.
                    for endpoint in data:
                        return endpoint.get("Id")
                print("Error: No Portainer environments found.")
                sys.exit(1)
            else:
                print(f"Error fetching endpoints. HTTP Status: {response.status}")
                sys.exit(1)
    except Exception as e:
        print(f"Error connecting to Portainer API to get endpoints: {e}")
        sys.exit(1)

def deploy_stack(args):
    base_url = args.url.rstrip('/')
    headers = {
        "X-API-Key": args.api_key,
        "Accept": "application/json",
        "Content-Type": "application/json"
    }

    print(f"Connecting to Portainer at: {base_url}...")
    endpoint_id = get_endpoint_id(base_url, headers)
    print(f"Found Target Endpoint ID: {endpoint_id}")

    # Portainer API payload for creating a stack from a git repository
    # method=repository for git, type=2 for standalone Docker
    create_stack_url = f"{base_url}/api/stacks/create/standalone/repository?endpointId={endpoint_id}"
    
    env_vars = []
    if args.env_file:
        try:
            with open(args.env_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, val = line.split('=', 1)
                        # Remove surrounding quotes from value if present
                        val = val.strip()
                        if (val.startswith('"') and val.endswith('"')) or (val.startswith("'") and val.endswith("'")):
                            val = val[1:-1]
                        env_vars.append({"name": key.strip(), "value": val})
        except Exception as e:
            print(f"Error reading env file: {e}")
            sys.exit(1)

    payload = {
        "Name": args.stack_name,
        "RepositoryURL": args.repo_url,
        "RepositoryReferenceName": args.repo_ref,
        "ComposeFile": args.compose_path,
        "RepositoryAuthentication": False,
        "Env": env_vars,
    }

    if args.git_username and args.git_password:
        payload["RepositoryAuthentication"] = True
        payload["RepositoryUsername"] = args.git_username
        payload["RepositoryPassword"] = args.git_password

    data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(create_stack_url, data=data, headers=headers, method='POST')
    
    try:
        with urllib.request.urlopen(req, context=get_ssl_context()) as response:
            resp_data = json.loads(response.read().decode())
            print(f"\n[Success] Stack '{args.stack_name}' created successfully!")
            print(f"Stack Details: {json.dumps(resp_data, indent=2)}")
    except HTTPError as e:
        print(f"\n[Error] Failed to create stack. HTTP Status: {e.code}")
        try:
            error_data = json.loads(e.read().decode())
            print(f"Details: {error_data}")
        except:
            print(f"Raw Response: {e.read().decode()}")
        sys.exit(1)
    except Exception as e:
        print(f"\n[Error] An unexpected error occurred: {e}")
        sys.exit(1)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Deploy a Docker Stack via Portainer API using a Git Repository")
    parser.add_argument("--url", required=True, help="Portainer URL (e.g., https://192.168.1.50:9443)")
    parser.add_argument("--api-key", required=True, help="Portainer API Key")
    parser.add_argument("--stack-name", required=True, help="Name of the stack to create")
    parser.add_argument("--repo-url", required=True, help="Git repository URL")
    parser.add_argument("--repo-ref", default="refs/heads/main", help="Git repository reference (default: refs/heads/main)")
    parser.add_argument("--compose-path", default="docker-compose.yml", help="Path to the compose file in the repo (default: docker-compose.yml)")
    parser.add_argument("--env-file", help="Path to a .env file to load environment variables from")
    parser.add_argument("--git-username", help="Git repository username")
    parser.add_argument("--git-password", help="Git repository password or PAT")
    
    args = parser.parse_args()
    deploy_stack(args)
