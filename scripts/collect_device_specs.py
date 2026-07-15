import argparse
import json
import os
import subprocess
import sys
import urllib.request
from urllib.error import HTTPError
from typing import Dict, Any, List, Optional
from utils import get_ssl_context

def run_ssh_command(ip: str, user: str, password: Optional[str], command: str) -> Optional[str]:
    """Execute a shell command on a remote host via SSH, supporting optional password input via sshpass."""
    if password:
        ssh_cmd = [
            "sshpass", "-p", password,
            "ssh", "-o", "StrictHostKeyChecking=no",
            "-o", "ConnectTimeout=5",
            f"{user}@{ip}", command
        ]
    else:
        ssh_cmd = [
            "ssh", "-o", "StrictHostKeyChecking=no",
            "-o", "ConnectTimeout=5",
            f"{user}@{ip}", command
        ]
    
    try:
        result = subprocess.run(ssh_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=False)
        if result.returncode == 255:
            print(f"SSH connection failed to {ip}: {result.stderr.strip()}")
            return None
        return result.stdout.strip()
    except FileNotFoundError:
        if password:
            print("Error: 'sshpass' is not installed or not in PATH, and password auth was requested.")
            print("Attempting standard ssh...")
            # Fallback to standard ssh
            return run_ssh_command(ip, user, None, command)
        return None
    except Exception as e:
        print(f"Exception executing SSH to {ip}: {e}")
        return None

def generate_portainer_api_key(url: str, username: str, password: str) -> Optional[str]:
    """Authenticate with Portainer and generate a new API key.
    
    Uses standard JWT Bearer token authentication to request the token.
    """
    base_url = url.rstrip('/')
    ctx = get_ssl_context(verify=False)
    
    # 1. Authenticate to get JWT
    auth_url = f"{base_url}/api/auth"
    payload = {
        "username": username,
        "password": password
    }
    data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(
        auth_url,
        data=data,
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        method='POST'
    )
    
    try:
        with urllib.request.urlopen(req, context=ctx) as response:
            resp = json.loads(response.read().decode())
            jwt = resp.get("jwt")
    except HTTPError as e:
        print(f"Portainer Auth failed on {url}. Status: {e.code}, Reason: {e.reason}")
        try:
            print("Error Details:", e.read().decode())
        except Exception:
            pass
        return None
    except Exception as e:
        print(f"Failed to connect to Portainer at {url}: {e}")
        return None

    # 2. Get current user ID
    user_url = f"{base_url}/api/users/me"
    req = urllib.request.Request(
        user_url,
        headers={"Authorization": f"Bearer {jwt}", "Accept": "application/json"}
    )
    try:
        with urllib.request.urlopen(req, context=ctx) as response:
            user_data = json.loads(response.read().decode())
            user_id = user_data.get("Id")
    except Exception as e:
        print(f"Failed to get current user ID: {e}")
        # Default to 1 if we can't get it
        user_id = 1

    # 3. Create API Key
    token_url = f"{base_url}/api/users/{user_id}/tokens"
    token_payload = {
        "password": password,
        "description": "homelab-spec-key"
    }
    token_data = json.dumps(token_payload).encode('utf-8')
    req = urllib.request.Request(
        token_url,
        data=token_data,
        headers={
            "Authorization": f"Bearer {jwt}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        },
        method='POST'
    )
    try:
        with urllib.request.urlopen(req, context=ctx) as response:
            token_resp = json.loads(response.read().decode())
            return token_resp.get("rawAPIKey")
    except Exception as e:
        print(f"Failed to create Portainer API Key: {e}")
        return None

def collect_device_specs(
    ip: str,
    user: str,
    password: Optional[str],
    portainer_url: Optional[str],
    portainer_user: Optional[str],
    portainer_pass: Optional[str]
) -> Dict[str, Any]:
    """Gather hardware specs, storage mounts, running containers, and API keys from a homelab device."""
    print(f"\n=========================================")
    print(f"Collecting specs for device: {ip}...")
    print(f"=========================================")

    # Test SSH connection and collect basic info
    print("[1/4] Running SSH checks...")
    
    # 1. MAC Address
    mac_cmd = "ip link show | grep link/ether | awk '{print $2}' | head -n 1"
    mac = run_ssh_command(ip, user, password, mac_cmd)
    if not mac:
        # Try fallback
        mac = run_ssh_command(ip, user, password, "cat /sys/class/net/eth0/address 2>/dev/null || cat /sys/class/net/enp3s0/address 2>/dev/null")
    if not mac:
        mac = "unknown_mac"
    print(f" -> MAC: {mac}")

    # 2. Architecture
    arch = run_ssh_command(ip, user, password, "uname -m") or "unknown_arch"
    print(f" -> Arch: {arch}")

    # 3. OS
    os_name = run_ssh_command(ip, user, password, "grep PRETTY_NAME /etc/os-release | cut -d'\"' -f2")
    if not os_name:
        os_name = run_ssh_command(ip, user, password, "uname -s") or "Linux"
    print(f" -> OS: {os_name}")

    # 4. UID
    uid = run_ssh_command(ip, user, password, "id -u") or "1000"
    print(f" -> UID: {uid}")

    # 5. CPU
    cpu = run_ssh_command(ip, user, password, "lscpu | grep 'Model name:' | sed 's/Model name:\\s*//'")
    if not cpu:
        cpu = run_ssh_command(ip, user, password, "grep 'model name' /proc/cpuinfo | head -n 1 | cut -d: -f2 | xargs")
    if not cpu:
        cpu = run_ssh_command(ip, user, password, "uname -p") or "Unknown CPU"
    print(f" -> CPU: {cpu}")

    # 6. RAM
    ram = run_ssh_command(ip, user, password, "free -h 2>/dev/null | grep Mem: | awk '{print $2}'")
    if not ram:
        ram_kb = run_ssh_command(ip, user, password, "grep MemTotal /proc/meminfo | awk '{print $2}'")
        if ram_kb:
            ram = f"{round(float(ram_kb)/1024/1024, 1)}GB"
        else:
            ram = "Unknown RAM"
    print(f" -> RAM: {ram}")

    # 7. GPU
    gpu = run_ssh_command(ip, user, password, "lspci 2>/dev/null | grep -i 'vga\\|3d\\|display\\|render'")
    if not gpu:
        has_dri = run_ssh_command(ip, user, password, "[ -d /dev/dri ] && echo 'Intel QuickSync (Detected)' || echo 'None'")
        gpu = has_dri if has_dri else "None"
    else:
        # Simplify/cleanup GPU output
        gpu = gpu.splitlines()[0] if isinstance(gpu, str) else "None"
    print(f" -> GPU: {gpu}")

    # 8. Mounts
    print("[2/4] Reading mounts...")
    mounts_raw = run_ssh_command(ip, user, password, "df -hT | grep -v -E 'tmpfs|devtmpfs|overlay|shm|udev'")
    mounts_list: List[str] = []
    if mounts_raw:
        for line in mounts_raw.splitlines():
            # Skip header
            if line.startswith("Filesystem") or not line.strip():
                continue
            parts = line.split()
            if len(parts) >= 7:
                fs, fs_type, size, used, avail, use_pct, target = parts[0], parts[1], parts[2], parts[3], parts[4], parts[5], parts[6]
                # Filter out standard system paths to focus on user mounts
                if target in ['/', '/boot', '/boot/efi'] or target.startswith('/sys') or target.startswith('/proc') or target.startswith('/dev'):
                    continue
                mounts_list.append(f"  - `{fs}` -> `{target}` ({size} {fs_type})")
    
    # 9. Docker Containers
    print("[3/4] Checking running containers...")
    docker_cmd = "docker ps -a --format '{{.Names}} ({{.Ports}})' 2>/dev/null || (echo '" + (password or "") + "' | sudo -S docker ps -a --format '{{.Names}} ({{.Ports}})' 2>/dev/null)"
    docker_raw = run_ssh_command(ip, user, password, docker_cmd)
    containers: List[str] = []
    if docker_raw:
        for line in docker_raw.splitlines():
            # Skip password prompt output from sudo -S (e.g. "[sudo] password for ...:")
            if "[sudo] password for" in line:
                continue
            if line.strip():
                containers.append(line.strip())
    
    # 10. Portainer API Key
    api_key = None
    if portainer_url and portainer_user and portainer_pass:
        print("[4/4] Generating Portainer API Key...")
        api_key = generate_portainer_api_key(portainer_url, portainer_user, portainer_pass)
        if api_key:
            print(" -> API Key successfully generated!")
        else:
            print(" -> API Key generation failed.")
    
    return {
        "ip": ip,
        "mac": mac,
        "arch": arch,
        "os": os_name,
        "uid": uid,
        "cpu": cpu,
        "ram": ram,
        "gpu": gpu,
        "mounts": mounts_list,
        "containers": containers,
        "portainer_url": portainer_url,
        "api_key": api_key,
        "ssh_user": user,
        "ssh_pass": password
    }

def update_spec_file(device_data: Dict[str, Any], spec_path: str) -> bool:
    """Write device specs and configuration sections back to the homelab-spec.md file."""
    if not os.path.exists(spec_path):
        print(f"Error: Specification file not found at {spec_path}")
        return False
    
    with open(spec_path, 'r') as f:
        content = f.read()

    hostname = device_data["hostname"]
    
    # Format mounts
    mounts_str = ""
    if device_data["mounts"]:
        mounts_str = "\n".join(device_data["mounts"])
    else:
        mounts_str = "  - None"

    # Format containers
    containers_str = ", ".join(device_data["containers"]) if device_data["containers"] else "None"

    # Portainer key detail
    api_key_str = f"`{device_data['api_key']}`" if device_data["api_key"] else "`[API_KEY_FAILED_TO_GENERATE]`"

    device_template = f"""### {hostname}
- **IP / MAC**: `{device_data['ip']}` / `{device_data['mac']}` (`{device_data['arch']}` | {device_data['os']} | UID: `{device_data['uid']}`)
- **Specs**: {device_data['cpu']} | {device_data['ram']} | GPU: {device_data['gpu']}
- **Mounts**:
{mounts_str}
- **Containers**: {containers_str}
- **Credentials**:
  - Portainer API Key: {api_key_str}
  - SSH: `{device_data['ssh_user']}@{device_data['ip']}` (password: `{device_data['ssh_pass']}`)
"""

    # Check if this device section already exists in the file
    section_header = f"### {hostname}"
    if section_header in content:
        # Replace the existing section
        lines = content.splitlines()
        start_idx = -1
        end_idx = len(lines)
        
        for idx, line in enumerate(lines):
            if line.startswith(section_header):
                start_idx = idx
                break
        
        if start_idx != -1:
            # Find the next h3 (### ) or h2 (## ) section to find the end
            for idx in range(start_idx + 1, len(lines)):
                if lines[idx].startswith("### ") or lines[idx].startswith("## "):
                    end_idx = idx
                    break
            
            # Replace the lines
            new_lines = lines[:start_idx] + device_template.splitlines() + lines[end_idx:]
            content = "\n".join(new_lines)
            print(f"Updated section for {hostname} in {spec_path}")
    else:
        # Append before the GitHub Integration section if it exists, otherwise at the end
        github_header = "## 🐙 GitHub Integration"
        if github_header in content:
            content = content.replace(github_header, f"{device_template}\n{github_header}")
            print(f"Added section for {hostname} in {spec_path}")
        else:
            content += f"\n{device_template}"
            print(f"Appended section for {hostname} to end of {spec_path}")

    with open(spec_path, 'w') as f:
        f.write(content)
    return True

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Collect specs from homelab devices and update homelab-spec.md")
    parser.add_argument("--spec-path", default="../.agents/references/homelab-spec.md", help="Path to homelab-spec.md")
    parser.add_argument("--device", choices=["Wyse1", "WumbologyNAS", "DietPi", "Wyse2"], help="Only run for a specific device")
    parser.add_argument("--creds", help="Path to JSON file containing credentials for non-interactive run")
    args = parser.parse_args()

    # Resolve absolute path to spec file
    script_dir = os.path.dirname(os.path.abspath(__file__))
    spec_path = os.path.abspath(os.path.join(script_dir, args.spec_path))

    # Load credentials if provided
    creds_data = {}
    if args.creds:
        try:
            with open(args.creds, 'r') as f:
                creds_data = json.load(f)
        except Exception as e:
            print(f"Error loading credentials from {args.creds}: {e}")
            sys.exit(1)

    devices = {
        "Wyse1": {
            "ip": "192.168.1.49",
            "portainer_url": "http://192.168.1.49:9002",
            "default_ssh_user": "dietpi"
        },
        "WumbologyNAS": {
            "ip": "192.168.1.70",
            "portainer_url": "http://192.168.1.70:9000",
            "default_ssh_user": "admin"
        },
        "DietPi": {
            "ip": "192.168.1.47",
            "portainer_url": "http://192.168.1.47:9002",
            "default_ssh_user": "dietpi"
        },
        "Wyse2": {
            "ip": "192.168.1.50",
            "portainer_url": "https://192.168.1.50:9443",
            "default_ssh_user": "dietpi"
        }
    }

    # Filter if specific device is requested
    target_devices = [args.device] if args.device else ["Wyse1", "WumbologyNAS", "DietPi", "Wyse2"]

    for name in target_devices:
        info = devices[name]
        
        if name in creds_data:
            ssh_user = creds_data[name].get("ssh_user", info['default_ssh_user'])
            ssh_pass = creds_data[name].get("ssh_pass", "")
            portainer_user = creds_data[name].get("portainer_user", "admin")
            portainer_pass = creds_data[name].get("portainer_pass", "")
        else:
            print(f"\n>>> Input Credentials for {name} ({info['ip']}) <<<")
            ssh_user = input(f"SSH Username [{info['default_ssh_user']}]: ").strip() or info['default_ssh_user']
            ssh_pass = input(f"SSH Password (hit Enter if no password/key auth): ").strip()
            portainer_user = input(f"Portainer Admin User [admin]: ").strip() or "admin"
            portainer_pass = input(f"Portainer Admin Password: ").strip()

        # Collect data
        data = collect_device_specs(
            info["ip"],
            ssh_user,
            ssh_pass,
            info["portainer_url"],
            portainer_user,
            portainer_pass
        )
        data["hostname"] = name
        
        # Update spec file
        update_spec_file(data, spec_path)

    print("\nAll done!")
