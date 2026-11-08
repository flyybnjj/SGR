import io
import zipfile
import re
from pathlib import PurePosixPath
from django.utils.text import get_valid_filename
from xml.etree import ElementTree
from django import forms
from django.core.files.uploadedfile import SimpleUploadedFile
from pypdf import PdfReader
from pypdf.generic import IndirectObject, DictionaryObject, ArrayObject
from .evidence import MultipleImageInput


MIMES = {'pdf': 'application/pdf', 'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', 'xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'}


def validar_pdf(content):
    reader = PdfReader(io.BytesIO(content), strict=True, xref_stream_maximum_entries=10000)
    try:
        if reader.is_encrypted or not 0 < len(reader.pages) <= 500:
            raise ValueError('PDF cifrado o demasiado extenso')
        queue, seen = [reader.root_object], set()
        blocked = {'/JavaScript', '/JS', '/OpenAction', '/AA', '/Launch', '/EmbeddedFiles', '/RichMedia'}
        while queue:
            node = queue.pop()
            if isinstance(node, IndirectObject):
                marker = (node.idnum, node.generation)
                if marker in seen:
                    continue
                seen.add(marker)
                if len(seen) > 10000:
                    raise ValueError('Demasiados objetos PDF')
                node = node.get_object()
            if isinstance(node, DictionaryObject):
                if blocked.intersection(str(k) for k in node.keys()) or str(node.get('/S')) in ('/JavaScript', '/Launch'):
                    raise ValueError('Contenido activo no permitido')
                queue.extend(node.values())
            elif isinstance(node, ArrayObject):
                queue.extend(node)
    finally:
        reader.close()


def validar_office(content, extension):
    with zipfile.ZipFile(io.BytesIO(content)) as archive:
        infos = archive.infolist()
        names = [i.filename for i in infos]
        if len(infos) > 2000 or len(names) != len(set(names)) or sum(i.file_size for i in infos) > 40 * 1024 * 1024:
            raise ValueError('Paquete demasiado grande')
        required = 'word/document.xml' if extension == 'docx' else 'xl/workbook.xml'
        if '[Content_Types].xml' not in names or required not in names:
            raise ValueError('El contenido no corresponde al formato')
        for entry in infos:
            path = PurePosixPath(entry.filename)
            lower = entry.filename.lower()
            if entry.flag_bits & 1 or path.is_absolute() or '..' in path.parts or any(v in lower for v in ('vbaproject', 'activex', '/embeddings/', 'xl/externallinks/', 'xl/connections', 'xl/querytables/', 'xl/macrosheets/')):
                raise ValueError('Macros o contenido incrustado no permitido')
            if entry.compress_type not in (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED):
                raise ValueError('Compresión no permitida')
            if lower.endswith('.rels') or entry.filename in ('[Content_Types].xml', required) or lower.startswith('xl/worksheets/') and lower.endswith('.xml'):
                if entry.file_size > 5 * 1024 * 1024:
                    raise ValueError('Documento demasiado complejo')
                xml = archive.read(entry)
                if b'<!DOCTYPE' in xml.upper() or b'<!ENTITY' in xml.upper() or b'macroenabled' in xml.lower():
                    raise ValueError('Contenido XML no permitido')
                tree = ElementTree.fromstring(xml)
                if entry.filename == required:
                    allowed_namespaces = ('http://schemas.openxmlformats.org/wordprocessingml/2006/main', 'http://purl.oclc.org/ooxml/wordprocessingml/main') if extension == 'docx' else ('http://schemas.openxmlformats.org/spreadsheetml/2006/main', 'http://purl.oclc.org/ooxml/spreadsheetml/main')
                    element = 'document' if extension == 'docx' else 'workbook'
                    if tree.tag not in {f'{{{namespace}}}{element}' for namespace in allowed_namespaces}:
                        raise ValueError('La raíz XML no corresponde al formato')
                for relation in tree.iter():
                    if relation.tag.rsplit('}', 1)[-1] == 'f' and re.search(r'(?i)WEBSERVICE\s*\(|\bCALL\s*\(|REGISTER\.ID|\|[^!]*!', relation.text or ''):
                        raise ValueError('Fórmula externa activa no permitida')
                    if relation.attrib.get('TargetMode') == 'External' and not relation.attrib.get('Type', '').endswith('/hyperlink'):
                        raise ValueError('Referencia externa activa no permitida')


class EvidenceDocumentField(forms.FileField):
    def clean(self, data, initial=None):
        file = super().clean(data, initial)
        if not file:
            return None
        extension = PurePosixPath(file.name.replace('\\', '/')).suffix.lstrip('.').lower()
        if extension not in MIMES or file.size > 10 * 1024 * 1024:
            raise forms.ValidationError('Adjunta un PDF, Word DOCX o Excel XLSX de hasta 10 MB. No se admiten archivos con macros.')
        file.seek(0)
        content = file.read()
        try:
            if extension == 'pdf':
                validar_pdf(content)
            else:
                validar_office(content, extension)
        except Exception:
            raise forms.ValidationError('No se pudo validar el documento. Usa un archivo sin contraseña, macros, archivos incrustados ni acciones automáticas.')
        return SimpleUploadedFile(get_valid_filename(PurePosixPath(file.name.replace('\\', '/')).name), content, content_type=MIMES[extension])


class ExtraDocumentsField(forms.Field):
    widget = MultipleImageInput(attrs={'accept': '.pdf,.docx,.xlsx'})

    def clean(self, data):
        files = data if isinstance(data, (list, tuple)) else [data] if data else []
        if len(files) > 3:
            raise forms.ValidationError('Adjunta como máximo tres documentos por etapa.')
        return [EvidenceDocumentField().clean(file) for file in files]


class EvidenceAnyField(forms.FileField):
    def clean(self, data, initial=None):
        if not data or not hasattr(data, 'name'):
            return super().clean(data, initial)
        extension = data.name.rsplit('.', 1)[-1].lower()
        if extension in ('jpg', 'jpeg', 'png', 'webp'):
            from .evidence import EvidenceImageField
            file = EvidenceImageField(required=self.required).clean(data, initial)
            file.name = get_valid_filename(PurePosixPath(file.name.replace('\\', '/')).name)
            return file
        return EvidenceDocumentField(required=self.required).clean(data, initial)


def guardar_documentos(action, files, author, resolution=None):
    from .models import DocumentoAccion
    records = []
    try:
        for file in files:
            obj = DocumentoAccion(accion=action, resolucion=resolution, archivo=file, nombre_original=file.name, etapa='despues' if resolution else 'antes', autor=author)
            records.append(obj)
            obj.save()
    except Exception:
        for obj in records:
            if obj.archivo and obj.archivo._committed:
                obj.archivo.delete(save=False)
        raise
    return records
