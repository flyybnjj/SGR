/* Manual tutorial adapted to the current page and visible permissions. */
(() => {
  'use strict';
  let tour;
  const motion = window.matchMedia('(prefers-reduced-motion: reduce)');
  const add = (element, title, description) => ({element, popover: {title, description, side: 'bottom', align: 'center'}});
  window.iniciarTutorialSGR = () => {
    if (document.querySelector('.modal.show')) return;
    if (!window.driver?.js?.driver) {
      if (window.Swal) Swal.fire({icon: 'warning', title: 'Tutorial no disponible', text: 'Recarga la página para cargar la guía.', confirmButtonText: 'Entendido'});
      return;
    }
    tour?.destroy();
    const steps = [
      add('#tour-brand', 'Plataforma municipal', 'Este enlace vuelve al panel de inicio. La guía explica las opciones disponibles en tu pantalla.'),
      add('.territory-banner', 'Tu delegación', 'Aquí se identifica el territorio que consultas o donde trabajas. El color lo configura el responsable y lo comparte todo su equipo.'),
      add('#btnToggleSidebar', 'Menú de trabajo', 'Abre o cierra el menú. En un teléfono, úsalo para acceder a las secciones de trabajo.'),
      add('nav[aria-labelledby="sidebar-attention-title"]', 'Atención al vecino', 'Busca a una persona, consulta su historial municipal o accede al padrón de vecinos desde este grupo.'),
      add('nav[aria-labelledby="sidebar-management-title"]', 'Gestión', 'Consulta acciones, metas y reportes. El administrador ve el ámbito municipal; cada funcionario trabaja en su delegación.'),
      add('.general-filters', 'Consulta por territorio', 'Selecciona comuna, delegación o responsable y pulsa Consultar. Ver todo restablece el resumen municipal. Estos filtros afectan los indicadores y metas de esta página.'),
      add('.metrics-strip', 'Indicadores de gestión', 'Revisa atenciones, personas atendidas, acciones pendientes y cumplimiento de metas, calculados con los registros de tu ámbito.'),
      add('#dashboard-search', 'Buscar un vecino', 'Busca por RUT, nombre o apellido. El historial muestra las atenciones del ámbito autorizado para tu cuenta.'),
      add('.pending-section', 'Acciones pendientes', 'Este resumen muestra hasta tres acciones pendientes de tu ámbito. Ver todas abre el listado filtrado; los perfiles autorizados pueden abrir su revisión.'),
      add('#grupoMantenedores', 'Administración', 'Desde el panel de administración se organizan delegaciones y equipos. Los accesos visibles dependen de tus permisos.'),
      add('.admin-workspace', 'Delegaciones y equipos', 'Crea una delegación, asigna su responsable y vincula a los usuarios desde la edición de su cuenta. El rol define sus permisos y la delegación define su ámbito de trabajo.'),
      add('.account-tabs', 'Tu cuenta personal', 'Cambia tu nombre de usuario, actualiza la contraseña, registra passkeys o consulta tu perfil y el color de tu delegación.'),
      add('.account-form', 'Cambios de cuenta', 'Completa el formulario y confirma tu contraseña actual. Revisa los mensajes de validación antes de guardar.'),
      add('[data-passkey-register]', 'Vincular tu teléfono', 'Con la sesión iniciada, registra una passkey y confirma tu identidad en el teléfono. Después podrás usarla para ingresar o restablecer tu contraseña.'),
      add('.appearance-form', 'Color compartido', 'Elige un color y comprueba la vista previa. Al guardarlo, todos los funcionarios de la delegación heredarán ese color.'),
      add('.table-responsive', 'Listados y consultas', 'Consulta registros, elige cuántas filas mostrar y exporta a Excel. Las acciones disponibles dependen de tu perfil.'),
      add('#tour-user-dropdown', 'Perfil y ajustes', 'Abre tu menú para consultar Mi perfil, editar tu cuenta, activar o detener las ondas del fondo y cerrar la sesión. La animación respeta reducir movimiento del equipo.'),
      add('#tour-tutorial-btn', 'Repetir la guía', 'Puedes volver a abrir este tutorial cuando lo necesites. Usa Siguiente y Anterior; cierra con la cruz o la tecla Escape.'),
    ].filter(step => {
      const element = document.querySelector(step.element);
      return element && element.getClientRects().length && !element.closest('[inert]');
    });
    if (!steps.length) return;
    tour = window.driver.js.driver({steps, showProgress: true, animate: !motion.matches, allowClose: true,
      overlayColor: '#111827', overlayOpacity: .55, stagePadding: 6, stageRadius: 10, popoverClass: 'municipal-tour',
      nextBtnText: 'Siguiente', prevBtnText: 'Anterior', doneBtnText: 'Finalizar', progressText: 'Paso {{current}} de {{total}}',
      onDestroyed: () => document.getElementById('tour-tutorial-btn')?.focus(),
    });
    tour.drive();
  };
  document.addEventListener('DOMContentLoaded', () => {
    document.getElementById('tour-tutorial-btn')?.addEventListener('click', window.iniciarTutorialSGR);
    if (new URLSearchParams(window.location.search).get('tutorial') === '1') window.iniciarTutorialSGR();
  });
})();
