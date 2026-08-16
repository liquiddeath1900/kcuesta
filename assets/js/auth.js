/* Kcuesta — sesión.
 *
 * El SDK de Supabase se carga SOLO cuando hace falta: al tocar un botón de
 * entrada, o si ya hay sesión guardada. La portada tiene que abrir en una
 * conexión de 384 Kbps y la mayoría de las visitas nunca inician sesión.
 */
(function () {
  'use strict';

  var CFG = {
    url:  window.KC_URL  || '',
    // La anon key es pública por diseño: RLS decide qué se puede leer.
    anon: window.KC_ANON || '',
    sdk:  'https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2/dist/umd/supabase.js'
  };

  var sb = null;
  var $ = function (id) { return document.getElementById(id); };

  function decir(msg, malo) {
    var el = $('estado');
    if (!el) return;
    el.textContent = msg || '';
    el.className = 'entrar-estado' + (malo ? ' malo' : '');
  }

  function cargarSDK() {
    return new Promise(function (ok, fail) {
      if (window.supabase) return ok(window.supabase);
      var s = document.createElement('script');
      s.src = CFG.sdk;
      s.onload = function () { ok(window.supabase); };
      s.onerror = function () { fail(new Error('No hay conexión para cargar la entrada.')); };
      document.head.appendChild(s);
    });
  }

  function cliente() {
    if (sb) return Promise.resolve(sb);
    if (!CFG.anon) return Promise.reject(new Error('Falta configurar la clave pública.'));
    return cargarSDK().then(function (lib) {
      sb = lib.createClient(CFG.url, CFG.anon, {
        auth: {
          // Recuerda al usuario en este dispositivo. El corte real de 30 días
          // se fija en Supabase (Auth → Sessions → Time-box = 720 h).
          persistSession: true,
          autoRefreshToken: true,
          detectSessionInUrl: true,
          storageKey: 'kcuesta-auth'
        }
      });
      return sb;
    });
  }

  /* Bitácora de accesos. Nunca bloquea la entrada. */
  function registrarAcceso(c, metodo) {
    return c.auth.getUser().then(function (r) {
      var u = r && r.data && r.data.user;
      if (!u) return;
      return c.from('auth_eventos').insert({
        user_id: u.id, evento: 'login', metodo: metodo,
        user_agent: navigator.userAgent.slice(0, 300)
      });
    }).catch(function () {});
  }

  function destinoTrasEntrar() {
    return location.pathname.replace(/[^/]*$/, '') + 'mercado.html';
  }

  /* ---------- Entradas ---------- */

  function entrarGoogle() {
    decir('Abriendo Google…');
    cliente().then(function (c) {
      return c.auth.signInWithOAuth({
        provider: 'google',
        options: { redirectTo: location.origin + destinoTrasEntrar() }
      });
    }).then(function (r) { if (r && r.error) throw r.error; })
      .catch(function (e) { decir('No se pudo entrar: ' + e.message, true); });
  }

  function entrarWhatsApp() {
    var paso = $('wa-paso');
    if (paso) { paso.hidden = false; $('wa-num').focus(); }
    decir('');
  }

  function enviarCodigo(e) {
    e.preventDefault();
    var crudo = ($('wa-num').value || '').replace(/\D/g, '');
    if (crudo.length < 10) { decir('Escribe tu número completo, con el código de área.', true); return; }
    var tel = '+1' + crudo.slice(-10);
    decir('Enviando código…');
    cliente().then(function (c) {
      return c.auth.signInWithOtp({ phone: tel, options: { channel: 'whatsapp' } });
    }).then(function (r) {
      if (r && r.error) throw r.error;
      decir('Te enviamos un código por WhatsApp.');
    }).catch(function (err) {
      var m = (err.message || '').toLowerCase();
      decir(/provider|disabled|sms|not enabled|unsupported/.test(m)
        ? 'La entrada por WhatsApp todavía no está activa. Usa Google por ahora.'
        : 'No se pudo enviar el código: ' + err.message, true);
    });
  }

  /* ---------- Sesión activa ---------- */

  function pintarSesion(perfil) {
    var host = $('sesion');
    if (!host) return;
    if (!perfil) {
      host.innerHTML = '<a class="boton btn-entrar" href="entrar.html">Entrar</a>';
      return;
    }
    // El nombre lleva a la cuenta; "Salir" queda dentro de esa página.
    host.innerHTML = '<a class="sesion-yo" href="perfil.html">' +
      '<span class="sesion-ini"></span><span class="sesion-n"></span></a>';
    var nom = perfil.nombre || 'Mi cuenta';
    host.querySelector('.sesion-n').textContent = nom;
    host.querySelector('.sesion-ini').textContent = nom.trim().charAt(0).toUpperCase();
  }

  function haySesionGuardada() {
    try {
      for (var i = 0; i < localStorage.length; i++) {
        var k = localStorage.key(i);
        if (k === 'kcuesta-auth' || k.indexOf('-auth-token') > -1) return true;
      }
    } catch (e) {}
    return false;
  }

  function revisarSesion() {
    if (!CFG.anon) return;
    var vuelve = /[?&#](code|access_token)=/.test(location.href);
    if (!haySesionGuardada() && !vuelve) return;

    cliente().then(function (c) {
      return c.auth.getSession().then(function (r) {
        var s = r && r.data && r.data.session;
        if (!s) { pintarSesion(null); return; }
        if (vuelve) {
          registrarAcceso(c, 'google');
          history.replaceState({}, '', location.pathname);
        }
        return c.from('perfiles').select('nombre,tipo').eq('id', s.user.id).single()
          .then(function (p) {
            var perfil = p.data || { nombre: s.user.email };
            pintarSesion(perfil);
            window.KC_SESION = { user: s.user, perfil: perfil, cliente: c };
            document.dispatchEvent(new CustomEvent('kc:sesion', { detail: window.KC_SESION }));
          });
      });
    }).catch(function () { pintarSesion(null); });
  }

  /* ---------- Eventos ---------- */

  document.addEventListener('click', function (e) {
    if (e.target.closest('#btn-google')) entrarGoogle();
    if (e.target.closest('#btn-wa'))     entrarWhatsApp();
    if (e.target.closest('#btn-salir')) {
      cliente().then(function (c) { return c.auth.signOut(); })
        .then(function () { location.href = 'index.html'; });
    }
  });

  var waForm = $('wa-paso');
  if (waForm) waForm.addEventListener('submit', enviarCodigo);

  // Si ya tiene sesión y abre la página de entrada, mandarlo al mercado.
  if (document.body.classList.contains('pag-entrar') && haySesionGuardada()) {
    cliente().then(function (c) { return c.auth.getSession(); }).then(function (r) {
      if (r && r.data && r.data.session) location.replace('mercado.html');
    }).catch(function () {});
  }

  revisarSesion();
})();
