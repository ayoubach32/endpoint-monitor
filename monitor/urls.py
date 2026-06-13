from django.urls import path
from . import views

urlpatterns = [
    path('',               views.dashboard,     name='dashboard'),
    path('api/metrics/',   views.api_metrics,   name='api_metrics'),
    path('api/history/',   views.api_history,   name='api_history'),
    path('api/alerts/',    views.api_alerts,    name='api_alerts'),
    path('api/processes/', views.api_processes, name='api_processes'),
    path('api/ml/',        views.api_ml,        name='api_ml'),
]