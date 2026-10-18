from django.urls import path
from . import views

app_name = 'territorial'

urlpatterns = [
    path('mi-perfil/apariencia/<int:pk>/', views.appearance_view, name='apariencia'),
    # Delegaciones Municipales
    path('mantenedores/delegaciones/', views.delegaciones_list_view, name='delegaciones_list'),
    path('mantenedores/delegaciones/crear/', views.delegaciones_save_view, name='delegaciones_create'),
    path('mantenedores/delegaciones/<int:pk>/editar/', views.delegaciones_save_view, name='delegaciones_edit'),
    path('mantenedores/delegaciones/<int:pk>/toggle/', views.delegaciones_toggle_activo, name='delegaciones_toggle'),
    path('mantenedores/delegaciones/exportar-excel/', views.delegaciones_export_excel, name='delegaciones_excel'),

    # Ítems de Metas
    path('mantenedores/metas/', views.metas_list_view, name='metas_list'),
    path('mantenedores/metas/crear/', views.metas_save_view, name='metas_create'),
    path('mantenedores/metas/<int:pk>/editar/', views.metas_save_view, name='metas_edit'),
    path('mantenedores/metas/<int:pk>/toggle/', views.metas_toggle_activo, name='metas_toggle'),
    path('mantenedores/metas/exportar-excel/', views.metas_export_excel, name='metas_excel'),
]
