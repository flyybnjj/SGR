from django.test import TestCase
from config.access import can_manage
from usuarios.models import Usuario, Rol
from territorial.models import DelegacionMunicipal


class JobPermissionTests(TestCase):
    def test_new_optional_fields_have_python_defaults_before_database_insert(self):
        from atenciones.models import Accion
        self.assertEqual(Usuario().cargo, '')
        self.assertEqual(Accion().solicitante, '')
        self.assertEqual(Accion().telefono_solicitante, '')

    def test_job_title_does_not_grant_administration(self):
        delegation = DelegacionMunicipal.objects.create(nombre='Centro cargos', direccion='Centro')
        role = Rol.objects.create(nombre='Funcionario cargos', puede_gestionar=False)
        user = Usuario.objects.create_user(username='coordinador-cargo', rol=role, delegacion=delegation, cargo='Coordinador de Servicios Comunitarios')
        self.assertFalse(user.is_superuser)
        self.assertFalse(can_manage(user))
        user.cargo = 'Delegado Municipal'
        user.save(update_fields=['cargo'])
        self.assertFalse(can_manage(user))
