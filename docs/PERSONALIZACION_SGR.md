# Personalización y avisos de contraseña

El despliegue con `deploy_ec2.sh` instala `sgr-password-reminder.timer` para
ejecutar cada día a las 09:00 de Santiago el comando
`venv/bin/python manage.py recordar_vencimiento_password`. Usa el directorio
del SGR y su configuración SMTP. `--simular` cuenta candidatos sin enviar
mensajes.

Las cuentas existentes sin historial tienen un plazo inicial de 30 días desde
la migración. El último cambio solo se muestra cuando se registró un cambio real.

## Fotografías de la vista local

- Faro Monumental — https://www.travelandes.com/es/chile/la-serena/
- Isla Damas — https://www.c5n.com/lifestyle/vacaciones-chile-2025-la-playa-tranquila-aguas-turquesas-que-esta-una-isla-n185283
- Guanaqueros — https://www.airbnb.com.ec/rooms/846194473694128240
- Pichidangui — https://www.tripadvisor.cl/Attractions-g2547333-Activities-Pichidangui_Coquimbo_Region.html
- Pisco Elqui — https://es.wikiloc.com/rutas-alpinismo/cerro-el-llano-pisco-elqui-43170733
- Puclaro — https://www.gochile.cl/es/fotos/109902-embalse-puclaro.htm
- Limarí — https://www.casonagourmet.cl/ruta-vinas-pisqueras.html
- Fray Jorge — Biovipah, CC BY-SA 4.0, https://commons.wikimedia.org/wiki/File:Bosque_y_cerros_de_Fray_Jorge.jpg
- Tololo — CTIO/NOIRLab/NSF/AURA/T. Matsopoulos, https://noirlab.edu/public/images/Cerro-Tololo-Drone-Pano_13-CC/

Las copias de vista local están reducidas y convertidas a WebP. La miniatura
recorta la foto. Confirma los permisos de reutilización antes de publicar las
fotos de referencia de procedencia externa.
