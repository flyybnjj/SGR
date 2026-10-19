
(() => {
  'use strict';
  function validRut(value) {
    const formatted = value.replace(/[. ]/g, '').toUpperCase();
    if (!/^\d{1,8}-?[0-9K]$/.test(formatted)) return false;
    const cleaned = formatted.replace('-', '');
    const digits = cleaned.slice(0, -1);
    let sum = 0, factor = 2;
    for (let index = digits.length - 1; index >= 0; index--) {
      sum += Number(digits[index]) * factor;
      factor = factor === 7 ? 2 : factor + 1;
    }
    const remainder = 11 - sum % 11;
    return cleaned.slice(-1) === (remainder === 11 ? '0' : remainder === 10 ? 'K' : String(remainder));
  }
  function validateField(field) {
    if (!field.willValidate) return;
    field.setCustomValidity('');
    if (['text', 'email', 'tel', 'search', 'textarea', 'url'].includes(field.type)) {
      field.value = field.value.trim();
    }
    if (field.required && !field.value.trim()) {
      field.setCustomValidity('Complete este campo.');
    } else if (field.value && (field.dataset.validate === 'rut' || /(^|-)rut$/.test(field.name)) && !validRut(field.value)) {
      field.setCustomValidity('Ingrese un RUT válido con su dígito verificador.');
    } else if (field.value && (field.dataset.validate === 'phone' || /(^|-)telefono$/.test(field.name)) && !/^(?:\+?56[ -]?)?[2-9](?:[ -]?\d){8}$/.test(field.value)) {
      field.setCustomValidity('Ingrese un teléfono chileno de 9 dígitos, opcionalmente con +56.');
    } else if (field.value && field.type === 'email' && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(field.value)) {
      field.setCustomValidity('Ingrese un correo electrónico válido.');
    }
    field.setAttribute('aria-invalid', String(!field.validity.valid));
  }
  window.initializeCrudForms = (root = document) => {
  root.querySelectorAll('form[data-crud-form], form[method="post"]:not([data-confirm]), form[method="POST"]:not([data-confirm])').forEach(form => {
    if (form.dataset.validationReady) return;
    form.dataset.validationReady = "true";
    form.noValidate = true;
    const fields = [...form.querySelectorAll('input, select, textarea')];
    fields.forEach(field => {
      field.addEventListener('input', () => { field.setCustomValidity(''); field.removeAttribute('aria-invalid'); });
      field.addEventListener('blur', () => validateField(field));
    });
    form.addEventListener('submit', event => {
      fields.forEach(validateField);
      const invalid = fields.find(field => field.willValidate && !field.validity.valid);
      if (!invalid) return;
      event.preventDefault();
      const label = invalid.labels?.[0]?.textContent.trim() || 'Campo';
      const message = invalid.validationMessage || 'Revise el valor ingresado.';
      if (window.Swal) {
        Swal.fire({ target: form.closest('.modal') || document.body, icon: 'error', title: 'Revise el formulario', text: `${label}: ${message}`, confirmButtonText: 'Corregir' }).then(() => invalid.focus());
      } else {
        invalid.reportValidity();
      }
    });
  });
  root.querySelectorAll('form[data-confirm]').forEach(form => {
    if (form.dataset.confirmReady) return;
    form.dataset.confirmReady = 'true';
    form.addEventListener('submit', async event => {
      event.preventDefault();
      if (form.dataset.confirmPending === 'true') return;
      form.dataset.confirmPending = 'true';
      const question = [form.dataset.confirmRecord, form.dataset.confirm].filter(Boolean).join('\n\n');
      const deleting = form.dataset.confirmAction === 'delete';
      const deactivating = deleting || form.dataset.confirmAction === 'deactivate';
      const restoring = form.dataset.confirmAction === 'restore';
      const stateAction = deactivating || restoring;
      const icon = restoring
        ? '<path d="M3 11a9 9 0 1 1 2.6 7M3 4v7h7"/>'
        : deleting
          ? '<path d="M3 6h18M9 6V3h6v3M5 6l1 15h12l1-15M10 10v7M14 10v7"/>'
          : '<path d="M12 2v10M5.6 5.6a9 9 0 1 0 12.8 0"/>';
      try {
        const confirmed = window.Swal
        ? (await Swal.fire({
          icon: stateAction ? 'warning' : 'question',
          iconHtml: stateAction ? `<svg viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false">${icon}</svg>` : undefined,
          titleText: form.dataset.confirmTitle || (deactivating ? 'Desactivar registro' : restoring ? 'Restaurar registro' : 'Cambiar estado'),
          text: question, showCancelButton: true,
          confirmButtonText: deactivating ? 'Desactivar' : restoring ? 'Restaurar' : 'Confirmar',
          cancelButtonText: 'Cancelar', focusCancel: true, reverseButtons: true,
          customClass: {
            popup: stateAction ? 'record-confirmation' : '',
            icon: stateAction ? `record-confirm-icon ${restoring ? 'record-confirm-icon-restore' : ''}` : '',
            confirmButton: deactivating ? 'confirm-record-delete' : restoring ? 'confirm-record-restore' : '',
            cancelButton: stateAction ? 'cancel-record-change' : '',
          },
        })).isConfirmed
        : window.confirm(question);
        if (confirmed) HTMLFormElement.prototype.submit.call(form);
        else delete form.dataset.confirmPending;
      } catch (error) {
        delete form.dataset.confirmPending;
        throw error;
      }
    });
  });
  };
  window.initializeCrudForms();
})();
