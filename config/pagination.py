from urllib.parse import urlsplit

from django.core.paginator import Paginator
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme

PAGE_SIZES = (10, 20, 50, 100)

def paginate(request, queryset):
    try:
        size = int(request.GET.get('per_page', 10))
    except (ValueError, TypeError):
        size = 10
    if size not in PAGE_SIZES:
        size = 10
    return Paginator(queryset, size).get_page(request.GET.get('page'))


def list_return(request, view_name):
    target = request.POST.get('volver') if request.method == 'POST' else request.GET.get('volver')
    path = reverse(view_name)
    if target and target.startswith(path) and url_has_allowed_host_and_scheme(target, allowed_hosts=set()):
        if urlsplit(target).path == path:
            return target
    return ''
