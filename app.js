// ---------- CONFIG ----------
const STEP_GOAL = 10000;
const KCAL_PER_STEP = 0.04;     // rough average estimate
const POLL_MS = 2000;
const HR_LOW = 50, HR_HIGH = 100, SPO2_LOW = 94;

const $ = id => document.getElementById(id);
let timer = null, notified = false;

// ---------- CHARTS ----------
const mkChart = (id, color) => new Chart($(id), {
  type: 'line',
  data: { labels: [], datasets: [{ data: [], borderColor: color, tension: .3, pointRadius: 0, spanGaps: false }] },
  options: { animation: false, plugins: { legend: { display: false } },
    scales: { x: { display: false }, y: { ticks: { color: '#8fa1b3' }, grid: { color: '#243242' } } } }
});
const hrChart = mkChart('hrChart', '#f87171');
const spChart = mkChart('spChart', '#38bdf8');

// ---------- CSV ----------
function parseCSV(text) {
  return text.trim().split(/\r?\n/).slice(1).map(l => {
    const [t, steps, bpm, spo2] = l.split(',').map(Number);
    return { t, steps, bpm, spo2 };
  }).filter(r => !isNaN(r.t));
}

// ---------- RENDER ----------
function render(rows) {
  if (!rows.length) return;
  const last = rows[rows.length - 1];

  // Steps
  $('steps').textContent = last.steps;
  $('stepBar').style.width = Math.min(100, last.steps / STEP_GOAL * 100) + '%';
  $('cal').textContent = (last.steps * KCAL_PER_STEP).toFixed(1);
  if (last.steps >= STEP_GOAL && !notified) { notified = true; toast('🎉 10,000 steps reached!'); }

  // Live HR / SpO2 (only when valid, i.e. finger on sensor)
  const hrOk = last.bpm > 0, spOk = last.spo2 > 0;
  $('hr').textContent = hrOk ? last.bpm : '--';
  $('hrNote').textContent = hrOk ? 'Live reading' : 'No finger detected';
  $('spo2').textContent = spOk ? last.spo2 : '--';
  $('spNote').textContent = spOk ? 'Live reading' : 'No finger detected';

  // Trends (gaps where reading invalid)
  const labels = rows.map((_, i) => i);
  hrChart.data.labels = labels;
  hrChart.data.datasets[0].data = rows.map(r => r.bpm > 0 ? r.bpm : null);
  spChart.data.labels = labels;
  spChart.data.datasets[0].data = rows.map(r => r.spo2 > 0 ? r.spo2 : null);
  hrChart.update(); spChart.update();

  analyse(rows);
}

// ---------- AI-STYLE ANALYSIS (rule based) ----------
function analyse(rows) {
  const hrs = rows.filter(r => r.bpm > 0).map(r => r.bpm);
  const sps = rows.filter(r => r.spo2 > 0).map(r => r.spo2);
  const steps = rows[rows.length - 1].steps;

  const avg = a => a.length ? Math.round(a.reduce((x, y) => x + y, 0) / a.length) : null;
  const avgHr = avg(hrs);
  const abn = hrs.filter(h => h < HR_LOW || h > HR_HIGH).length;

  // Count distinct low-SpO2 events (consecutive low readings = one event)
  let lowEv = 0, inLow = false;
  rows.forEach(r => {
    const low = r.spo2 > 0 && r.spo2 < SPO2_LOW;
    if (low && !inLow) lowEv++;
    inLow = low;
  });

  $('avgHr').textContent = avgHr ?? '--';
  $('rngHr').textContent = hrs.length ? `${Math.min(...hrs)} / ${Math.max(...hrs)}` : '--';
  $('lowEv').textContent = lowEv;
  $('abnHr').textContent = abn;

  // Risk score
  let score = 0;
  if (lowEv >= 3) score += 3; else if (lowEv >= 1) score += 1;
  if (hrs.length && abn / hrs.length > 0.3) score += 2; else if (abn) score += 1;
  if (steps < 2000) score += 1;
  const risk = score >= 4 ? 'high' : score >= 2 ? 'moderate' : 'low';
  const r = $('risk'); r.textContent = risk.toUpperCase(); r.className = 'risk ' + risk;

  const ins = [], recs = [];
  if (!hrs.length) ins.push('No heart rate data yet. Keep a finger on the sensor.');
  else {
    ins.push(`Average heart rate is ${avgHr} BPM.`);
    if (hrs.some(h => h > HR_HIGH)) { ins.push('Elevated heart rate (tachycardia pattern) detected.'); recs.push('Rest, hydrate and avoid caffeine; consult a doctor if it persists.'); }
    if (hrs.some(h => h < HR_LOW)) { ins.push('Low heart rate (bradycardia pattern) detected.'); recs.push('If you feel dizzy or faint, seek medical advice.'); }
    if (!abn) ins.push('Heart rate stayed in the normal range (50-100 BPM).');
  }
  if (sps.length) {
    ins.push(`Average SpO2 is ${avg(sps)}%.`);
    if (lowEv) { ins.push(`${lowEv} low-SpO2 event(s) (<${SPO2_LOW}%) recorded.`); recs.push('Practice deep breathing and check sensor placement; see a doctor if low SpO2 repeats.'); }
  }
  ins.push(`Steps today: ${steps} (${Math.round(steps / STEP_GOAL * 100)}% of goal).`);
  if (steps < STEP_GOAL) recs.push(`Aim for ${STEP_GOAL.toLocaleString()} steps per day; ${(STEP_GOAL - steps).toLocaleString()} to go.`);
  recs.push('Diet: more leafy greens, nuts, fruits and lean protein; limit salt and processed food.');
  recs.push('Sleep 7-8 hours and drink 2-3 litres of water daily.');

  $('insights').innerHTML = ins.map(x => `<li>${x}</li>`).join('');
  $('recs').innerHTML = recs.map(x => `<li>${x}</li>`).join('');
}

// ---------- LIVE FETCH + UPLOAD ----------
async function poll() {
  const ip = $('ip').value.trim();
  try {
    const res = await fetch(`http://${ip}/data`, { cache: 'no-store' });
    render(parseCSV(await res.text()));
    setStatus(true, 'Live: ' + ip);
  } catch (e) { setStatus(false, 'Cannot reach ESP'); }
}
$('liveBtn').onclick = () => {
  if (timer) { clearInterval(timer); timer = null; $('liveBtn').textContent = 'Start Live'; setStatus(false, 'Stopped'); return; }
  if (!$('ip').value.trim()) return toast('Enter the ESP IP first');
  localStorage.setItem('nexfit_ip', $('ip').value.trim());
  poll(); timer = setInterval(poll, POLL_MS); $('liveBtn').textContent = 'Stop Live';
};
$('file').onchange = async e => {
  const f = e.target.files[0]; if (!f) return;
  render(parseCSV(await f.text())); setStatus(true, 'CSV loaded');
};

function setStatus(on, txt) { const s = $('status'); s.textContent = txt; s.className = 'pill ' + (on ? 'on' : 'off'); }
function toast(msg) { const t = $('toast'); t.textContent = msg; t.style.display = 'block'; setTimeout(() => t.style.display = 'none', 4000); }

$('ip').value = localStorage.getItem('nexfit_ip') || '';
