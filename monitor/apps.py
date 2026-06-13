from django.apps import AppConfig


class MonitorConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'monitor'

    def ready(self):
        import sys
        if 'runserver' not in sys.argv:
            return
        from . import collector
        from . import ml_engine
        ml_engine.load_models()
        collector.start()