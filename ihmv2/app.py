"""
app.py - FOSM-1 Ground Station Web Server
────────────────────────────────────────

Central Flask/SocketIO hub for FOSM-1 satellite ground chain.
Aggregates RX telemetry from GNU Radio and manages TX uplink commands.

Usage:
    python app.py
    Then open http://localhost:5000 in your browser
"""

import threading
import struct
import subprocess
import time
import sys
import xmlrpc.client
from datetime import datetime
from pathlib import Path
from flask import Flask, request, jsonify, render_template
from flask_socketio import SocketIO
from flask_cors import CORS
import zmq
import pmt

from config import (
    FLASK_HOST, FLASK_PORT, FLASK_DEBUG,
    FLASK_ALLOW_UNSAFE_WERKZEUG,
    ZMQ_RX_URL, ZMQ_FFT_URL, ZMQ_TX_URL,
    UPLINK_COMMANDS_DIR, UPLINK_DEFAULT_CALLSIGN,
    ALLOWED_PARAMS, XMLRPC_URL, zmq_context,
    TEMPLATES_DIR, STATIC_DIR,
)
from descambler import descrambler
from downlink import parse_spino_frame, zmq_listener_thread
from uplink import (
    get_available_uplink_commands,
    resolve_command_file,
    send_uplink_bytes,
    is_uplink_socket_open,
    close_uplink_socket,
)
from utils import (
    normalize_callsign,
    parse_hex_command,
    read_command_bytes_from_file,
    probe_tcp_port,
)


# ─────────────────────────────────────────────────────────────────────
# Flask & SocketIO Setup
# ─────────────────────────────────────────────────────────────────────

app = Flask(__name__, template_folder=str(TEMPLATES_DIR), static_folder=str(STATIC_DIR))
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")

# Remote control of GNU Radio via XMLRPC
try:
    sdr_rpc = xmlrpc.client.ServerProxy(XMLRPC_URL)
except Exception as e:
    print(f"[!] XMLRPC client setup failed: {e}")
    sdr_rpc = None

# Global state
recording_active = False
recording_lock = threading.Lock()
process_lock = threading.Lock()
rx_process = None
tx_process = None
RECORDING_FILE = Path(__file__).resolve().with_name("recording_hex.log")
GNURADIO_RX_SCRIPT = Path(__file__).resolve().parent.parent / "gnuradio" / "spino_rx_lf_setup.py"
GNURADIO_TX_SCRIPT = Path(__file__).resolve().parent.parent / "gnuradio" / "full_TX_chain.py"
FLOWGRAPH_SETTLE_DELAY = 0.1
TX_STARTUP_TIMEOUT = 6.0


def wait_for_process_ready(process: subprocess.Popen, timeout: float) -> None:
    """Wait until a child process is alive long enough to be considered ready."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError(f"Flowgraph exited early with code {process.returncode}")
        time.sleep(0.25)


def start_rx_flowgraph() -> None:
    """Start the GNU Radio RX flowgraph if it is not already running."""
    global rx_process

    with process_lock:
        if rx_process is not None and rx_process.poll() is None:
            return

        if not GNURADIO_RX_SCRIPT.exists():
            raise FileNotFoundError(f"RX flowgraph not found: {GNURADIO_RX_SCRIPT}")

        rx_process = subprocess.Popen(
            [sys.executable, str(GNURADIO_RX_SCRIPT)],
            cwd=str(GNURADIO_RX_SCRIPT.parent.parent),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            
        )


def stop_rx_flowgraph() -> None:
    """Stop the GNU Radio RX flowgraph if it is running."""
    global rx_process

    with process_lock:
        if rx_process is None:
            return
        if rx_process.poll() is None:
            rx_process.terminate()
            try:
                rx_process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                rx_process.kill()
        rx_process = None


def start_tx_flowgraph() -> None:
    """Start the GNU Radio TX flowgraph if it is not already running."""
    global tx_process

    with process_lock:
        if tx_process is not None and tx_process.poll() is None:
            return

        if not GNURADIO_TX_SCRIPT.exists():
            raise FileNotFoundError(f"TX flowgraph not found: {GNURADIO_TX_SCRIPT}")

        tx_process = subprocess.Popen(
            [sys.executable, str(GNURADIO_TX_SCRIPT)],
            cwd=str(GNURADIO_TX_SCRIPT.parent.parent),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )


def stop_tx_flowgraph() -> None:
    """Stop the GNU Radio TX flowgraph if it is running."""
    global tx_process

    close_uplink_socket()

    with process_lock:
        if tx_process is None:
            return
        if tx_process.poll() is None:
            tx_process.terminate()
            try:
                tx_process.wait(timeout=0.2)
            except subprocess.TimeoutExpired:
                tx_process.kill()
        tx_process = None


def run_tx_cycle(command_bytes: bytes, operator_callsign: str) -> dict:
    """Pause RX, launch TX, send one command, then restore RX."""
    stop_rx_flowgraph()
    try:
        time.sleep(FLOWGRAPH_SETTLE_DELAY)
        start_tx_flowgraph()
        wait_for_process_ready(tx_process, TX_STARTUP_TIMEOUT)
        time.sleep(FLOWGRAPH_SETTLE_DELAY)

        frame_len = send_uplink_bytes(command_bytes, operator_callsign)
        print(f"[TX] Sent frame of length {frame_len} bytes : {command_bytes.hex(' ').upper()}")
        # time.sleep(0.2)
        return {"frame_len": frame_len}
    finally:
        stop_tx_flowgraph()
        # time.sleep(0.1)
        start_rx_flowgraph()


def append_recording_entry(raw_hex: str) -> None:
    """Log raw frame to recording file."""
    if not recording_active:
        return
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] {raw_hex}\n"
    with recording_lock:
        with RECORDING_FILE.open("a", encoding="utf-8") as f:
            f.write(line)


# ─────────────────────────────────────────────────────────────────────
# HTTP Routes
# ─────────────────────────────────────────────────────────────────────

@app.route('/')
def index():
    """Serve main ground station UI."""
    return render_template('index.html')

@app.route('/settings')
def settings():
    """Serve the settings panel UI."""
    return render_template('settings.html')


@app.route('/api/uplink/commands', methods=['GET'])
def uplink_commands():
    """List available command files."""
    commands = get_available_uplink_commands()
    return jsonify({
        'commands': commands,
        'commands_dir': str(UPLINK_COMMANDS_DIR),
    })


@app.route('/api/uplink/send', methods=['POST'])
def uplink_send():
    """Send a command via uplink (TX)."""
    data = request.get_json(silent=True) or {}

    command_name = (data.get('command_name') or '').strip()
    command_text = (data.get('command_text') or '').strip()
    raw_operator = (data.get('operator_callsign') or data.get('license') or '').strip()

    if not raw_operator:
        return jsonify({'ok': False, 'error': 'Operator identifier is required'}), 400

    operator_callsign = normalize_callsign(raw_operator, UPLINK_DEFAULT_CALLSIGN)

    if not command_name and not command_text:
        return jsonify({'ok': False, 'error': 'Provide command_name or command_text'}), 400

    try:
        source = ''
        used_name = ''

        if command_name:
            file_path = resolve_command_file(command_name)
            if not file_path:
                return jsonify({'ok': False, 'error': f'Unknown command file: {command_name}'}), 404
            command_bytes = read_command_bytes_from_file(file_path)
            source = 'command_file'
            used_name = file_path.name
        else:
            file_path = resolve_command_file(command_text)
            if file_path:
                command_bytes = read_command_bytes_from_file(file_path)
                source = 'command_file'
                used_name = file_path.name
            else:
                command_bytes = parse_hex_command(command_text)
                source = 'manual_hex'
                used_name = 'manual'

        print(
            f"[TX] operator={operator_callsign} source={source} command={used_name} "
            f"hex={command_bytes.hex(' ').upper()}"
        )
        tx_result = run_tx_cycle(command_bytes, operator_callsign)
        frame_len = tx_result['frame_len']
        socketio.emit('uplink_status', {
            'ok': True,
            'source': source,
            'command': used_name,
            'operator_callsign': operator_callsign,
            'frame_len': frame_len,
            'timestamp': datetime.now().strftime('%H:%M:%S'),
        })

        return jsonify({
            'ok': True,
            'source': source,
            'command': used_name,
            'operator_callsign': operator_callsign,
            'frame_len': frame_len,
            'bytes_len': len(command_bytes),
        })

    except ValueError as exc:
        return jsonify({'ok': False, 'error': str(exc)}), 400
    except Exception as exc:
        print(f"[UPLINK ERR] {exc}")
        return jsonify({'ok': False, 'error': 'Failed to send uplink command'}), 500


@app.route('/api/uplink/status', methods=['GET'])
def uplink_status_endpoint():
    """Check if uplink TX link is ready."""
    host = "127.0.0.1"
    port_text = ZMQ_TX_URL.rsplit(':', 1)[-1]
    try:
        port = int(port_text)
    except ValueError:
        port = 8669

    tx_ready = probe_tcp_port(host, port)
    return jsonify({
        'ok': True,
        'tx_ready': tx_ready,
        'socket_open': is_uplink_socket_open(),
        'tx_host': host,
        'tx_port': port,
        'commands_dir': str(UPLINK_COMMANDS_DIR),
    })


@app.route('/send_command', methods=['POST'])
def send_command_legacy():
    """Legacy endpoint for backward compatibility."""
    data = request.get_json(silent=True) or {}
    mapped_payload = {
        'command_text': data.get('text', ''),
        'operator_callsign': data.get('license', ''),
    }
    with app.test_request_context(json=mapped_payload):
        return uplink_send()


# ─────────────────────────────────────────────────────────────────────
# WebSocket Events
# ─────────────────────────────────────────────────────────────────────

@socketio.on('toggle_recording')
def toggle_recording(data):
    """Enable/disable RX frame recording."""
    global recording_active
    if not isinstance(data, dict):
        data = {}
    recording_active = data.get('active', data.get('status', False))
    print(f"Recording {'enabled' if recording_active else 'disabled'}")


@socketio.on('update_radio_param')
def handle_radio_param(data):
    """Update GNU Radio parameters via XMLRPC."""
    if not sdr_rpc:
        print("[!] XMLRPC not available")
        return

    param = data.get('param', '')
    try:
        value = float(data.get('val', 0))
    except (ValueError, TypeError):
        print(f"[-] Invalid parameter value: {data.get('val')}")
        return

    if param not in ALLOWED_PARAMS:
        print(f"[?] Unauthorized parameter: {param}")
        return

    try:
        setter_method = getattr(sdr_rpc, f"set_{param}")
        setter_method(value)
        print(f"[+] Updated GNU Radio: {param} = {value}")
    except Exception as e:
        print(f"[-] XMLRPC error for {param}: {e}")


# ─────────────────────────────────────────────────────────────────────
# Background Threads
# ─────────────────────────────────────────────────────────────────────

def spectrum_listener():
    """Background thread for FFT spectrum from GNU Radio."""
    ctx = zmq.Context()
    fft_socket = ctx.socket(zmq.SUB)
    fft_socket.connect(ZMQ_FFT_URL)
    fft_socket.setsockopt_string(zmq.SUBSCRIBE, "")
    fft_socket.setsockopt(zmq.CONFLATE, 1)
    fft_socket.setsockopt(zmq.RCVHWM, 1)

    print(f"[ZMQ FFT] Listening on {ZMQ_FFT_URL}")

    while True:
        try:
            raw_data = fft_socket.recv()

            while True:
                try:
                    raw_data = fft_socket.recv(flags=zmq.NOBLOCK)
                except zmq.Again:
                    break

            num_floats = len(raw_data) // 4
            spectrum_tuple = struct.unpack(f"<{num_floats}f", raw_data)
            socketio.emit('new_spectrum_data', {'spectrum': list(spectrum_tuple)})
            socketio.sleep(0)
        except Exception as e:
            print(f"[FFT ERR] {e}")
            socketio.sleep(1)


# ─────────────────────────────────────────────────────────────────────
# Startup
# ─────────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    start_rx_flowgraph()

    # Start background listener threads
    threading.Thread(
        target=zmq_listener_thread,
        args=(socketio, append_recording_entry, ZMQ_RX_URL, pmt),
        daemon=True
    ).start()

    threading.Thread(target=spectrum_listener, daemon=True).start()

    print(f"\n{'='*60}")
    print(f"  FOSM-1 Ground Station Ready")
    print(f"  Web UI: http://{FLASK_HOST}:{FLASK_PORT}")
    print(f"{'='*60}\n")

    socketio.run(
        app,
        debug=FLASK_DEBUG,
        host=FLASK_HOST,
        port=FLASK_PORT,
        use_reloader=False,
        allow_unsafe_werkzeug=FLASK_ALLOW_UNSAFE_WERKZEUG,
    )
