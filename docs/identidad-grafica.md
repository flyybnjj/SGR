# Identidad municipal y color territorial

Revisión de los puntos de identidad de `Requisitos_Segunda_Evaluacion_SGR.pdf`, páginas 2 y 4. Se conserva el diseño aprobado por el titular; esta comprobación técnica no constituye autorización del Departamento de Comunicaciones ni certificación integral WCAG.

## Fuentes contrastadas

- [Normas gráficas municipales](https://laserena.cl/conocenos/normas-graficas).
- [Reglamento y manual de 2019](https://laserena.cl/documentos/docs/REGLAMENTO_normas_graficas_2019.pdf), 27 páginas: invariabilidad del escudo, proporciones y área de autonomía. La indicación de Arial de la página 25 se refiere a documentos internos, no establece una fuente obligatoria para todos los controles de una web.
- [SVG horizontal del servidor municipal](https://framework.laserena.cl/img/horizontal-color.svg), comparado con `static/img/horizontal-color.svg`.

## Comprobaciones realizadas

| Elemento | Comprobación y evidencia |
|---|---|
| Dibujo oficial | Los XML canonizados son idénticos: SHA-256 `03e09023bb66bd16691c1e74996cc43c8bada33c2199e245f8900e1b835f44e0`. El archivo municipal usa UTF-16 y la copia local UTF-8; esa conversión no cambió formas, texto dibujado, colores ni proporciones. |
| Rojo del logo | El propio SVG declara `#B80003`. Se usa como imagen y no se recolorea con el tema del funcionario. |
| Proporciones | El SVG tiene viewBox `0 0 10.153 2.784`. Se miden las cajas renderizadas en 390/1440 px con tolerancia del 1 % por la caja intrínseca 98 × 27. No se estira ni transforma el dibujo. |
| Logo legible | Imagen cargada, alternativa «Municipalidad de La Serena», sin filtros ni transformaciones en las vistas medidas. El marco reserva su espacio; las ondas se mantienen detrás de la interfaz. |
| Color predeterminado | Sin color confirmado, login, recuperación y cuenta conservan blanco/rojo institucional. Un valor antiguo no confirmado no configura el tema por una visita. |
| Tema territorial | El responsable y el personal heredan el mismo color de su sede de trabajo. Los estados de error, advertencia y éxito conservan su significado. El logo sigue rojo. |
| Contraste | Nueve temas incluyen rosa, azul, verde, blanco, negro y amarillo; primer plano de botones, texto seleccionado y texto sobre superficie tenue se calculan con mínimo 4.5:1. Los valores medidos están en el JSON. |
| Tipografía | Interfaz con pila nativa del sistema, tamaño base 16 px e interlineado 1.5. No se modifica la tipografía que forma parte del dibujo oficial. La aprobación estética del titular no se presenta como homologación municipal. |
| Adaptación | Navegador a 390/1440 px, sin desbordamiento horizontal en las vistas comprobadas; foco/hover, editor, tutorial y menú móvil se ejercitan sin fotografías. |
| Recuperación | Se comprueban pegado de los seis dígitos, movimiento del foco con flechas y botón accesible para mostrar/ocultar contraseña. |

Resultados: [identidad-grafica.json](evidencias/entrega-final/identidad-grafica.json) y [navegador-sin-capturas.json](evidencias/entrega-final/navegador-sin-capturas.json). Se usan datos sintéticos y una base SQLite temporal; no se modifican cuentas reales ni se generan capturas.

## Alcance de la revisión

Axe conserva por separado las comprobaciones incompletas de contraste sobre fotografías y superficies translúcidas. No se convierten en aprobadas por ausencia de infracciones automáticas. La comprobación del dibujo oficial, la geometría del logo y los temas es reproducible; no se afirma haber certificado todas las combinaciones posibles de imagen, dispositivo o tecnología de asistencia.

El PDF permite adaptar la distribución de sus mockups. La aplicación conserva el carrusel de cinco fotografías y el diseño territorial elegido; las propuestas ilustrativas no sustituyen las pantallas operativas ni sus datos.
