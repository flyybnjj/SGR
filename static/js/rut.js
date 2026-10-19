(() => {
  'use strict';
  const compact = value => value.toUpperCase().replace(/[.\s-]/g, '');
  function normalize(value) {
    const raw = value.replace(/\s+/g, '').toUpperCase();
    if (!/^(?:[0-9]{1,8}|[0-9]{1,3}(?:\.[0-9]{3}){1,2})-?[0-9K]$/.test(raw)) return null;
    const clean = compact(raw), body = clean.slice(0, -1), dv = clean.slice(-1);
    if (body.length > 8 || !Number(body)) return null;
    let sum = 0;
    for (let i = 0; i < body.length; i++) sum += Number(body[body.length - i - 1]) * (2 + i % 6);
    const remainder = 11 - sum % 11;
    const expected = remainder === 11 ? '0' : remainder === 10 ? 'K' : String(remainder);
    return dv === expected ? `${Number(body)}-${dv}` : null;
  }
  function format(value) {
    if (!/^[0-9kK.\s-]*$/.test(value)) return value;
    const clean = compact(value);
    if (!/^[0-9]{0,8}[0-9K]?$/.test(clean) || clean.length < 2) return value;
    return clean.slice(0, -1).replace(/\B(?=(?:[0-9]{3})+(?![0-9]))/g, '.') + '-' + clean.slice(-1);
  }
  function bind(root = document) {
    root.querySelectorAll('input[data-validate="rut"], input[name="rut"], input[name$="-rut"], input[data-rut-identifier]').forEach(field => {
      if (field.dataset.rutReady) return;
      field.dataset.rutReady = 'true';
      if (field.hasAttribute('data-rut-identifier')) {
        field.addEventListener('input', () => { delete field.dataset.rutOriginal; });
        field.addEventListener('blur', () => {
          if (!normalize(field.value)) return;
          if (!field.dataset.rutOriginal) field.dataset.rutOriginal = field.value;
          field.value = format(field.value);
        });
        field.form?.addEventListener('formdata', event => {
          const original = field.dataset.rutOriginal;
          if (original && normalize(original) === normalize(field.value)) event.formData.set(field.name, original);
        });
        return;
      }
      field.maxLength = 24;
      field.autocapitalize = 'characters';
      field.spellcheck = false;
      const update = () => {
        const old = field.value, position = field.selectionStart;
        const digitsBefore = compact(old.slice(0, position)).length;
        const next = format(old);
        if (next === old) return;
        field.value = next;
        if (position === old.length) field.setSelectionRange(next.length, next.length);
        else {
          let cursor = 0, count = 0;
          while (cursor < next.length && count < digitsBefore) {
            if (/[0-9K]/.test(next[cursor])) count++;
            cursor++;
          }
          field.setSelectionRange(cursor, cursor);
        }
      };
      field.addEventListener('input', event => { if (!event.isComposing) update(); });
      field.addEventListener('compositionend', update);
      field.addEventListener('blur', update);
      update();
    });
  }
  window.MunicipalRut = {normalize, format, bind};
  bind();
})();
