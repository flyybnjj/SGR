from django.urls import path
from . import views

app_name = 'cartas'
urlpatterns = [path('cartas/<int:pk>/respaldo/', views.respaldo, name='respaldo')]
urlpatterns += [path('cartas/', views.listado, name='listado'), path('cartas/nueva/', views.editar, name='crear'), path('cartas/<int:pk>/', views.detalle, name='detalle'), path('cartas/<int:pk>/editar/', views.editar, name='editar')]

urlpatterns += [path('cartas/<int:pk>/puntaje/', views.puntaje, name='puntaje'), path('cartas/<int:pk>/mover/', views.mover, name='mover')]
