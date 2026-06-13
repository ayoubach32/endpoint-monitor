from multiprocessing.util import info
import socket
from django.shortcuts import render
from django.http import JsonResponse
from django.utils import timezone
from datetime import timedelta
from . import ml_engine

import psutil

from .models import MetricSnapshot, Alert




def dashboard(request):
    return render(request, 'monitor/dashboard.html')


def api_metrics(request):
    """Return the latest snapshot from DB, fallback to live psutil."""
    snap = MetricSnapshot.objects.first()

    if snap is None:
        # DB empty — collector hasn't fired yet, return live data
        import psutil
        net  = __import__('psutil').net_io_counters()
        ram  = __import__('psutil').virtual_memory()
        disk = __import__('psutil').disk_usage('/')
        return JsonResponse({
            'hostname':       socket.gethostname(),
            'cpu_percent':    __import__('psutil').cpu_percent(interval=0.5),
            'cpu_cores':      __import__('psutil').cpu_count(logical=True),
            'ram_percent':    ram.percent,
            'ram_used':       ram.used,
            'ram_total':      ram.total,
            'disk_percent':   disk.percent,
            'disk_used':      disk.used,
            'disk_total':     disk.total,
            'net_bytes_sent': net.bytes_sent,
            'net_bytes_recv': net.bytes_recv,
            'source': 'live',
        })

    return JsonResponse({
        'hostname':       socket.gethostname(),
        'cpu_percent':    snap.cpu_percent,
        'cpu_cores':      snap.cpu_cores,
        'ram_percent':    snap.ram_percent,
        'ram_used':       snap.ram_used,
        'ram_total':      snap.ram_total,
        'disk_percent':   snap.disk_percent,
        'disk_used':      snap.disk_used,
        'disk_total':     snap.disk_total,
        'net_bytes_sent': snap.net_bytes_sent,
        'net_bytes_recv': snap.net_bytes_recv,
        'source': 'db',
    })


def api_history(request):
    """Return last N minutes of snapshots for charts."""
    minutes = int(request.GET.get('minutes', 15))
    since   = timezone.now() - timedelta(minutes=minutes)

    snaps = (
        MetricSnapshot.objects
        .filter(timestamp__gte=since)
        .order_by('timestamp')
        .values('timestamp', 'cpu_percent', 'ram_percent', 'disk_percent')
    )

    return JsonResponse({
        'snapshots': [
            {
                'time':         s['timestamp'].strftime('%H:%M:%S'),
                'cpu_percent':  s['cpu_percent'],
                'ram_percent':  s['ram_percent'],
                'disk_percent': s['disk_percent'],
            }
            for s in snaps
        ]
    })


def api_alerts(request):
    """Return recent alerts from DB."""
    alerts = Alert.objects.order_by('-timestamp')[:20]
    return JsonResponse({
        'alerts': [
            {
                'severity': a.severity,
                'metric':   a.metric,
                'message':  a.message,
                'value':    a.value,
                'time':     a.timestamp.strftime('%H:%M:%S'),
            }
            for a in alerts
        ]
    })



def api_processes(request):
    """Return top 5 processes by CPU usage."""
    processes = []

    for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent', 'status']):
        try:
            info = proc.info
            if info['name'] == 'System Idle Process':
              continue
            if info['memory_percent'] is None:
                info['memory_percent'] = 0.0
            processes.append(info)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    top5 = sorted(processes, key=lambda p: p['cpu_percent'], reverse=True)[:5]

    return JsonResponse({'processes': top5})





# keep a rolling buffer of last 10 readings for forecasting
_cpu_history = []
_ram_history = []


def api_ml(request):
    """Return anomaly detection + forecast for current metrics."""
    global _cpu_history, _ram_history

    snap = MetricSnapshot.objects.first()
    if snap is None:
        return JsonResponse({'error': 'No data yet'}, status=404)

    # update rolling history
    _cpu_history.append(snap.cpu_percent)
    _ram_history.append(snap.ram_percent)
    if len(_cpu_history) > 10:
        _cpu_history.pop(0)
    if len(_ram_history) > 10:
        _ram_history.pop(0)

    # run models
    anomaly  = ml_engine.detect_anomaly(snap.cpu_percent, snap.ram_percent)
    forecast = ml_engine.forecast(_cpu_history, _ram_history)

    return JsonResponse({
        'anomaly':  anomaly,
        'forecast': forecast,
    })
