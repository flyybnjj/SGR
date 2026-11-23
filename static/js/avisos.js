(() => {
  const drawer = document.querySelector('#avisos-drawer');
  if (!drawer?.showModal) return;

  const content = drawer.querySelector('[data-avisos-content]');
  const status = drawer.querySelector('[data-avisos-status]');
  const inboxUrl = drawer.dataset.avisosUrl;
  let currentUrl = inboxUrl;
  let busy = false;

  function showStatus(message) {
    status.textContent = message;
    status.hidden = !message;
  }

  function updateCounters(count) {
    document.querySelectorAll('[data-unread-count]').forEach(badge => {
      badge.textContent = count;
      badge.hidden = count === 0;
      badge.setAttribute('aria-label', count + ' sin leer');
    });
  }

  async function loadInbox(href, focusSelector) {
    const url = new URL(href, location.origin);
    url.searchParams.set('fragmento', '1');
    const response = await fetch(url, {cache: 'no-store'});
    if (!response.ok || response.redirected) throw new Error('No se pudo abrir la bandeja.');
    content.innerHTML = await response.text();
    currentUrl = href;
    const count = Number(content.querySelector('[data-unread-count]').textContent);
    updateCounters(count);
    if (focusSelector && drawer.open) {
      (content.querySelector(focusSelector) || drawer.querySelector('button')).focus({preventScroll: true});
    }
  }

  async function run(operation, errorMessage) {
    if (busy) return;
    busy = true;
    content.setAttribute('aria-busy', 'true');
    try {
      await operation();
      showStatus('');
    } catch {
      const fallback = document.createElement('a');
      fallback.href = inboxUrl;
      fallback.textContent = 'Abrir la página de avisos';
      showStatus(errorMessage + ' ');
      status.append(fallback);
    } finally {
      busy = false;
      content.removeAttribute('aria-busy');
    }
  }

  function plainClick(event) {
    return event.button === 0 && !event.metaKey && !event.ctrlKey && !event.shiftKey && !event.altKey;
  }

  document.addEventListener('click', event => {
    const opener = event.target.closest('[data-open-avisos]');
    if (!opener || !plainClick(event)) return;
    event.preventDefault();
    drawer.showModal();
    drawer.scrollTop = 0;
    run(async () => {
      showStatus('Cargando avisos…');
      await loadInbox(inboxUrl);
    }, 'No se pudieron cargar los avisos.');
  });

  content.addEventListener('click', event => {
    const link = event.target.closest('[data-avisos-nav]');
    if (!link || !plainClick(event)) return;
    event.preventDefault();
    run(async () => {
      await loadInbox(link.href, '[aria-current="true"]');
      drawer.scrollTop = 0;
    }, 'No se pudieron cargar los avisos.');
  });

  content.addEventListener('submit', event => {
    const form = event.target.closest('[data-aviso-read]');
    if (!form) return;
    event.preventDefault();
    run(async () => {
      const response = await fetch(form.action, {
        method: 'POST',
        headers: {Accept: 'application/json'},
        body: new FormData(form),
      });
      if (!response.ok || response.redirected) throw new Error('No se pudo marcar el aviso.');
      updateCounters((await response.json()).no_leidos);
      const record = form.nextElementSibling;
      const recordLabel = record.getAttribute('aria-label');
      form.closest('.aviso-row').classList.remove('aviso-unread');
      form.closest('.aviso-row').querySelector('.aviso-unread-label')?.remove();
      record.focus({preventScroll: true});
      form.remove();
      await loadInbox(currentUrl, '[aria-label="' + CSS.escape(recordLabel) + '"]');
    }, 'No se pudo actualizar la bandeja.');
  });

  drawer.addEventListener('click', event => {
    if (event.target !== drawer) return;
    const bounds = drawer.getBoundingClientRect();
    if (event.clientX < bounds.left || event.clientX > bounds.right ||
        event.clientY < bounds.top || event.clientY > bounds.bottom) {
      drawer.close();
    }
  });
})();
