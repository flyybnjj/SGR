import math
import re
from datetime import datetime, time, timedelta, timezone
from html.parser import HTMLParser
from urllib.request import urlopen

from django.core.cache import cache
from django.utils.timezone import localtime


DMC_URL = 'https://climatologia.meteochile.gob.cl/application/diarioe/datosEstacionesPronostico'
STATIONS = {
    '290004': ('Elqui', 'La Serena'),
    '300024': ('Limarí', 'Ovalle'),
    '310040': ('Choapa', 'Illapel'),
}
AGE = re.compile(r'(?:(\d+)\s*hrs?\s*)?(?:(\d+)\s*min\s*)?(?:(\d+)\s*seg)?')


class StationTable(HTMLParser):
    def __init__(self):
        super().__init__()
        self.rows = {}
        self.row = None
        self.cell = None

    def handle_starttag(self, tag, attrs):
        if tag == 'tr':
            self.row = []
        elif tag == 'td' and self.row is not None:
            self.cell = []

    def handle_data(self, data):
        if self.cell is not None:
            self.cell.append(data)

    def handle_endtag(self, tag):
        if tag == 'td' and self.cell is not None and self.row is not None:
            self.row.append(''.join(self.cell).strip())
            self.cell = None
        elif tag == 'tr' and self.row is not None:
            if len(self.row) == 13 and self.row[1] in STATIONS and self.row[2] == 'DMC':
                self.rows[self.row[1]] = self.row
            self.row = None


def parse_observations(html):
    table = StationTable()
    table.feed(html)
    now = datetime.now(timezone.utc)
    readings = []
    for code, (province, city) in STATIONS.items():
        row = table.rows.get(code)
        if row is None:
            continue
        age = AGE.fullmatch(row[5])
        if not age or not any(age.groups()):
            continue
        hours, minutes, seconds = (int(value or 0) for value in age.groups())
        if timedelta(hours=hours, minutes=minutes, seconds=seconds) > timedelta(hours=2):
            continue
        try:
            temperature = float(row[8].replace(',', '.'))
            observed = datetime.combine(now.date(), time.fromisoformat(row[4]), tzinfo=timezone.utc)
        except ValueError:
            continue
        if not math.isfinite(temperature):
            continue
        if observed > now + timedelta(minutes=5):
            observed -= timedelta(days=1)
        if now - observed > timedelta(hours=2):
            continue
        readings.append({
            'province': province, 'city': city, 'station': row[3],
            'temperature': temperature, 'time': localtime(observed).strftime('%H:%M'),
        })
    return readings


def regional_weather():
    key = 'dashboard:clima-coquimbo:dmc:v1'
    cached = cache.get(key)
    if cached is not None:
        return cached
    try:
        with urlopen(DMC_URL, timeout=4) as response:
            readings = parse_observations(response.read(524288).decode('utf-8'))
    except (OSError, ValueError):
        readings = []
    cache.set(key, readings, timeout=300 if readings else 60)
    return readings
