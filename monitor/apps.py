from django.apps import AppConfig


class MonitorConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'monitor'

    def ready(self):
        # only start in the main process (not during migrate, shell, etc.)
        import sys
        if 'runserver' not in sys.argv:
            return
        from . import collector
        collector.start()