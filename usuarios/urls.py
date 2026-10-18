from django.urls import path
from . import views
from . import passkeys
from . import account

app_name = 'usuarios'

urlpatterns = [
    path('mi-perfil/ajustes/', account.settings_view, name='account_settings'),
    path('mi-perfil/contrasena/', account.settings_view, {'section': 'password'}, name='account_password'),
    path('mi-perfil/passkeys/', passkeys.manage, name='passkeys'),
    path('passkeys/registro/opciones/', passkeys.registration_options, name='passkey_registration_options'),
    path('passkeys/registro/verificar/', passkeys.registration_verify, name='passkey_registration_verify'),
    path('passkeys/ingreso/opciones/', passkeys.authentication_options, name='passkey_authentication_options'),
    path('passkeys/ingreso/verificar/', passkeys.authentication_verify, name='passkey_authentication_verify'),
    path('passkeys/restablecer-password/', passkeys.password_reset, name='passkey_password'),
    path('passkeys/<int:pk>/revocar/', passkeys.revoke, name='passkey_revoke'),
    path('passkeys/preferencia/', passkeys.preference, name='passkey_preference'),
    # Autenticación y Recuperación
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('ficha-usuario/', views.ficha_usuario_view, name='ficha_usuario'),
    path('recuperar-password/', views.recuperar_password_view, name='recuperar_password'),
    path('validar-codigo/', views.validar_codigo_view, name='validar_codigo'),
    path('reenviar-codigo/', views.reenviar_codigo_view, name='reenviar_codigo'),
    path('cambiar-password/', views.cambiar_password_view, name='cambiar_password'),

    # Mantenedor de Roles
    path('mantenedores/roles/', views.roles_list_view, name='roles_list'),
    path('mantenedores/roles/crear/', views.roles_save_view, name='roles_create'),
    path('mantenedores/roles/<int:pk>/editar/', views.roles_save_view, name='roles_edit'),
    path('mantenedores/roles/<int:pk>/toggle/', views.roles_toggle_activo, name='roles_toggle'),
    path('mantenedores/roles/exportar-excel/', views.roles_export_excel, name='roles_excel'),

    # Mantenedor de Usuarios
    path('mantenedores/usuarios/', views.usuarios_list_view, name='usuarios_list'),
    path('mantenedores/usuarios/crear/', views.usuarios_save_view, name='usuarios_create'),
    path('mantenedores/usuarios/<int:pk>/editar/', views.usuarios_save_view, name='usuarios_edit'),
    path('mantenedores/usuarios/<int:pk>/toggle/', views.usuarios_toggle_activo, name='usuarios_toggle'),
    path('mantenedores/usuarios/exportar-excel/', views.usuarios_export_excel, name='usuarios_excel'),
]
