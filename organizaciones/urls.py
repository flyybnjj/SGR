from django.urls import path
from . import views

app_name = 'organizaciones'
urlpatterns = [
    path('organizaciones/', views.listado, name='listado'),
    path('organizaciones/nueva/', views.editar, name='crear'),
    path('organizaciones/<int:pk>/', views.detalle, name='detalle'),
    path('organizaciones/<int:pk>/editar/', views.editar, name='editar'),
]
