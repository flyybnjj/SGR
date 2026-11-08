(() => {
  'use strict';
  document.querySelectorAll('[data-neighbor-search]').forEach((input, index) => {
    const form = input.form;
    if (!form) return;
    const submitButton = form.querySelector('button[type="submit"]');
    const results = document.createElement('div');
    results.id = `neighbor-suggestions-${index}`;
    results.className = 'neighbor-suggestions';
    results.setAttribute('role', 'listbox');
    results.setAttribute('aria-label', 'Vecinos encontrados');
    results.hidden = true;
    const status = document.createElement('p');
    status.className = 'neighbor-search-status';
    status.setAttribute('role', 'status');
    status.setAttribute('aria-live', 'polite');
    form.append(results, status);
    if (submitButton) {
      submitButton.dataset.autoFilterSubmit = '';
      submitButton.hidden = true;
    }
    input.setAttribute('role', 'combobox');
    input.setAttribute('aria-autocomplete', 'list');
    input.setAttribute('aria-controls', results.id);
    input.setAttribute('aria-expanded', 'false');
    let timer, controller, version = 0, active = -1;
    const hide = () => {
      results.hidden = true;
      input.setAttribute('aria-expanded', 'false');
      input.removeAttribute('aria-activedescendant');
      active = -1;
    };
    const stop = () => { clearTimeout(timer); controller?.abort(); version++; hide(); };
    const search = async () => {
      const query = input.value.trim();
      if (query.length < 1) { stop(); results.replaceChildren(); status.textContent = ''; return; }
      controller?.abort();
      controller = new AbortController();
      const ownVersion = ++version;
      status.textContent = 'Buscando vecinos…';
      const url = new URL(input.dataset.neighborSearch, location.origin);
      url.searchParams.set('format', 'json'); url.searchParams.set('q', query);
      try {
        const response = await fetch(url, {signal: controller.signal, credentials: 'same-origin', headers: {'Accept': 'application/json'}});
        if (!response.ok) throw new Error('search');
        const data = await response.json();
        if (ownVersion !== version || input.value.trim() !== query) return;
        results.replaceChildren(); active = -1;
        data.results.forEach((person, n) => {
          const link = document.createElement('a');
          const name = document.createElement('strong');
          const rut = document.createElement('small');
          const target = new URL(person.url, location.origin);
          if (target.origin !== location.origin) return;
          link.href = target.href; link.id = `${results.id}-${n}`;
          link.className = 'neighbor-suggestion'; link.setAttribute('role', 'option');
          link.setAttribute('aria-selected', 'false');
          name.textContent = person.nombre + (person.activo ? '' : ' · Inactivo');
          rut.textContent = person.rut || 'Sin RUT';
          link.append(name, rut); results.append(link);
        });
        results.hidden = !results.children.length;
        if (submitButton) submitButton.hidden = true;
        input.setAttribute('aria-expanded', String(!results.hidden));
        status.textContent = results.children.length ? `${results.children.length} coincidencias. Usa las flechas o selecciona un vecino.` : 'No hay coincidencias en tu ámbito de trabajo.';
      } catch (error) {
        if (error.name === 'AbortError' || ownVersion !== version) return;
        if (submitButton) submitButton.hidden = false;
        hide(); status.textContent = 'No se pudieron cargar las sugerencias. Puedes usar Buscar para reintentar.';
      }
    };
    input.addEventListener('input', event => {
      stop(); status.textContent = '';
      if (!event.isComposing) timer = setTimeout(search, 250);
    });
    input.addEventListener('compositionend', () => { stop(); timer = setTimeout(search, 250); });
    input.addEventListener('keydown', event => {
      if (event.key === 'Escape') { stop(); status.textContent = ''; return; }
      const options = [...results.children];
      if (results.hidden || !options.length) return;
      if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
        event.preventDefault();
        active = (active + (event.key === 'ArrowDown' ? 1 : -1) + options.length) % options.length;
        options.forEach((option, n) => option.setAttribute('aria-selected', String(n === active)));
        input.setAttribute('aria-activedescendant', options[active].id);
        options[active].scrollIntoView({block: 'nearest'});
      } else if (event.key === 'Enter' && active >= 0) {
        event.preventDefault(); location.assign(options[active].href);
      }
    });
    form.addEventListener('focusout', event => { if (!form.contains(event.relatedTarget)) stop(); });
    document.addEventListener('pointerdown', event => { if (!form.contains(event.target)) stop(); });
    form.addEventListener('submit', stop);
  });
})();
