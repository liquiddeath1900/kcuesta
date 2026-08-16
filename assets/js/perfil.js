/* Kcuesta — mi cuenta.
 * Depende de auth.js, que dispara 'kc:sesion' cuando hay sesión válida.
 */
(function () {
  'use strict';

  var PROVS = ['Azua','Bahoruco','Barahona','Dajabón','Distrito Nacional','Duarte','El Seibo',
    'Elías Piña','Espaillat','Hato Mayor','Hermanas Mirabal','Independencia','La Altagracia',
    'La Romana','La Vega','María Trinidad Sánchez','Monseñor Nouel','Monte Cristi','Monte Plata',
    'Pedernales','Peravia','Puerto Plata','Samaná','San Cristóbal','San José de Ocoa','San Juan',
    'San Pedro de Macorís','Sánchez Ramírez','Santiago','Santiago Rodríguez','Santo Domingo','Valverde'];

  var $ = function (id) { return document.getElementById(id); };
  var S = null;              // { user, perfil, cliente }
  var tipo = 'comprador';

  $('provincia').innerHTML = '<option value="">Elige…</option>' +
    PROVS.map(function (p) { return '<option>' + p + '</option>'; }).join('');

  function decir(msg, malo) {
    var el = $('estado');
    el.textContent = msg || '';
    el.className = 'entrar-estado' + (malo ? ' malo' : '');
  }

  function pintarTipo() {
    Array.prototype.forEach.call($('tipo').children, function (b) {
      b.classList.toggle('on', b.dataset.tipo === tipo);
    });
    $('solo-vendedor').hidden = (tipo === 'comprador');
  }

  /* Qué le falta al perfil para que el trato pueda ocurrir */
  function revisarCompleto() {
    var falta = [];
    if (!$('telefono').value.trim()) falta.push('tu teléfono');
    if (!$('provincia').value)       falta.push('tu provincia');
    if (tipo !== 'comprador' && !$('negocio').value.trim()) falta.push('el nombre de tu finca');

    var av = $('aviso');
    if (!falta.length) { av.hidden = true; return; }
    av.hidden = false;
    $('aviso-txt').textContent = 'Falta ' + falta.join(', ') +
      '. Sin eso, un comprador no puede cerrar un trato contigo.';
  }

  function cargar(det) {
    S = det;
    var u = S.user, p = S.perfil || {};

    $('cargando').hidden = true;
    $('cuenta').hidden = false;

    $('perfil-nombre').textContent = p.nombre || 'Mi cuenta';
    $('perfil-email').textContent = u.email || '';
    $('avatar').textContent = (p.nombre || u.email || '?').trim().charAt(0).toUpperCase();

    $('nombre').value   = p.nombre || '';
    $('negocio').value  = p.negocio || '';
    $('provincia').value = p.provincia || '';
    $('municipio').value = p.municipio || '';
    $('tareas').value    = p.tareas != null ? p.tareas : '';
    $('cultivos').value  = (p.cultivos || []).join(', ');
    tipo = p.tipo || 'comprador';
    pintarTipo();

    $('desde').textContent = p.creado
      ? new Date(p.creado).toLocaleDateString('es-DO', { year: 'numeric', month: 'long' })
      : '—';

    // El contacto vive en otra tabla (RLS lo protege): se pide aparte.
    S.cliente.from('perfiles_contacto')
      .select('telefono,whatsapp,metodo_registro').eq('id', u.id).single()
      .then(function (r) {
        var c = r.data || {};
        var t = (c.telefono || c.whatsapp || '').replace(/^\+1/, '');
        $('telefono').value = t;
        $('metodo').textContent = { google: 'Google', telefono: 'WhatsApp', email: 'Correo' }[c.metodo_registro] || '—';
        revisarCompleto();
      })
      .catch(function () { revisarCompleto(); });
  }

  function guardar(e) {
    e.preventDefault();
    if (!S) return;
    var btn = $('btn-guardar');
    btn.disabled = true;
    decir('Guardando…');

    var crudo = $('telefono').value.replace(/\D/g, '');
    var tel = crudo ? '+1' + crudo.slice(-10) : null;
    var cultivos = $('cultivos').value.split(',')
      .map(function (s) { return s.trim(); }).filter(Boolean);

    var perfil = {
      nombre: $('nombre').value.trim() || 'Usuario',
      negocio: $('negocio').value.trim() || null,
      provincia: $('provincia').value || null,
      municipio: $('municipio').value.trim() || null,
      tareas: $('tareas').value ? parseInt($('tareas').value, 10) : null,
      cultivos: cultivos,
      tipo: tipo
    };

    S.cliente.from('perfiles').update(perfil).eq('id', S.user.id)
      .then(function (r) {
        if (r.error) throw r.error;
        return S.cliente.from('perfiles_contacto')
          .update({ telefono: tel, whatsapp: tel }).eq('id', S.user.id);
      })
      .then(function (r) {
        if (r && r.error) throw r.error;
        decir('Guardado.');
        $('perfil-nombre').textContent = perfil.nombre;
        var n = document.querySelector('.sesion-n');
        if (n) n.textContent = perfil.nombre;
        revisarCompleto();
      })
      .catch(function (err) { decir('No se pudo guardar: ' + err.message, true); })
      .then(function () { btn.disabled = false; });
  }

  /* ---------- eventos ---------- */

  document.addEventListener('click', function (e) {
    var t = e.target.closest('[data-tipo]');
    if (t) { tipo = t.dataset.tipo; pintarTipo(); revisarCompleto(); }
  });

  ['telefono', 'provincia', 'negocio'].forEach(function (id) {
    $(id).addEventListener('change', revisarCompleto);
  });

  $('form-perfil').addEventListener('submit', guardar);

  $('btn-salir-2').addEventListener('click', function () {
    if (!S) return;
    S.cliente.auth.signOut().then(function () { location.href = 'index.html'; });
  });

  document.addEventListener('kc:sesion', function (e) { cargar(e.detail); });

  // Si tras un momento no hubo sesión, ofrecer entrar.
  setTimeout(function () {
    if (!S) { $('cargando').hidden = true; $('sin-sesion').hidden = false; }
  }, 3000);
})();
