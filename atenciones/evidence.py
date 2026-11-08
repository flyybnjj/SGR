import io
import warnings
from pathlib import Path

from django import forms
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.validators import FileExtensionValidator
from PIL import Image, ImageOps, UnidentifiedImageError


class EvidenceImageField(forms.ImageField):
    def to_python(self, data):
        if not data:
            return None
        if data.size > 5 * 1024 * 1024:
            raise forms.ValidationError('La imagen no puede superar 5 MB.')
        FileExtensionValidator(['jpg', 'jpeg', 'png', 'webp'])(data)
        image = super().to_python(data)
        try:
            with warnings.catch_warnings():
                warnings.simplefilter('error', Image.DecompressionBombWarning)
                image.seek(0)
                with Image.open(image) as decoded:
                    image_format = decoded.format
                    if image_format not in {'JPEG', 'PNG', 'WEBP'}:
                        raise forms.ValidationError('Use una imagen JPEG, PNG o WebP.')
                    if decoded.width * decoded.height > 20_000_000:
                        raise forms.ValidationError('La imagen no puede superar 20 megapíxeles.')
                    decoded.load()
                    cleaned = ImageOps.exif_transpose(decoded)
                    if image_format == 'JPEG' and cleaned.mode not in {'RGB', 'L'}:
                        cleaned = cleaned.convert('RGB')
                    cleaned.info.clear()
                    output = io.BytesIO()
                    cleaned.save(output, format=image_format)
        except (OSError, ValueError, UnidentifiedImageError, Image.DecompressionBombError, Image.DecompressionBombWarning):
            raise forms.ValidationError('No se pudo leer la imagen. Adjunte una foto JPEG, PNG o WebP válida.')
        if output.tell() > 5 * 1024 * 1024:
            raise forms.ValidationError('La imagen procesada no puede superar 5 MB.')
        extension, mime = {'JPEG': ('jpg', 'image/jpeg'), 'PNG': ('png', 'image/png'), 'WEBP': ('webp', 'image/webp')}[image_format]
        return SimpleUploadedFile(Path(image.name).stem + '.' + extension, output.getvalue(), content_type=mime)


class MultipleImageInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class ExtraPhotosField(forms.Field):
    widget = MultipleImageInput(attrs={'accept': 'image/jpeg,image/png,image/webp'})

    def clean(self, data):
        files = data if isinstance(data, (list, tuple)) else [data] if data else []
        if len(files) > 4:
            raise forms.ValidationError('Puedes adjuntar hasta cuatro fotos adicionales: cinco en total por etapa.')
        return [EvidenceImageField().clean(file) for file in files]


def guardar_fotos(action, files, author, resolution=None):
    from .models import FotoAccion
    records = []
    try:
        for file in files:
            obj = FotoAccion(accion=action, archivo=file, autor=author, etapa='despues' if resolution else 'antes', resolucion=resolution)
            records.append(obj)
            obj.save()
    except Exception:
        for record in records:
            if record.archivo and record.archivo._committed:
                record.archivo.delete(save=False)
        raise
    return records
