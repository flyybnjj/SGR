import io

import openpyxl
from openpyxl.drawing.image import Image as ExcelImage
from openpyxl.utils import get_column_letter
from PIL import Image, ImageOps

from config.excel_utils import export_queryset_to_excel


def export_actions_with_photos(actions, headers, rows):
    final_photos = [action.final_records[0].evidencia_final if action.final_records else None for action in actions]
    photo_rows = [list(row) + ['Foto inicial' if action.evidencia else 'Sin foto inicial', 'Foto final' if final else 'Sin foto final'] for row, action, final in zip(rows, actions, final_photos)]
    response = export_queryset_to_excel('Acciones', 'Acciones', headers + ['Foto inicial', 'Foto final'], photo_rows)
    workbook = openpyxl.load_workbook(io.BytesIO(response.content))
    sheet = workbook.active
    for index, (action, final) in enumerate(zip(actions, final_photos), 4):
        for column, evidence in [(len(headers) + 1, action.evidencia), (len(headers) + 2, final)]:
            if not evidence:
                continue
            cell = sheet.cell(row=index, column=column)
            try:
                with evidence.open('rb') as source, Image.open(source) as photo:
                    if photo.format not in {'JPEG', 'PNG', 'WEBP'} or photo.width * photo.height > 20_000_000:
                        raise ValueError('Imagen no compatible')
                    thumb = ImageOps.exif_transpose(photo)
                    thumb.thumbnail((160, 120))
                    data = io.BytesIO()
                    thumb.save(data, format='PNG')
                    data.seek(0)
                image = ExcelImage(data)
                sheet.add_image(image, f'{get_column_letter(column)}{index}')
                cell.value = ''
                sheet.row_dimensions[index].height = max(sheet.row_dimensions[index].height or 20, 96)
            except (OSError, ValueError, Image.DecompressionBombError):
                cell.value = 'Archivo no disponible'
    for column in [len(headers) + 1, len(headers) + 2]:
        sheet.column_dimensions[get_column_letter(column)].width = 26
    output = io.BytesIO()
    workbook.save(output)
    response.content = output.getvalue()
    response['Cache-Control'] = 'private, no-store'
    return response
