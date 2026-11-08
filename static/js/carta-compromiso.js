(() => {
  const reset = document.querySelector('[data-reset-commitment]');
  const form = reset?.form;
  if (!form) return;

  const received = form.elements.fecha_ingreso;
  const commitment = form.elements.fecha_compromiso;
  const mode = form.elements.compromiso_automatico;
  const suggest = () => {
    if (mode.value !== '1') return;
    const date = received.valueAsDate;
    if (date) date.setUTCDate(date.getUTCDate() + 15);
    commitment.valueAsDate = date;
  };
  reset.classList.remove('d-none');
  reset.addEventListener('click', () => {
    mode.value = '1';
    suggest();
    commitment.focus();
  });
  received.addEventListener('input', suggest);
  mode.addEventListener('change', suggest);
  commitment.addEventListener('input', () => { mode.value = '0'; });
})();
