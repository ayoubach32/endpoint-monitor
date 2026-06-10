from django.db import models

# Create your models here.
from django.db import models


class MetricSnapshot(models.Model):
    timestamp    = models.DateTimeField(auto_now_add=True)
    cpu_percent  = models.FloatField()
    cpu_cores    = models.IntegerField()
    ram_percent  = models.FloatField()
    ram_used     = models.BigIntegerField()
    ram_total    = models.BigIntegerField()
    disk_percent = models.FloatField()
    disk_used    = models.BigIntegerField()
    disk_total   = models.BigIntegerField()
    net_bytes_sent = models.BigIntegerField()
    net_bytes_recv = models.BigIntegerField()

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.timestamp:%Y-%m-%d %H:%M:%S} | CPU {self.cpu_percent}%"


class Alert(models.Model):
    SEVERITY_CHOICES = [
        ('warn', 'Warning'),
        ('crit', 'Critical'),
    ]
    timestamp = models.DateTimeField(auto_now_add=True)
    severity  = models.CharField(max_length=4, choices=SEVERITY_CHOICES)
    metric    = models.CharField(max_length=20)
    message   = models.CharField(max_length=255)
    value     = models.FloatField()

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"[{self.severity.upper()}] {self.message}"