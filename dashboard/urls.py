from django.urls import path
from . import views
from . import updates

app_name = 'dashboard'

urlpatterns = [
    path('mi-resumen/', views.inicio_view, {'personal': True}, name='personal'),
    path('novedades/', updates.novedades, name='novedades'),
    path('novedades/<slug:slug>/leida/', updates.marcar_leida, name='novedad_leida'),
    path('administracion/', views.administracion_view, name='administracion'),
    path('', views.inicio_view, name='inicio'),
    path('inicio/', views.inicio_view, name='inicio_alias'),
    path('dashboard/', views.inicio_view, name='inicio_dashboard'),
    path('reportes/', views.reportes_view, name='reportes'),
    path('dashboard/reportes/', views.reportes_view, name='reportes_dashboard'),
]
