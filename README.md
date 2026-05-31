# FOSM-1 Ground Station

Modular Python/Flask-based ground station software for the FOSM-1 satellite communication system. Provides a web UI for commanding the satellite via UHF uplink and monitoring telemetry via RX frames in real-time.

## Architecture

### Components

```
pronto_gr16/
├── gnuradio/                    # GNU Radio flowgraph scripts
│   ├── full_TX_chain.py        # TX chain
│   ├── spino_rx_lf_setup_epy_block_5.py  # block for reception
│   ├── spino_rx_lf_setup.py    # RX chain: USRP → BPF → FSK demod → burst detection
│   └── tx_commands/             # Folder with all the possible commands to send

├── ihmv2/                       # Web application (Flask + SocketIO)
│   ├── app.py                   # Main Flask app routing + WebSocket handler
│   ├── config.py                # Centralized configuration (ZMQ URLs, paths, constants)
│   ├── utils.py                 # Utility functions (CRC, hex parsing, AX.25 callsign encoding)
│   ├── uplink.py                # TX command logic (frame building, socket management)
│   ├── downlink.py              # RX frame parsing & decoding (CRC validation, descrambling)
│   ├── static/
│   │   ├── css/style.css        # UI styling (dark theme, responsive layout)
│   │   └── js/script.js         # Frontend logic (SocketIO handlers, API calls)
│   └── templates/
│       └── index.html           # Single-page web UI (3-column layout)
├── requirements.txt             # Python dependencies
└── README.md                    # This file
```



For Docker, we have :

```
pronto_gr16/
├── gnuradio/                    # GNU Radio flowgraph scripts
│   ├── full_TX_chain.py        # TX chain
│   ├── spino_rx_lf_setup_epy_block_5.py  # block for reception
│   ├── spino_rx_lf_setup.py    # RX chain: USRP → BPF → FSK demod → burst detection
│   └── tx_commands/             # Folder with all the possible commands to send

├── ihmv2/                       # Web application (Flask + SocketIO)
│   ├── app.py                   # Main Flask app routing + WebSocket handler
│   ├── config.py                # Centralized configuration (ZMQ URLs, paths, constants)
│   ├── utils.py                 # Utility functions (CRC, hex parsing, AX.25 callsign encoding)
│   ├── uplink.py                # TX command logic (frame building, socket management)
│   ├── downlink.py              # RX frame parsing & decoding (CRC validation, descrambling)
│   ├── static/
│   │   ├── css/style.css        # UI styling (dark theme, responsive layout)
│   │   └── js/script.js         # Frontend logic (SocketIO handlers, API calls)
│   └── templates/
│       └── index.html           # Single-page web UI (3-column layout)
├── .gitignore                         # PGitignore file
├── Dockerfile                        #  Settings of the container
├── docker-compose.yml     # Enable the user to use the app within a container
├── launch_spino.py                   # Alternative to Docker, that start the app (if the user have everything)
├── requirements.txt             # Python dependencies
└── README.md                    # This file
```
## Features

### Uplink (TX Command)

- **Command Library**: Pre-built command files in `gnu_radio/tx_commands/`
- **Manual Command Entry**: Direct hex input or command name selection
- **Operator Validation**: Mandatory operator ID (callsign) for all transmissions
- **Frame Building**: AX.25-compatible frame with:
  - Preamble (16× 0xAA)
  - Sync word (0x2E 0xFC 0x98 0x27)
  - Shifted AX.25 header (dest/src callsigns, control, PID)
  - Payload length (LE)
  - CRC-16/XMODEM (BE)
  - Flag (16× 0xAA)
- **Persistent ZMQ Socket**: Single PUSH socket reused for all TX, preventing message loss
- **Logging**: Console output of all TX events with hex bytes

### Downlink (RX Telemetry)

- **Real-time Decoding**: Processes incoming frames via ZMQ from GNU Radio
- **CRC Validation**: Detects transmission errors
- **Dual Frame Format Support**:
  - SPINO format (with length field)
  - Beacon UI format (no length field)
- **Descrambling**: Optional payload descrambling for encoded messages
- **Statistics**: Live counters (received, CRC OK, rejected)
- **Frame History**: Expandable frame list with full details

### Web UI

- **3-Column Layout**:
  - **Left**: Command selection, operator ID input, single send button
  - **Center**: RX statistics, last frame details, frame history
  - **Right**: Recording control, console logs, event history
- **Dark Theme**: Optimized for operations center displays
- **Real-time Updates**: WebSocket-driven (Socket.IO)
- **Recording**: Save RX frames to disk for post-analysis

## Installation

### Prerequisites

- Python 3.8+
- GNU Radio 3.10+
- USRP hardware (compatible with UHD)

### Running With Docker

For now, the docker solution is not working. The project is still functionnal with the launch_spino.py.

First, you need to have Docker installed on your device

1. **Build and start the container:**
   ```bash
   docker compose up --build
   ```

2. **Open the web UI:**
   Go to `http://localhost:5000`.

3. **If you use a USRP in the container:**
   Keep `/dev/bus/usb` available to the container. If your setup needs stricter access, adjust the Compose device mapping or run the container with the privileges required by UHD on your host.

The container runs the Flask app directly and starts the GNU Radio flowgraphs headlessly. The web server listens on `0.0.0.0:5000` inside the container.


### Setup (if you don't use Docker or if it doesn't work)

1. **Install dependencies:**
   ```bash
   cd pronto_gr16
   pip install -r requirements.txt
   ```

2. **Copy helper modules:**
   Ensure these are in the project root or Python path:
   - `descambler.py` (bit descrambling for payloads)

3. **Prepare command files:**
   Command files should be in `gnuradio/tx_commands/` as `.txt` files with hex bytes (space or comma-separated).

### Running Locally

1. **Start GNU Radio RX flowgraph** (in a separate terminal):
   ```bash
   python gnuradio/spino_rx_lf_setup.py
   ```
   This will:
   - Open a GUI window with controls
   - Listen on USRP
   - Push telemetry to ZMQ 5555
   - Push FFT spectrum to ZMQ 5557
   - Listen for TX commands on ZMQ 8669

2. **Start Flask web server:**
   ```bash
   cd ihmv2
   python app.py
   ```
   Then open `http://localhost:5000` in your browser.

## API Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/` | Serve main UI |
| GET | `/api/uplink/commands` | List available command files |
| POST | `/api/uplink/send` | Send a command (requires `command_text` + `operator_callsign`) |
| GET | `/api/uplink/status` | Check TX link readiness |

## WebSocket Events

| Event | From | Payload | Purpose |
|-------|------|---------|---------|
| `new_telemetry` | Server | Decoded frame object | Broadcast RX frame to all clients |
| `uplink_status` | Server | TX confirmation | Notify command sent |
| `new_spectrum_data` | Server | FFT array | Push spectrum for visualization |
| `toggle_recording` | Client | `{status: bool}` | Enable/disable frame recording |
| `update_radio_param` | Client | `{param, val}` | Change GNU Radio parameter via XMLRPC |

## Configuration

Edit `ihmv2/config.py`:
- `ZMQ_RX_URL`: GNU Radio RX telemetry endpoint (default `tcp://127.0.0.1:5555`)
- `ZMQ_FFT_URL`: GNU Radio FFT spectrum endpoint (default `tcp://127.0.0.1:5557`)
- `ZMQ_TX_URL`: Uplink command endpoint (default `tcp://127.0.0.1:8669`)
- `UPLINK_COMMANDS_DIR`: Path to command files
- `UPLINK_DEFAULT_CALLSIGN`: Default operator callsign if none provided

## Development Notes

### Module Organization

- **config.py**: Centralized configuration (paths, ZMQ URLs, constants)
- **utils.py**: Reusable utilities (CRC, hex parsing, AX.25 encoding)
- **uplink.py**: TX-specific logic (frame building, persistent socket)
- **downlink.py**: RX-specific logic (frame parsing, descrambling)
- **app.py**: Flask routes, WebSocket handlers, startup

### Adding a New Command

1. Create a `.txt` file in `gnuradio/tx_commands/`:
   ```
   AA BB CC DD  # Space-separated hex bytes
   ```

2. Reload the UI (click "Refresh List")

3. Select the command from the dropdown or type its name

### Extending the UI

1. Edit `ihmv2/templates/index.html` for HTML structure
2. Edit `ihmv2/static/css/style.css` for styling
3. Edit `ihmv2/static/js/script.js` for client logic

There is also the same structure for the settings page (with html, css and javascript)

## Troubleshooting

| Issue | Solution |
|-------|----------|
| No commands appearing | Check `gnuradio/tx_commands/` path and file permissions |
| TX not working | Verify GNU Radio is running, check ZMQ port 8669 |
| RX frames not appearing | Ensure GNU Radio flowgraph is running, check ZMQ 5555 |
| "Operator ID is required" | Fill in the Operator ID field before sending |
| Web UI not loading | Check Flask is running on port 5000, check browser console for errors |
| Docker container cannot see the USRP | Make sure `/dev/bus/usb` is mounted into the container and UHD can access the device |

## License

GPL-3.0 (GNU Radio compatibility)

## Contributors

- Ground Station Team :
   - CRISTINAR Matei
   - GAILLARD Clément
   - GHARBI Mohamed Belhassen
   - MALAISE Tim
   - SAMRANI Mohamed Yazid

- Thomas Bouteraon (original GNU Radio flowgraph)
