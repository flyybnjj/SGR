import io
import zipfile
from django.test import SimpleTestCase
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.exceptions import ValidationError
from pypdf import PdfWriter
from atenciones.documents import EvidenceDocumentField


class DocumentValidationTests(SimpleTestCase):
    def test_valid_pdf_is_accepted(self):
        buffer = io.BytesIO()
        writer = PdfWriter()
        writer.add_blank_page(width=200, height=200)
        writer.write(buffer)
        result = EvidenceDocumentField().clean(SimpleUploadedFile('respaldo.pdf', buffer.getvalue()))
        self.assertEqual(result.content_type, 'application/pdf')

    def test_javascript_pdf_is_rejected(self):
        buffer = io.BytesIO()
        writer = PdfWriter()
        writer.add_blank_page(width=200, height=200)
        writer.add_js('app.alert("No permitido")')
        writer.write(buffer)
        with self.assertRaises(ValidationError):
            EvidenceDocumentField().clean(SimpleUploadedFile('activo.pdf', buffer.getvalue()))

    def test_fake_document_and_executable_are_rejected(self):
        for name in ('falso.pdf', 'falso.docx', 'falso.xlsx', 'programa.exe'):
            with self.assertRaises(ValidationError):
                EvidenceDocumentField().clean(SimpleUploadedFile(name, b'MZ no es un documento'))

    def test_valid_xlsx_is_accepted(self):
        import openpyxl
        buffer = io.BytesIO()
        workbook = openpyxl.Workbook()
        workbook.active.append(['Informe', 1])
        workbook.save(buffer)
        result = EvidenceDocumentField().clean(SimpleUploadedFile('informe.xlsx', buffer.getvalue()))
        self.assertIn('spreadsheetml', result.content_type)

    def test_ooxml_with_macro_is_rejected(self):
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, 'w') as z:
            z.writestr('[Content_Types].xml', '<Types/>')
            z.writestr('word/document.xml', '<document/>')
            z.writestr('word/vbaProject.bin', 'macro')
        with self.assertRaises(ValidationError):
            EvidenceDocumentField().clean(SimpleUploadedFile('macro.docx', buffer.getvalue()))
