(() => {
  document.querySelectorAll('[data-quarter-filter]').forEach(form => {
    form.querySelector('select[name="trimestre"]').addEventListener('change', () => form.requestSubmit());
  });

  if (window.bootstrap?.Tooltip && document.querySelector('.management-grid, [data-column-help]')) {
    new window.bootstrap.Tooltip(document.body, {
      selector: '.record-actions [title], [data-column-help]',
      container: 'body',
      trigger: 'hover focus',
    });
  }

  const sidebar = document.querySelector('#tour-sidebar-nav .sidebar-scroll');
  if (sidebar) {
    const key = 'sgr:sidebar:' + document.body.dataset.userId;
    const load = suffix => { try { return sessionStorage.getItem(key + suffix); } catch (_) { return null; } };
    const save = (suffix, value) => { try { sessionStorage.setItem(key + suffix, value); } catch (_) {} };
    const syncScrollFade = () => {
      sidebar.toggleAttribute('data-more-below', sidebar.scrollHeight - sidebar.scrollTop - sidebar.clientHeight > 2);
    };

    if (window.bootstrap?.Collapse) {
      for (const toggle of sidebar.querySelectorAll('[data-sidebar-group]')) {
        const panel = document.getElementById(toggle.getAttribute('aria-controls'));
        const suffix = ':' + toggle.dataset.sidebarGroup;
        const stored = load(suffix);
        const expanded = stored ? stored === 'open' : Boolean(panel.querySelector('.nav-link-stitch.active'));
        panel.classList.toggle('show', expanded);
        toggle.classList.toggle('collapsed', !expanded);
        toggle.setAttribute('aria-expanded', String(expanded));
        panel.addEventListener('show.bs.collapse', () => save(suffix, 'open'));
        panel.addEventListener('hide.bs.collapse', () => save(suffix, 'closed'));
        panel.addEventListener('shown.bs.collapse', syncScrollFade);
        panel.addEventListener('hidden.bs.collapse', syncScrollFade);
      }
    }
    const top = Number(load(':top'));
    const restore = () => requestAnimationFrame(() => {
      if (top > 0) sidebar.scrollTo({top, behavior: 'instant'});
      syncScrollFade();
      sidebar.addEventListener('scroll', () => {
        save(':top', sidebar.scrollTop);
        syncScrollFade();
      }, {passive:true});
      new ResizeObserver(syncScrollFade).observe(sidebar);
    });
    if (document.readyState === 'loading' || document.readyState === 'interactive') {
      document.addEventListener('DOMContentLoaded', restore, {once:true});
    } else {
      restore();
    }
    sidebar.addEventListener('click', event => {
      if (event.target.closest('a[href]')) save(':top', sidebar.scrollTop);
    });
  }

  const disclosures = document.querySelector('.dashboard-disclosures');
  if (disclosures) {
    const toolbar = document.createElement('div');
    toolbar.className = 'dashboard-action-tiles';
    const entries = [];
    const syncTiles = () => entries.forEach(({panel, button}) => button.setAttribute('aria-expanded', String(panel.open)));
    disclosures.querySelectorAll(':scope > details').forEach(panel => {
      const summary = panel.querySelector(':scope > summary');
      const content = panel.querySelector('.disclosure-content');
      const button = document.createElement('button');
      button.type = 'button';
      button.className = 'dashboard-action-tile metric';
      button.id = summary.id;
      content.id = button.id + '-contenido';
      button.setAttribute('aria-controls', content.id);
      button.replaceChildren(...[...summary.childNodes].map(node => node.cloneNode(true)));
      summary.removeAttribute('id');
      summary.hidden = true;
      button.addEventListener('click', () => { panel.open = !panel.open; syncTiles(); });
      panel.addEventListener('toggle', syncTiles);
      toolbar.append(button);
      entries.push({panel, button});
    });
    disclosures.prepend(toolbar);
    disclosures.setAttribute('data-tile-actions', '');
    syncTiles();
  }

  const account = document.querySelector('[data-username-form]');
  if (account) {
    const method = account.elements.method;
    const update = () => {
      account.querySelectorAll('[data-username-method]').forEach(panel => {
        panel.hidden = panel.dataset.usernameMethod !== (method.value || 'password');
        panel.querySelectorAll('input, button').forEach(field => { field.disabled = panel.hidden; });
      });
    };
    method.addEventListener('change', update);
    update();
  }

  document.querySelectorAll('[data-personalize]').forEach(form => {
    const {blanco: white, color, estilo: style} = form.elements;
    const originalTint = form.style.getPropertyValue('--landscape-tint');
    const options = [...form.querySelectorAll('[name=paisaje]')];
    const gallery = form.querySelector('[data-landscape-gallery]');
    const preview = form.querySelector('[data-landscape-preview]');
    const scene = form.querySelector('[data-preview-scene]');
    const dialog = form.closest('dialog');
    let draft;

    const applyScene = (element, selection, tint) => {
      const disabled = white.checked || !selection;
      element.classList.toggle('is-white', disabled);
      element.style.setProperty('--landscape-image', disabled ? 'none' : 'url("' + selection.dataset.photo + '")');
      element.style.setProperty('--landscape-tint', tint);
      element.dataset.scene = disabled ? '' : selection.value;
    };

    const update = (live = false) => {
      gallery.hidden = white.checked;
      options.forEach(option => { option.disabled = white.checked; });
      const selected = options.find(option => option.checked);
      const tint = color && !color.disabled ? color.value : originalTint;
      preview.dataset.style = style.value;
      form.style.setProperty('--landscape-tint', tint);
      applyScene(scene, selected, tint);

      if (live) {
        if (!draft) {
          draft = scene.cloneNode(true);
          draft.className = 'landscape-ambient';
          draft.removeAttribute('data-preview-scene');
          draft.setAttribute('data-background-draft', '');
          document.body.prepend(draft);
          document.body.setAttribute('data-background-preview', '');
        }
        applyScene(draft, selected, tint);
      }
    };
    form.addEventListener('input', () => update(true));
    dialog?.addEventListener('close', () => {
      draft?.remove();
      draft = undefined;
      document.body.removeAttribute('data-background-preview');
    });
    update();

    const next = form.querySelector('[data-appearance-next]');
    if (!next) return;
    const sections = [...form.querySelectorAll('[data-appearance-step]')];
    const colorSection = form.querySelector('[data-appearance-color]');
    const back = form.querySelector('[data-appearance-prev]');
    const save = form.querySelector('[data-appearance-save]');
    let step = 0;
    const show = (index, focus = false) => {
      step = index;
      sections.forEach((section, position) => { section.hidden = position !== step; });
      colorSection.hidden = step !== 0;
      back.hidden = step === 0;
      next.hidden = step === sections.length - 1;
      save.hidden = !next.hidden;
      if (focus) {
        const legend = sections[step].querySelector('legend');
        legend.tabIndex = -1;
        legend.focus();
      }
    };
    next.addEventListener('click', () => show(step + 1, true));
    back.addEventListener('click', () => show(step - 1, true));
    form.addEventListener('submit', event => {
      if (step < sections.length - 1) {
        event.preventDefault();
        show(step + 1, true);
      }
    });
    show(0);
  });
})();
