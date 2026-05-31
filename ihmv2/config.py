"""
config.py - Configuration centralisée pour FOSM-1 Ground Station
"""

import os
from pathlib import Path
import zmq


def _env_bool(name: str, default: bool = False) -> bool:
	value = os.getenv(name)
	if value is None:
		return default
	return value.strip().lower() in {"1", "true", "yes", "on"}

# Paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent
TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"
STATIC_DIR = Path(__file__).resolve().parent / "static"
RECORDING_FILE = Path(__file__).resolve().with_name("recording_hex.log")

# ZMQ Configuration
ZMQ_RX_URL = "tcp://127.0.0.1:5555"      # GNU Radio RX telemetry
ZMQ_FFT_URL = "tcp://127.0.0.1:5557"     # GNU Radio FFT spectrum
ZMQ_TX_URL = "tcp://127.0.0.1:8669"      # Uplink TX commands

# Uplink (TX) Configuration
UPLINK_COMMANDS_DIR = PROJECT_ROOT / "gnuradio" / "tx_commands"
UPLINK_SEND_REPEAT = 5
UPLINK_DEFAULT_CALLSIGN = "F4AKAG"

# XML-RPC Configuration
XMLRPC_URL = "http://127.0.0.1:8080"

# Security & Validation
ALLOWED_PARAMS = ['freq_MHz', 'gain_dB', 'seuil', 'rbw_num', 'freq_num']

# Web Server
FLASK_HOST = os.getenv("FOSM_FLASK_HOST", "127.0.0.1")
FLASK_PORT = int(os.getenv("FOSM_FLASK_PORT", "5000"))
FLASK_DEBUG = _env_bool("FOSM_FLASK_DEBUG", False)
FLASK_ALLOW_UNSAFE_WERKZEUG = _env_bool("FOSM_ALLOW_UNSAFE_WERKZEUG", False)

# ZMQ Context (singleton)
zmq_context = zmq.Context.instance()
