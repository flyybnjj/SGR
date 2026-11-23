from django.urls import path
from . import views

app_name = 'organizaciones'
urlpatterns = [
    path('organizaciones/', views.listado, name='listado'),
    path('organizaciones/buscar-directiva/', views.buscar_directiva, name='buscar_directiva'),
    path('organizaciones/crear-vecino-directiva/', views.crear_vecino_directiva, name='crear_vecino_directiva'),
    path('organizaciones/nueva/', views.editar, name='crear'),
    path('organizaciones/<int:pk>/', views.detalle, name='detalle'),
    path('organizaciones/<int:pk>/editar/', views.editar, name='editar'),
]
