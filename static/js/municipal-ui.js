function closeSidebarMobile() {
  const sidebar = document.getElementById('tour-sidebar-nav');
  sidebar.classList.remove('mobile-open');
  document.getElementById('sidebarBackdrop').classList.remove('active');
  document.body.classList.remove('sidebar-drawer-open');
  document.getElementById('btnToggleSidebar').setAttribute('aria-expanded', 'false');
  if (window.innerWidth < 992) sidebar.inert = true;
  document.getElementById('btnToggleSidebar').focus();
}
function toggleSidebarMenu() {
  const sidebar = document.getElementById('tour-sidebar-nav');
  const toggle = document.getElementById('btnToggleSidebar');
  if (window.innerWidth < 992) {
    if (sidebar.classList.contains('mobile-open')) return closeSidebarMobile();
    sidebar.inert = false;
    sidebar.classList.add('mobile-open');
    document.getElementById('sidebarBackdrop').classList.add('active');
    document.body.classList.add('sidebar-drawer-open');
    toggle.setAttribute('aria-expanded', 'true');
    sidebar.querySelector('button, a').focus();
  } else {
    const collapsed = document.querySelector('.layout-stitch').classList.toggle('sidebar-collapsed');
    sidebar.inert = collapsed;
    toggle.setAttribute('aria-expanded', String(!collapsed));
  }
}
document.addEventListener('DOMContentLoaded', async () => {
  const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
  const preferenceKey = `muni:ambient-motion:${document.body.dataset.userId}`;
  let ambientEnabled = true;
  try { ambientEnabled = localStorage.getItem(preferenceKey) !== 'off'; } catch (_) { /* Preferencia opcional si el almacenamiento está bloqueado. */ }
  const updateAmbientMotion = () => {
    document.body.dataset.ambientMotion = ambientEnabled && !reducedMotion.matches && !document.hidden ? 'running' : 'paused';
    document.querySelectorAll('[data-ambient-toggle]').forEach(toggle => {
      toggle.checked = ambientEnabled && !reducedMotion.matches;
      toggle.disabled = reducedMotion.matches;
    });
  };
  document.querySelectorAll('[data-ambient-toggle]').forEach(toggle => toggle.addEventListener('change', () => {
    ambientEnabled = toggle.checked;
    try { localStorage.setItem(preferenceKey, ambientEnabled ? 'on' : 'off'); } catch (_) { /* La preferencia funciona durante la sesión. */ }
    updateAmbientMotion();
  }));
  reducedMotion.addEventListener('change', updateAmbientMotion);
  document.addEventListener('visibilitychange', updateAmbientMotion);
  updateAmbientMotion();
  document.querySelectorAll('[data-territory-banner]').forEach(banner => {
    const updateMotion = () => {
      banner.dataset.motion = reducedMotion.matches ? 'paused' : 'running';
    };
    reducedMotion.addEventListener('change', updateMotion);
    updateMotion();
  });
  const createModalId = window.location.hash.slice(1);
  if (['nuevaDelegacionModal', 'nuevoUsuarioModal'].includes(createModalId) && window.bootstrap?.Modal) {
    const createModal = document.getElementById(createModalId);
    if (createModal && !document.getElementById('delegationAppearanceModal')) new bootstrap.Modal(createModal).show();
  }
  document.querySelectorAll('[data-appearance-form]').forEach(form => {
    const picker = form.querySelector('[name="color"]');
    const preview = form.querySelector('.appearance-preview');
    const swatches = form.querySelectorAll('[data-color]');
    const update = () => {
      const color = picker.value.toUpperCase();
      preview.style.setProperty('--preview-color', color);
      const channels = color.slice(1).match(/../g).map(value => parseInt(value, 16) / 255)
        .map(value => value <= .04045 ? value / 12.92 : ((value + .055) / 1.055) ** 2.4);
      const luminance = channels.reduce((sum, value, index) => sum + value * [.2126, .7152, .0722][index], 0);
      preview.style.setProperty('--preview-on', luminance > .179 ? '#000000' : '#ffffff');
      form.querySelector('[data-color-value]').textContent = color;
      swatches.forEach(button => button.setAttribute('aria-pressed', String(button.dataset.color === color)));
    };
    swatches.forEach(button => button.addEventListener('click', () => {
      picker.value = button.dataset.color;
      update();
    }));
    picker.addEventListener('input', update);
    update();
  });
  const appearanceModal = document.getElementById('delegationAppearanceModal');
  if (appearanceModal) {
    if (window.bootstrap?.Modal) {
      appearanceModal.addEventListener('show.bs.modal', () => document.body.classList.add('appearance-onboarding-open'));
      appearanceModal.addEventListener('hidden.bs.modal', () => document.body.classList.remove('appearance-onboarding-open'));
      appearanceModal.addEventListener('shown.bs.modal', () => appearanceModal.querySelector('[data-color][aria-pressed="true"]')?.focus());
      new bootstrap.Modal(appearanceModal).show();
    } else {
      window.location.assign(appearanceModal.querySelector('form').action);
    }
  }
  const sidebar = document.getElementById('tour-sidebar-nav');
  const resetNavigation = () => {
    if (!sidebar) return;
    const mobile = window.innerWidth < 992;
    sidebar.inert = mobile && !sidebar.classList.contains('mobile-open');
    if (!mobile) {
      document.body.classList.remove('sidebar-drawer-open');
      document.getElementById('sidebarBackdrop').classList.remove('active');
      sidebar.inert = document.querySelector('.layout-stitch').classList.contains('sidebar-collapsed');
    }
    document.getElementById('btnToggleSidebar').setAttribute('aria-expanded', String(!sidebar.inert));
  };
  resetNavigation();
  window.addEventListener('resize', resetNavigation);
  document.addEventListener('keydown', event => {
    if (!sidebar || !sidebar.classList.contains('mobile-open') || window.innerWidth >= 992) return;
    if (event.key === 'Escape') closeSidebarMobile();
    if (event.key === 'Tab') {
      const controls = [...sidebar.querySelectorAll('a, button')].filter(el => el.getClientRects().length);
      const first = controls[0], last = controls[controls.length - 1];
      if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus(); }
      else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
    }
  });
  document.querySelectorAll('.nav-link-stitch.active').forEach(link => link.setAttribute('aria-current', 'page'));
  const activeSection = document.querySelector('.sidebar-stitch .nav-link-stitch.active')?.getAttribute('href');
  document.querySelectorAll('.mobile-bottom-nav a').forEach(link => {
    if (link.getAttribute('href') === activeSection) {
      link.classList.add('active');
      link.setAttribute('aria-current', 'page');
    }
  });
  document.querySelectorAll('.table-responsive').forEach(table => {
    table.tabIndex = 0;
    table.setAttribute('role', 'region');
    table.setAttribute('aria-label', 'Tabla de registros; desplazar para ver todas las columnas');
  });
  for (const message of document.querySelectorAll('.municipal-message')) {
    if (!window.Swal) continue;
    const level = message.dataset.level;
    const icon = ['error', 'warning', 'info'].includes(level) ? level : 'success';
    message.hidden = true;
    await Swal.fire({text: message.textContent.trim(), icon,
      toast: icon === 'success', position: icon === 'success' ? 'bottom-end' : 'center',
      showConfirmButton: icon !== 'success', confirmButtonText: 'Entendido',
      ...(icon === 'success' ? {timer: 4000, timerProgressBar: true} : {})});
  }
});
