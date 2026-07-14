---
name: portainer_deploy
description: "Deploys a Docker stack to a Portainer instance on a specific homelab device from a Git repository."
---

# Portainer Deployment Skill

Use this skill when the user wants to deploy a Docker Compose stack to a Portainer instance in their homelab. This skill specifically uses Portainer's Git repository deployment feature and its REST API.

## Workflow

1. **Identify Target Device**: Ensure you know which homelab device the user wants to deploy to (e.g., `Wyse2`, `srv-docker-01`). If the user didn't specify, ask them first.
2. **Retrieve Portainer Configuration**: Read the file `/Users/jason/Developer/projects/homelab/.agents/references/homelab-spec.md`. Look for the device's entry to find:
   - Its IP address (or hostname)
   - Portainer's port (e.g., `9443` or `9000`)
   - The Portainer API Key
3. **Gather Repository Info**: Ensure you have the following information from the user (prompt if missing):
   - The Git repository URL (e.g., `https://github.com/username/repo.git`)
   - The branch or reference (default: `refs/heads/main`)
   - The path to the `docker-compose.yml` file within the repo (default: `docker-compose.yml`)
   - A name for the stack
4. **Deploy Stack**: Execute the helper Python script located in the `scripts` directory of the homelab project (absolute path: `/Users/jason/Developer/projects/homelab/scripts/deploy_stack.py`).

## Using the Helper Script

To deploy the stack, run the Python script using the appropriate arguments:

```bash
python3 /Users/jason/Developer/projects/homelab/scripts/deploy_stack.py \
  --url "https://[IP]:[PORT]" \
  --api-key "[API_KEY]" \
  --stack-name "[STACK_NAME]" \
  --repo-url "[GIT_REPO_URL]" \
  --repo-ref "[GIT_BRANCH_OR_REF]" \
  --compose-path "[COMPOSE_FILE_PATH]"
```

*Note: You may omit `--repo-ref` (defaults to `refs/heads/main`) and `--compose-path` (defaults to `docker-compose.yml`) if the defaults apply.*

After the script runs, check its output. If successful, it will print "Stack '[STACK_NAME]' created successfully!". If it fails, report the error to the user and investigate if necessary.
