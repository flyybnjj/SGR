from django.urls import path
from . import views

app_name = 'catalogos'
urlpatterns = [
    path('opciones-localidad/', views.opciones_localidad, name='opciones_localidad'),
    path('<slug:tipo>/', views.listado, name='listado'),
    path('<slug:tipo>/nuevo/', views.editar, name='crear'),
    path('<slug:tipo>/<int:pk>/editar/', views.editar, name='editar'),
    path('<slug:tipo>/<int:pk>/estado/', views.cambiar_estado, name='estado'),
    path('<slug:tipo>/<int:pk>/eliminar/', views.eliminar, name='eliminar'),
]
