import threading
import time
import logging

import psutil

logger = logging.getLogger(__name__)

INTERVAL = 5
MAX_ROWS = 2000


def _collect_once():
    from .models import MetricSnapshot
    from .alerts import check_and_alert

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

    check_and_alert(snap)
    _prune()


def _prune():
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
    while True:
        try:
            _collect_once()
        except Exception as e:
            logger.error("Collector error: %s", e)
        time.sleep(INTERVAL)


_thread = None

def start():
    global _thread
    if _thread is not None:
        return
    _thread = threading.Thread(target=_loop, daemon=True, name="metric-collector")
    _thread.start()
    logger.info("Metric collector started (interval=%ds)", INTERVAL)