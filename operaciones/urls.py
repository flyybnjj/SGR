from django.urls import path
from . import views

app_name = 'operaciones'
urlpatterns = [
    path('avisos/', views.avisos, name='avisos'),
    path('avisos/<int:pk>/leido/', views.leer, name='leer'),
    path('calidad/', views.datos, name='calidad'),
    path('atenciones/<int:pk>/corregir/', views.corregir, name='corregir'),
    path('casos/', views.casos, name='casos'),
    path('casos/nuevo/', views.caso_editar, name='caso_crear'),
    path('casos/<int:pk>/', views.caso_editar, name='caso_editar'),
]
