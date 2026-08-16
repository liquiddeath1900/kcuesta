/* Kcuesta — lógica del mercado. Sin dependencias. */
(function () {
  'use strict';

  var P = window.KC.precios;
  var A = window.KC.anuncios;
  var O = window.KC.ofertas || { ofertas: [], cadenas: {} };
  var cultivoPorId = {};
  P.cultivos.forEach(function (c) { cultivoPorId[c.id] = c; });

  // Mientras no haya productores publicando, el mercado muestra ofertas
  // reales de supermercado en vez de anuncios de muestra. No se disfrazan
  // de oferta de finca: son precio de góndola y la tarjeta lo dice. Sirven
  // de referencia — es contra este número que se leerá la primera oferta
  // de finca que entre.
  var HAY_ANUNCIOS = A.anuncios.length > 0;

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
    var hoy = new Date();
    hoy.setHours(0, 0, 0, 0);
    var d = Math.round((hoy - new Date(iso)) / 86400000);
    if (d <= 0) return 'Hoy';
    if (d === 1) return 'Ayer';
    return 'Hace ' + d + ' días';
  }

  /* ---------- cintillo de precios oficiales ---------- */

  function pintarCintillo() {
    // No todo rubro trae mayorista: el Ministerio publica varios solo a
    // nivel minorista o de supermercado. La cinta cotiza por mayor, así que
    // los que no lo tienen se quedan fuera en vez de imprimir un hueco.
    var conMayorista = P.cultivos.filter(function (c) {
      return typeof c.precio_mayorista === 'number';
    });
    var destacados = conMayorista.filter(function (c) { return c.destacado; });
    var resto = conMayorista.filter(function (c) { return !c.destacado; });
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
    { id: 'granos', nombre: 'Granos' },
    // Faltaba entera: las fuentes traen cerdo, pollo, res, huevos y leche,
    // así que había rubros que ningún filtro alcanzaba. Se rotula
    // "Pecuario" —el término del Ministerio— y no "Carnes", que dejaba
    // fuera el huevo y la leche que también caen aquí.
    { id: 'pecuario', nombre: 'Pecuario' }
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

  /* ---------- tarjeta de rubro (comparación de precios) ----------
     Una tarjeta por RUBRO, no por oferta. Con 147 ofertas en 43 rubros, la
     lista plana repetía "Ají" trece veces seguidas.

     La tarjeta cerrada carga todo lo que hace falta para decidir sin tocar
     nada: mejor precio, cuántas tiendas, el rango y el sobreprecio contra
     el mayorista. Se abre con <details>/<summary> nativo — ya trae
     semántica de botón y estado abierto/cerrado para lectores de pantalla,
     sin ARIA y sin JS.

     Los porcentajes se reservan para la comparación contra el mayorista,
     donde son grandes y cuentan la historia (+83%). Entre cadenas la
     diferencia es de RD$4 a RD$25 y ahí un "+7%" no dice nada, así que va
     en pesos. */

  function tarjetaRubro(r) {
    var cad = function (id) { return (O.cadenas[id] || {}).nombre || id; };
    var mejor = r.ofertas[0];
    var hayVarias = r.n > 1;
    // Todo se compara POR LIBRA. Antes la cebolla decía "RD$46 – RD$10,750"
    // porque metía la libra suelta y el saco de 50 en el mismo rango: el
    // saco parecía 234 veces más caro cuando por libra es 4.7.
    var porLb = r.precio_lb_min !== null && r.precio_lb_min !== undefined;
    var rango = hayVarias && porLb && r.precio_lb_max > r.precio_lb_min;

    var foto = r.foto
      ? '<img src="' + esc(r.foto) + '" alt="' + esc(r.nombre) + '" loading="lazy" width="160" height="160">'
      : '<div class="sin-foto"><span>' + esc(r.nombre.charAt(0)) + '</span></div>';

    var marca = r.sobreprecio === null ? ''
      : '<span class="marca ' + (r.sobreprecio > 0 ? 'sube' : 'baja') + '">' +
          (r.sobreprecio > 0 ? '+' : '') + r.sobreprecio + '% sobre mayorista</span>';

    // Encabezado: nombre a la izquierda, precio a la derecha en la misma
    // línea base. Es la franja que se escanea con el pulgar.
    // La referencia mayorista va en su PROPIA fila, a todo el ancho. Metida
    // en la columna de texto la dejaba en 111px y todo se partía en cinco
    // líneas: la cabecera medía 218px de alto en un teléfono.
    var cabecera =
      '<div class="rb-foto">' + foto + '</div>' +
      '<div class="rb-txt">' +
        '<div class="rb-nom">' + esc(r.nombre) + '</div>' +
        '<div class="rb-meta">' +
          (hayVarias ? r.n + ' tiendas' : '1 tienda') +
          (rango ? ' · ' + rd(r.precio_lb_min, 2) + ' – ' + rd(r.precio_lb_max, 2) + '/lb'
                 : ' · ' + esc(cad(mejor.cadena))) +
        '</div>' +
      '</div>' +
      '<div class="rb-precio">' +
        '<span class="cifra">' +
          rd(porLb ? r.precio_lb_min : r.precio_min, 2) + '</span>' +
        '<span class="rb-u">' + (porLb ? '/lb' : '/' + esc(mejor.unidad)) + '</span>' +
      '</div>' +
      (r.mercado_ref_unidad && porLb
        ? '<div class="rb-ref">Mayorista ' + rd(r.mercado_ref_unidad, 2) + '/lb ' + marca + '</div>'
        : '<div class="rb-ref silencio">Sin referencia comparable</div>');

    // Un solo precio no necesita desplegable: se dibuja la misma cáscara
    // sin control, para que los rubros de una sola tienda no parezcan
    // datos rotos al lado de los demás.
    //
    // Tampoco se le cuelga la lista: con una sola oferta, la cabecera YA
    // trae el precio y la tienda, así que la lista repetía lo mismo y
    // dejaba estas trece tarjetas al doble de alto que las demás. Solo se
    // rescata el enlace a la tienda.
    if (!hayVarias) {
      return '<article class="rubro rubro-sola">' +
        '<div class="rb-cab">' + cabecera +
          (mejor.url
            ? '<a class="rb-ir" href="' + esc(mejor.url) + '" target="_blank" rel="noopener nofollow">Ver →</a>'
            : '') +
        '</div>' +
      '</article>';
    }

    return '<article class="rubro">' +
      '<details>' +
        '<summary class="rb-cab">' + cabecera +
          '<span class="rb-flecha" aria-hidden="true">▾</span>' +
        '</summary>' +
        filasOfertas(r) +
      '</details>' +
    '</article>';
  }

  function filasOfertas(r) {
    var cad = function (id) { return (O.cadenas[id] || {}).nombre || id; };
    var base = r.precio_lb_min;

    return '<ul class="rb-lista">' + r.ofertas.map(function (o, i) {
      // Entre cadenas la diferencia va en PESOS por libra. En porcentaje
      // sería ruido: son RD$4 a RD$25. El porcentaje se guarda para el
      // mayorista, donde es +161% y sí cuenta algo.
      // No hay insignia de "más barato", ni siquiera para las cadenas.
      // Premiar visualmente al precio más bajo es la guerra de precios
      // convertida en trofeo, y el día que esta lista traiga productores
      // —que son los usuarios de Kcuesta— ese trofeo los pone a competir a
      // la baja entre ellos. Ver ESCALA.md. La lista ya viene de menor a
      // mayor: quien busca el más barato lo tiene de primero igual, sin que
      // el sitio le diga a nadie que rebajar es lo que se premia.
      var etiqueta;
      if (!o.precio_lb) {
        etiqueta = '<span class="rb-dif">empaque sin peso declarado</span>';
      } else if (i === 0) {
        etiqueta = '';
      } else {
        var dif = o.precio_lb - base;
        etiqueta = '<span class="rb-dif">+' + rd(dif, 2) + '/lb</span>';
      }
      var rebaja = (o.precio_lista && o.precio_lista > o.precio)
        ? ' <s class="silencio cifra">' + rd(o.precio_lista, 2) + '</s>' : '';

      return '<li class="rb-fila">' +
        '<div class="rb-cadena">' +
          '<b>' + esc(cad(o.cadena)) + '</b>' +
          '<span class="silencio rb-desc">' + esc(o.titulo) + '</span>' +
        '</div>' +
        '<div class="rb-cifras">' +
          '<span class="cifra rb-p">' +
            rd(o.precio_lb || o.precio, 2) + '</span>' +
          '<span class="rb-u">' + (o.precio_lb ? '/lb' : '/' + esc(o.unidad)) + '</span>' +
          // El precio de etiqueta también se muestra: es lo que se paga en
          // caja, y el de por libra es para comparar.
          (o.precio_lb && o.libras !== 1
            ? '<span class="rb-etiq silencio">' + rd(o.precio, 2) + ' el empaque</span>'
            : '') + rebaja +
          etiqueta +
        '</div>' +
        (o.url
          ? '<a class="rb-ir" href="' + esc(o.url) + '" target="_blank" rel="noopener nofollow">Ver →</a>'
          : '') +
      '</li>';
    }).join('') + '</ul>' +
    '<div class="rb-pie silencio">Precio al consumidor, no de finca · ' +
      esc(diasDesde(r.ofertas[0].fecha)) + ' · foto: ' + esc(r.foto_credito) + '</div>';
  }

  /* ---------- tarjeta de vendedor ----------
     El otro eje. Agrupar solo por rubro esconde que una cadena está en
     cuarenta tarjetas, y cuando entren productores de verdad una finca va a
     publicar plátano, yuca y ají a la vez. Son dos preguntas distintas:
     "¿a cómo está el ají?" y "¿qué tiene esta finca?". */

  function tarjetaVendedor(v) {
    var med = v.sobreprecio_mediana;
    return '<article class="rubro vendedor">' +
      '<details>' +
        '<summary class="rb-cab">' +
          '<div class="rb-txt">' +
            '<div class="rb-nom">' + esc(v.nombre) + '</div>' +
            '<div class="rb-meta">' + v.n_rubros + ' rubros · ' + v.n + ' artículos</div>' +
            (med === null ? ''
              : '<div class="rb-ref">Mediana <span class="marca ' +
                  (med > 0 ? 'sube' : 'baja') + '">' + (med > 0 ? '+' : '') + med +
                  '% sobre mayorista</span></div>') +
          '</div>' +
          '<span class="rb-flecha" aria-hidden="true">▾</span>' +
        '</summary>' +
        '<ul class="rb-lista">' + v.articulos.map(function (a) {
          return '<li class="rb-fila">' +
            '<div class="rb-cadena">' +
              '<b>' + esc(a.nombre) + '</b>' +
              '<span class="silencio rb-desc">' + esc(a.titulo) + '</span>' +
            '</div>' +
            '<div class="rb-cifras">' +
              '<span class="cifra rb-p">' + rd(a.precio, a.precio % 1 ? 2 : 0) + '</span>' +
              '<span class="rb-u">/' + esc(a.unidad) + '</span>' +
            '</div>' +
            (a.url ? '<a class="rb-ir" href="' + esc(a.url) + '" target="_blank" rel="noopener nofollow">Ver →</a>' : '') +
          '</li>';
        }).join('') + '</ul>' +
      '</details>' +
    '</article>';
  }

  /* ---------- render ---------- */

  // Filtro por cadena: la investigación es clara en que agrupar por cadena
  // rompe la comparación, pero filtrar por ella sí responde "¿qué cobra
  // Nacional?" sin reordenar nada.
  var cadenaActiva = 'todas';
  var vista = 'rubro';          // 'rubro' | 'vendedor'

  function render() {
    var orden = document.getElementById('orden').value;
    var lista, html, etiqueta;

    if (HAY_ANUNCIOS) {
      lista = A.anuncios.filter(function (an) {
        if (catActiva === 'todos') return true;
        var c = cultivoPorId[an.cultivo];
        return c && c.categoria === catActiva;
      });
      lista.sort(function (x, y) {
        if (orden === 'brecha') return (brecha(x) || 0) - (brecha(y) || 0);
        if (orden === 'barato') return x.precio_por_unidad - y.precio_por_unidad;
        if (orden === 'volumen') return y.cantidad - x.cantidad;
        return new Date(y.publicado) - new Date(x.publicado);
      });
      html = lista.map(tarjeta).join('');
      etiqueta = lista.length === 1 ? ' anuncio' : ' anuncios';

    } else if (vista === 'vendedor') {
      lista = O.vendedores.slice();
      html = lista.map(tarjetaVendedor).join('');
      etiqueta = lista.length === 1 ? ' vendedor' : ' vendedores';

    } else {
      lista = O.rubros.filter(function (r) {
        if (catActiva !== 'todos' && r.categoria !== catActiva) return false;
        if (cadenaActiva !== 'todas' &&
            !r.ofertas.some(function (o) { return o.cadena === cadenaActiva; })) return false;
        return true;
      });

      // Si hay filtro de cadena, se recorta cada rubro a esa cadena: si no,
      // la tarjeta diría "5 tiendas" mientras el filtro dice una.
      if (cadenaActiva !== 'todas') {
        lista = lista.map(function (r) {
          var solo = r.ofertas.filter(function (o) { return o.cadena === cadenaActiva; });
          var precios = solo.map(function (o) { return o.precio; });
          return Object.assign({}, r, {
            ofertas: solo, n: solo.length,
            precio_min: Math.min.apply(null, precios),
            precio_max: Math.max.apply(null, precios),
            sobreprecio: r.mercado_ref_unidad
              ? Math.round((Math.min.apply(null, precios) - r.mercado_ref_unidad) /
                  r.mercado_ref_unidad * 100)
              : null
          });
        });
      }

      lista.sort(function (x, y) {
        if (orden === 'brecha') return (y.sobreprecio || -1e9) - (x.sobreprecio || -1e9);
        if (orden === 'barato') return x.precio_min - y.precio_min;
        if (orden === 'nombre') return x.nombre.localeCompare(y.nombre, 'es');
        return (y.n - x.n) || x.nombre.localeCompare(y.nombre, 'es');
      });
      html = lista.map(tarjetaRubro).join('');
      etiqueta = lista.length === 1 ? ' rubro' : ' rubros';
    }

    document.getElementById('cuenta').textContent = lista.length + etiqueta;
    document.getElementById('rejilla').innerHTML = html;
    document.getElementById('vacio').hidden = lista.length !== 0;
  }

  /* ---------- controles de vista y cadena ---------- */

  function pintarControles() {
    if (HAY_ANUNCIOS) return;

    var vistas = document.getElementById('vistas');
    if (vistas) {
      vistas.innerHTML =
        '<button class="pastilla' + (vista === 'rubro' ? ' on' : '') + '" data-vista="rubro">Por rubro</button>' +
        '<button class="pastilla' + (vista === 'vendedor' ? ' on' : '') + '" data-vista="vendedor">Por vendedor</button>';
    }

    var caja = document.getElementById('cadenas');
    if (caja) {
      caja.hidden = vista !== 'rubro';
      var ids = Object.keys(O.cadenas).filter(function (id) {
        return O.rubros.some(function (r) {
          return r.ofertas.some(function (o) { return o.cadena === id; });
        });
      });
      caja.innerHTML = ['todas'].concat(ids).map(function (id) {
        // Nombre corto en el chip, completo en el title: "Supermercados
        // Nacional" empujaba la fila fuera de la pantalla.
        var c = O.cadenas[id] || {};
        var n = id === 'todas' ? 'Todas' : (c.corto || c.nombre || id);
        var largo = id === 'todas' ? 'Todas las tiendas' : (c.nombre || id);
        return '<button class="pastilla chica' + (id === cadenaActiva ? ' on' : '') +
               '" data-cadena="' + esc(id) + '" title="' + esc(largo) + '">' +
               esc(n) + '</button>';
      }).join('');
    }
  }

  /* ---------- eventos ---------- */

  document.addEventListener('click', function (e) {
    var pas = e.target.closest('[data-cat]');
    if (pas) { catActiva = pas.dataset.cat; pintarPastillas(); render(); return; }

    var vis = e.target.closest('[data-vista]');
    if (vis) { vista = vis.dataset.vista; pintarControles(); render(); return; }

    var cad = e.target.closest('[data-cadena]');
    if (cad) { cadenaActiva = cad.dataset.cadena; pintarControles(); render(); return; }

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
  pintarControles();
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

/* ============================================================
   Vitrina: sin cuenta se ve el mercado, pero no se puede actuar.
   Ver es gratis; contactar y publicar piden sesión.
   Lo que de verdad protege el teléfono del vendedor es RLS en Postgres,
   no esto — esto solo decide qué se dibuja.
   ============================================================ */
(function () {
  'use strict';
  if (!document.body.classList.contains('pag-privada')) return;

  // La vitrina aplica SIEMPRE, muestre anuncios de productor u ofertas de
  // supermercado. No es solo por proteger el contacto del vendedor: sin
  // cuenta no hay forma de saber quién está usando la plataforma, y eso es
  // lo único que dice si esto le sirve a alguien antes de que haya
  // productores publicando.
  var VISIBLES = 6;   // cuántas tarjetas se ven completas sin cuenta

  function hayToken() {
    try {
      for (var i = 0; i < localStorage.length; i++) {
        var k = localStorage.key(i);
        if (k === 'kcuesta-auth' || k.indexOf('-auth-token') > -1) return true;
      }
    } catch (e) {}
    return false;
  }

  function bloquear() {
    document.body.classList.add('sin-cuenta');

    // Las acciones de cada anuncio llevan a la entrada.
    document.querySelectorAll('.tarjeta .acciones').forEach(function (acc) {
      // Un solo botón: ocupa el ancho completo, si no el texto se parte en dos.
      acc.className = 'acciones acciones-una';
      acc.innerHTML = '<a class="boton" href="entrar.html">Entrar para contactar</a>';
    });

    // En las tarjetas de rubro no hay bloque de acciones: lo que saca de la
    // página es el enlace "Ver →" de cada cadena. Sin cuenta lleva a entrar.
    document.querySelectorAll('.rubro .rb-ir').forEach(function (a) {
      a.setAttribute('href', 'entrar.html');
      a.removeAttribute('target');
      a.textContent = 'Entrar para ver →';
    });

    // A partir de la sexta tarjeta: se difumina y aparece la invitación.
    // Sirve para los dos tipos, anuncio de productor y rubro.
    var tarjetas = document.querySelectorAll('#rejilla .tarjeta, #rejilla .rubro');
    if (tarjetas.length > VISIBLES) {
      for (var i = VISIBLES; i < tarjetas.length; i++) {
        tarjetas[i].classList.add('velada');
      }
      var corte = document.getElementById('corte-vitrina');
      if (!corte) {
        var soloOfertas = !document.querySelector('#rejilla .tarjeta:not(.tarjeta-oferta)');
        corte = document.createElement('div');
        corte.id = 'corte-vitrina';
        corte.className = 'corte-vitrina';
        corte.innerHTML =
          '<div class="corte-caja">' +
            (soloOfertas
              ? '<h3>Hay ' + tarjetas.length + ' precios de supermercado hoy</h3>' +
                '<p class="silencio">Entra gratis para verlos todos, comparar cadenas ' +
                'y recibir aviso cuando un productor publique tu rubro.</p>'
              : '<h3>Hay ' + tarjetas.length + ' anuncios hoy</h3>' +
                '<p class="silencio">Entra gratis para verlos todos, ver el teléfono del ' +
                'productor y escribirle.</p>') +
            '<a class="boton grande" href="entrar.html">Comenzar</a>' +
          '</div>';
        document.getElementById('rejilla').after(corte);
      }
    }
  }

  function desbloquear() {
    document.body.classList.remove('sin-cuenta');
    var c = document.getElementById('corte-vitrina');
    if (c) c.remove();
    document.querySelectorAll('.tarjeta.velada, .rubro.velada').forEach(function (t) {
      t.classList.remove('velada');
    });
  }

  function aplicar() {
    if (document.body.dataset.sesion === 'si') desbloquear(); else bloquear();
  }

  document.addEventListener('kc:sesion', function () {
    document.body.dataset.sesion = 'si';
    aplicar();
  });

  // Estado inicial: sin rastro de sesión, se bloquea de una vez.
  if (!hayToken() && !/[?&#](code|access_token)=/.test(location.href)) {
    aplicar();
  } else {
    setTimeout(function () { if (document.body.dataset.sesion !== 'si') aplicar(); }, 3000);
  }

  // Si el filtro vuelve a dibujar la rejilla, se reaplica.
  var obs = new MutationObserver(function () {
    if (document.body.dataset.sesion !== 'si') bloquear();
  });
  var rej = document.getElementById('rejilla');
  if (rej) obs.observe(rej, { childList: true });
})();
