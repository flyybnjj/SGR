(() => {
  'use strict';
  const config = document.currentScript.dataset;
  const svgNamespace = 'http://www.w3.org/2000/svg';
  const reduceMotion = matchMedia('(prefers-reduced-motion: reduce)');
  const finePointer = matchMedia('(hover: hover) and (pointer: fine)');
  const navigation = '.sidebar-stitch, .mobile-bottom-nav';
  const navIcons = {
    'house-door': 'home', 'person-lines-fill': 'barChart2', 'chat-square-text': 'messageSquare',
    people: 'users', buildings: 'building-static', 'envelope-paper': 'mail',
    'check2-square': 'columns', bullseye: 'target', 'file-earmark-spreadsheet': 'fileText',
    'calendar-minus': 'calendar', grid: 'settings', 'geo-alt': 'mapPin', 'person-badge': 'user',
    'shield-check': 'shield', 'list-check': 'clipboard', tag: 'tag', 'diagram-3': 'gitBranch',
    list: 'menu',
  };
  const placements = [
    ...Object.entries(navIcons).map(([glyph, name]) => [`:is(${navigation}) .bi-${glyph}`, name]),
    ['#btnToggleSidebar', 'menu'],
    ['#updates-launch', 'notification3'],
    ['#tour-tutorial-btn', 'help'],
    ['.user-badge-avatar .bi-person', 'user'],
    ['.btn-stitch .bi-plus-lg', 'plusCircle'],
    ['.btn-stitch .bi-search', 'searchToX'],
    ['.btn-stitch-excel', 'download'],
    ['.record-actions .bi-eye, .btn-stitch .bi-eye, a.activity-open', 'visibility2'],
    ['.record-actions .bi-pencil, .btn-stitch .bi-pencil', 'edit'],
    ['a.evidence-link', 'camera'],
    ['.form-actions button.btn-stitch-primary[type="submit"]:not([name])', 'save'],
    ['button[name="estado"][value="Aprobada"]', 'checkCircle'],
    ['.btn-record-deactivate', 'toggle'],
    ['.btn-record-delete', 'trash2'],
  ];
  const decorate = (element, name) => {
    const control = element.closest('button, a, label[data-sgr-icon]');
    if (!control || control.dataset.sgrIconReady || !name) return;
    control.dataset.sgrIconReady = name;
    if (name === 'building-static') return;

    const original = element.matches('i.bi') ? element : control.querySelector(':scope > i.bi, :scope > svg');
    const icon = document.createElement('span');
    icon.className = 'sgr-icon';
    icon.setAttribute('aria-hidden', 'true');
    const svg = document.createElementNS(svgNamespace, 'svg');
    svg.classList.add('sgr-icon-static');
    svg.setAttribute('focusable', 'false');
    const use = document.createElementNS(svgNamespace, 'use');
    use.setAttribute('href', `${config.symbols}#${name}`);
    svg.append(use);
    icon.append(svg);
    if (original) original.replaceWith(icon);
    else control.prepend(icon);
  };
  const install = root => {
    const apply = (selector, getName) => {
      if (root.matches?.(selector)) decorate(root, getName(root));
      root.querySelectorAll(selector).forEach(element => decorate(element, getName(element)));
    };
    apply('[data-sgr-icon]', element => element.dataset.sgrIcon);
    placements.forEach(([selector, name]) => apply(selector, () => name));
  };
  let resources;
  let currentAnimation;
  let generation = 0;
  const stop = () => {
    generation++;
    if (!currentAnimation) return;
    const { player, layer, icon } = currentAnimation;
    currentAnimation = null;
    player.destroy();
    layer.remove();
    delete icon.dataset.playing;
  };
  const loadMotion = () => resources ??= Promise.all([
    new Promise((resolve, reject) => {
      const script = document.createElement('script');
      script.src = config.player;
      script.onload = resolve;
      script.onerror = reject;
      document.head.append(script);
    }),
    fetch(config.animations).then(response => {
      if (!response.ok) throw new Error('No se cargaron las animaciones de iconos.');
      return response.json();
    }),
  ]).catch(() => []);

  const play = async (control, allowed = () => true, started = () => {}) => {
    if (reduceMotion.matches || document.hidden || control.disabled || !allowed()) return;
    const icon = control.querySelector('.sgr-icon');
    if (!icon || currentAnimation?.icon === icon) return;
    stop();
    const request = generation;
    const [, animations] = await loadMotion();
    if (request !== generation || !icon.isConnected || reduceMotion.matches || document.hidden || !allowed()) return;
    const data = animations?.[control.dataset.sgrIconReady];
    if (!data || !window.lottie) return;
    const layer = document.createElement('span');
    layer.className = 'sgr-icon-motion';
    icon.append(layer);
    const player = window.lottie.loadAnimation({
      container: layer, renderer: 'svg', loop: false, autoplay: false,
      animationData: structuredClone(data),
    });
    currentAnimation = { player, layer, icon };
    player.addEventListener('DOMLoaded', () => {
      if (currentAnimation?.player !== player) return;
      if (!allowed()) { stop(); return; }
      const originalDuration = player.getDuration();
      const visibleDuration = Math.min(1.1, Math.max(0.74, originalDuration / 1.35));
      player.setSpeed(originalDuration / visibleDuration);
      icon.dataset.playing = '';
      started();
      player.goToAndPlay(0, true);
    });
    player.addEventListener('complete', stop);
    player.addEventListener('data_failed', stop);
  };

  const announceUnread = () => {
    const link = document.getElementById('updates-launch');
    if (!link?.dataset.sgrNotice || generation > 0) return;
    const key = `sgr:icono-novedades:${document.body.dataset.userId}`;
    try {
      if (sessionStorage.getItem(key) === link.dataset.sgrNotice) return;
    } catch (_) {}
    play(link, () => Boolean(link.querySelector('.updates-new')), () => {
      try { sessionStorage.setItem(key, link.dataset.sgrNotice); } catch (_) {}
    });
  };

  fetch(config.symbols).then(response => {
    if (!response.ok) return;
    install(document);
    new MutationObserver(records => {
      records.forEach(record => record.addedNodes.forEach(node => {
        if (node instanceof HTMLElement) install(node);
      }));
    }).observe(document.body, { childList: true, subtree: true });
    document.addEventListener('pointerover', event => {
      if (!finePointer.matches || event.pointerType !== 'mouse') return;
      const control = event.target.closest('[data-sgr-icon-ready]');
      if (!control || control.contains(event.relatedTarget) || control.id === 'updates-launch') return;
      play(control, () => control.matches(':hover'));
    });
    document.addEventListener('pointerdown', event => {
      if (event.pointerType !== 'touch') return;
      const control = event.target.closest('button[data-sgr-icon-ready]');
      if (control) play(control);
    });
    reduceMotion.addEventListener('change', event => { if (event.matches) stop(); });
    document.addEventListener('visibilitychange', () => { if (document.hidden) stop(); });
    if ('requestIdleCallback' in window) window.requestIdleCallback(announceUnread);
    else setTimeout(announceUnread, 250);
  }).catch(() => {});
})();
