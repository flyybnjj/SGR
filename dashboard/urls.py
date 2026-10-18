from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    path('administracion/', views.administracion_view, name='administracion'),
    path('', views.inicio_view, name='inicio'),
    path('inicio/', views.inicio_view, name='inicio_alias'),
    path('dashboard/', views.inicio_view, name='inicio_dashboard'),
    path('reportes/', views.reportes_view, name='reportes'),
    path('dashboard/reportes/', views.reportes_view, name='reportes_dashboard'),
]
