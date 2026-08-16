/* Kcuesta — lógica del mercado. Sin dependencias. */
(function () {
  'use strict';

  var P = window.KC.precios;
  var A = window.KC.anuncios;
  var cultivoPorId = {};
  P.cultivos.forEach(function (c) { cultivoPorId[c.id] = c; });

  /* ---------- utilidades ---------- */

  function rd(n, dec) {
    return 'RD$ ' + n.toLocaleString('es-DO', {
      minimumFractionDigits: dec === undefined ? 0 : dec,
      maximumFractionDigits: dec === undefined ? 0 : dec
    });
  }

  // Diferencia del anuncio contra el precio mayorista oficial, por unidad comparable
  function brecha(an) {
    if (!an.mercado_ref_unidad) return null;
    return ((an.precio_por_unidad - an.mercado_ref_unidad) / an.mercado_ref_unidad) * 100;
  }

  function textoBrecha(p) {
    var abs = Math.abs(p).toFixed(0);
    if (p <= -1) return { txt: abs + '% bajo el precio del mercado', cls: 'baja' };
    if (p >= 1) return { txt: abs + '% sobre el precio del mercado', cls: 'sube' };
    return { txt: 'Al precio del mercado', cls: '' };
  }

  function esc(s) {
    return String(s).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }

  function diasDesde(iso) {
    var d = Math.round((new Date('2026-08-16') - new Date(iso)) / 86400000);
    if (d <= 0) return 'Hoy';
    if (d === 1) return 'Ayer';
    return 'Hace ' + d + ' días';
  }

  /* ---------- cintillo de precios oficiales ---------- */

  function pintarCintillo() {
    var destacados = P.cultivos.filter(function (c) { return c.destacado; });
    var resto = P.cultivos.filter(function (c) { return !c.destacado; });
    var todos = destacados.concat(resto);

    var html = todos.map(function (c) {
      var d = c.cambio_semanal_mayorista || 0;
      var cls = d > 0 ? 'up' : (d < 0 ? 'down' : 'flat');
      var flecha = d > 0 ? '▲' : (d < 0 ? '▼' : '–');
      var signo = d === 0 ? 'estable' : Math.abs(d).toFixed(1) + '%';
      return '<span class="tick"><b>' + esc(c.nombre) + '</b>' +
        '<span class="v cifra">' + rd(c.precio_mayorista) + '</span>' +
        '<span class="silencio">/' + esc(c.unidad_mayorista) + '</span>' +
        '<span class="d ' + cls + '">' + flecha + ' ' + signo + '</span></span>';
    }).join('');

    // Dos copias idénticas: al desplazar exactamente el 50% el salto es invisible.
    var pista = document.getElementById('cintillo');
    pista.innerHTML = '<div class="cinta-grupo">' + html + '</div>' +
                      '<div class="cinta-grupo" aria-hidden="true">' + html + '</div>';

    // La duración depende del ancho real: velocidad constante, no importa
    // cuántos rubros haya ni el tamaño de la pantalla.
    requestAnimationFrame(function () {
      var g = pista.querySelector('.cinta-grupo');
      if (!g) return;
      var px = g.getBoundingClientRect().width;
      if (px > 0) pista.style.setProperty("--vel", Math.round(px / 45) + "s");
    });
  }

  /* ---------- filtros por categoría ---------- */

  var CATS = [
    { id: 'todos', nombre: 'Todo' },
    { id: 'viveres', nombre: 'Víveres' },
    { id: 'vegetales', nombre: 'Vegetales' },
    { id: 'frutas', nombre: 'Frutas' },
    { id: 'granos', nombre: 'Granos' }
  ];
  var catActiva = 'todos';

  function pintarPastillas() {
    document.getElementById('pastillas').innerHTML = CATS.map(function (c) {
      return '<button class="pastilla' + (c.id === catActiva ? ' on' : '') +
        '" data-cat="' + c.id + '">' + c.nombre + '</button>';
    }).join('');
  }

  /* ---------- tarjeta de anuncio ---------- */

  function tarjeta(an) {
    var cult = cultivoPorId[an.cultivo] || {};
    var v = A.vendedores[an.vendedor] || {};
    var p = brecha(an);
    var b = p === null ? null : textoBrecha(p);

    var foto = an.foto
      ? '<img src="' + esc(an.foto) + '" alt="' + esc(an.titulo) + '" loading="lazy" width="480" height="360">'
      : '<div class="sin-foto"><span>' + esc(an.titulo.charAt(0)) + '</span></div>';

    return '' +
    '<article class="tarjeta">' +
      '<div class="tarjeta-foto">' + foto +
        '<span class="flota chip' + (v.verificado ? ' verificado' : '') + '">' +
          (v.verificado ? '✓ Verificado' : 'Nuevo') + '</span>' +
        (an.urgente ? '<span class="flota flota-d chip sube">Urge vender</span>' : '') +
      '</div>' +
      '<div class="tarjeta-cuerpo">' +
        '<div>' +
          '<div class="tarjeta-tit">' + esc(an.titulo) + '</div>' +
          '<div class="tarjeta-meta">' +
            esc(an.calidad) + ' · ' + esc(an.cantidad) + ' ' + esc(an.unidad_venta) +
            (an.cantidad > 1 ? 'es' : '') +
          '</div>' +
        '</div>' +

        '<div class="linea-meta">' +
          '<span>📍 ' + esc(an.municipio) + ', ' + esc(an.provincia) + '</span>' +
          '<span>🗓 ' + esc(an.corte_texto) + '</span>' +
        '</div>' +

        '<div class="ancla">' +
          '<div class="nivel nivel-mayor">' +
            '<span class="nivel-et">Por mayor</span>' +
            '<div class="ancla-precio">' +
              '<span class="n cifra">' + rd(an.precio) + '</span>' +
              '<span class="u">/ ' + esc(an.unidad_venta) + '</span>' +
            '</div>' +
            (b ? '<div class="delta ' + b.cls + '">' + b.txt + '</div>' : '') +
          '</div>' +
          (an.detalle && an.detalle.disponible
            ? '<div class="nivel nivel-detalle">' +
                '<span class="nivel-et">Al detalle</span>' +
                '<div class="det-linea">' +
                  '<b class="cifra">' + rd(an.detalle.precio, an.detalle.precio % 1 ? 2 : 0) + '</b>' +
                  '<span class="u">/ ' + esc(an.detalle.unidad) + '</span>' +
                  '<span class="det-sep">·</span>' +
                  '<span class="det-min">mínimo ' + esc(an.detalle.minimo) + ' ' +
                    esc(an.detalle.unidad.toLowerCase()) + 's</span>' +
                '</div>' +
              '</div>'
            : '<div class="nivel nivel-detalle vacio-det">' +
                '<span class="nivel-et">Al detalle</span>' +
                '<div class="det-linea silencio">Solo vende por mayor</div>' +
              '</div>') +
          '<div class="ancla-ref">' +
            'Mercado Nuevo hoy: <strong class="cifra">' + rd(an.mercado_ref_unidad, 2) + '</strong> por unidad' +
          '</div>' +
        '</div>' +

        '<div class="entrega">' +
          '<span class="chip">' + esc(an.entrega) + '</span>' +
          '<span class="chip">' + esc(an.pago) + '</span>' +
        '</div>' +

        '<div class="vend">' +
          '<div class="vend-n">' + esc(v.nombre || '') + '</div>' +
          '<div class="silencio">' + esc(v.responsable || '') +
            (v.tareas ? ' · ' + v.tareas + ' tareas' : '') + ' · ' + diasDesde(an.publicado) + '</div>' +
        '</div>' +

        '<div class="acciones">' +
          '<button class="boton" data-contactar="' + esc(an.id) + '">Contactar</button>' +
          '<button class="boton fantasma" data-tel="' + esc(an.id) + '">Ver teléfono</button>' +
        '</div>' +
      '</div>' +
    '</article>';
  }

  /* ---------- render ---------- */

  function render() {
    var lista = A.anuncios.filter(function (an) {
      if (catActiva === 'todos') return true;
      var c = cultivoPorId[an.cultivo];
      return c && c.categoria === catActiva;
    });

    var orden = document.getElementById('orden').value;
    lista.sort(function (x, y) {
      if (orden === 'brecha') return (brecha(x) || 0) - (brecha(y) || 0);
      if (orden === 'barato') return x.precio_por_unidad - y.precio_por_unidad;
      if (orden === 'volumen') return y.cantidad - x.cantidad;
      return new Date(y.publicado) - new Date(x.publicado);
    });

    document.getElementById('cuenta').textContent =
      lista.length + (lista.length === 1 ? ' resultado' : ' resultados');
    document.getElementById('rejilla').innerHTML = lista.map(tarjeta).join('');
    document.getElementById('vacio').hidden = lista.length !== 0;
  }

  /* ---------- eventos ---------- */

  document.addEventListener('click', function (e) {
    var pas = e.target.closest('[data-cat]');
    if (pas) { catActiva = pas.dataset.cat; pintarPastillas(); render(); return; }

    var con = e.target.closest('[data-contactar]');
    if (con) { abrirContacto(con.dataset.contactar); return; }

    var tel = e.target.closest('[data-tel]');
    if (tel) {
      tel.outerHTML = '<a class="boton fantasma" href="tel:+18095550100">(809) 555-0100</a>';
      return;
    }
  });

  function abrirContacto(id) {
    var an = A.anuncios.filter(function (a) { return a.id === id; })[0];
    if (!an) return;
    var v = A.vendedores[an.vendedor] || {};
    var msg = 'Saludos, vi su anuncio en Kcuesta: ' + an.titulo + ' (' + an.cantidad + ' ' +
      an.unidad_venta + ') en ' + an.municipio + ' a ' + rd(an.precio) + '. ¿Todavía está disponible?';
    var m = document.getElementById('modal');
    m.querySelector('.modal-tit').textContent = 'Contactar a ' + (v.nombre || 'el productor');
    m.querySelector('.modal-msg').value = msg;
    m.showModal();
  }

  document.getElementById('orden').addEventListener('change', render);

  pintarCintillo();
  pintarPastillas();
  render();

  /* Hoja informativa: la explicación a un toque, fuera del camino. */
  var dlgInfo = document.getElementById('dlg-info');
  document.addEventListener('click', function (e) {
    if (e.target.closest('#btn-info') && dlgInfo && dlgInfo.showModal) dlgInfo.showModal();
    if (e.target.closest('#btn-info-cerrar') && dlgInfo) dlgInfo.close();
  });
  if (dlgInfo) dlgInfo.addEventListener('click', function (e) {
    if (e.target === dlgInfo) dlgInfo.close();   // tocar fuera cierra
  });


  /* Tocar la cinta la detiene, para poder leer un precio en el teléfono. */
  var cinta = document.querySelector('.cintillo');
  if (cinta) {
    cinta.addEventListener('click', function () { cinta.classList.toggle('quieto'); });
  }

})();
