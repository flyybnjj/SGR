from django.urls import path
from . import views

app_name = 'periodos'
urlpatterns = [
    path('', views.listado, name='listado'),
    path('nuevo/', views.formulario, name='crear'),
    path('<int:pk>/', views.detalle, name='detalle'),
    path('<int:pk>/editar/', views.formulario, name='editar'),
    path('<int:pk>/abrir/', views.abrir, name='abrir'),
    path('<int:pk>/anular/', views.anular, name='anular'),
    path('<int:pk>/cierre/', views.cierre, name='cierre'),
]
