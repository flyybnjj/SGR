(() => {
  if ((CSS.supports('appearance: base-select') && CSS.supports('selector(select::picker(select))')) || !window.bootstrap?.Dropdown) return;
  const selector = 'form[method="get" i] select:not(:disabled):not([multiple]):is(:not([size]), [size="1"])';
  let sequence = 0;
  const enhance = select => {
    if (select.dataset.enhancedSelect) return;
    select.id ||= `sgr-select-${++sequence}`;
    const wrapper = document.createElement('div');
    wrapper.className = select.hasAttribute('data-page-size') ? 'dropdown sgr-select sgr-select-compact' : 'dropdown sgr-select';
    const trigger = document.createElement('button');
    trigger.type = 'button';
    trigger.id = `${select.id}-trigger`;
    trigger.className = 'form-select sgr-select-trigger';
    trigger.dataset.bsToggle = 'dropdown';
    trigger.setAttribute('aria-expanded', 'false');
    trigger.setAttribute('aria-haspopup', 'listbox');
    const value = document.createElement('span');
    value.id = `${select.id}-value`;
    const chevron = document.createElement('i');
    chevron.className = 'bi bi-chevron-down';
    chevron.setAttribute('aria-hidden', 'true');
    trigger.append(value, chevron);
    const menu = document.createElement('div');
    menu.id = `${select.id}-options`;
    menu.className = 'dropdown-menu sgr-select-menu';
    menu.setAttribute('role', 'listbox');
    trigger.setAttribute('aria-controls', menu.id);
    const label = select.labels[0];
    if (label) {
      label.id ||= `${select.id}-label`;
      trigger.setAttribute('aria-labelledby', `${label.id} ${value.id}`);
      menu.setAttribute('aria-labelledby', label.id);
    } else {
      trigger.setAttribute('aria-label', select.getAttribute('aria-label') || select.name);
    }
    const items = [...select.options].map((option, index) => {
      const item = document.createElement('button');
      item.type = 'button';
      item.id = `${select.id}-option-${index}`;
      item.className = 'dropdown-item sgr-select-option';
      item.setAttribute('role', 'option');
      item.disabled = option.disabled;
      const title = document.createElement('span');
      title.textContent = option.text;
      const check = document.createElement('i');
      check.className = 'bi bi-check2';
      check.setAttribute('aria-hidden', 'true');
      item.append(title, check);
      item.addEventListener('click', () => {
        if (select.value !== option.value) {
          select.value = option.value;
          select.dispatchEvent(new Event('change', { bubbles: true }));
        }
        bootstrap.Dropdown.getOrCreateInstance(trigger).hide();
        trigger.focus();
      });
      menu.append(item);
      return item;
    });
    const sync = () => {
      value.textContent = select.selectedOptions[0]?.text || '';
      items.forEach((item, index) => item.setAttribute('aria-selected', String(index === select.selectedIndex)));
    };
    let typed = '', typedAt = 0;
    menu.addEventListener('keydown', event => {
      const enabled = items.filter(item => !item.disabled);
      if (event.key === 'Home' || event.key === 'End') {
        event.preventDefault();
        enabled[event.key === 'Home' ? 0 : enabled.length - 1]?.focus();
      } else if (event.key.length === 1 && event.key !== ' ' && !event.ctrlKey && !event.metaKey && !event.altKey) {
        const now = Date.now();
        typed = now - typedAt > 700 ? event.key : typed + event.key;
        typedAt = now;
        const normalize = text => text.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase();
        const match = enabled.find(item => normalize(item.textContent.trim()).startsWith(normalize(typed)));
        if (match) { event.preventDefault(); match.focus(); }
      }
    });
    trigger.addEventListener('shown.bs.dropdown', () => {
      (items.find(item => item.getAttribute('aria-selected') === 'true' && !item.disabled) || items.find(item => !item.disabled))?.focus();
    });
    select.addEventListener('change', sync);
    select.form?.addEventListener('reset', () => requestAnimationFrame(sync));
    select.before(wrapper);
    wrapper.append(select, trigger, menu);
    if (label) label.htmlFor = trigger.id;
    sync();
    select.dataset.enhancedSelect = 'true';
    select.hidden = true;
  };
  const install = root => {
    if (root.matches?.(selector)) enhance(root);
    root.querySelectorAll(selector).forEach(enhance);
  };
  install(document);
  const main = document.getElementById('main-content');
  if (main) {
    new MutationObserver(records => records.forEach(record => record.addedNodes.forEach(node => {
      if (node instanceof HTMLElement) install(node);
    }))).observe(main, { childList: true, subtree: true });
  }
})();
