from datetime import date
from io import BytesIO

from django.test import SimpleTestCase
from openpyxl import load_workbook

from config.excel_utils import export_queryset_to_excel


class ExcelResilienceTests(SimpleTestCase):
    def workbook(self, rows):
        response = export_queryset_to_excel('Reporte', 'Reporte', ['Dato'], rows)
        self.assertEqual(response.status_code, 200)
        return load_workbook(BytesIO(response.content)).active

    def test_copied_control_characters_do_not_break_export(self):
        original = 'Atención\x00\x08\x0b\x0c\x1b municipal\tcon detalle\ny dirección'
        sheet = self.workbook([[original]])
        self.assertEqual(sheet['A4'].value, 'Atención municipal\tcon detalle\ny dirección')

    def test_export_keeps_formulas_as_text_and_preserves_native_values(self):
        sheet = self.workbook([['=1+2'], [25], [date(2026, 10, 19)]])
        self.assertEqual(sheet['A4'].value, '=1+2')
        self.assertEqual(sheet['A4'].data_type, 's')
        self.assertEqual(sheet['A5'].value, 25)
        self.assertEqual(sheet['A6'].value.date(), date(2026, 10, 19))
