(() => {
  'use strict';
  const menu = document.querySelector('.tubo-filter-menu');
  if (!menu) return;
  const trigger = menu.querySelector('summary');
  document.addEventListener('click', event => {
    if (menu.open && !menu.contains(event.target)) menu.open = false;
  });
  menu.addEventListener('keydown', event => {
    if (event.key !== 'Escape' || !menu.open) return;
    // The inner select handles its own Escape before the filter panel closes.
    if (menu.querySelector('.dropdown-menu.show')) return;
    event.preventDefault();
    menu.open = false;
    trigger.focus();
  });
})();
