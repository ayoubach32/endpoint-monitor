# Endpoint Monitor

A real-time system monitoring dashboard built with Django and psutil.
Mimics tools like Datadog and Prometheus — scoped to a single machine.

## Features
- Live CPU, RAM, disk, and network metrics
- Historical graphs with Chart.js
- Threshold-based alerts (warning + critical)
- Background metric collection every 5 seconds
- SQLite storage with automatic pruning

## Tech stack
- Python 3 / Django
- psutil
- Chart.js
- SQLite

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