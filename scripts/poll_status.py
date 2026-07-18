#!/usr/bin/env python3
"""Poll for a condition to become true, with retries, backoff, and timeout.

Designed to be launched as a single background command so the calling agent
pays zero intermediate token cost -- it sleeps here, not in the model.

Three polling modes:
  http    - Poll a URL for an expected HTTP status code.
  command - Run a shell command repeatedly until it exits 0.
  docker  - Check a Docker container's state via ``docker inspect``.

All modes support ``--host <user@host>`` to execute the check on a remote
machine over SSH (key-based auth assumed).

Exit codes:
  0  Success ([READY])
  1  Timeout ([TIMEOUT])
  2  Fatal error ([ERROR])
"""

import argparse
import shlex
import subprocess
import sys
import time
import urllib.error
import urllib.request
from typing import List, Optional, Tuple

# ---------------------------------------------------------------------------
# Resolve path to sibling utils module so the script works when invoked from
# any working directory.
# ---------------------------------------------------------------------------
import os

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if _SCRIPT_DIR not in sys.path:
    sys.path.insert(0, _SCRIPT_DIR)

from utils import get_ssl_context  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _run_local(cmd: List[str]) -> Tuple[int, str]:
    """Run *cmd* locally and return (exit_code, combined_output)."""
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30,
        )
        output = (result.stdout + result.stderr).strip()
        return result.returncode, output
    except subprocess.TimeoutExpired:
        return 1, "subprocess timed out after 30s"
    except Exception as exc:
        return 2, str(exc)


def _run_remote(host: str, cmd: List[str]) -> Tuple[int, str]:
    """Run *cmd* on a remote host via SSH and return (exit_code, output)."""
    # Build a single quoted string safe for the remote shell.
    remote_cmd = " ".join(shlex.quote(c) for c in cmd)
    ssh_cmd = [
        "ssh",
        "-o", "StrictHostKeyChecking=accept-new",
        "-o", "ConnectTimeout=10",
        host,
        remote_cmd,
    ]
    return _run_local(ssh_cmd)


def _run(cmd: List[str], host: Optional[str] = None) -> Tuple[int, str]:
    """Dispatch to local or remote runner."""
    if host:
        return _run_remote(host, cmd)
    return _run_local(cmd)


# ---------------------------------------------------------------------------
# Poll modes
# ---------------------------------------------------------------------------

def poll_http(
    url: str,
    expect_status: int,
    timeout: float,
    interval: float,
    backoff: float,
    max_interval: float,
    quiet: bool,
    insecure: bool,
) -> bool:
    """Poll an HTTP endpoint until it returns *expect_status*."""
    ctx = get_ssl_context(verify=not insecure)
    deadline = time.monotonic() + timeout
    attempt = 0

    while time.monotonic() < deadline:
        attempt += 1
        try:
            req = urllib.request.Request(url, method="GET")
            with urllib.request.urlopen(req, context=ctx, timeout=10) as resp:
                status = resp.status
        except urllib.error.HTTPError as exc:
            status = exc.code
        except Exception as exc:
            if not quiet:
                print(f"[attempt {attempt}] connection error: {exc}")
            time.sleep(interval)
            interval = min(interval * backoff, max_interval)
            continue

        if status == expect_status:
            print(f"[READY] {url} returned HTTP {status} after {attempt} attempt(s)")
            return True

        if not quiet:
            print(f"[attempt {attempt}] {url} -> HTTP {status} (want {expect_status})")

        time.sleep(interval)
        interval = min(interval * backoff, max_interval)

    print(f"[TIMEOUT] {url} did not return HTTP {expect_status} within {timeout}s")
    return False


def poll_command(
    cmd: List[str],
    host: Optional[str],
    timeout: float,
    interval: float,
    backoff: float,
    max_interval: float,
    quiet: bool,
) -> bool:
    """Poll a shell command until it exits 0."""
    deadline = time.monotonic() + timeout
    attempt = 0
    label = " ".join(cmd)
    if host:
        label = f"{host}: {label}"

    while time.monotonic() < deadline:
        attempt += 1
        rc, output = _run(cmd, host=host)

        if rc == 0:
            print(f"[READY] command succeeded after {attempt} attempt(s): {output or '(no output)'}")
            return True

        if not quiet:
            print(f"[attempt {attempt}] exit {rc}: {output[:200] if output else '(no output)'}")

        time.sleep(interval)
        interval = min(interval * backoff, max_interval)

    print(f"[TIMEOUT] command did not succeed within {timeout}s: {label}")
    return False


def poll_docker(
    container: str,
    desired_state: str,
    host: Optional[str],
    timeout: float,
    interval: float,
    backoff: float,
    max_interval: float,
    quiet: bool,
) -> bool:
    """Poll a Docker container until it reaches *desired_state*."""
    # Map friendly names to docker inspect format strings.
    format_str: str
    if desired_state == "healthy":
        format_str = "{{.State.Health.Status}}"
    else:
        format_str = "{{.State.Status}}"

    cmd = ["docker", "inspect", "--format", format_str, container]
    deadline = time.monotonic() + timeout
    attempt = 0

    while time.monotonic() < deadline:
        attempt += 1
        rc, output = _run(cmd, host=host)

        if rc != 0:
            if not quiet:
                print(f"[attempt {attempt}] docker inspect failed: {output[:200]}")
        else:
            current = output.strip().lower()
            if current == desired_state.lower():
                print(f"[READY] container '{container}' is {desired_state} after {attempt} attempt(s)")
                return True
            if not quiet:
                print(f"[attempt {attempt}] container '{container}' state: {current} (want {desired_state})")

        time.sleep(interval)
        interval = min(interval * backoff, max_interval)

    print(f"[TIMEOUT] container '{container}' did not reach '{desired_state}' within {timeout}s")
    return False


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser."""
    parser = argparse.ArgumentParser(
        description="Poll for a condition with retries, backoff, and timeout.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    # Common options
    parser.add_argument("--interval", type=float, default=5.0,
                        help="Seconds between polls (default: 5)")
    parser.add_argument("--timeout", type=float, default=120.0,
                        help="Total seconds before giving up (default: 120)")
    parser.add_argument("--backoff", type=float, default=1.0,
                        help="Multiplier applied to interval after each attempt (default: 1.0 = fixed)")
    parser.add_argument("--max-interval", type=float, default=60.0,
                        help="Cap for backoff growth in seconds (default: 60)")
    parser.add_argument("--quiet", action="store_true",
                        help="Suppress per-attempt output; only print final result")

    subparsers = parser.add_subparsers(dest="mode", required=True, help="Polling mode")

    # -- http --
    http_parser = subparsers.add_parser("http", help="Poll an HTTP endpoint")
    http_parser.add_argument("--url", required=True, help="URL to poll")
    http_parser.add_argument("--expect-status", type=int, default=200,
                             help="Expected HTTP status code (default: 200)")
    http_parser.add_argument("--insecure", action="store_true",
                             help="Skip SSL certificate verification")

    # -- command --
    cmd_parser = subparsers.add_parser("command", help="Poll a shell command until exit 0")
    cmd_parser.add_argument("--host", default=None,
                            help="Run command on remote host via SSH (e.g. dietpi@192.168.1.49)")
    cmd_parser.add_argument("cmd", nargs=argparse.REMAINDER,
                            help="Command to run (use -- before the command)")

    # -- docker --
    docker_parser = subparsers.add_parser("docker", help="Poll a Docker container state")
    docker_parser.add_argument("--container", required=True, help="Container name or ID")
    docker_parser.add_argument("--state", default="running",
                               help="Desired state: running, healthy, etc. (default: running)")
    docker_parser.add_argument("--host", default=None,
                               help="Check container on remote host via SSH")

    return parser


def main() -> int:
    """Entry point."""
    parser = build_parser()
    args = parser.parse_args()

    success: bool = False

    try:
        if args.mode == "http":
            success = poll_http(
                url=args.url,
                expect_status=args.expect_status,
                timeout=args.timeout,
                interval=args.interval,
                backoff=args.backoff,
                max_interval=args.max_interval,
                quiet=args.quiet,
                insecure=args.insecure,
            )

        elif args.mode == "command":
            # argparse.REMAINDER includes the leading "--"; strip it.
            cmd = args.cmd
            if cmd and cmd[0] == "--":
                cmd = cmd[1:]
            if not cmd:
                print("[ERROR] No command specified. Use: poll_status.py command -- <your command>")
                return 2
            success = poll_command(
                cmd=cmd,
                host=args.host,
                timeout=args.timeout,
                interval=args.interval,
                backoff=args.backoff,
                max_interval=args.max_interval,
                quiet=args.quiet,
            )

        elif args.mode == "docker":
            success = poll_docker(
                container=args.container,
                desired_state=args.state,
                host=args.host,
                timeout=args.timeout,
                interval=args.interval,
                backoff=args.backoff,
                max_interval=args.max_interval,
                quiet=args.quiet,
            )

    except KeyboardInterrupt:
        print("\n[ERROR] Interrupted by user")
        return 2
    except Exception as exc:
        print(f"[ERROR] {exc}")
        return 2

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
