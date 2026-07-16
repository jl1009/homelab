import argparse
import sys
import json
from utils import make_portainer_request, parse_env_file, get_endpoint_id, find_stack_by_name

def deploy_stack(args):
    print(f"Connecting to Portainer at: {args.url}...")
    endpoint_id = get_endpoint_id(args.url, args.api_key)
    print(f"Found Target Endpoint ID: {endpoint_id}")

    create_stack_endpoint = f"/api/stacks/create/standalone/repository?endpointId={endpoint_id}"
    env_vars = parse_env_file(args.env_file) if args.env_file else []
    
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

    resp_data = make_portainer_request(
        args.url,
        create_stack_endpoint,
        args.api_key,
        method='POST',
        payload=payload
    )
    print(f"\n[Success] Stack '{args.stack_name}' created successfully!")
    if resp_data:
        print(f"Stack Details: {json.dumps(resp_data, indent=2)}")

def redeploy_stack(args):
    print(f"Finding stack '{args.stack_name}' in Portainer...")
    stack_id, endpoint_id = find_stack_by_name(args.url, args.api_key, args.stack_name)
    if not stack_id:
        raise RuntimeError(f"Stack '{args.stack_name}' not found.")
    
    print(f"Found Stack ID: {stack_id}, Endpoint ID: {endpoint_id}. Redeploying...")
    env_vars = parse_env_file(args.env_file) if args.env_file else []
    
    payload = {
        "env": env_vars,
        "Env": env_vars,
        "prune": True,
        "pullImage": True,
    }
    
    redeploy_endpoint = f"/api/stacks/{stack_id}/git/redeploy?endpointId={endpoint_id}"
    resp = make_portainer_request(args.url, redeploy_endpoint, args.api_key, method="PUT", payload=payload)
    print(f"[Success] Stack '{args.stack_name}' redeployed successfully!")
    if resp:
        print(f"Details: {json.dumps(resp, indent=2)}")

def delete_stack(args):
    print(f"Finding stack '{args.stack_name}' in Portainer...")
    stack_id, endpoint_id = find_stack_by_name(args.url, args.api_key, args.stack_name)
    if not stack_id:
        print(f"[Info] Stack '{args.stack_name}' not found. No deletion needed.")
        return
        
    print(f"Found Stack ID: {stack_id}, Endpoint ID: {endpoint_id}. Deleting...")
    delete_endpoint = f"/api/stacks/{stack_id}?endpointId={endpoint_id}"
    make_portainer_request(args.url, delete_endpoint, args.api_key, method="DELETE")
    print(f"[Success] Stack '{args.stack_name}' deleted successfully.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Manage Portainer Stacks (deploy, redeploy, delete)")
    parser.add_argument("--url", required=True, help="Portainer URL")
    parser.add_argument("--api-key", required=True, help="Portainer API Key")
    
    subparsers = parser.add_subparsers(dest="action", required=True, help="Action to perform")
    
    # Deploy
    deploy_parser = subparsers.add_parser("deploy", help="Deploy a new stack from Git")
    deploy_parser.add_argument("--stack-name", required=True, help="Name of the stack to create")
    deploy_parser.add_argument("--repo-url", required=True, help="Git repository URL")
    deploy_parser.add_argument("--repo-ref", default="refs/heads/main", help="Git repository reference (default: refs/heads/main)")
    deploy_parser.add_argument("--compose-path", default="docker-compose.yml", help="Path to compose file in repo")
    deploy_parser.add_argument("--env-file", help="Path to .env file")
    deploy_parser.add_argument("--git-username", help="Git repository username")
    deploy_parser.add_argument("--git-password", help="Git repository password or PAT")
    
    # Redeploy
    redeploy_parser = subparsers.add_parser("redeploy", help="Redeploy an existing Git-backed stack")
    redeploy_parser.add_argument("--stack-name", required=True, help="Stack Name")
    redeploy_parser.add_argument("--env-file", help="Path to env file")
    
    # Delete
    delete_parser = subparsers.add_parser("delete", help="Delete a stack by name")
    delete_parser.add_argument("--stack-name", required=True, help="Name of the stack to delete")
    
    args = parser.parse_args()
    
    try:
        if args.action == "deploy":
            deploy_stack(args)
        elif args.action == "redeploy":
            redeploy_stack(args)
        elif args.action == "delete":
            delete_stack(args)
    except Exception as e:
        print(f"\n[Error] {e}")
        sys.exit(1)
