from django import forms


class NombreCatalogoUnicoMixin:
    campo_ambito_nombre = None

    def clean(self):
        data = super().clean()
        name = data.get('nombre')
        if not name:
            return data
        name = ' '.join(name.split())
        data['nombre'] = name
        queryset = self._meta.model.objects.exclude(pk=self.instance.pk)
        scope = self.campo_ambito_nombre
        if scope:
            if not data.get(scope):
                return data
            queryset = queryset.filter(**{scope: data[scope]})
        # casefold también cubre diferencias Unicode y espacios heredados.
        if any(' '.join(existing.split()).casefold() == name.casefold()
               for existing in queryset.values_list('nombre', flat=True)):
            self.add_error('nombre', 'Ya existe un registro con este nombre. Puedes reactivar el existente.')
        return data
