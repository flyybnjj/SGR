document.addEventListener('DOMContentLoaded', () => {
  const data = document.getElementById('attention-subtypes');
  const kind = document.getElementById('id_tipo_atencion');
  const subtype = document.getElementById('id_sub_atencion');
  if (!data || !kind || !subtype) return;
  const options = JSON.parse(data.textContent || '[]');
  const update = () => {
    const previous = subtype.value;
    const matching = options.filter(item => String(item.tipo_atencion_id) === kind.value);
    subtype.replaceChildren(new Option(kind.value ? 'Selecciona una subatención (opcional)' : 'Selecciona primero un tipo', ''));
    matching.forEach(item => subtype.add(new Option(item.nombre, item.id)));
    subtype.value = matching.some(item => String(item.id) === previous) ? previous : '';
    subtype.disabled = !kind.value;
  };
  kind.addEventListener('change', update);
  update();
  kind.form?.addEventListener('submit', () => {
    if (!kind.form.checkValidity()) return;
    requestAnimationFrame(() => kind.form.querySelectorAll('button[type="submit"]').forEach(button => {
      button.disabled = true;
      button.setAttribute('aria-busy', 'true');
    }));
  });
});
