import hashlib
import json
from functools import wraps
from django.conf import settings
from django.core.exceptions import PermissionDenied, ValidationError
from django.http import JsonResponse, Http404, QueryDict
from django.utils import timezone
from django.utils.crypto import constant_time_compare
from django.utils.datastructures import MultiValueDict
from django.views.decorators.csrf import csrf_exempt
from django.contrib.messages.storage.base import BaseStorage
from config.access import operational
from .models import TokenMovil


class ApiMessages(BaseStorage):
    def _get(self, *args, **kwargs):
        return [], True

    def _store(self, messages, response, *args, **kwargs):
        return []


def payload(request):
    if request.content_type == 'application/json':
        try:
            length = int(request.META.get('CONTENT_LENGTH') or 0)
        except ValueError:
            raise ValidationError('La longitud del cuerpo no es válida.')
        if length > 65536:
            raise ValidationError('El cuerpo JSON es demasiado grande.')
        try:
            data = json.loads(request.body or b'{}')
        except (ValueError, UnicodeDecodeError):
            raise ValidationError('El JSON no es válido.')
        if not isinstance(data, dict) or any(not isinstance(v, (str, int, float, bool, type(None))) for v in data.values()):
            raise ValidationError('Envía un objeto JSON con campos simples.')
        post = QueryDict('', mutable=True)
        for key, value in data.items():
            post[key] = '' if value is None else str(value)
        request._post = post
        request._files = MultiValueDict()
        return post
    return request.POST


def endpoint(methods=('GET',), authenticated=True):
    def decorate(view):
        @csrf_exempt
        @wraps(view)
        def wrapped(request, *args, **kwargs):
            if not settings.DEBUG and not request.is_secure():
                return JsonResponse({'error': 'Utiliza HTTPS para acceder a la API.'}, status=400)
            if request.method not in methods:
                response = JsonResponse({'error': 'Método no permitido.'}, status=405)
                response['Allow'] = ', '.join(methods)
                return response
            try:
                if authenticated:
                    header = request.headers.get('Authorization', '')
                    token = None
                    if header.startswith('Bearer ') and len(header) <= 512:
                        digest = hashlib.sha256(header[7:].encode()).hexdigest()
                        token = TokenMovil.objects.select_related('usuario__rol', 'usuario__delegacion').filter(resumen=digest, expira__gt=timezone.now(), revocado=False).first()
                    if not token or not operational(token.usuario) or not constant_time_compare(token.sello_password, token.usuario.get_session_auth_hash()) or token.usuario.debe_cambiar_password:
                        response = JsonResponse({'error': 'El acceso expiró o no es válido. Inicia sesión nuevamente.'}, status=401)
                        response['WWW-Authenticate'] = 'Bearer'
                        return response
                    request.user, request.api_token = token.usuario, token
                    request._messages = ApiMessages(request)
                response = view(request, *args, **kwargs)
            except Http404:
                response = JsonResponse({'error': 'Registro no encontrado.'}, status=404)
            except PermissionDenied:
                response = JsonResponse({'error': 'Tu perfil no tiene permiso para esta operación.'}, status=403)
            except ValidationError as error:
                response = JsonResponse({'error': 'Revisa los datos enviados.', 'detalles': error.messages}, status=400)
            response['Cache-Control'] = 'private, no-store'
            response['Vary'] = 'Authorization'
            return response
        return wrapped
    return decorate
