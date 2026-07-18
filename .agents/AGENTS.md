# Homelab Agent Rules

These rules govern the development, configuration, and management of Docker containers and related infrastructure in this homelab repository. All agents must strictly adhere to these instructions.

## 1. Sensitive Information & Environment Variables
- **No Hardcoded Secrets/IPs**: Always use environment variables for sensitive information. This includes, but is not limited to:
  - Passwords and API keys
  - IP addresses and domain names
  - Tokens and private credentials
- **Mock Templates (`.env.example`)**: Every template environment file (`.env.example`) must contain only mock/placeholder values. Never include actual credentials, IP addresses, or secrets.
- **Git Safety for Credentials**: Actual configuration/credential files (e.g., `container-name.env` files) must never be committed to GitHub. They must always be added/present in the `.gitignore` file.

## 2. Structure for New Containers
When adding or configuring a new container in the homelab, always create a subdirectory under the workspace root (`/Users/jason/Developer/projects/homelab/<new-container>`).

Each new container directory must strictly include the following files:
1. `docker-compose.yml`: The Docker Compose file defining the services, volume mounts, and network settings.
2. `.env.example`: A template configuration file containing mock values for all required environment variables.
3. `<container-name>.env`: The environment file containing the actual local configuration and secret credentials (which must be ignored in `.gitignore`).

### Directory Layout Example
```
/Users/jason/Developer/projects/homelab/
└── <new-container>/
    ├── docker-compose.yml
    ├── .env.example
    └── <container-name>.env
```

## 3. Token-Optimized Polling
When you need to poll or wait for a condition (container health, deployment readiness, service availability), **never** poll inline. Follow these rules strictly:

- **Do NOT** write `while`/`until` loops inside `run_command` to check status repeatedly.
- **Do NOT** make repeated sequential tool calls (e.g., calling `curl` or `docker inspect` in a loop) to watch for state changes.
- **Delegate to `scripts/poll_status.py`**: Launch it as a **background task** with `run_command`. The script handles retries, backoff, and timeout internally in a single process.
- **Go idle after launch**: After starting the poll, **stop calling tools** and let the system wake you when the script exits.

### Polling Modes
| Mode | Use case | Example |
|------|----------|---------|
| `http` | Wait for an HTTP endpoint to return a status code | `poll_status.py --timeout 60 http --url https://host:9443 --insecure` |
| `command` | Wait for any shell command to exit 0 | `poll_status.py command --host user@host -- systemctl is-active myservice` |
| `docker` | Wait for a container state (`running`, `healthy`) | `poll_status.py docker --container myapp --state healthy --host user@host` |

### Remote Execution
All `command` and `docker` mode polls support `--host user@host` to run the check on a remote machine via SSH. Use this for checking services on Wyse1/Wyse2 from the local Mac.
