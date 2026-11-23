(() => {
  'use strict';
  const configuration = document.getElementById('sgr-tutorial-config');
  if (!configuration) return;
  const config = JSON.parse(configuration.textContent);
  const motion = window.matchMedia('(prefers-reduced-motion: reduce)');
  const launch = document.getElementById('tour-tutorial-btn');
  const requestedTour = new URLSearchParams(window.location.search).get('tutorial');
  let tour, waiting, starting = false;
  const add = (element, title, description) => ({element, popover: {title, description, side: 'bottom', align: 'center'}});
  const findVisible = selector => [...document.querySelectorAll(selector)].find(element => {
    if (element.closest('[hidden], [inert]') || !element.getClientRects().length) return false;
    const box = element.getBoundingClientRect();
    if (box.width === 0 || box.height === 0 || getComputedStyle(element).visibility !== 'visible') return false;
    for (let ancestor = element.parentElement; ancestor; ancestor = ancestor.parentElement) {
      if (ancestor.matches('details:not([open])') && !ancestor.querySelector(':scope > summary')?.contains(element)) return false;
    }
    return true;
  });
  const visible = step => Boolean(findVisible(step.element));
  const prepare = steps => steps.flatMap(step => {
    const element = findVisible(step.element);
    return element ? [{...step, element}] : [];
  });
  const contextSteps = () => {
    const admin = config.profile === 'administrador';
    const responsible = config.profile === 'responsable';
    const scope = config.page === 'personal' ? 'tu actividad personal' : admin ? 'el ámbito municipal o el territorio que selecciones' : 'tu delegación';
    const steps = [];
    if (config.namespace === 'dashboard' && config.page === 'novedades') {
      steps.push(add('#updates-launch', 'Novedades de SGR', 'El indicador Nuevo aparece cuando hay mejoras que todavía no has marcado como leídas. Puedes consultarlas sin interrumpir tu trabajo.'));
      steps.push(add('[data-update-tour]', 'Ver cómo funciona una mejora', 'Cada publicación explica un cambio disponible para tu perfil. Cuando haya un recorrido, puedes abrirlo desde su publicación.'));
      steps.push(add('[data-update-read]', 'Guardar tu lectura', 'Pulsa Marcar como leída cuando termines. La confirmación se guarda para tu cuenta; el recorrido seguirá disponible.'));
      return prepare(steps);
    }
    if (config.namespace === 'operaciones' && config.page === 'avisos') {
      steps.push(add('.avisos-heading h1', 'Mis avisos', 'Los avisos se agrupan por fecha, con los más recientes arriba.'));
      steps.push(add('.avisos-tabs', 'Revisar los avisos sin leer', 'Alterna entre Todos y No leídos para ponerte al día.'));
      steps.push(add('.aviso-actions', 'Marcar o abrir un aviso', 'El visto marca como leído y la flecha abre el registro relacionado.'));
      return prepare(steps);
    }
    if (config.namespace === 'dashboard' && config.page === 'personal') {
      steps.push(add('.personal-metrics', 'Tu trabajo del trimestre', 'Consulta tus actividades a cargo, las atenciones que registraste y las actividades en revisión.'));
      steps.push(add('.personal-commitments', 'Próximos compromisos', 'Abre una actividad para revisar su fecha y seguimiento.'));
      steps.push(add('.dashboard-heading-actions [data-open-avisos]', 'Abrir Mis avisos', 'Revisa tus avisos sin salir de Mi resumen.'));
      return prepare(steps);
    }
    const modules = {
      organizaciones: ['Organizaciones del territorio', 'Consulta la ficha, su asignación y los datos originales. Las organizaciones importadas requieren revisión; no son cuentas de usuario.'],
      cartas: ['Bandeja de cartas', 'Registra remitente y contacto, asigna un encargado y conserva el seguimiento. Una carta se cierra con respuesta o con un motivo de No aplica. El ajuste formal de puntaje requiere validación y respaldo.'],
    };
    if (modules[config.namespace]) {
      const [title, description] = modules[config.namespace];
      steps.push(add('.page-heading', title, description));
      steps.push(add('.transaction-filter', 'Encontrar un registro', 'La búsqueda y el estado se actualizan automáticamente. Los resultados se limitan al ámbito autorizado para tu cuenta.'));
      steps.push(add('.activity-board', 'Seguir el trabajo', 'Las tarjetas pertenecen a esta página; los contadores muestran toda la consulta. Alterna con Bandeja y expediente para leer el detalle junto al listado.'));
      steps.push(add('.table-responsive', 'Consultar la información', 'Abre una ficha desde el nombre. Puedes cambiar de página sin perder los filtros.'));
      steps.push(add('.form-panel', 'Guardar los datos', 'Completa los campos y revisa los errores indicados al guardar. Los cambios de seguimiento conservan su historial.'));
      return prepare(steps);
    }
    if (config.namespace === 'atenciones' && config.page.startsWith('action')) {
      steps.push(add('.page-heading', 'Actividades y seguimiento', 'Alterna entre tabla y tablero y abre la ficha para consultar responsable, compromiso y avance.'));
      steps.push(add('.transaction-filter', 'Filtrar actividades', 'El avance del trabajo y la revisión de evidencia son estados distintos. Los filtros se aplican a la consulta y a la exportación.'));
      steps.push(add('.activity-board', 'Tablero por avances', 'Ingresada, Asignada, En proceso y Finalizada organizan el trabajo. Los contadores abarcan toda la consulta y las tarjetas corresponden a esta página. Los botones de avance no aprueban la evidencia.'));
      steps.push(add('.tubo-metrics', 'Resumen del tubo', 'Gestiones, realizadas, en proceso y alertas usan los filtros actuales, sin limitarse a las tarjetas de una sola página.'));
      steps.push(add('.evidence-comparison', 'Comparar el trabajo', 'Consulta las fotografías inicial y final lado a lado. Los documentos siguen siendo privados.'));
      steps.push(add('[name="fecha_actividad"]', 'Fecha y cierre semanal', 'El lunes permite ingresar la semana anterior. Desde el martes solo puedes registrar la semana actual; no se admiten fechas futuras.'));
      steps.push(add('[name="solicitante"]', 'Datos necesarios para puntuar', 'Las actividades nuevas necesitan nombre y teléfono del beneficiario para sumar al cumplimiento. También se aplica el límite de siete registros diarios por funcionario.'));
      steps.push(add('[name="documentos"]', 'Respaldar el trabajo', 'La foto inicial es opcional. Puedes adjuntar hasta cinco fotos y tres respaldos PDF, DOCX o XLSX; los archivos permanecen privados.'));
      steps.push(add('#resolve-action-title', 'Revisar el trabajo terminado', 'Aprobar exige foto final. Finalizar el avance no equivale a aprobar la evidencia ni vuelve puntuable una actividad excluida.'));
      steps.push(add('.form-panel', 'Asignación y avance', 'Los campos disponibles dependen de tu rol y tu relación con la actividad. Los cambios de avance quedan registrados.'));
      return prepare(steps);
    }
    if (config.namespace === 'territorial' && config.page.startsWith('ausencia')) {
      steps.push(add('.page-heading', 'Ausencias y metas individuales', 'Los responsables registran intervalos de lunes a viernes. No se solicitan diagnósticos médicos.'));
      steps.push(add('.form-panel', 'Registrar un intervalo', 'Selecciona a una persona autorizada y las fechas. No se permiten ausencias superpuestas.'));
      steps.push(add('.table-responsive', 'Conservar el historial', 'Anular una ausencia conserva su registro y restituye los días disponibles en las metas individuales.'));
      return prepare(steps);
    }
    if (config.namespace === 'usuarios' && config.page === 'appearance') {
      steps.push(add('.landscape-grid', 'Elegir un paisaje', 'Selecciona una foto o activa Fondo blanco. Con fondo blanco se conserva la última foto que elegiste.'));
      steps.push(add('[data-landscape-preview]', 'Comparar en tiempo real', 'La vista previa cambia con el fondo, el estilo y el color de la delegación.'));
      steps.push(add('.appearance-style-options', 'Comparar los estilos', 'Prueba Modo normal y Modo vidrio antes de guardar.'));
      steps.push(add('[data-appearance-save]', 'Guardar apariencia', 'Guarda tu elección para recuperarla en tu próximo ingreso.'));
      return prepare(steps);
    }
    if (config.namespace === 'usuarios' && ['account_settings', 'account_password'].includes(config.page)) {
      steps.push(add('.account-tabs', 'Perfil y apariencia', 'Usa Perfil para la seguridad de la cuenta y Apariencia para elegir el fondo y el estilo.'));
      steps.push(add('.account-options', 'Cuenta y seguridad', 'Abre Nombre de usuario, Contraseña o Passkeys para revisar sus ajustes.'));
      steps.push(add('.account-form summary', 'Editar tus datos', config.page === 'account_password'
        ? 'Revisa el último cambio, el próximo vencimiento y el plazo. Abre Cambiar contraseña para actualizarla.'
        : 'Abre Cambiar nombre de usuario y confirma con tu contraseña actual o un código al correo.'));
      return prepare(steps);
    }
    if (config.namespace === 'atenciones' && config.page === 'meta_list') {
      steps.push(add('#id_trimestre, .transaction-filter', 'Elegir un trimestre', 'Filtra las metas por el período que quieres revisar. La consulta también permite acotar por delegación o por tus propias metas.'));
      steps.push(add('.table-responsive', 'Consultar avance y reprogramar', 'Compara las acciones aprobadas y el objetivo ajustado. Si tu perfil puede gestionar metas, Reprogramar permite continuar en un trimestre futuro.'));
      steps.push(add('.grid-pagination', 'Mostrar resultados', 'Cambia las filas por página o elige Todos para ver las metas filtradas.'));
      return prepare(steps);
    }
    if (config.auto_start === 'bienvenida') {
      steps.push(add('#tour-hero-banner', admin ? 'Bienvenido al resumen municipal' : responsible ? 'Bienvenido, responsable de delegación' : 'Bienvenido a tu espacio de trabajo',
        admin ? 'Consulta todas las delegaciones, revisa sus resultados y organiza responsables y equipos desde Administración.' : responsible ? 'Este inicio reúne la actividad de tu delegación. Tu equipo comparte el color que configuras; cada cuenta conserva los permisos de su rol.' : 'Comienza buscando un vecino para revisar su historial. Las consultas y registros respetan el ámbito y los permisos de tu cuenta.'));
    }
    if (config.page === 'passkeys') {
      steps.push(add('.dashboard-section > details:has([data-passkey-register]) > summary', 'Vincular tu teléfono, si lo deseas', 'Abre Agregar passkey y escribe un nombre para reconocer el dispositivo y tu contraseña personal. Pulsa Vincular teléfono y sigue la verificación del navegador. La passkey es opcional; puedes continuar usando contraseña.'));
      steps.push(add('[data-passkey-preference]', 'Elegir cómo ingresar', 'Después de registrar una passkey puedes elegirla como acceso preferido. Guarda la preferencia; tendrás también el ingreso con contraseña.'));
      steps.push(add('.table-responsive', 'Revisar tus dispositivos', 'Aquí aparecen las passkeys registradas y su último uso. Revoca una si dejas de usar el dispositivo; sólo administras las passkeys de tu propia cuenta.'));
      if (config.auto_start === 'passkeys') steps.push(add('#tour-brand', 'Continuar al inicio', 'Al terminar o cerrar esta guía puedes volver al inicio desde el logo municipal. Allí te espera la bienvenida a tus herramientas de trabajo.'));
    } else {
      steps.push(add('.territory-scope > summary', 'Consultar un territorio', 'Abre el selector para elegir una delegación. El resumen conserva el trimestre y toma el color de la sede. Todas las delegaciones recupera la vista municipal.'));
      steps.push(add('.metrics-strip', 'Resultados de tu ámbito', `Estos indicadores reúnen atenciones, personas atendidas, acciones pendientes y metas de ${scope}. El cumplimiento considera acciones aprobadas.`));
      steps.push(add('#neighbor-search-heading', 'Empezar por el vecino', 'Abre Buscar un vecino para desplegar el buscador. Puedes usar RUT, nombre o apellido y revisar el historial antes de registrar una atención.'));
      steps.push(add('#pending-actions-heading', 'Dar seguimiento a las acciones', config.can_approve ? 'Despliega Acciones pendientes y abre una actividad para revisarla. Ver todas muestra el listado completo; al aprobar se solicita la evidencia del trabajo terminado.' : 'Despliega Acciones pendientes y usa Ver todas para abrir el listado completo. Los controles de revisión aparecen sólo a quienes tienen ese permiso.'));
      steps.push(add('#current-goals-heading', 'Seguir las metas vigentes', 'Despliega Metas vigentes y compara las acciones aprobadas con el objetivo del período. Ver todas abre el detalle completo y sus fechas.'));
      steps.push(add('.admin-workspace', 'Organizar delegaciones y equipos', 'Crea delegaciones, asigna su responsable y vincula a los funcionarios desde Usuarios. El rol define permisos y la delegación define el ámbito de trabajo.'));
      steps.push(add('.report-grid', 'Elegir un reporte', 'Abre la consulta que necesitas o descarga Excel. En Acciones y Metas, aplica primero los filtros del listado para conservarlos al exportar.'));
      steps.push(add('[data-neighbor-search]:not(#dashboard-search)', 'Encontrar a una persona', 'Busca por RUT, nombre o apellido. Las sugerencias permiten abrir la ficha y revisar su historial antes de registrar una atención.'));
      steps.push(add('.record-summary', 'Confirmar la ficha', 'Comprueba el RUT y los datos de contacto. El historial inferior muestra las atenciones autorizadas para tu cuenta.'));
      if (config.can_register) steps.push(add('[aria-labelledby="register-attention-title"]', 'Registrar la atención', 'Selecciona el tipo y la subatención, describe lo realizado y guarda. Revisa primero el historial para evitar registrar dos veces la misma solicitud.'));
      steps.push(add('.transaction-detail', 'Revisar el trabajo y su evidencia', 'Consulta el estado, los datos de la acción y las fotos disponibles. Revisa las validaciones del formulario antes de confirmar una decisión.'));
      steps.push(add('.account-tabs', 'Ajustar tu cuenta', 'Desde estas pestañas puedes editar tu usuario, cambiar tu contraseña, administrar passkeys y consultar tu perfil.'));
      steps.push(add('.account-form', 'Guardar cambios personales', 'Completa los campos y confirma con tu contraseña actual cuando se solicite. Los mensajes indican qué debes corregir antes de guardar.'));
      steps.push(add('.appearance-form', 'Definir el color del equipo', 'Elige un color y revisa la vista previa antes de guardar. La identidad del encabezado se comparte con todos los usuarios de esta delegación.'));
      if (config.page === 'usuarios_list') {
        steps.push(add('[data-bs-target="#nuevoUsuarioModal"]', 'Crear una cuenta para el equipo', 'Ingresa un correo único, el RUT válido, el rol y la delegación. El sistema genera la contraseña temporal y la envía al correo; la persona debe cambiarla al ingresar. Si no aparece el mensaje, revisa spam y la confirmación del envío.'));
        steps.push(add('#main-content [data-confirm-action="remove"]', 'Eliminar es distinto de desactivar', 'El botón de encendido bloquea o reactiva el acceso y conserva el historial. La papelera roja elimina una cuenta sin registros relacionados, después de confirmar. Las cuentas protegidas o con historial no se borran.'));
      } else if (config.page === 'delegaciones_list') {
        steps.push(add('[data-bs-target="#nuevaDelegacionModal"]', 'Organizar una delegación', 'La comuna está fijada en La Serena. El responsable debe trabajar en la misma delegación que dirige. Vincula los funcionarios desde Usuarios y conserva las asignaciones de su equipo.'));
        steps.push(add('#main-content [data-confirm-action="remove"]', 'Conservar el historial de la sede', 'Desactivar conserva la delegación y sus registros. La papelera roja sólo permite eliminar una sede sin responsable, funcionarios, vecinos ni historial relacionado.'));
      } else if (config.page === 'vecinos_list') {
        steps.push(add('[data-bs-target="#nuevoVecinoModal"]', 'Registrar al vecino en su territorio', 'Escribe el RUT completo de 8 cifras y su verificador; los puntos y el guion se agregan solos. Revisa primero las coincidencias para evitar duplicar una ficha. Tu cuenta sólo opera en su delegación.'));
        steps.push(add('#main-content [data-confirm-action="remove"]', 'Elegir entre desactivar y eliminar', 'Desactivar conserva la ficha y su historial. La papelera roja pide confirmación y sólo elimina vecinos sin atenciones ni registros relacionados.'));
      } else if (config.page === 'action_create') {
        steps.push(add('[name="evidencia"]', 'Adjuntar la foto inicial', 'La acción requiere una imagen real JPEG, PNG o WebP de hasta 5 MB. Describe la solicitud, comprueba la delegación y guarda una sola vez. La foto final se adjunta al aprobar el trabajo.'));
      } else if (config.page === 'action_review') {
        steps.push(add('[aria-labelledby="resolve-action-title"]', 'Aprobar o rechazar con fundamento', 'Para aprobar, escribe el motivo y adjunta la foto final del trabajo terminado. Para rechazar, indica el motivo. La decisión se conserva en la auditoría y una acción resuelta no se vuelve a resolver.'));
      }
      const filter = document.querySelector('form.transaction-filter, form.search-box-stitch');
      if (filter) steps.push(add('form.transaction-filter, form.search-box-stitch', 'Filtrar este listado', 'Escribe para actualizar los resultados. Los selectores se aplican al cambiarlos y puedes vaciar el texto para quitar ese filtro.'));
      steps.push(add('#main-content .table-responsive', 'Leer los resultados', config.page === 'action_list' ? 'Consulta la fecha, la delegación, el autor, el estado y la evidencia de cada acción. Filtra por estado para localizar las pendientes.' : config.page === 'meta_list' ? 'Compara objetivo, ejecución y avance dentro de cada período. El avance se calcula con las acciones aprobadas asociadas a la meta.' : 'Revisa las filas del resultado. Los botones de cada registro muestran las operaciones habilitadas para tu cuenta.'));
      steps.push(add('.grid-pagination', 'Recorrer y exportar resultados', 'Elige las filas por página o avanza entre páginas. La búsqueda conserva su filtro. El botón Exportar Excel de la página descarga la consulta disponible.'));
      steps.push(add('#main-content .form-panel form', 'Completar este formulario', 'Revisa las etiquetas y los campos obligatorios. Al guardar se validan los datos; si aparece un error, corrige el campo indicado y vuelve a confirmar.'));
      if (admin) steps.push(add('#tour-mantenedores', 'Administrar el municipio', 'Aquí se accede a delegaciones, responsables, usuarios, roles y catálogos. Asigna a cada funcionario su delegación y los permisos que necesita.'));
      else if (responsible) steps.push(add('.territory-banner', 'Identidad de tu delegación', 'Eres el responsable asignado a esta delegación. Su color identifica a todo tu equipo; las funciones de administración y aprobación dependen de los permisos de tu rol.'));
      else if (config.can_manage) steps.push(add('#tour-mantenedores', 'Herramientas de gestión', 'Tu rol habilita estos catálogos de trabajo. Los accesos y datos disponibles conservan el ámbito autorizado para tu cuenta.'));
    }
    if (!steps.some(visible)) steps.push(add('#main-content', 'Ayuda de esta página', 'Revisa el título y las indicaciones de la sección. Los formularios señalan los campos necesarios y explican sus errores al guardar; el menú permite volver al inicio o abrir otra consulta.'));
    steps.push(add('.territory-banner', admin ? 'Comprobar el ámbito consultado' : 'Tu delegación de trabajo', admin ? 'Todas las delegaciones identifica la vista municipal. Al seleccionar una delegación en el resumen, el encabezado muestra el territorio consultado.' : 'Este encabezado identifica la delegación de tu cuenta y utiliza el color definido por su responsable.'));
    steps.push(add('#btnToggleSidebar', 'Abrir el menú', 'Usa este botón para acceder a las secciones. En pantallas pequeñas abre el menú de trabajo.'));
    steps.push(add('#tour-user-dropdown', 'Perfil y seguridad', 'Desde tu nombre puedes consultar el perfil, editar tu cuenta y cerrar sesión. En los ajustes encontrarás contraseña y passkeys.'));
    steps.push(add('#tour-tutorial-btn', 'Volver a consultar esta ayuda', 'Este botón abre la guía de la página donde estás. Usa Siguiente y Anterior o las flechas del teclado; cierra con Escape o Cerrar.'));
    return prepare(steps);
  };
  const complete = async kind => {
    if (!kind) return;
    try {
      const response = await fetch(config.complete_url, {method: 'POST', credentials: 'same-origin', keepalive: true,
        headers: {'X-CSRFToken': config.csrf_token, 'Accept': 'application/json', 'Content-Type': 'application/x-www-form-urlencoded'},
        body: new URLSearchParams({kind})});
      if (!response.ok) throw new Error('completion');
      if (config.auto_start === kind) config.auto_start = '';
    } catch (_) {
      const notice = document.createElement('p');
      notice.className = 'alert alert-warning';
      notice.setAttribute('role', 'status');
      notice.textContent = 'No se pudo guardar que revisaste la guía. Puede aparecer de nuevo al volver al inicio.';
      document.getElementById('main-content')?.prepend(notice);
    }
  };
  const start = (fromUpdates = false) => {
    if (starting || tour?.isActive() || document.querySelector('[data-glass-welcome][open]')) return;
    if (document.querySelector('.modal.show, .modal.showing')) {
      waiting = {fromUpdates};
      return;
    }
    waiting = false;
    if (!window.driver?.js?.driver) {
      if (window.Swal) window.Swal.fire({icon: 'warning', title: 'Tutorial no disponible', text: 'Recarga la página para cargar la guía.', confirmButtonText: 'Entendido'});
      return;
    }
    const steps = contextSteps();
    if (!steps.length) return;
    if (fromUpdates) {
      steps.unshift({popover: {title: 'Recorrido de Novedades',
        description: 'Usa Siguiente para explorar la mejora. Al finalizar o salir, volverás al inicio.'}});
    }
    const completion = fromUpdates ? '' : config.auto_start;
    const scrollPosition = window.scrollY;
    const url = new URL(window.location.href);
    if (url.searchParams.has('tutorial')) {
      url.searchParams.delete('tutorial');
      window.history.replaceState(window.history.state, '', url);
    }
    starting = true;
    tour = window.driver.js.driver({steps, showProgress: true, animate: !motion.matches, allowClose: true, allowKeyboardControl: true,
      overlayColor: '#111827', overlayOpacity: .55, stagePadding: 6, stageRadius: 10, popoverClass: 'municipal-tour',
      nextBtnText: 'Siguiente', prevBtnText: 'Anterior',
      doneBtnText: fromUpdates ? 'Volver al inicio' : 'Finalizar',
      progressText: fromUpdates ? 'Novedades · {{current}} de {{total}}' : 'Paso {{current}} de {{total}}',
      onPopoverRender: popover => {
        popover.closeButton.setAttribute('aria-label', fromUpdates ? 'Salir del recorrido y volver al inicio' : 'Cerrar tutorial');
        popover.wrapper.setAttribute('aria-modal', 'true');
      },
      ...(fromUpdates && {onDestroyStarted: () => window.location.replace(config.home_url)}),
      onDestroyed: () => {
        starting = false;
        complete(completion);
        launch?.focus({preventScroll: true});
        window.scrollTo({top: scrollPosition, behavior: 'instant'});
      },
    });
    tour.drive();
    starting = false;
  };
  window.iniciarTutorialSGR = () => start();
  document.addEventListener('DOMContentLoaded', () => {
    launch?.addEventListener('click', () => start());
    document.querySelectorAll('[data-update-tour]').forEach(button => {
      button.addEventListener('click', () => start(true));
    });
    const startAutomatically = () => {
      const requested = new URLSearchParams(window.location.search).get('tutorial');
      if (config.auto_start || requested === '1' || requested === 'novedades') {
        start(requested === 'novedades');
      }
    };
    document.addEventListener('hidden.bs.modal', () => {
      if (waiting) {
        const retry = waiting;
        window.setTimeout(() => start(retry.fromUpdates), 100);
      }
    });
    document.querySelector('[data-glass-welcome]')?.addEventListener('close', () => {
      window.setTimeout(startAutomatically, 100);
    });
    if (config.auto_start || requestedTour === '1' || requestedTour === 'novedades') {
      window.setTimeout(startAutomatically, 250);
    }
  });
})();
