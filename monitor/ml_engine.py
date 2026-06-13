import os
import logging
import json
import numpy as np
import joblib
from django.conf import settings
from .anomaly_detector import ZScoreAnomalyDetector

logger = logging.getLogger(__name__)

ML_DIR = os.path.join(settings.BASE_DIR, 'monitor', 'ml_models')


def _load(filename):
    path = os.path.join(ML_DIR, filename)
    if not os.path.exists(path):
        logger.warning("ML model not found: %s", path)
        return None
    return joblib.load(path)


_anomaly_model       = None
_forecast_cpu_model  = None
_forecast_ram_model  = None
_forecast_cpu_scaler = None
_forecast_ram_scaler = None


def load_models():
    global _anomaly_model
    global _forecast_cpu_model, _forecast_ram_model
    global _forecast_cpu_scaler, _forecast_ram_scaler

    # load anomaly model from JSON
    anomaly_path = os.path.join(ML_DIR, 'anomaly_model.json')
    if os.path.exists(anomaly_path):
        _anomaly_model = ZScoreAnomalyDetector.load(anomaly_path)
        logger.info("Anomaly detection model loaded from JSON")
    else:
        logger.warning("anomaly_model.json not found")

    # load forecasting models from pkl (no custom class — safe)
    _forecast_cpu_model  = _load('forecasting_cpu_model.pkl')
    _forecast_ram_model  = _load('forecasting_ram_model.pkl')
    _forecast_cpu_scaler = _load('forecasting_cpu_scaler.pkl')
    _forecast_ram_scaler = _load('forecasting_ram_scaler.pkl')

    if _forecast_cpu_model:
        logger.info("Forecasting models loaded")


def detect_anomaly(cpu_percent, ram_percent):
    if _anomaly_model is None:
        return _fallback_anomaly(cpu_percent, ram_percent)

    cpu_result = _anomaly_model.predict('cpu_percent', cpu_percent)
    ram_result = _anomaly_model.predict('ram_percent', ram_percent)

    return {
        'cpu': {
            'is_anomaly': cpu_result['is_anomaly'],
            'z_score':    cpu_result['z_score'],
            'severity':   cpu_result['severity'],
        },
        'ram': {
            'is_anomaly': ram_result['is_anomaly'],
            'z_score':    ram_result['z_score'],
            'severity':   ram_result['severity'],
        },
    }


def forecast(cpu_history, ram_history):
    if len(cpu_history) < 10 or len(ram_history) < 10:
        return None

    if _forecast_cpu_model is None or _forecast_ram_model is None:
        return {
            'cpu_forecast':    round(cpu_history[-1], 1),
            'ram_forecast':    round(ram_history[-1], 1),
            'horizon_seconds': 30,
            'available':       False,
        }

    try:
        x_cpu = np.array(cpu_history[-10:]).reshape(1, -1)
        x_ram = np.array(ram_history[-10:]).reshape(1, -1)

        cpu_pred = _forecast_cpu_model.predict(
            _forecast_cpu_scaler.transform(x_cpu)
        )[0]
        ram_pred = _forecast_ram_model.predict(
            _forecast_ram_scaler.transform(x_ram)
        )[0]

        return {
            'cpu_forecast':    round(float(np.clip(cpu_pred, 0, 100)), 1),
            'ram_forecast':    round(float(np.clip(ram_pred, 0, 100)), 1),
            'horizon_seconds': 30,
            'available':       True,
        }
    except Exception as e:
        logger.error("Forecast error: %s", e)
        return None


def _fallback_anomaly(cpu, ram):
    return {
        'cpu': {
            'is_anomaly': cpu > 90,
            'z_score':    0,
            'severity':   'critical' if cpu > 90 else 'normal',
        },
        'ram': {
            'is_anomaly': ram > 90,
            'z_score':    0,
            'severity':   'critical' if ram > 90 else 'normal',
        },
    }