from django.urls import path
from . import views

app_name = 'atenciones'

urlpatterns = [

    path('mantenedores/tipos-atencion/', views.tipo_atencion_list_view, name='tipo_atencion_list'),
    path('mantenedores/tipos-atencion/crear/', views.tipo_atencion_save_view, name='tipo_atencion_create'),
    path('mantenedores/tipos-atencion/<int:pk>/editar/', views.tipo_atencion_save_view, name='tipo_atencion_edit'),
    path('mantenedores/tipos-atencion/<int:pk>/toggle/', views.tipo_atencion_toggle_activo, name='tipo_atencion_toggle'),
    path('mantenedores/tipos-atencion/exportar-excel/', views.tipo_atencion_export_excel, name='tipo_atencion_excel'),


    path('mantenedores/sub-atenciones/', views.sub_atencion_list_view, name='sub_atencion_list'),
    path('mantenedores/sub-atenciones/crear/', views.sub_atencion_save_view, name='sub_atencion_create'),
    path('mantenedores/sub-atenciones/<int:pk>/editar/', views.sub_atencion_save_view, name='sub_atencion_edit'),
    path('mantenedores/sub-atenciones/<int:pk>/toggle/', views.sub_atencion_toggle_activo, name='sub_atencion_toggle'),
    path('mantenedores/sub-atenciones/exportar-excel/', views.sub_atencion_export_excel, name='sub_atencion_excel'),
]
urlpatterns += [
    path('atenciones/', views.attention_search, name='attention_search'),
    path('atenciones/nueva-persona/', views.attention_new, name='attention_new'),
    path('atenciones/persona/<int:pk>/', views.attention_detail, name='attention_detail'),
    path('acciones/', views.action_list, name='action_list'),
    path('acciones/nueva/', views.action_create, name='action_create'),
    path('acciones/<int:pk>/revision/', views.action_review, name='action_review'),
    path('acciones/<int:pk>/resolver/', views.action_resolve, name='action_resolve'),
    path('acciones/<int:pk>/evidencia/', views.action_evidence, name='action_evidence'),
    path('metas/', views.meta_list, name='meta_list'),
    path('metas/nueva/', views.meta_save, name='meta_create'),
    path('metas/<int:pk>/editar/', views.meta_save, name='meta_edit'),
]
