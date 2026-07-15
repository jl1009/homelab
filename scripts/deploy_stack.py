import argparse
import json
import sys
from typing import List, Dict, Optional
from utils import make_portainer_request

def get_endpoint_id(base_url: str, api_key: str) -> int:
    """Retrieve the ID of the first active endpoint/environment in Portainer.
    
    Raises RuntimeError if no environments are found or if the request fails.
    """
    data = make_portainer_request(base_url, "/api/endpoints", api_key)
    if isinstance(data, list) and data:
        # Returns the first available endpoint ID
        return data[0].get("Id")
    raise RuntimeError("No active Portainer environments found.")

def parse_env_file(env_file_path: str) -> List[Dict[str, str]]:
    """Parse a local .env file into the JSON structure expected by Portainer API.
    
    Format: [{"name": "KEY", "value": "VAL"}, ...]
    """
    env_vars: List[Dict[str, str]] = []
    try:
        with open(env_file_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, val = line.split('=', 1)
                    val = val.strip()
                    # Remove surrounding quotes from value if present
                    if (val.startswith('"') and val.endswith('"')) or (val.startswith("'") and val.endswith("'")):
                        val = val[1:-1]
                    env_vars.append({"name": key.strip(), "value": val})
    except Exception as e:
        raise RuntimeError(f"Error reading env file: {e}") from e
    return env_vars

def deploy_stack(
    base_url: str,
    api_key: str,
    stack_name: str,
    repo_url: str,
    repo_ref: str = "refs/heads/main",
    compose_path: str = "docker-compose.yml",
    env_file: Optional[str] = None,
    git_username: Optional[str] = None,
    git_password: Optional[str] = None
) -> None:
    """Deploy a standalone Docker stack via a Git repository reference using Portainer API.
    
    Raises RuntimeError on failure.
    """
    print(f"Connecting to Portainer at: {base_url}...")
    endpoint_id = get_endpoint_id(base_url, api_key)
    print(f"Found Target Endpoint ID: {endpoint_id}")

    create_stack_endpoint = f"/api/stacks/create/standalone/repository?endpointId={endpoint_id}"
    
    env_vars = parse_env_file(env_file) if env_file else []

    payload = {
        "Name": stack_name,
        "RepositoryURL": repo_url,
        "RepositoryReferenceName": repo_ref,
        "ComposeFile": compose_path,
        "RepositoryAuthentication": False,
        "Env": env_vars,
    }

    if git_username and git_password:
        payload["RepositoryAuthentication"] = True
        payload["RepositoryUsername"] = git_username
        payload["RepositoryPassword"] = git_password

    resp_data = make_portainer_request(
        base_url,
        create_stack_endpoint,
        api_key,
        method='POST',
        payload=payload
    )
    print(f"\n[Success] Stack '{stack_name}' created successfully!")
    print(f"Stack Details: {json.dumps(resp_data, indent=2)}")

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
    
    try:
        deploy_stack(
            base_url=args.url,
            api_key=args.api_key,
            stack_name=args.stack_name,
            repo_url=args.repo_url,
            repo_ref=args.repo_ref,
            compose_path=args.compose_path,
            env_file=args.env_file,
            git_username=args.git_username,
            git_password=args.git_password
        )
    except Exception as e:
        print(f"\n[Error] Failed to deploy stack: {e}")
        sys.exit(1)
