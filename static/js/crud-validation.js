
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
      const question = form.dataset.confirm;
      const deleting = form.dataset.confirmAction === 'delete';
      const restoring = form.dataset.confirmAction === 'restore';
      const confirmed = window.Swal
        ? (await Swal.fire({
          icon: deleting || restoring ? undefined : 'question',
          title: deleting ? 'Eliminar registro' : restoring ? 'Restaurar registro' : 'Cambiar estado',
          text: question, showCancelButton: true,
          confirmButtonText: deleting ? 'Eliminar' : restoring ? 'Restaurar' : 'Confirmar',
          cancelButtonText: 'Cancelar', focusCancel: true,
          customClass: {
            popup: deleting || restoring ? 'record-confirmation' : '',
            confirmButton: deleting ? 'confirm-record-delete' : restoring ? 'confirm-record-restore' : '',
          },
        })).isConfirmed
        : window.confirm(question);
      if (confirmed) HTMLFormElement.prototype.submit.call(form);
    });
  });
  };
  window.initializeCrudForms();
})();
