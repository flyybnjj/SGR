from django.urls import path
from . import views

app_name = 'vecinos'

urlpatterns = [
    path('mantenedores/vecinos/', views.vecinos_list_view, name='vecinos_list'),
    path('mantenedores/vecinos/crear/', views.vecinos_save_view, name='vecinos_create'),
    path('mantenedores/vecinos/<int:pk>/editar/', views.vecinos_save_view, name='vecinos_edit'),
    path('mantenedores/vecinos/<int:pk>/toggle/', views.vecinos_toggle_activo, name='vecinos_toggle'),
    path('mantenedores/vecinos/exportar-excel/', views.vecinos_export_excel, name='vecinos_excel'),
]
