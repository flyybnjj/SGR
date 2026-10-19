import re

from django.db.models import Q, Value
from django.db.models.functions import Replace, Upper


def filter_with_rut(queryset, search, condition):
    if re.fullmatch(r'[0-9.kK\s-]+', search):
        compact = re.sub(r'[.\s-]+', '', search).upper()
        if compact:
            expression = Replace(Replace(Replace('rut', Value('.'), Value('')), Value('-'), Value('')), Value(' '), Value(''))
            queryset = queryset.alias(rut_compact_search=Upper(expression))
            condition |= Q(rut_compact_search__icontains=compact)
    return queryset.filter(condition)
