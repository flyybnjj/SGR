(() => {
  'use strict';
  const form = document.querySelector('[data-directiva-url]');
  if (!form) return;
  const territory = form.elements.namedItem('delegacion');
  const dialog = document.querySelector('#alta-vecino-directiva');
  const createForm = dialog?.querySelector('[data-directiva-create-form]');
  const createStatus = dialog?.querySelector('[data-directiva-create-status]');
  let currentPicker, creating = false;
  dialog?.querySelector('[data-directiva-create-cancel]')?.addEventListener('click', () => {
    if (!creating) dialog.close();
  });
  dialog?.addEventListener('cancel', event => { if (creating) event.preventDefault(); });
  createForm?.addEventListener('submit', async event => {
    event.preventDefault();
    if (creating || !currentPicker || !createForm.reportValidity()) return;
    const selectedTerritory = territory.value;
    const targetPicker = currentPicker;
    const data = new FormData(createForm);
    data.set('delegacion', selectedTerritory);
    data.set('csrfmiddlewaretoken', form.elements.namedItem('csrfmiddlewaretoken').value);
    creating = true;
    createStatus.textContent = 'Registrando vecino…';
    createForm.querySelector('button[type="submit"]').disabled = true;
    try {
      const response = await fetch(form.dataset.directivaCreateUrl, {method: 'POST', body: data, credentials: 'same-origin'});
      const result = await response.json();
      if (!response.ok) {
        createStatus.textContent = result.errors
          ? Object.values(result.errors).flat().join(' ')
          : 'No se pudo registrar. Revisa los datos e inténtalo nuevamente.';
        return;
      }
      if (territory.value !== selectedTerritory) {
        createStatus.textContent = 'El vecino fue registrado en la delegación anterior. Busca en esa delegación para seleccionarlo.';
        return;
      }
      targetPicker.dispatchEvent(new CustomEvent('directiva:select', {detail: result.vecino}));
      dialog.close();
    } catch (error) {
      createStatus.textContent = 'No se pudo confirmar el registro. Reintenta con el mismo RUT; no se creará un duplicado.';
    } finally {
      creating = false;
      createForm.querySelector('button[type="submit"]').disabled = false;
    }
  });

  form.querySelectorAll('[data-directiva-picker]').forEach(picker => {
    const value = picker.querySelector('input[type="hidden"]');
    const search = picker.querySelector('[data-directiva-search]');
    const status = picker.querySelector('[data-directiva-status]');
    const options = picker.querySelector('[data-directiva-options]');
    const clear = picker.querySelector('[data-directiva-clear]');
    const create = picker.querySelector('[data-directiva-create]');
    let timer, controller;

    const resetResults = () => {
      clearTimeout(timer);
      controller?.abort();
      options.replaceChildren();
      options.hidden = true;
    };
    const select = person => {
      resetResults();
      value.value = person ? person.id : '';
      search.value = '';
      clear.hidden = !person;
      status.textContent = person ? 'Seleccionado: ' + person.nombre : 'Sin selección.';
      search.focus();
    };
    const fetchResults = async () => {
      const active = new AbortController();
      controller = active;
      const url = new URL(form.dataset.directivaUrl, window.location.origin);
      url.searchParams.set('delegacion', territory.value);
      url.searchParams.set('q', search.value.trim());
      status.textContent = 'Buscando vecinos…';
      try {
        const response = await fetch(url, {signal: active.signal, credentials: 'same-origin'});
        if (!response.ok) throw new Error('request');
        const data = await response.json();
        if (active.signal.aborted) return;
        for (const person of data.results) {
          const button = document.createElement('button');
          button.type = 'button';
          button.className = 'neighbor-suggestion btn btn-light w-100 text-start';
          const name = document.createElement('strong');
          const rut = document.createElement('small');
          name.textContent = person.nombre;
          rut.textContent = person.rut || 'Sin RUT';
          button.append(name, rut);
          button.addEventListener('click', () => select(person));
          options.append(button);
        }
        options.hidden = !data.results.length;
        status.textContent = data.results.length
          ? (value.value ? 'Elige un vecino para reemplazar la selección.' : 'Elige un vecino de los resultados.')
          : 'No hay coincidencias en esta delegación.';
      } catch (error) {
        if (!active.signal.aborted) status.textContent = 'No se pudo buscar. Vuelve a intentarlo.';
      }
    };
    const syncTerritory = () => {
      search.disabled = !territory.value;
      if (create) create.disabled = !territory.value;
      if (search.disabled) status.textContent = 'Primero elige una delegación.';
    };
    territory.addEventListener('change', () => {
      resetResults();
      value.value = '';
      search.value = '';
      clear.hidden = true;
      status.textContent = 'Busca un vecino de la nueva delegación.';
      syncTerritory();
    });
    search.addEventListener('input', () => {
      resetResults();
      if (search.value.trim().length >= 2) timer = setTimeout(fetchResults, 250);
      else status.textContent = 'Escribe al menos dos caracteres.';
    });
    search.addEventListener('keydown', event => {
      if (event.key === 'Enter') {
        event.preventDefault();
        options.querySelector('button')?.focus();
      }
      if (event.key === 'Escape') resetResults();
    });
    clear.addEventListener('click', () => select(null));
    picker.addEventListener('directiva:select', event => select(event.detail));
    create?.addEventListener('click', () => {
      if (!dialog || !territory.value) return;
      currentPicker = picker;
      createForm.reset();
      createStatus.textContent = '';
      dialog.showModal();
      createForm.elements.namedItem('nombre').focus();
    });
    syncTerritory();
  });
})();
