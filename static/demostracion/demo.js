(() => {
  'use strict';
  const area = document.querySelector('[data-demo-scenario]');
  if (!area) return;
  const result = area.querySelector('[data-demo-result]');
  const form = area.querySelector('[data-demo-form]');
  const photo = area.querySelector('[data-demo-photo]');
  const initialResult = result.textContent;
  let previewUrl;
  function report(message, error = false) {
    result.textContent = message;
    if (window.Swal) window.Swal.fire({ icon: error ? 'warning' : 'info', title: error ? 'Revisa la práctica' : 'Resultado simulado', text: message, confirmButtonText: 'Entendido' });
  }
  if (photo) photo.addEventListener('change', () => {
    const preview = document.getElementById(photo.dataset.demoPhoto);
    if (previewUrl) URL.revokeObjectURL(previewUrl);
    preview.hidden = true;
    preview.removeAttribute('src');
    const file = photo.files[0];
    if (!file) return;
    if (!['image/jpeg', 'image/png', 'image/webp'].includes(file.type) || file.size > 8 * 1024 * 1024) {
      photo.value = '';
      report('Elige una imagen JPEG, PNG o WebP de hasta 8 MB. No se ha enviado ningún archivo.', true);
      return;
    }
    previewUrl = URL.createObjectURL(file);
    preview.src = previewUrl;
    preview.hidden = false;
  });
  window.addEventListener('pagehide', () => {
    if (previewUrl) URL.revokeObjectURL(previewUrl);
    form.reset();
    result.textContent = initialResult;
    if (photo) {
      photo.value = '';
      const preview = document.getElementById(photo.dataset.demoPhoto);
      preview.hidden = true;
      preview.removeAttribute('src');
    }
  });
  // Sin action ni llamadas de red: los valores de práctica nunca se persisten.
  form.addEventListener('submit', event => {
    event.preventDefault();
    const inputs = Array.from(form.querySelectorAll('input, textarea'));
    const invalid = inputs.find(input => !input.checkValidity() || (input.tagName === 'TEXTAREA' && !input.value.trim()));
    if (invalid) {
      report('Completa los campos obligatorios con valores válidos. La práctica no ha guardado cambios.', true);
      invalid.focus();
      return;
    }
    if (area.dataset.demoScenario === 'proyeccion') {
      const target = Number(document.getElementById('demo-target').value);
      const approved = 18 + Number(document.getElementById('demo-extra').value);
      report(`Proyección ficticia: ${approved} / ${target} · ${Math.round(approved * 100 / target)} %. No se modificó ninguna meta real.`);
    } else if (area.dataset.demoScenario === 'revision') {
      const decision = event.submitter && event.submitter.value;
      if (!['Aprobada', 'Rechazada'].includes(decision)) return;
      report(`Decisión simulada: ${decision.toLowerCase()}. No se modificó ninguna acción ni se creó una resolución auditada.`);
    } else {
      report('Práctica completada en este dispositivo. No se creó una acción, no se cerró una intervención ni se envió la fotografía.');
    }
  });
})();
