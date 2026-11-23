(() => {
  'use strict';

  const labels = document.querySelectorAll('[data-quarter-rotate]:has([data-quarter-period])');
  for (const label of labels) label.classList.add('quarter-alternating');
  if (labels.length) {
    window.setInterval(() => {
      if (document.hidden) return;
      for (const label of labels) label.classList.toggle('show-quarter');
    }, 5000);
  }

  if (!HTMLInputElement.prototype.showPicker) return;
  const enhance = root => {
    for (const input of root.querySelectorAll('input[type="date"]:not([data-date-control])')) {
      input.dataset.dateControl = '';
      const wrapper = document.createElement('div');
      wrapper.className = 'date-control';
      const button = document.createElement('button');
      button.type = 'button';
      button.className = 'btn-stitch btn-stitch-secondary date-picker-button';
      button.setAttribute('aria-label', 'Abrir calendario' + (input.labels?.[0] ? ' · ' + input.labels[0].textContent.trim() : ''));
      button.innerHTML = '<i class="bi bi-calendar3" aria-hidden="true"></i>';
      button.addEventListener('click', () => {
        input.focus();
        try { input.showPicker(); } catch (_) { /* El indicador nativo sigue disponible. */ }
      });
      input.before(wrapper);
      wrapper.append(input, button);
    }
  };
  const main = document.getElementById('main-content');
  if (main) {
    enhance(main);
    new MutationObserver(() => enhance(main)).observe(main, {childList: true, subtree: true});
  }
})();
