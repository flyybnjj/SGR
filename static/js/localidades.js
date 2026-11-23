(() => {
  'use strict';
  const initialize = root => {
    root.querySelectorAll('form[data-localidades-url]').forEach(form => {
      if (form.dataset.localidadesInitialized) return;
      const territory = form.elements.namedItem('delegacion') || form.elements.namedItem('territorio');
      const locality = form.elements.namedItem('localidad');
      if (!territory || !locality) return;
      form.dataset.localidadesInitialized = 'true';
      let controller;
      territory.addEventListener('change', async () => {
        controller?.abort();
        const active = new AbortController();
        controller = active;
        locality.replaceChildren(new Option('-- Sin asignar --', ''));
        if (!territory.value) return;
        locality.disabled = true;
        const url = new URL(form.dataset.localidadesUrl, window.location.origin);
        url.searchParams.set('delegacion', territory.value);
        try {
          const response = await fetch(url, {signal: active.signal, credentials: 'same-origin'});
          if (!response.ok) throw new Error('request');
          const data = await response.json();
          if (active.signal.aborted) return;
          for (const item of data.results) locality.append(new Option(item.nombre, item.id));
          locality.setCustomValidity('');
        } catch (error) {
          if (!active.signal.aborted) locality.setCustomValidity('No se pudieron cargar las localidades. Selecciona nuevamente la delegación.');
        } finally {
          if (!active.signal.aborted) locality.disabled = false;
        }
      });
    });
  };
  initialize(document);
  new MutationObserver(records => {
    if (records.some(record => record.addedNodes.length)) initialize(document);
  }).observe(document.body, {childList: true, subtree: true});
})();
