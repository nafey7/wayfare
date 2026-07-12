#!/usr/bin/env python
"""Run the FastAPI application using the root .venv environment."""

import atexit
import os
import platform
import signal
import subprocess
import sys
from typing import Any

import uvicorn

from app.core.config import settings


def setup_windows_environment() -> None:
    """Configure environment variables for Windows to improve output."""
    if sys.platform == "win32":
        os.environ["NO_COLOR"] = "1"  # Disable ANSI colors
        os.environ["PYTHON_UNBUFFERED"] = "1"  # Unbuffered output for real-time logs


def get_uvicorn_log_config() -> dict[str, Any]:
    """
    Get custom logging configuration for Uvicorn to match backend format.
    Applies consistent formatting across all log messages.

    Returns:
        Custom log config that matches backend logging format
    """
    # Custom logging config that matches our backend format
    return {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "default": {
                "format": "[UVICORN ] %(levelname)-8s | %(filename)-20s:%(lineno)-4d | %(name)-25s | %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S",
            },
            "access": {
                "format": "[ACCESS ] %(levelname)-8s | %(filename)-20s:%(lineno)-4d | %(name)-25s | %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S",
            },
        },
        "handlers": {
            "default": {
                "formatter": "default",
                "class": "logging.StreamHandler",
                "stream": "ext://sys.stdout",
            },
            "access": {
                "formatter": "access",
                "class": "logging.StreamHandler",
                "stream": "ext://sys.stdout",
            },
        },
        "loggers": {
            "uvicorn": {"handlers": ["default"], "level": "INFO", "propagate": False},
            "uvicorn.error": {
                "handlers": ["default"],
                "level": "INFO",
                "propagate": False,
            },
            "uvicorn.access": {
                "handlers": ["access"],
                "level": "INFO",
                "propagate": False,
            },
        },
    }


def cleanup_on_exit() -> None:
    """Clean up resources when the application exits."""
    print("\n>>> Shutting down server...")
    # Uvicorn automatically closes the port when it shuts down
    # This is just for any additional cleanup if needed
    print(">>> Server stopped. Port released.")


def handle_shutdown_signal(_signum: int, _frame: Any) -> None:
    """Handle shutdown signals (Ctrl+C, etc.)."""
    cleanup_on_exit()
    sys.exit(0)


def kill_uvicorn_processes() -> None:
    """Kill only uvicorn/backend processes on port 8000."""
    print(">>> Killing existing backend processes on port 8000...")

    current_pid = os.getpid()
    killed_count = 0

    # Only kill processes on port 8000
    try:
        # Find processes using port 8000 - cross-platform
        if platform.system() == "Windows":
            result = subprocess.run(
                "netstat -ano | findstr :8000",
                shell=True,
                capture_output=True,
                text=True,
                check=False,
            )
        else:
            # Unix/Linux/macOS - use lsof
            result = subprocess.run(
                ["lsof", "-i", ":8000", "-t"],
                capture_output=True,
                text=True,
                check=False,
            )

        if result.stdout:
            pids_to_kill = set()

            if platform.system() == "Windows":
                # Parse Windows netstat output
                lines = result.stdout.strip().split("\n")
                for line in lines:
                    if "LISTENING" in line or "ESTABLISHED" in line:
                        parts = line.split()
                        if parts:
                            pid = parts[-1]
                            if pid.isdigit() and pid != "0" and int(pid) != current_pid:
                                pids_to_kill.add(pid)
            else:
                # Parse Unix lsof output (PIDs only, one per line)
                for pid in result.stdout.strip().split("\n"):
                    pid = pid.strip()
                    if pid.isdigit() and pid != "0" and int(pid) != current_pid:
                        pids_to_kill.add(pid)

            for pid in pids_to_kill:
                try:
                    # Get process name cross-platform
                    process_name = "Unknown"
                    try:
                        if platform.system() == "Windows":
                            name_result = subprocess.run(
                                [
                                    "tasklist",
                                    "/FI",
                                    f"PID eq {pid}",
                                    "/FO",
                                    "CSV",
                                    "/NH",
                                ],
                                capture_output=True,
                                text=True,
                                check=False,
                            )
                            if name_result.stdout:
                                # Parse CSV output: "process_name.exe","PID","Session Name","Session#","Mem Usage"
                                csv_line = name_result.stdout.strip().split('","')
                                if csv_line and len(csv_line) > 0:
                                    process_name = csv_line[0].strip('"')
                        else:
                            # Unix/Linux/macOS
                            name_result = subprocess.run(
                                ["ps", "-p", pid, "-o", "comm="],
                                capture_output=True,
                                text=True,
                                check=False,
                            )
                            if name_result.stdout:
                                process_name = name_result.stdout.strip()
                    except Exception:
                        process_name = "Unknown"

                    # Kill the process (but never kill ourselves!)
                    if int(pid) != current_pid:
                        try:
                            os.kill(int(pid), signal.SIGTERM)
                            print(
                                f"  [✓] Killed {process_name} on port 8000 (PID: {pid})"
                            )
                            killed_count += 1
                        except (ProcessLookupError, PermissionError) as e:
                            print(
                                f"  [WARN] Could not kill {process_name} (PID: {pid}): {e}"
                            )
                    else:
                        print(f"  [SKIP] Not killing ourselves (PID: {pid})")
                except Exception:
                    pass

    except Exception as e:
        print(f"[WARN] Could not check port 8000: {e}")

    if killed_count > 0:
        print(f"[OK] Killed {killed_count} processes on port 8000")
        # Give processes time to fully terminate
        import time

        time.sleep(1)
    else:
        print("[INFO] Port 8000 is already free")

    print()


def kill_ports() -> None:
    """Kill processes on common development ports before starting."""
    ports_to_check = [3000, 3001, 5000, 5001, 8000, 8080, 8081]

    print(">>> Checking and killing processes on development ports...")

    for port in ports_to_check:
        try:
            # Find processes using the port - cross-platform
            if platform.system() == "Windows":
                result = subprocess.run(
                    f"netstat -ano | findstr :{port}",
                    shell=True,
                    capture_output=True,
                    text=True,
                    check=False,
                )
            else:
                # Unix/Linux/macOS - use lsof
                result = subprocess.run(
                    ["lsof", "-i", f":{port}", "-t"],
                    capture_output=True,
                    text=True,
                    check=False,
                )

            if result.stdout:
                pids = set()

                if platform.system() == "Windows":
                    # Parse Windows netstat output
                    lines = result.stdout.strip().split("\n")
                    for line in lines:
                        if "LISTENING" in line:
                            parts = line.split()
                            if parts:
                                pid = parts[-1]
                                if pid.isdigit() and pid != "0":
                                    pids.add(pid)
                else:
                    # Parse Unix lsof output (PIDs only, one per line)
                    for pid in result.stdout.strip().split("\n"):
                        pid = pid.strip()
                        if pid.isdigit() and pid != "0":
                            pids.add(pid)

                # Kill each unique PID
                for pid in pids:
                    try:
                        os.kill(int(pid), signal.SIGTERM)
                        print(f"[OK] Killed process {pid} on port {port}")
                    except (ProcessLookupError, PermissionError, ValueError) as e:
                        # ProcessLookupError: Process doesn't exist
                        # PermissionError: Insufficient permissions
                        # ValueError: Invalid PID format
                        print(
                            f"[WARN] Could not kill process {pid} on port {port}: {e}"
                        )
            else:
                print(f"[INFO] Port {port} is free")

        except (subprocess.SubprocessError, OSError, ValueError) as e:
            # SubprocessError: Issue running netstat command
            # OSError: System-level error accessing network info
            # ValueError: Issue parsing port or PID data
            print(f"[WARN] Error checking port {port}: {e}")

    print(">>> All ports cleared!")


def run_server() -> None:
    """Start the FastAPI server with appropriate configuration."""
    # Kill existing processes on development ports first (cross-platform)
    kill_ports()

    # Register cleanup handlers
    atexit.register(cleanup_on_exit)
    signal.signal(signal.SIGINT, handle_shutdown_signal)
    signal.signal(signal.SIGTERM, handle_shutdown_signal)

    try:
        uvicorn.run(
            "app.main:app",
            host=settings.HOST,
            port=settings.PORT,
            reload=settings.DEBUG,
            log_level=settings.LOG_LEVEL.lower(),
            access_log=settings.DEBUG,
            use_colors=False if sys.platform == "win32" else None,
            log_config=get_uvicorn_log_config(),
        )
    except KeyboardInterrupt:
        cleanup_on_exit()
    except (OSError, RuntimeError) as e:
        # OSError: Network/socket related errors
        # RuntimeError: Uvicorn runtime issues
        print(f">>> Error: {e}")
        cleanup_on_exit()
        raise


# Setup environment before imports that might use it
setup_windows_environment()

if __name__ == "__main__":
    run_server()
