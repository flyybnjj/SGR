from django import forms
from django.db import transaction


class NombreCatalogoUnicoMixin:
    campo_ambito_nombre = None

    def clean(self):
        data = super().clean()
        try:
            self.validar_nombre_unico(data)
        except forms.ValidationError as error:
            self.add_error(None, error)
        return data

    def validar_nombre_unico(self, data):
        name = data.get('nombre')
        if not name:
            return
        name = ' '.join(name.split())
        data['nombre'] = name
        queryset = self._meta.model.objects.exclude(pk=self.instance.pk)
        scope = self.campo_ambito_nombre
        if scope:
            if not data.get(scope):
                return
            queryset = queryset.filter(**{scope: data[scope]})

        if any(' '.join(existing.split()).casefold() == name.casefold()
               for existing in queryset.values_list('nombre', flat=True)):
            raise forms.ValidationError({'nombre': 'Ya existe un registro con este nombre. Puedes reactivar el existente.'})

    @transaction.atomic
    def save(self, commit=True):
        instance = super().save(commit=False)
        self.validar_nombre_unico(self.cleaned_data)
        if commit:
            instance.save()
            self.save_m2m()
        return instance
