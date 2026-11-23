(() => {
  'use strict';
  const form = document.querySelector('[data-carta-opciones]');
  if (!form) return;
  const territory = form.elements.namedItem('delegacion');
  if (territory.disabled) return;
  const organization = form.elements.namedItem('organizacion');
  const assignee = form.elements.namedItem('responsable');
  const area = form.elements.namedItem('area_derivacion');
  const status = form.querySelector('[data-carta-opciones-estado]');
  const submit = form.querySelector('button[type="submit"]');
  let controller;

  const options = (select, choices, placeholder) => {
    select.replaceChildren(new Option(placeholder, ''));
    for (const [id, name] of choices) select.add(new Option(name, id));
  };
  const sync = () => {
    organization.disabled = assignee.disabled = !territory.value;
    if (area) area.disabled = !territory.value;
  };
  territory.addEventListener('change', async () => {
    controller?.abort();
    options(organization, [], 'Selecciona una organización');
    options(assignee, [], 'Selecciona un encargado');
    if (area) options(area, [], 'Sin área del catálogo');
    sync();
    status.textContent = '';
    submit.disabled = false;
    if (!territory.value) return;

    const current = new AbortController();
    controller = current;
    const url = new URL(form.dataset.cartaOpciones, window.location.origin);
    url.searchParams.set('delegacion', territory.value);
    organization.disabled = assignee.disabled = submit.disabled = true;
    if (area) area.disabled = true;
    status.textContent = 'Cargando organizaciones y encargados de esta delegación…';
    try {
      const response = await fetch(url, {signal: current.signal, credentials: 'same-origin'});
      if (!response.ok) throw new Error('request');
      const data = await response.json();
      if (current.signal.aborted) return;
      options(organization, data.organizaciones, 'Selecciona una organización');
      options(assignee, data.responsables, 'Selecciona un encargado');
      if (area) options(area, data.areas || [], 'Sin área del catálogo');
      status.textContent = 'Opciones actualizadas para esta delegación.';
      sync();
    } catch (error) {
      if (!current.signal.aborted) status.textContent = 'No se pudieron cargar las opciones. Vuelve a seleccionar la delegación para reintentar.';
    } finally {
      if (!current.signal.aborted) submit.disabled = false;
    }
  });
  sync();
})();
