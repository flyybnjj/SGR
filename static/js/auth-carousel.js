(() => {
  const root = document.getElementById('laSerenaAuthCarousel');
  if (!root || !window.bootstrap?.Carousel) return;
  const toggle = root.querySelector('[data-carousel-toggle]');
  const reduced = matchMedia('(prefers-reduced-motion: reduce)');
  const desktop = matchMedia('(min-width: 992px)');
  const carousel = bootstrap.Carousel.getOrCreateInstance(root, { interval: 6000, ride: false, pause: false, touch: true, keyboard: true, wrap: true });
  let paused = reduced.matches;
  const sync = () => {
    const focused = root.contains(document.activeElement) && document.activeElement !== toggle;
    carousel.pause();
    if (!paused && !document.hidden && desktop.matches && !focused) carousel.cycle();
    toggle.setAttribute('aria-label', paused ? 'Reproducir carrusel de fotos' : 'Pausar carrusel de fotos');
    toggle.setAttribute('aria-pressed', String(paused));
    toggle.title = paused ? 'Reproducir fotos' : 'Pausar fotos';
    toggle.querySelector('i').className = paused ? 'bi bi-play-fill' : 'bi bi-pause-fill';
  };
  const preloadNext = () => {
    const slides = [...root.querySelectorAll('.carousel-item')];
    const current = slides.findIndex(slide => slide.classList.contains('active'));
    const next = slides[(current + 1) % slides.length]?.querySelector('img');
    if (next) next.loading = 'eager';
  };
  toggle.hidden = false;
  toggle.addEventListener('click', () => { paused = !paused; sync(); });
  root.addEventListener('focusin', sync);
  root.addEventListener('focusout', () => requestAnimationFrame(sync));
  root.addEventListener('slid.bs.carousel', preloadNext);
  document.addEventListener('visibilitychange', sync);
  desktop.addEventListener('change', sync);
  reduced.addEventListener('change', event => { if (event.matches) paused = true; sync(); });
  window.addEventListener('pagehide', () => carousel.pause());
  preloadNext();
  sync();
})();
