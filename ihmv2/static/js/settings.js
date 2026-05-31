const socket = io();

function syncInput(id, value) {
  const slider = document.getElementById(`${id}_slider`);
  const number = document.getElementById(`${id}_num`);
  if (slider) slider.value = value;
  if (number) number.value = value;
  sendParam(id, value);
}

function sendParam(name, val) {
  socket.emit('update_radio_param', { param: name, val: parseFloat(val) });
}

const ctx = document.getElementById('spectrumChart').getContext('2d');
let latestSpectrum = [];

const spectrumChart = new Chart(ctx, {
  type: 'line',
  data: {
    labels: [],
    datasets: [{
      label: 'Spectrum',
      data: [],
      borderColor: '#38bdf8',
      backgroundColor: 'rgba(56, 189, 248, 0.08)',
      borderWidth: 1.6,
      pointRadius: 0,
      fill: false,
      tension: 0.12,
    }],
  },
  options: {
    responsive: true,
    maintainAspectRatio: false,
    animation: false,
    plugins: {
      legend: { display: false },
    },
    scales: {
      x: {
        title: { display: true, text: 'Bin', color: '#8ea0b6' },
        grid: { color: '#1d2a3b' },
        ticks: { color: '#8ea0b6', maxTicksLimit: 10 },
      },
      y: {
        min: -140,
        max: 10,
        title: { display: true, text: 'Relative Gain (dB)', color: '#8ea0b6' },
        grid: { color: '#1d2a3b' },
        ticks: { color: '#8ea0b6' },
      },
    },
  },
});

socket.on('new_spectrum_data', (data) => {
  if (!data || !Array.isArray(data.spectrum)) {
    return;
  }
  latestSpectrum = data.spectrum;
});

function renderSpectrum() {
  if (!latestSpectrum.length) {
    return;
  }

  spectrumChart.data.labels = latestSpectrum.map((_, index) => index);
  spectrumChart.data.datasets[0].data = latestSpectrum;
  spectrumChart.update('none');
}

setInterval(renderSpectrum, 50);

socket.on('connect', () => {
  const statusBox = document.getElementById('settingsStatus');
  if (statusBox) {
    statusBox.textContent = 'Connected. Live parameters can be changed now.';
  }
});

socket.on('disconnect', () => {
  const statusBox = document.getElementById('settingsStatus');
  if (statusBox) {
    statusBox.textContent = 'Disconnected from settings channel.';
  }
});
