from django.core.paginator import Paginator

PAGE_SIZES = (10, 25, 50, 100)

def paginate(request, queryset):
    try:
        size = int(request.GET.get('per_page', 10))
    except (ValueError, TypeError):
        size = 10
    if size not in PAGE_SIZES:
        size = 10
    return Paginator(queryset, size).get_page(request.GET.get('page'))
