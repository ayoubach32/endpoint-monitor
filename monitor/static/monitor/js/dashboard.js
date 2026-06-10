const POLL_INTERVAL = 3000
const MAX_HISTORY   = 30

const chartDefaults = (label, color) => ({
  type: 'line',
  data: {
    labels: Array(MAX_HISTORY).fill(''),
    datasets: [{
      label,
      data: Array(MAX_HISTORY).fill(null),
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
      x: { display: false }
    },
    plugins: { legend: { display: false } }
  }
})

const cpuChart = new Chart(document.getElementById('chart-cpu'), chartDefaults('CPU %', '#185FA5'))
const ramChart = new Chart(document.getElementById('chart-ram'), chartDefaults('RAM %', '#3B6D11'))

function pushToChart(chart, value) {
  chart.data.datasets[0].data.push(value)
  chart.data.datasets[0].data.shift()
  chart.update('none')
}

function severity(value, warnAt, critAt) {
  if (value >= critAt)  return 'crit'
  if (value >= warnAt)  return 'warn'
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

const alertLog = []

function addAlert(sev, message) {
  const time = new Date().toLocaleTimeString()
  alertLog.unshift({ sev, message, time })
  if (alertLog.length > 20) alertLog.pop()
  renderAlerts()
}

function renderAlerts() {
  const list = document.getElementById('alerts-list')
  document.getElementById('alert-count').textContent = alertLog.length
  if (alertLog.length === 0) {
    list.innerHTML = '<div class="alert-empty">No alerts — all metrics within normal range.</div>'
    return
  }
  list.innerHTML = alertLog.map(a => `
    <div class="alert-item">
      <span class="alert-sev ${a.sev}">${a.sev.toUpperCase()}</span>
      <span class="alert-msg">${a.message}</span>
      <span class="alert-time">${a.time}</span>
    </div>
  `).join('')
}

function updateDashboard(data) {
  document.getElementById('hostname').textContent = data.hostname

  const cpu    = data.cpu_percent
  const cpuSev = severity(cpu, 70, 90)
  document.getElementById('val-cpu').textContent = cpu.toFixed(1) + '%'
  document.getElementById('bar-cpu').style.width = cpu + '%'
  document.getElementById('sub-cpu').textContent = data.cpu_cores + ' logical cores'
  applyBadge(document.getElementById('badge-cpu'), document.getElementById('bar-cpu'), cpuSev)
  pushToChart(cpuChart, cpu)

  const ram    = data.ram_percent
  const ramSev = severity(ram, 75, 90)
  document.getElementById('val-ram').textContent = ram.toFixed(1) + '%'
  document.getElementById('bar-ram').style.width = ram + '%'
  document.getElementById('sub-ram').textContent = fmtBytes(data.ram_used) + ' / ' + fmtBytes(data.ram_total)
  applyBadge(document.getElementById('badge-ram'), document.getElementById('bar-ram'), ramSev)
  pushToChart(ramChart, ram)

  const disk    = data.disk_percent
  const diskSev = severity(disk, 80, 95)
  document.getElementById('val-disk').textContent = disk.toFixed(1) + '%'
  document.getElementById('bar-disk').style.width = disk + '%'
  document.getElementById('sub-disk').textContent = fmtBytes(data.disk_used) + ' / ' + fmtBytes(data.disk_total)
  applyBadge(document.getElementById('badge-disk'), document.getElementById('bar-disk'), diskSev)

  document.getElementById('val-net-sent').textContent = fmtBytes(data.net_bytes_sent) + '/s'
  document.getElementById('val-net-recv').textContent = fmtBytes(data.net_bytes_recv) + '/s'

  document.getElementById('status-dot').className = 'status-dot'

  if (cpuSev === 'crit')  addAlert('crit', `CPU at ${cpu.toFixed(1)}% — above 90% threshold`)
  else if (cpuSev === 'warn') addAlert('warn', `CPU at ${cpu.toFixed(1)}% — above 70% threshold`)
  if (ramSev === 'crit')  addAlert('crit', `RAM at ${ram.toFixed(1)}% — above 90% threshold`)
  if (diskSev === 'crit') addAlert('crit', `Disk at ${disk.toFixed(1)}% — above 95% threshold`)
}

async function poll() {
  try {
    const res  = await fetch('/api/metrics/')
    const data = await res.json()
    updateDashboard(data)
  } catch (err) {
    document.getElementById('status-dot').className = 'status-dot offline'
    console.error('Poll failed:', err)
  }
}

poll()
setInterval(poll, POLL_INTERVAL)