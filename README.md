# Endpoint Monitor

A real-time system monitoring dashboard built with Django, psutil, and scikit-learn.
Mimics professional tools like Datadog and Prometheus — scoped to a single machine.

## Features

- Live CPU, RAM, disk, and network metrics — updated every 5 seconds
- Historical graphs with Chart.js — loads last 15 minutes on page open
- Threshold-based alerts — Warning and Critical levels per metric
- Email notifications via Gmail SMTP with 5-minute cooldown
- Background metric collection via Python threading — runs independently of web requests
- SQLite storage with automatic pruning — keeps last 2000 snapshots
- Top 5 CPU-consuming processes — updated every 10 seconds
- ML anomaly detection — Z-score model flags abnormal CPU/RAM behavior
- ML forecasting — Linear regression predicts CPU/RAM usage 30 seconds ahead

## Tech stack

- Python 3 / Django
- psutil
- Chart.js
- SQLite
- scikit-learn
- Jupyter Notebook (model training)

## ML models

Two models are trained in Jupyter and integrated into Django:

**1. Anomaly Detection (Z-score)**
Learns the mean and standard deviation of CPU and RAM from training data.
Flags any reading more than 3 standard deviations from normal as an anomaly.
Saved as `monitor/ml_models/anomaly_model.json`.

**2. Resource Forecasting (Linear Regression)**
Takes the last 10 readings as input features and predicts CPU and RAM
usage 30 seconds into the future. Achieves MAE of ~3.3% on CPU and ~2.5% on RAM.
Saved as `monitor/ml_models/forecasting_*.pkl`.

## Project structure

endpoint_monitor/

├── core/               # Django project settings

├── monitor/            # Main app

│   ├── models.py       # MetricSnapshot + Alert models

│   ├── views.py        # REST API endpoints

│   ├── collector.py    # Background thread — psutil every 5s

│   ├── alerts.py       # Threshold logic + email

│   ├── ml_engine.py    # Loads and runs ML models

│   └── ml_models/      # Saved model files (.json + .pkl)

├── ml/                 # Jupyter notebooks for model training

│   ├── anomaly_detection.ipynb

│   └── forecasting.ipynb

└── manage.py

## API endpoints

| Endpoint | Description |
|---|---|
| `GET /` | Dashboard UI |
| `GET /api/metrics/` | Latest snapshot — CPU, RAM, disk, network |
| `GET /api/history/` | Last N minutes of snapshots for charts |
| `GET /api/alerts/` | Last 20 alerts from DB |
| `GET /api/processes/` | Top 5 processes by CPU usage |
| `GET /api/ml/` | Anomaly detection + 30s forecast |

## Setup

```bash
git clone https://github.com/ayoubach32/endpoint-monitor.git
cd endpoint-monitor
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

Open http://127.0.0.1:8000

## Email alerts setup

Create a Gmail App Password at myaccount.google.com → Security → App passwords.
Then add these lines to `core/settings.py`:

```python
EMAIL_HOST_USER     = 'your_gmail@gmail.com'
EMAIL_HOST_PASSWORD = 'your_16_char_app_password'
ALERT_RECIPIENT     = 'your_gmail@gmail.com'
```

## Retraining the ML models

After several hours of data collection, export your real metrics and retrain:

```bash
python manage.py shell
```

```python
from monitor.models import MetricSnapshot
import csv

with open('ml/real_data.csv', 'w', newline='') as f:
    writer = csv.writer(f)
    writer.writerow(['timestamp', 'cpu_percent', 'ram_percent', 'disk_percent'])
    for snap in MetricSnapshot.objects.order_by('timestamp'):
        writer.writerow([snap.timestamp, snap.cpu_percent,
                         snap.ram_percent, snap.disk_percent])
```

Then open the Jupyter notebooks and replace the synthetic data cell with:

```python
df = pd.read_csv('real_data.csv')
```