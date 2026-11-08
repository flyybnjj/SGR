(() => {
  'use strict';
  const enhancePagination = () => document.querySelectorAll('[data-page-size-apply]').forEach(button => { button.hidden = true; });
  const panel = document.querySelector('[data-live-neighbor-list]');
  const form = panel?.querySelector('[data-live-filter]');
  const input = form?.querySelector('[name="q"]');
  const clearLink = form?.querySelector('[data-live-clear]');
  const manualSubmit = (form, visible) => {
    form.querySelectorAll('button[type="submit"]:not([name])').forEach(button => {
      button.dataset.autoFilterSubmit = '';
      button.hidden = !visible;
    });
  };
  const setPageSize = (form, size) => {
    let field = form.elements.namedItem('per_page');
    if (!field) {
      field = document.createElement('input');
      field.type = 'hidden';
      field.name = 'per_page';
      form.append(field);
    }
    field.value = size;
  };
  const filterForms = [...document.querySelectorAll('form.transaction-filter, form.search-box-stitch, form.general-filters')]
    .filter(filter => filter.method.toLowerCase() === 'get' && !filter.matches('[data-live-filter]') && !filter.querySelector('[data-neighbor-search]'));
  const focusKey = `sgr:filter-focus:${document.body.dataset.userId}:${location.pathname}`;
  filterForms.forEach((filter, index) => {
    let debounce, composing = false, submitting = false;
    manualSubmit(filter, false);
    const remember = field => {
      if (field?.form !== filter || !field.name || !field.matches('input:not([type="hidden"]), select, textarea')) return;
      try {
        sessionStorage.setItem(focusKey, JSON.stringify({index, name: field.name, value: field.value,
          start: field.selectionStart, end: field.selectionEnd, scroll: window.scrollY, at: Date.now()}));
      } catch (_) {}
    };
    const keepPageSize = () => {
      if (filter.elements.namedItem('per_page')) return;
      const size = new URL(location.href).searchParams.get('per_page');
      if (size) setPageSize(filter, size);
    };
    const submit = field => {
      clearTimeout(debounce);
      if (submitting || composing) return;
      remember(field);
      keepPageSize();
      filter.requestSubmit();
    };
    filter.addEventListener('submit', () => {
      clearTimeout(debounce);
      keepPageSize();
      remember(document.activeElement);
      submitting = true;
      filter.setAttribute('aria-busy', 'true');
    });
    filter.querySelectorAll('input[type="search"], input[type="text"], input:not([type]), textarea').forEach(field => {
      field.addEventListener('compositionstart', () => { composing = true; clearTimeout(debounce); });
      field.addEventListener('compositionend', () => { composing = false; debounce = setTimeout(() => submit(field), 400); });
      field.addEventListener('input', event => {
        clearTimeout(debounce);
        if (!event.isComposing && !composing) debounce = setTimeout(() => submit(field), 400);
      });
    });
    filter.querySelectorAll('select').forEach(field => field.addEventListener('change', () => submit(field)));
    filter.querySelectorAll('input[type="checkbox"], input[type="radio"], input[type="date"]').forEach(field => {
      field.addEventListener('change', () => submit(field));
    });
    window.addEventListener('pageshow', event => {
      if (!event.persisted) return;
      submitting = false;
      filter.removeAttribute('aria-busy');
    });
  });
  document.addEventListener('DOMContentLoaded', () => {
    try {
      const saved = JSON.parse(sessionStorage.getItem(focusKey));
      sessionStorage.removeItem(focusKey);
      if (!saved || Date.now() - saved.at > 15000) return;
      const field = filterForms[saved.index]?.elements.namedItem(saved.name);
      if (!field || (field.value !== saved.value && !(field.name === 'q' && field.value === saved.value.trim()))) return;
      const target = field.hidden && field.id ? document.getElementById(`${field.id}-trigger`) : field;
      target?.focus({preventScroll: true});
      if (typeof saved.start === 'number' && typeof field.setSelectionRange === 'function') field.setSelectionRange(saved.start, saved.end);
      window.scrollTo(0, saved.scroll);
    } catch (_) {}
  });
  let timer, controller, version = 0;
  let status;
  if (input) {
    status = document.createElement('p');
    status.className = 'small text-secondary px-3 mb-2';
    status.setAttribute('role', 'status');
    status.setAttribute('aria-live', 'polite');
    form.closest('.card-stitch-header').after(status);
  }
  const cancel = () => { clearTimeout(timer); controller?.abort(); version++; };
  const update = async (url, writeHistory = true) => {
    cancel();
    controller = new AbortController();
    const ownVersion = version;
    panel.setAttribute('aria-busy', 'true');
    status.textContent = 'Buscando vecinos…';
    try {
      const response = await fetch(url, {signal: controller.signal, credentials: 'same-origin', headers: {'Accept': 'text/html'}});
      if (!response.ok || new URL(response.url).pathname !== url.pathname) throw new Error('filter');
      const page = new DOMParser().parseFromString(await response.text(), 'text/html');
      if (ownVersion !== version) return;
      const incoming = page.querySelector('[data-live-neighbor-list]');
      const table = incoming?.querySelector('.table-responsive');
      const pagination = incoming?.querySelector('.grid-pagination');
      const total = pagination?.dataset.resultCount;
      if (!table || !pagination || total === undefined) throw new Error('filter');
      panel.querySelector('.table-responsive').replaceChildren(...table.childNodes);
      panel.querySelector('.grid-pagination').replaceWith(pagination);
      const count = panel.querySelector('[data-neighbor-count]');
      if (count) count.textContent = total;
      setPageSize(form, pagination.querySelector('[data-page-size]').value);
      if (clearLink) clearLink.hidden = !input.value.trim();
      const exportLink = document.querySelector('[data-neighbor-export]');
      if (exportLink) {
        const exportURL = new URL(exportLink.href);
        if (input.value.trim()) exportURL.searchParams.set('q', input.value.trim());
        else exportURL.searchParams.delete('q');
        exportLink.href = exportURL.href;
      }
      if (writeHistory) history.replaceState(null, '', url);
      enhancePagination();
      manualSubmit(form, false);
      status.textContent = input.value.trim() ? `${total} ${total === '1' ? 'vecino encontrado' : 'vecinos encontrados'}.` : '';
    } catch (error) {
      if (error.name === 'AbortError' || ownVersion !== version) return;
      manualSubmit(form, true);
      status.textContent = 'No se pudo actualizar el listado. Pulsa Buscar para reintentar.';
    } finally {
      if (ownVersion === version) panel.removeAttribute('aria-busy');
    }
  };
  const searchURL = () => {
    const url = new URL(location.href);
    url.searchParams.delete('page');
    if (input.value.trim()) url.searchParams.set('q', input.value.trim());
    else url.searchParams.delete('q');
    return url;
  };
  if (input) {
    manualSubmit(form, false);
    input.addEventListener('input', event => {
      cancel();
      panel.removeAttribute('aria-busy');
      status.textContent = '';
      if (!event.isComposing) timer = setTimeout(() => update(searchURL()), 250);
    });
    input.addEventListener('compositionend', () => { cancel(); timer = setTimeout(() => update(searchURL()), 250); });
    form.addEventListener('submit', () => cancel());
    clearLink?.addEventListener('click', event => {
      event.preventDefault(); input.value = ''; input.focus(); update(searchURL());
    });
    panel.addEventListener('click', event => {
      const link = event.target.closest('.grid-pagination a');
      if (!link || event.ctrlKey || event.metaKey || event.shiftKey || event.altKey || event.button) return;
      event.preventDefault(); update(new URL(link.href));
    });
    window.addEventListener('popstate', () => {
      input.value = new URL(location.href).searchParams.get('q') || '';
      update(new URL(location.href), false);
    });
  }
  document.addEventListener('change', event => {
    const select = event.target;
    if (!select.matches('[data-page-size]')) return;
    const filter = filterForms[0];
    if (filter) {
      setPageSize(filter, select.value);
      filter.requestSubmit();
      return;
    }
    const url = new URL(location.href);
    url.searchParams.set('per_page', select.value);
    url.searchParams.delete('page');
    if (input && panel.contains(select)) {
      if (input.value.trim()) url.searchParams.set('q', input.value.trim());
      else url.searchParams.delete('q');
      update(url);
    } else location.assign(url.href);
  });
  enhancePagination();
})();
