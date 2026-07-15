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
