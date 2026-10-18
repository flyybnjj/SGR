
(() => {
  'use strict';
  const decode = value => Uint8Array.from(atob(value.replace(/-/g, '+').replace(/_/g, '/').padEnd(Math.ceil(value.length / 4) * 4, '=')), c => c.charCodeAt(0));
  const encode = value => btoa(String.fromCharCode(...new Uint8Array(value))).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
  const supported = window.isSecureContext && !!window.PublicKeyCredential && !!navigator.credentials;
  let busy = false;
  function status(message) {
    document.querySelectorAll('[data-passkey-status]').forEach(el => { el.textContent = message; });
  }
  async function post(url, body) {
    const csrf = document.querySelector('[name="csrfmiddlewaretoken"]')?.value;
    const response = await fetch(url, {method: 'POST', credentials: 'same-origin', headers: {'Content-Type': 'application/json', 'X-CSRFToken': csrf || ''}, body: JSON.stringify(body)});
    let data;
    try { data = await response.json(); } catch { throw new Error('No se pudo completar la solicitud. Recarga la página e intenta nuevamente.'); }
    if (!response.ok) throw new Error(data.error || 'La solicitud no pudo completarse.');
    return data;
  }
  function serialize(credential) {
    const response = credential.response;
    const result = {id: credential.id, rawId: encode(credential.rawId), type: credential.type, response: {clientDataJSON: encode(response.clientDataJSON)}};
    if (response.attestationObject) {
      result.response.attestationObject = encode(response.attestationObject);
      result.response.transports = response.getTransports?.() || [];
    } else {
      result.response.authenticatorData = encode(response.authenticatorData);
      result.response.signature = encode(response.signature);
      result.response.userHandle = response.userHandle ? encode(response.userHandle) : null;
    }
    return result;
  }
  async function run(button, action) {
    if (busy) return;
    busy = true;
    button.disabled = true;
    button.setAttribute('aria-busy', 'true');
    status('Sigue las indicaciones de tu dispositivo…');
    try {
      const result = await action();
      if (result?.redirect) window.location.assign(result.redirect);
    } catch (error) {
      const message = error.name === 'NotAllowedError' || error.name === 'AbortError'
        ? 'No se completó la verificación. Puedes volver a intentarlo o usar tu contraseña.'
        : error.name === 'InvalidStateError' ? 'Esa passkey ya está registrada. Usa otra o ingresa con la que ya tienes.'
        : error.name === 'SecurityError' ? 'Usa la dirección configurada para las passkeys y un navegador compatible.'
        : error.message || 'No se pudo completar la operación.';
      status(message);
      if (window.Swal) await Swal.fire({icon: 'warning', title: 'Passkey', text: message, confirmButtonText: 'Entendido'});
    } finally {
      busy = false;
      button.disabled = false;
      button.removeAttribute('aria-busy');
    }
  }
  document.querySelectorAll('[data-passkey-action]').forEach(button => {
    button.disabled = !supported;
    button.addEventListener('click', () => run(button, async () => {
      const options = await post('/passkeys/ingreso/opciones/', {purpose: button.dataset.passkeyAction});
      options.challenge = decode(options.challenge);
      (options.allowCredentials || []).forEach(item => { item.id = decode(item.id); });
      const credential = await navigator.credentials.get({publicKey: options});
      if (!credential) throw new Error('No se seleccionó una passkey.');
      return post('/passkeys/ingreso/verificar/', serialize(credential));
    }));
  });
  const register = document.querySelector('[data-passkey-register]');
  if (register) {
    register.querySelector('[type="submit"]').disabled = !supported;
    register.addEventListener('submit', event => {
      event.preventDefault();
      if (!register.reportValidity()) return;
      run(register.querySelector('[type="submit"]'), async () => {
        const password = register.elements.password;
        let options;
        try {
          options = await post(register.action, {name: register.elements.name.value.trim(), password: password.value, preferred: register.elements.preferred.checked});
        } finally { password.value = ''; }
        options.challenge = decode(options.challenge);
        options.user.id = decode(options.user.id);
        (options.excludeCredentials || []).forEach(item => { item.id = decode(item.id); });
        const credential = await navigator.credentials.create({publicKey: options});
        if (!credential) throw new Error('No se creó una passkey.');
        return post('/passkeys/registro/verificar/', serialize(credential));
      });
    });
  }
  document.querySelectorAll('[data-passkey-revoke]').forEach(button => button.addEventListener('click', () => run(button, async () => {
    if (!window.Swal) throw new Error('Recarga la página para abrir la confirmación.');
    const answer = await Swal.fire({icon: 'warning', title: 'Revocar passkey', text: `Confirma tu contraseña para revocar «${button.dataset.passkeyName}».`, input: 'password', inputLabel: 'Contraseña actual', inputAttributes: {autocomplete: 'current-password'}, showCancelButton: true, confirmButtonText: 'Revocar', cancelButtonText: 'Cancelar', inputValidator: value => !value && 'Escribe tu contraseña actual.'});
    if (!answer.isConfirmed) { status('No se revocó la passkey.'); return; }
    return post(button.dataset.passkeyRevoke, {password: answer.value});
  })));
  document.querySelector('[data-passkey-preference]')?.addEventListener('submit', event => {
    event.preventDefault();
    const form = event.currentTarget;
    run(form.querySelector('button'), () => post(form.action, {preferred: form.elements.preferred.checked}));
  });
  if (!supported) status('Este navegador no admite passkeys aquí. Usa un navegador compatible en HTTPS o localhost; puedes continuar con contraseña.');
})();
