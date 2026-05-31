/**
 * script.js - FOSM-1 Ground Station UI Logic
 */

// Socket.IO
const socket = io();
let isRecording = false;

// ─────────────────────────────────────────────────────────────────
// Clock & Time Display
// ─────────────────────────────────────────────────────────────────

function updateClock() {
  document.getElementById('clock').textContent =
    new Date().toLocaleTimeString('en-GB', { hour12: false });
}
setInterval(updateClock, 1000);
updateClock();


// ─────────────────────────────────────────────────────────────────
// Statistics Counters
// ─────────────────────────────────────────────────────────────────

let cntTotal = 0, cntOk = 0, cntErr = 0;

function updateStats(crcOk) {
  cntTotal++;
  if (crcOk === true)       cntOk++;
  else if (crcOk === false) cntErr++;
  document.getElementById('cntTotal').textContent = cntTotal;
  document.getElementById('cntOk').textContent    = cntOk;
  document.getElementById('cntErr').textContent   = cntErr;
}


// ─────────────────────────────────────────────────────────────────
// RX Telemetry Handler
// ─────────────────────────────────────────────────────────────────

socket.on('new_telemetry', (f) => {
  updateStats(f.crc_ok);

  // Raw frame
  document.getElementById('rawHex').textContent = f.raw || '—';

  // Decoded fields
  document.getElementById('fDest').textContent = f.dest || '—';
  document.getElementById('fSrc').textContent  = f.src  || '—';
  document.getElementById('fCtrl').textContent = f.ctrl || '—';
  document.getElementById('fPid').textContent  = f.pid  || '—';

  // Type badge
  const typeEl = document.getElementById('fType');
  if (f.type === 'beacon') {
    typeEl.innerHTML = '<span class="type-badge beacon">BEACON UI</span>';
  } else {
    typeEl.innerHTML = '<span class="type-badge spino">SPINO TM</span>';
  }

  // CRC badge
  const crcEl = document.getElementById('fCrc');
  if (f.crc_ok === null) {
    crcEl.innerHTML = `<span class="crc-badge na">N/A</span>`;
  } else if (f.crc_ok) {
    crcEl.innerHTML = `<span class="crc-badge ok">✓ ${f.crc}</span>`;
  } else {
    crcEl.innerHTML = `<span class="crc-badge err">✗ ${f.crc}</span>`;
  }

  // Length: hidden for beacons
  const lenCard = document.getElementById('lenCard');
  if (f.length !== null && f.length !== undefined) {
    lenCard.style.display = '';
    document.getElementById('fLen').textContent = `${f.length} bytes`;
  } else {
    lenCard.style.display = 'none';
  }

  // Payload hex
  document.getElementById('fPayload').textContent = f.payload || '—';

  // Payload ASCII (if available)
  const asciiCard = document.getElementById('asciiCard');
  if (f.payload_ascii && f.payload_ascii.trim()) {
    asciiCard.style.display = '';
    document.getElementById('fAscii').textContent = f.payload_ascii;
  } else {
    asciiCard.style.display = 'none';
  }

  // Descrambled Payload hex
  document.getElementById('fDescrambledPayload').textContent = f.descrambled_payload || '—';

  // Descrambled Payload ASCII (if available)
  const descrambledAsciiCard = document.getElementById('descrambledAsciiCard');
  if (f.descrambled_payload_ascii && f.descrambled_payload_ascii.trim()) {
    descrambledAsciiCard.style.display = '';
    document.getElementById('fDescrambledAscii').textContent = f.descrambled_payload_ascii;
  } else {
    descrambledAsciiCard.style.display = 'none';
  }

  // Add to history
  addFrameHistory(f);

  // Log console
  const crcStr = f.crc_ok === null ? '' : (f.crc_ok ? ' ✓' : ' ✗ CRC ERR');
  addLog(`[${f.timestamp}] ${f.src} → ${f.dest} | ${f.type}${crcStr}`,
         f.crc_ok === false ? 'err' : 'ok');
});


// ─────────────────────────────────────────────────────────────────
// Frame History Management
// ─────────────────────────────────────────────────────────────────

let frameCount = 0;

function addFrameHistory(f) {
  frameCount++;
  const history = document.getElementById('frameHistory');

  const entry = document.createElement('div');
  entry.className = 'frame-entry';
  const id = `fe-${frameCount}`;

  const crcBadge = f.crc_ok === null
    ? '<span class="crc-badge na">N/A</span>'
    : f.crc_ok
      ? `<span class="crc-badge ok">✓</span>`
      : `<span class="crc-badge err">✗</span>`;

  // One-line summary
  let summary = `${f.src} → ${f.dest}`;
  if (f.payload_ascii && f.payload_ascii.trim()) {
    summary += ` | "${f.payload_ascii.trim().substring(0, 30)}"`;
  } else if (f.length !== null && f.length !== undefined) {
    summary += ` | ${f.length}o`;
  }

  entry.innerHTML = `
    <div class="frame-entry-header" onclick="toggleFrame('${id}')">
      <span class="frame-entry-ts">${f.timestamp}</span>
      ${crcBadge}
      <span class="type-badge ${f.type === 'beacon' ? 'beacon' : 'spino'}">${f.type === 'beacon' ? 'BCN' : 'TM'}</span>
      <span class="frame-entry-summary">${summary}</span>
      <span class="frame-entry-chevron">▶</span>
    </div>
    <div class="frame-entry-body" id="${id}">
      <div class="decoded-grid" style="margin-bottom:8px">
        <div class="field-card">
          <div class="fc-label">Destination</div>
          <div class="fc-value blue">${f.dest}</div>
        </div>
        <div class="field-card">
          <div class="fc-label">Sender</div>
          <div class="fc-value green">${f.src}</div>
        </div>
        <div class="field-card">
          <div class="fc-label">Ctrl/PID</div>
          <div class="fc-value">${f.ctrl} / ${f.pid}</div>
        </div>
        ${f.length !== null && f.length !== undefined
          ? `<div class="field-card"><div class="fc-label">Length</div><div class="fc-value amber">${f.length} bytes</div></div>`
          : ''}
        <div class="field-card full">
          <div class="fc-label">Raw HEX</div>
          <div class="fc-value" style="font-size:0.6rem;line-height:1.6;color:var(--text2)">${f.raw}</div>
        </div>
        <div class="field-card full">
          <div class="fc-label">Payload HEX</div>
          <div class="fc-value" style="font-size:0.65rem;line-height:1.6">${f.payload || '—'}</div>
        </div>
        ${f.payload_ascii && f.payload_ascii.trim()
          ? `<div class="field-card full"><div class="fc-label">ASCII Message</div><div class="ascii-block">${escHtml(f.payload_ascii)}</div></div>`
          : ''}
        
        ${f.descrambled_payload_ascii && f.descrambled_payload_ascii.trim()
          ? `<div class="field-card full"><div class="fc-label">Descrambled ASCII</div><div class="ascii-block">${escHtml(f.descrambled_payload_ascii)}</div></div>`
          : ''}
      </div>
    </div>`;

  history.prepend(entry);

  // Keep max 50 frames in history
  while (history.children.length > 50) {
    history.removeChild(history.lastChild);
  }
}

function toggleFrame(id) {
  const body   = document.getElementById(id);
  const entry  = body.parentElement;
  entry.classList.toggle('open');
}

function escHtml(s) {
  return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}


// ─────────────────────────────────────────────────────────────────
// Console Logging
// ─────────────────────────────────────────────────────────────────

function addLog(msg, type = 'info') {
  const container = document.getElementById('log-container');
  const el = document.createElement('div');
  el.className = 'log-entry';
  const ts = new Date().toLocaleTimeString('en-GB', { hour12: false });
  el.innerHTML = `<span class="log-ts">[${ts}]</span> <span class="log-${type}">${escHtml(msg)}</span>`;
  container.prepend(el);
  if (container.childNodes.length > 100) container.removeChild(container.lastChild);
}

function clearLogs() {
  document.getElementById('log-container').innerHTML = '';
}


// ─────────────────────────────────────────────────────────────────
// Recording Control
// ─────────────────────────────────────────────────────────────────

function toggleRecording() {
  const btn = document.getElementById('recordBtn');
  const isRecordingNow = btn.textContent === 'Start recording';
  if (isRecordingNow) {
    btn.textContent = 'Stop recording';
    btn.className   = 'btn btn-stop';
    addLog('Recording started', 'ok');
  } else {
    btn.textContent = 'Start recording';
    btn.className   = 'btn btn-green';
    addLog('Recording stopped', 'info');
  }
  socket.emit('toggle_recording', { status: isRecordingNow });
}


// ─────────────────────────────────────────────────────────────────
// Uplink (TX) Controls
// ─────────────────────────────────────────────────────────────────

const licenseInput = document.getElementById('licenseInput');
const commandInput = document.getElementById('commandInput');
const commandList  = document.getElementById('uplinkCommandList');
const uplinkStatus = document.getElementById('uplinkStatus');
const sendBtn = document.getElementById('sendBtn');
const sendProgress = document.getElementById('sendProgress');
const sendProgressLabel = document.getElementById('sendProgressLabel');
const sendProgressBar = document.getElementById('sendProgressBar');

let isSendingUplink = false;
let sendProgressTimer = null;
let sendProgressValue = 0;

function setUplinkStatus(message, type = 'info') {
  uplinkStatus.textContent = message;
  uplinkStatus.className = `uplink-status ${type === 'ok' ? 'ok' : type === 'err' ? 'err' : ''}`;
}

function getOperatorId() {
  return (licenseInput.value || '').trim();
}

function refreshSendButtonState() {
  sendBtn.disabled = isSendingUplink || getOperatorId().length === 0;
}

function startSendProgress(message = 'Sending command...') {
  if (sendProgressTimer) {
    clearInterval(sendProgressTimer);
  }
  sendProgressValue = 8;
  sendProgress.classList.add('visible');
  sendProgressLabel.textContent = message;
  sendProgressBar.style.width = `${sendProgressValue}%`;

  sendProgressTimer = setInterval(() => {
    sendProgressValue = Math.min(sendProgressValue + 6, 92);
    sendProgressBar.style.width = `${sendProgressValue}%`;
  }, 250);
}

function stopSendProgress(success = true, message = '') {
  if (sendProgressTimer) {
    clearInterval(sendProgressTimer);
    sendProgressTimer = null;
  }

  sendProgressBar.style.width = '100%';
  sendProgressLabel.textContent = message || (success ? 'Command sent' : 'Send failed');

  setTimeout(() => {
    sendProgress.classList.remove('visible');
    sendProgressBar.style.width = '0%';
  }, 500);
}

function setSendingUplink(active) {
  isSendingUplink = active;
  sendBtn.textContent = active ? 'Sending...' : 'Send Command';
  refreshSendButtonState();
}

licenseInput.addEventListener('input', () => {
  const val = getOperatorId();
  licenseInput.className = val.length ? 'valid' : '';
  refreshSendButtonState();
});

async function loadUplinkCommands() {
  try {
    const response = await fetch('/api/uplink/commands');
    const payload = await response.json();

    commandList.innerHTML = '';
    const commands = payload.commands || [];

    if (!commands.length) {
      setUplinkStatus('No command file found in best_tx_chain/new_commands', 'err');
      return;
    }

    for (const commandName of commands) {
      const option = document.createElement('option');
      option.value = commandName;
      option.textContent = commandName;
      commandList.appendChild(option);
    }

    commandList.selectedIndex = 0;
    commandInput.value = commandList.value.replace(/\.txt$/i, '');
    setUplinkStatus(`${commands.length} command files loaded`, 'ok');
  } catch (error) {
    setUplinkStatus('Unable to load uplink command list', 'err');
    addLog(`Uplink list error: ${error}`, 'err');
  }
}

async function sendTextToPython() {
  if (isSendingUplink) {
    return;
  }

  const commandText = commandInput.value.trim();
  const operatorCallsign = getOperatorId();

  if (!operatorCallsign) {
    setUplinkStatus('Operator ID is required before sending', 'err');
    refreshSendButtonState();
    return;
  }

  if (!commandText) {
    setUplinkStatus('Type a command name or HEX bytes', 'err');
    return;
  }

  try {
    setSendingUplink(true);
    startSendProgress('Sending command...');

    const response = await fetch('/api/uplink/send', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        command_text: commandText,
        operator_callsign: operatorCallsign
      })
    });
    const result = await response.json();

    if (!response.ok || !result.ok) {
      const err = result.error || 'Send failed';
      setUplinkStatus(err, 'err');
      addLog(`Manual uplink error: ${err}`, 'err');
      stopSendProgress(false, 'Send failed');
      return;
    }

    setUplinkStatus(`Manual command sent as ${result.operator_callsign}`, 'ok');
    addLog(`Manual uplink sent: ${commandText} (${result.operator_callsign})`, 'ok');
    stopSendProgress(true, 'Command sent');
    commandInput.value = '';
  } catch (error) {
    setUplinkStatus('Network error while sending manual command', 'err');
    addLog(`Manual uplink send error: ${error}`, 'err');
    stopSendProgress(false, 'Network error');
  } finally {
    setSendingUplink(false);
  }
}

commandList.addEventListener('change', () => {
  commandInput.value = commandList.value.replace(/\.txt$/i, '');
  setUplinkStatus(`Selected ${commandInput.value}`, 'ok');
});

async function refreshUplinkStatus() {
  try {
    const response = await fetch('/api/uplink/status');
    const status = await response.json();
    if (status.tx_ready) {
      setUplinkStatus(`TX link ready on ${status.tx_host}:${status.tx_port}`, 'ok');
    } else {
      setUplinkStatus(`TX link not ready on ${status.tx_host}:${status.tx_port}`, 'err');
    }
  } catch (error) {
    setUplinkStatus('Unable to check TX link status', 'err');
  }
}

socket.on('uplink_status', (status) => {
  if (status && status.ok) {
    addLog(`TX frame sent (${status.command}, ${status.frame_len} bytes)`, 'ok');
  }
});


// ─────────────────────────────────────────────────────────────────
// Initialization
// ─────────────────────────────────────────────────────────────────

loadUplinkCommands();
refreshUplinkStatus();
setInterval(refreshUplinkStatus, 5000);
refreshSendButtonState();
