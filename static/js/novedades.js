(() => {
  'use strict';
  document.querySelectorAll('[data-update-tour]').forEach(button => {
    button.addEventListener('click', () => document.getElementById('tour-tutorial-btn')?.click());
  });
})();
