from django.urls import path
from . import views

app_name = 'api'
urlpatterns = [
    path('compromisos/', views.commitments, name='compromisos'),
    path('compromisos/<int:pk>/evidencia/', views.commitment_evidence, name='evidencia_compromiso'),
    path('login/', views.login, name='login'), path('logout/', views.logout, name='logout'), path('perfil/', views.perfil, name='perfil'),
    path('actividades/', views.activity_list, name='actividades'), path('actividades/<int:pk>/', views.activity_detail, name='detalle'),
    path('actividades/<int:pk>/avance/', views.progress, name='avance'), path('actividades/<int:pk>/resolver/', views.resolve, name='resolver'),
    path('actividades/<int:pk>/foto/', views.foto, name='foto'), path('metas/', views.metas, name='metas'),
]
