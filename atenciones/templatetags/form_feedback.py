"""Errores de formularios del servidor, sin incluir sus valores ni credenciales."""
from django import template
from django.forms import BaseForm
from django.utils.html import json_script

register = template.Library()


@register.simple_tag(takes_context=True)
def server_form_feedback(context):
    errors, seen, focus_id = [], set(), ''
    for form in context.flatten().values():
        if not isinstance(form, BaseForm) or id(form) in seen or not form.is_bound:
            continue
        seen.add(id(form))
        for name, messages in form.errors.items():
            field = form[name] if name in form.fields else None
            label = str(field.label) if field else 'Formulario'
            errors.extend(f'{label}: {message}' for message in messages)
            if field and not field.is_hidden and not focus_id:
                focus_id = field.id_for_label
    return json_script({'errors': errors, 'focus_id': focus_id}, 'server-form-feedback') if errors else ''
