---
name: portainer_manage
description: "Manage Portainer Docker stacks (deploy, redeploy, delete) across homelab devices."
---

# Portainer Stack Management

Use this skill to deploy, redeploy, or delete Docker stacks on Portainer instances.

## Workflow
*   **Target Device**: Ask the user for the target device (e.g., `Wyse1`, `Wyse2`) if not specified.
*   **Read Specs**: Parse `/Users/jason/Developer/projects/homelab/.agents/references/homelab-spec.json` to get the device's Portainer URL and API key.
*   **Execute Tool**: Use `/Users/jason/Developer/projects/homelab/scripts/manage_stack.py`.

## Commands

### 1. Deploy Stack
```bash
python3 /Users/jason/Developer/projects/homelab/scripts/manage_stack.py --url "<URL>" --api-key "<KEY>" deploy \
  --stack-name "<NAME>" \
  --repo-url "<GIT_URL>" \
  [--repo-ref "refs/heads/main"] \
  [--compose-path "docker-compose.yml"] \
  [--env-file "path/to/.env"]
```

### 2. Redeploy Stack (Git Pull)
```bash
python3 /Users/jason/Developer/projects/homelab/scripts/manage_stack.py --url "<URL>" --api-key "<KEY>" redeploy \
  --stack-name "<NAME>" \
  [--env-file "path/to/.env"]
```

### 3. Delete Stack
```bash
python3 /Users/jason/Developer/projects/homelab/scripts/manage_stack.py --url "<URL>" --api-key "<KEY>" delete \
  --stack-name "<NAME>"
```

*Note: The script outputs JSON response details. Check output for success or errors.*
