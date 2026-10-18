
(() => {
  'use strict';
  const element = document.getElementById('crudEditModal');
  if (!element || !window.bootstrap) return;
  const content = element.querySelector('.modal-content');
  const modal = bootstrap.Modal.getOrCreateInstance(element);
  let controller, opener, sequence = 0, isShown = false;
  const focusField = () => content.querySelector('input:not([type="hidden"]):not(:disabled), select:not(:disabled), textarea:not(:disabled)')?.focus();
  element.addEventListener('shown.bs.modal', () => { isShown = true; focusField(); });
  const loading = content.innerHTML;
  element.addEventListener('hidden.bs.modal', () => {
    isShown = false;
    sequence++;
    controller?.abort();
    if (opener?.isConnected) {
      opener.disabled = false;
      opener.removeAttribute('aria-busy');
      opener.focus();
    }
  });
  document.addEventListener('click', async event => {
    const button = event.target.closest('[data-edit-form]');
    if (!button || button.disabled) return;
    controller?.abort();
    controller = new AbortController();
    const current = ++sequence;
    opener = button;
    content.innerHTML = loading;
    content.setAttribute('aria-busy', 'true');
    element.setAttribute('aria-labelledby', 'crudEditTitle');
    button.disabled = true;
    button.setAttribute('aria-busy', 'true');
    isShown = false;
    modal.show();
    try {
      const response = await fetch(button.dataset.editForm, { credentials: 'same-origin', signal: controller.signal, headers: { 'X-Requested-With': 'XMLHttpRequest' } });
      if (!response.ok || response.redirected) throw new Error('No se pudo cargar el formulario. Cierra esta ventana e intenta nuevamente.');
      const fragment = new DOMParser().parseFromString(await response.text(), 'text/html');
      const formContent = fragment.querySelector('.modal-content');
      if (!formContent) throw new Error('El formulario no está disponible.');
      if (current !== sequence) return;
      content.replaceChildren(...Array.from(formContent.childNodes));
      const title = content.querySelector('h2[id], h5[id]');
      if (title) element.setAttribute('aria-labelledby', title.id);
      window.initializeCrudForms?.(content);
      if (isShown) focusField();
    } catch (error) {
      if (error.name === 'AbortError' || current !== sequence) return;
      const status = content.querySelector('[role="status"]');
      status.setAttribute('role', 'alert');
      status.textContent = 'No se pudo cargar el formulario. Cierra esta ventana e intenta nuevamente.';
      if (window.Swal) {
        await Swal.fire({target: element, icon: 'error', title: 'No se pudo abrir el formulario',
          text: status.textContent, confirmButtonText: 'Entendido', returnFocus: false});
        content.querySelector('[data-bs-dismiss="modal"]')?.focus();
      }
    } finally {
      button.disabled = false;
      button.removeAttribute('aria-busy');
      if (current === sequence) content.setAttribute('aria-busy', 'false');
    }
  });
})();
