from django.db import migrations
import re


def normalize_legacy(apps, schema_editor):
    Model = apps.get_model("vecinos", "Vecino")
    records = list(Model.objects.exclude(rut__isnull=True).values_list("pk", "rut"))
    groups = {}
    for pk, raw in records:
        if not raw.strip():
            Model.objects.filter(pk=pk).update(rut=None)
            continue
        compact = raw.strip().upper().replace(".", "").replace(" ", "")
        if not re.fullmatch(r"\d{1,8}-?[0-9K]", compact):
            continue
        compact = compact.replace("-", "")
        body, dv = compact[:-1], compact[-1]
        total = sum(int(n) * (2 + i % 6) for i, n in enumerate(reversed(body)))
        expected = "0123456789K0"[11 - total % 11]
        if dv == expected:
            canonical = f"{int(body)}-{dv}"
            groups.setdefault(canonical, []).append(pk)
    # Ambiguous legacy duplicates remain intact for manual review: never merge people.
    for canonical, ids in groups.items():
        if len(ids) == 1:
            Model.objects.filter(pk=ids[0]).update(rut=canonical)


class Migration(migrations.Migration):
    dependencies = [("vecinos", "0002_alter_vecino_direccion_alter_vecino_nombre_and_more")]
    operations = [migrations.RunPython(normalize_legacy, migrations.RunPython.noop)]
