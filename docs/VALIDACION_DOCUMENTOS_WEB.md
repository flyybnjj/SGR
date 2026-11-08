# Respaldos documentales

Formatos web: fotos JPEG/PNG/WebP, PDF, Word DOCX y Excel XLSX. Los formatos antiguos DOC/XLS y los documentos con macros no se admiten. Las fotos principales de inicio y cierre conservan la obligatoriedad acordada; los documentos son complementarios.

Cada etapa admite una foto principal, cuatro fotos adicionales y tres documentos. Cada foto tiene un máximo de 5 MB y 20 megapíxeles; cada documento, 10 MB. El límite del proxy debe permitir el envío completo (60 MB), manteniendo las comprobaciones por archivo del servidor.

La extensión no basta: se comprueba el contenido. Los PDF se analizan con `PdfReader` de pypdf 6.21.4 y se rechazan cifrado, JavaScript, acciones automáticas, archivos incrustados y límites excesivos de páginas/objetos. Referencia de la API utilizada: [documentación oficial de PdfReader](https://pypdf.readthedocs.io/en/stable/modules/PdfReader.html).

Los DOCX/XLSX deben tener la estructura OOXML esperada. Se limitan las entradas y el tamaño descomprimido, y se rechazan macros, objetos incrustados y referencias externas automáticas. Los hipervínculos normales no se ejecutan en el servidor. Estas comprobaciones de formato y contenido no equivalen a una certificación antivirus.

El almacenamiento sigue siendo privado. Las fotos se entregan mediante vistas autenticadas y los documentos como descargas adjuntas con `nosniff` y `private, no-store`. El acceso se valida por objeto y territorio. La API móvil rechaza documentos y mantiene el flujo de imágenes.
