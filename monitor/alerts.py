import logging
import time

from django.core.mail import send_mail
from django.conf import settings

logger = logging.getLogger(__name__)

# thresholds — same as collector.py
THRESHOLDS = {
    'cpu':  {'warn': 70, 'crit': 90},
    'ram':  {'warn': 75, 'crit': 90},
    'disk': {'warn': 80, 'crit': 95},
}

ALERT_COOLDOWN = 300   # seconds between same alert
_last_alert: dict = {}


def check_and_alert(snap):
    """
    Called from collector after every snapshot.
    Saves Alert to DB and sends email if threshold crossed.
    """
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
            limit = thresh['crit']
        elif value >= thresh['warn']:
            sev = 'warn'
            limit = thresh['warn']
        else:
            continue

        cooldown_key = f"{key}_{sev}"
        last = _last_alert.get(cooldown_key, 0)
        if now - last < ALERT_COOLDOWN:
            continue

        _last_alert[cooldown_key] = now

        message = f"{label} at {value:.1f}% — above {limit}% threshold"

        # save to DB
        Alert.objects.create(
            severity = sev,
            metric   = key,
            value    = value,
            message  = message,
        )
        logger.warning("[%s] %s", sev.upper(), message)

        # send email
        _send_email(sev, label, value, limit, message)


def _send_email(sev, label, value, limit, message):
    """Send an alert email via Gmail SMTP."""
    recipient = getattr(settings, 'ALERT_RECIPIENT', None)
    if not recipient:
        logger.warning("ALERT_RECIPIENT not set — skipping email")
        return

    severity_label = 'CRITICAL' if sev == 'crit' else 'WARNING'
    hostname       = __import__('socket').gethostname()

    subject = f"[{severity_label}] {label} alert on {hostname}"

    body = f"""
Endpoint Monitor Alert
======================

Severity : {severity_label}
Host     : {hostname}
Metric   : {label}
Value    : {value:.1f}%
Threshold: {limit}%

Message  : {message}

--
This alert was generated automatically by Endpoint Monitor.
Next alert for this metric will fire in 5 minutes minimum.
    """.strip()

    try:
        send_mail(
            subject             = subject,
            message             = body,
            from_email          = settings.DEFAULT_FROM_EMAIL,
            recipient_list      = [recipient],
            fail_silently       = False,
        )
        logger.info("Alert email sent to %s", recipient)
    except Exception as e:
        logger.error("Failed to send alert email: %s", e)