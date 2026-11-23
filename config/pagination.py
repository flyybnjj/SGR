from urllib.parse import urlsplit

from django.core.paginator import Paginator
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme

PAGE_SIZES = (10, 20, 50, 100)

def paginate(request, queryset, *, allow_all=True):
    requested_size = request.GET.get('per_page', '10')
    if allow_all and requested_size == 'all':
        paginator = Paginator(queryset, 1)
        paginator.per_page = max(1, paginator.count)
        page = paginator.page(1)
        page.page_size = 'all'
        return page
    try:
        size = int(requested_size)
    except (ValueError, TypeError):
        size = 10
    if size not in PAGE_SIZES:
        size = 10
    page = Paginator(queryset, size).get_page(request.GET.get('page'))
    page.page_size = size
    return page


def list_return(request, view_name):
    target = request.POST.get('volver') if request.method == 'POST' else request.GET.get('volver')
    path = reverse(view_name)
    if target and target.startswith(path) and url_has_allowed_host_and_scheme(target, allowed_hosts=set()):
        if urlsplit(target).path == path:
            return target
    return ''
