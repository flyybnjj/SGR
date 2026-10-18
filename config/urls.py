from django.contrib import admin
from django.urls import path, include
from .crud_modals import edit_form
from .crud_details import detail

urlpatterns = [
    path('demostracion/', include('config.role_demo')),
    path("consulta/<str:resource>/<int:pk>/", detail, name="crud_detail"),
    path("formularios/<str:resource>/<int:pk>/", edit_form, name="crud_edit_form"),

    path('', include('dashboard.urls')),
    path('', include('usuarios.urls')),
    path('', include('territorial.urls')),
    path('', include('atenciones.urls')),
    path('', include('vecinos.urls')),


    path('admin/', admin.site.urls),
]
