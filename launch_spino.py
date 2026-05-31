#!/usr/bin/env python3
"""
launch_spino.py - Orchestrate FOSM-1 ground station startup

Starts the Flask web server, which now manages the RX/TX GNU Radio
flowgraphs on demand, then opens browser.
Graceful shutdown on Ctrl+C closes the web server cleanly.
"""

import subprocess
import time
import signal
import sys
import webbrowser
from pathlib import Path

# ───────────────────────────────────────────────────────────────────
# Configuration
# ───────────────────────────────────────────────────────────────────

PROJECT_ROOT = Path(__file__).resolve().parent
FLASK_APP = PROJECT_ROOT / "ihmv2" / "app.py"

# Flask Web Server
FLASK_HOST = "127.0.0.1"
FLASK_PORT = 5000
FLASK_URL = f"http://{FLASK_HOST}:{FLASK_PORT}"

# GNU Radio startup timeouts
FLASK_STARTUP_TIMEOUT = 3  # seconds to wait for Flask server to start


# ───────────────────────────────────────────────────────────────────
# Process Management
# ───────────────────────────────────────────────────────────────────

flask_process = None


def cleanup(signum=None, frame=None):
    """Graceful shutdown of both processes."""
    print("\n[*] Shutting down...")

    if flask_process and flask_process.poll() is None:
        print("[*] Stopping Flask...")
        flask_process.terminate()
        try:
            flask_process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            flask_process.kill()

    print("[*] Goodbye!")
    sys.exit(0)


signal.signal(signal.SIGINT, cleanup)
signal.signal(signal.SIGTERM, cleanup)


# ───────────────────────────────────────────────────────────────────
# Startup
# ───────────────────────────────────────────────────────────────────

def main():
    global flask_process

    print("""
╔════════════════════════════════════════════════════════════════════╗
║           FOSM-1 Ground Station Launcher                          ║
║                                                                    ║
║  Starting Flask web server...                                     ║
╚════════════════════════════════════════════════════════════════════╝
    """)

    # ── Step 1: Start Flask Web Server ──────────────────────────────
    print(f"[1/2] Starting Flask web server...")
    print(f"      App: {FLASK_APP}")

    if not FLASK_APP.exists():
        print(f"[!] Error: Flask app not found: {FLASK_APP}")
        cleanup()
        sys.exit(1)

    try:
        flask_process = subprocess.Popen(
            [sys.executable, str(FLASK_APP)],
            cwd=str(PROJECT_ROOT / "ihmv2"),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        print(f"      Process ID: {flask_process.pid}")
        print(f"      Waiting {FLASK_STARTUP_TIMEOUT}s for server to start...")
        time.sleep(FLASK_STARTUP_TIMEOUT)

        if flask_process.poll() is not None:
            stdout, stderr = flask_process.communicate()
            print(f"[!] Flask exited unexpectedly:")
            print(f"    stdout: {stdout}")
            print(f"    stderr: {stderr}")
            cleanup()
            sys.exit(1)

        print("      ✓ Flask running")

    except Exception as e:
        print(f"[!] Failed to start Flask: {e}")
        cleanup()
        sys.exit(1)

    # ── Step 2: Open Browser ────────────────────────────────────────
    print(f"\n[2/2] Opening web browser...")
    try:
        webbrowser.open(FLASK_URL)
        print(f"      ✓ Browser opened: {FLASK_URL}")
    except Exception as e:
        print(f"[!] Failed to open browser: {e}")
        print(f"      Manually visit: {FLASK_URL}")

    # ── Monitor Processes ───────────────────────────────────────────
    print(f"""
╔════════════════════════════════════════════════════════════════════╗
║                   FOSM-1 READY                                    ║
║                                                                    ║
║  Web UI:        {FLASK_URL}
║  GNU Radio RX/TX: Managed by Flask on demand                      ║
║                                                                    ║
║  Press Ctrl+C to stop all services                                ║
╚════════════════════════════════════════════════════════════════════╝
    """)

    try:
        while True:
            # Check if either process died
            # gnuradio_status = gnuradio_process.poll()
            flask_status = flask_process.poll()

            # if gnuradio_status is not None:
            #     print(f"[!] GNU Radio exited with code {gnuradio_status}")
            #     cleanup()
            #     sys.exit(1)

            if flask_status is not None:
                print(f"[!] Flask exited with code {flask_status}")
                cleanup()
                sys.exit(1)

            time.sleep(1)

    except KeyboardInterrupt:
        cleanup()


if __name__ == '__main__':
    main()
