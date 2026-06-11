const POLL_INTERVAL = 5000
const MAX_POINTS    = 60

// ── chart factory ─────────────────────────────────────────────
function makeChart(id, label, color) {
  return new Chart(document.getElementById(id), {
    type: 'line',
    data: {
      labels: [],
      datasets: [{
        label,
        data: [],
        borderColor: color,
        borderWidth: 2,
        pointRadius: 0,
        fill: true,
        backgroundColor: color + '18',
        tension: 0.4,
      }]
    },
    options: {
      animation: false,
      responsive: true,
      scales: {
        y: {
          min: 0, max: 100,
          grid: { color: '#88878022' },
          ticks: { color: '#888780', font: { size: 11 }, callback: v => v + '%' }
        },
        x: {
          display: true,
          ticks: {
            color: '#888780',
            font: { size: 10 },
            maxTicksLimit: 6,
            maxRotation: 0,
          },
          grid: { display: false }
        }
      },
      plugins: { legend: { display: false } }
    }
  })
}

const cpuChart = makeChart('chart-cpu', 'CPU %', '#185FA5')
const ramChart = makeChart('chart-ram', 'RAM %', '#3B6D11')

// ── push one point to a chart ─────────────────────────────────
function pushPoint(chart, label, value) {
  chart.data.labels.push(label)
  chart.data.datasets[0].data.push(value)
  if (chart.data.labels.length > MAX_POINTS) {
    chart.data.labels.shift()
    chart.data.datasets[0].data.shift()
  }
  chart.update('none')
}

// ── load history from DB on page open ────────────────────────
async function loadHistory() {
  try {
    const res  = await fetch('/api/history/?minutes=15')
    const data = await res.json()

    data.snapshots.forEach(s => {
      pushPoint(cpuChart, s.time, s.cpu_percent)
      pushPoint(ramChart, s.time, s.ram_percent)
    })
  } catch (err) {
    console.warn('History load failed:', err)
  }
}

// ── severity helpers ──────────────────────────────────────────
function severity(value, warnAt, critAt) {
  if (value >= critAt) return 'crit'
  if (value >= warnAt) return 'warn'
  return 'ok'
}

function applyBadge(badgeEl, barEl, sev) {
  const labels = { ok: 'normal', warn: 'warning', crit: 'critical' }
  badgeEl.textContent = labels[sev]
  badgeEl.className   = 'metric-badge' + (sev !== 'ok' ? ' ' + sev : '')
  barEl.className     = 'metric-bar'   + (sev !== 'ok' ? ' ' + sev : '')
}

function fmtBytes(bytes) {
  if (bytes >= 1e9) return (bytes / 1e9).toFixed(1) + ' GB'
  if (bytes >= 1e6) return (bytes / 1e6).toFixed(1) + ' MB'
  return (bytes / 1e3).toFixed(0) + ' KB'
}

// ── load alerts from DB ───────────────────────────────────────
async function loadAlerts() {
  try {
    const res  = await fetch('/api/alerts/')
    const data = await res.json()
    renderAlerts(data.alerts)
  } catch (err) {
    console.warn('Alerts load failed:', err)
  }
}

function renderAlerts(alerts) {
  const list = document.getElementById('alerts-list')
  document.getElementById('alert-count').textContent = alerts.length

  if (alerts.length === 0) {
    list.innerHTML = '<div class="alert-empty">No alerts — all metrics within normal range.</div>'
    return
  }

  list.innerHTML = alerts.map(a => `
    <div class="alert-item">
      <span class="alert-sev ${a.severity}">${a.severity.toUpperCase()}</span>
      <span class="alert-msg">${a.message}</span>
      <span class="alert-time">${a.time}</span>
    </div>
  `).join('')
}

// ── update metric cards ───────────────────────────────────────
function updateCards(data) {
  document.getElementById('hostname').textContent = data.hostname

  const cpu    = data.cpu_percent
  const cpuSev = severity(cpu, 70, 90)
  document.getElementById('val-cpu').textContent = cpu.toFixed(1) + '%'
  document.getElementById('bar-cpu').style.width = cpu + '%'
  document.getElementById('sub-cpu').textContent = data.cpu_cores + ' logical cores'
  applyBadge(document.getElementById('badge-cpu'), document.getElementById('bar-cpu'), cpuSev)

  const ram    = data.ram_percent
  const ramSev = severity(ram, 75, 90)
  document.getElementById('val-ram').textContent = ram.toFixed(1) + '%'
  document.getElementById('bar-ram').style.width = ram + '%'
  document.getElementById('sub-ram').textContent = fmtBytes(data.ram_used) + ' / ' + fmtBytes(data.ram_total)
  applyBadge(document.getElementById('badge-ram'), document.getElementById('bar-ram'), ramSev)

  const disk    = data.disk_percent
  const diskSev = severity(disk, 80, 95)
  document.getElementById('val-disk').textContent = disk.toFixed(1) + '%'
  document.getElementById('bar-disk').style.width = disk + '%'
  document.getElementById('sub-disk').textContent = fmtBytes(data.disk_used) + ' / ' + fmtBytes(data.disk_total)
  applyBadge(document.getElementById('badge-disk'), document.getElementById('bar-disk'), diskSev)

  document.getElementById('val-net-sent').textContent = fmtBytes(data.net_bytes_sent) + '/s'
  document.getElementById('val-net-recv').textContent = fmtBytes(data.net_bytes_recv) + '/s'

  document.getElementById('status-dot').className = 'status-dot'
}

// ── main poll loop ────────────────────────────────────────────
async function poll() {
  try {
    const res  = await fetch('/api/metrics/')
    const data = await res.json()
    const now  = new Date().toLocaleTimeString()

    updateCards(data)
    pushPoint(cpuChart, now, data.cpu_percent)
    pushPoint(ramChart, now, data.ram_percent)
  } catch (err) {
    document.getElementById('status-dot').className = 'status-dot offline'
    console.error('Poll failed:', err)
  }
}

// ── startup sequence ──────────────────────────────────────────
async function init() {
  await loadHistory()   // 1. fill charts with DB history
  await loadAlerts()    // 2. load saved alerts
  await poll()          // 3. first live update immediately
  setInterval(poll, POLL_INTERVAL)                    // 4. keep polling
  setInterval(loadAlerts, 30000)                      // 5. refresh alerts every 30s
}

init()