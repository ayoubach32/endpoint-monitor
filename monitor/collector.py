import socket
import threading
import time
import logging

import psutil

logger = logging.getLogger(__name__)

INTERVAL     = 5    # collect every 5 seconds
MAX_ROWS     = 2000 # keep at most 2000 rows in DB (~2.7 hours at 5s)

# alert thresholds
THRESHOLDS = {
    'cpu':  {'warn': 70, 'crit': 90},
    'ram':  {'warn': 75, 'crit': 90},
    'disk': {'warn': 80, 'crit': 95},
}

# cooldown: don't fire same alert twice within this many seconds
ALERT_COOLDOWN = 300
_last_alert: dict = {}


def _collect_once():
    """Collect one snapshot and save to DB."""
    from .models import MetricSnapshot, Alert

    net  = psutil.net_io_counters()
    ram  = psutil.virtual_memory()
    disk = psutil.disk_usage('/')

    snap = MetricSnapshot.objects.create(
        cpu_percent    = psutil.cpu_percent(interval=0.5),
        cpu_cores      = psutil.cpu_count(logical=True),
        ram_percent    = ram.percent,
        ram_used       = ram.used,
        ram_total      = ram.total,
        disk_percent   = disk.percent,
        disk_used      = disk.used,
        disk_total     = disk.total,
        net_bytes_sent = net.bytes_sent,
        net_bytes_recv = net.bytes_recv,
    )

    _check_alerts(snap)
    _prune()


def _check_alerts(snap):
    """Create an Alert row if a metric crosses a threshold."""
    from .models import Alert

    checks = [
        ('cpu',  snap.cpu_percent,  'CPU'),
        ('ram',  snap.ram_percent,  'RAM'),
        ('disk', snap.disk_percent, 'Disk'),
    ]

    now = time.time()

    for key, value, label in checks:
        thresh = THRESHOLDS[key]

        if value >= thresh['crit']:
            sev = 'crit'
        elif value >= thresh['warn']:
            sev = 'warn'
        else:
            continue

        cooldown_key = f"{key}_{sev}"
        last = _last_alert.get(cooldown_key, 0)
        if now - last < ALERT_COOLDOWN:
            continue

        _last_alert[cooldown_key] = now
        Alert.objects.create(
            severity = sev,
            metric   = key,
            value    = value,
            message  = (
                f"{label} at {value:.1f}% — "
                f"above {'90' if sev == 'crit' else thresh['warn']}% threshold"
            ),
        )
        logger.warning("[%s] %s at %.1f%%", sev.upper(), label, value)


def _prune():
    """Delete oldest rows when DB grows too large."""
    from .models import MetricSnapshot
    count = MetricSnapshot.objects.count()
    if count > MAX_ROWS:
        oldest_ids = (
            MetricSnapshot.objects
            .order_by('timestamp')
            .values_list('id', flat=True)[:count - MAX_ROWS]
        )
        MetricSnapshot.objects.filter(id__in=list(oldest_ids)).delete()


def _loop():
    """Background thread loop."""
    while True:
        try:
            _collect_once()
        except Exception as e:
            logger.error("Collector error: %s", e)
        time.sleep(INTERVAL)


_thread = None

def start():
    """Start the collector thread (call once at startup)."""
    global _thread
    if _thread is not None:
        return
    _thread = threading.Thread(target=_loop, daemon=True, name="metric-collector")
    _thread.start()
    logger.info("Metric collector started (interval=%ds)", INTERVAL)