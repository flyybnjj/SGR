from django.test import TestCase
from django.urls import reverse
from territorial.models import DelegacionMunicipal
from usuarios.models import Usuario, Rol
from vecinos.models import Vecino

class IdentitySearchTests(TestCase):
    def setUp(self):
        self.seat=DelegacionMunicipal.objects.create(nombre="Sede local",direccion="Calle uno")
        self.other=DelegacionMunicipal.objects.create(nombre="Otra sede",direccion="Calle dos")
        role=Rol.objects.create(nombre="Personal de prueba")
        self.user=Usuario.objects.create_user(username="operador",rol=role,delegacion=self.seat)
        self.client.force_login(self.user)
        self.marta=Vecino.objects.create(nombre="Marta Valenzuela Contreras",rut="14.892.103-5",territorio=self.seat)
        self.cristian=Vecino.objects.create(nombre="Cristian Alejandro Ramos Flores",rut="18899001-0",territorio=self.seat)
        self.match=Vecino.objects.create(nombre="Ana Local",rut="21984440-9",territorio=self.seat)
        Vecino.objects.create(nombre="Cristian Otra Sede",rut="21984441-7",territorio=self.other)

    def search(self,q):
        response=self.client.get(reverse("atenciones:attention_search"),{"q":q,"format":"json"})
        self.assertEqual(response.status_code,200)
        self.assertEqual(response.headers["Cache-Control"],"private, no-store")
        return response.json()["results"]

    def test_numeric_search_matches_rut_start_not_middle(self):
        self.assertEqual([p["id"] for p in self.search("21")],[self.match.pk])

    def test_dotted_rut_prefix_matches_unformatted_storage(self):
        self.assertEqual([p["id"] for p in self.search("21.984")],[self.match.pk])

    def test_complete_formatted_rut_matches(self):
        self.assertEqual([p["id"] for p in self.search("21.984.440-9")],[self.match.pk])

    def test_one_letter_returns_names_in_authorized_seat(self):
        self.assertEqual({p["id"] for p in self.search("c")},{self.marta.pk,self.cristian.pk,self.match.pk})

    def test_results_format_ruts_consistently_without_editing_storage(self):
        self.assertEqual(self.search("cr")[0]["rut"],"18.899.001-0")
        self.cristian.refresh_from_db()
        self.assertEqual(self.cristian.rut,"18899001-0")

    def test_no_results_and_empty_query(self):
        self.assertEqual(self.search("zzzzz"),[])
        self.assertEqual(self.search(""),[])

    def test_other_seat_never_leaks(self):
        self.assertEqual([p["id"] for p in self.search("cr")],[self.cristian.pk])

    def test_html_search_uses_same_prefix_and_formatted_rut(self):
        response=self.client.get(reverse("atenciones:attention_search"),{"q":"21"})
        self.assertContains(response,"21.984.440-9")
        self.assertNotContains(response,self.marta.nombre)

    def test_results_remain_bounded_and_ordered(self):
        for n in range(12):
            Vecino.objects.create(nombre=f"Cristian Vecino {n:02d}",territorio=self.seat)
        result=self.search("cr")
        self.assertEqual(len(result),8)
        self.assertEqual([p["nombre"] for p in result],sorted(p["nombre"] for p in result))

    def test_excessively_long_query_is_rejected(self):
        response=self.client.get(reverse("atenciones:attention_search"),{"q":"a"*121,"format":"json"})
        self.assertEqual(response.status_code,400)

    def test_padron_rut_prefix_and_display_match_suggestions(self):
        response=self.client.get(reverse("vecinos:vecinos_list"),{"q":"21"})
        self.assertContains(response,"21.984.440-9")
        self.assertNotContains(response,self.marta.nombre)
        self.assertNotContains(response,"Cristian Otra Sede")

    def test_padron_clear_returns_all_local_records(self):
        response=self.client.get(reverse("vecinos:vecinos_list"),{"q":""})
        self.assertEqual(response.context["page_obj"].paginator.count,3)

    def test_padron_page_size_is_applied_with_search(self):
        for n in range(30):
            Vecino.objects.create(nombre=f"Cristian Prueba {n:02d}",territorio=self.seat)
        response=self.client.get(reverse("vecinos:vecinos_list"),{"q":"cr","per_page":"20","page":"1"})
        self.assertEqual(len(response.context["page_obj"]),20)
        self.assertEqual(response.context["page_obj"].paginator.count,31)
        self.assertNotContains(response,"Cristian Otra Sede")
