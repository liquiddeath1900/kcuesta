/* ============================================================
   Perfil de gremio — el parte del día

   Resuelve el problema de "muchos artículos, un solo usuario". La
   asociación publica catorce rubros cada mañana y eso NO son catorce
   anuncios sueltos con su nombre repetido catorce veces: es UNA cosa, el
   parte del día. Misma lógica que ya se aplicó al mercado cuando dejó de
   repetir "Ají" trece veces seguidas.

   La unidad de la tarjeta es el RUBRO, y adentro va la escalera de calidad.
   Así "Chinola 1ª 12–14 · 2ª 8–10 · 3ª 5–7" se lee como lo que es —un
   producto con tres grados— y no como tres productos.
   ============================================================ */
(function () {
  'use strict';

  // Tres archivos, a propósito:
  //   partes.json          — qué partes hay. Se carga el más reciente.
  //   partes/<fecha>.json  — SOLO lo del día: precio y foto.
  //   gremio-rubros.json   — lo que no cambia: nombre, unidad, libras y la
  //                          foto de respaldo.
  // Los rubros se repiten todas las mañanas y lo único que se mueve es el
  // precio y la foto. Publicar el parte de mañana es escribir un archivo de
  // precios; no hay que volver a tocar nombres, unidades ni fotos, y los
  // partes viejos quedan intactos porque nadie los reescribe.
  var V = '?v=10';
  var INDICE = 'data/partes.json' + V;
  var CATALOGO = 'data/gremio-rubros.json' + V;

  function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }
  function rd(n, d) {
    if (n == null) return '—';
    return 'RD$ ' + Number(n).toLocaleString('es-DO', {
      minimumFractionDigits: d == null ? 2 : d, maximumFractionDigits: d == null ? 2 : d });
  }
  // Un rango donde los dos extremos son iguales no es un rango: es un
  // número. Enseñar "12 – 12" hace dudar del dato.
  function rango(a, b, d) {
    return a === b ? rd(a, d) : rd(a, d) + ' – ' + rd(b, d);
  }
  function fechaLarga(iso) {
    var M = ['enero','febrero','marzo','abril','mayo','junio','julio',
             'agosto','septiembre','octubre','noviembre','diciembre'];
    var p = String(iso).split('-');
    return Number(p[2]) + ' de ' + M[Number(p[1]) - 1] + ' ' + p[0];
  }

  var ORDEN_CAL = { premium: 0, primera: 1, segunda: 2, regular: 2, tercera: 3 };
  var ETIQ_CAL = { premium: 'Prímium', primera: 'Primera', segunda: 'Segunda',
                   tercera: 'Tercera', regular: 'Regular' };

  function traer(u) { return fetch(u).then(function (r) { return r.json(); }); }

  Promise.all([traer(INDICE), traer(CATALOGO)]).then(function (res) {
    var publicados = (res[0].partes || []).filter(function (p) {
      return p.estado === 'publicado';
    });
    if (!publicados.length) throw new Error('sin partes publicados');
    // El índice viene con el más reciente de primero, pero se ordena igual:
    // un archivo mal puesto no debería hacer que la página enseñe ayer.
    publicados.sort(function (a, b) { return a.fecha < b.fecha ? 1 : -1; });
    return traer(publicados[0].archivo + V).then(function (parte) {
      return [parte, res[1].rubros || {}];
    });
  }).then(function (par) {
    var d = par[0], CAT = par[1];
    var m = d._meta;

    // El parte trae precio y foto; el catálogo pone lo que no cambia. La
    // foto del día MANDA sobre la del catálogo: el gremio retrata la
    // mercancía que entró esa mañana, y esa dice más que una de archivo.
    var items = (d.items || []).map(function (i) {
      var c = CAT[i.cultivo] || {};
      // La unidad del RENGLÓN manda sobre la del catálogo. Un mismo rubro
      // se cotiza en dos unidades a la vez: la lechoza va por quintal en
      // bulto y por unidad la fruta suelta. Con una sola unidad por rubro,
      // los 60–80 por fruta se dividían entre 100 libras y la tarjeta
      // enseñaba lechoza de primera a 60 centavos la libra.
      var unidad = i.unidad !== undefined ? i.unidad : c.unidad;
      var libras = i.libras_unidad !== undefined ? i.libras_unidad : c.libras_unidad;
      return {
        cultivo: i.cultivo,
        nombre: c.nombre || i.cultivo,
        calidad: i.calidad,
        procedencia: i.procedencia,
        unidad: unidad,
        libras_unidad: libras,
        unidad_confianza: c.unidad_confianza,
        nota: i.nota || c.nota_unidad,
        precio_min: i.precio_min,
        precio_max: i.precio_max,
        // Se normaliza AQUÍ y no en el archivo: el precio por libra es una
        // cuenta —precio entre libras del empaque— y guardarla en el JSON
        // la deja envejecer mal el día que se corrija una unidad.
        precio_lb_min: libras ? +(i.precio_min / libras).toFixed(2) : null,
        precio_lb_max: libras ? +(i.precio_max / libras).toFixed(2) : null,
        foto: i.foto || c.foto || null,
        foto_credito: i.foto ? (i.foto_credito || 'foto del día')
                             : (c.foto ? c.foto_credito : null)
      };
    });

    /* ---------- cabecera ---------- */
    var rubros = {};
    items.forEach(function (i) { rubros[i.cultivo] = 1; });
    var nRubros = Object.keys(rubros).length;

    document.getElementById('cab').innerHTML =
      '<div class="gr-id">' +
        '<div class="gr-avatar" aria-hidden="true">🤝</div>' +
        '<div class="gr-txt">' +
          '<h1 class="gr-nom">' + esc(m.fuente) + '</h1>' +
          // El rótulo que evita la mentira. No vende: reporta.
          '<div class="gr-tipo"><span class="etiq-reporta">Reporta la plaza</span>' +
            '<span class="silencio"> · no vende</span></div>' +
          '<div class="gr-meta silencio">' +
            esc(m.plaza) + ' · ' + esc(m.provincia) +
          '</div>' +
        '</div>' +
      '</div>' +
      '<div class="gr-cifras">' +
        // Sale del dato y se rotula por lo que de verdad se sabe: son 203
        // en el canal de WhatsApp. Cuántos socios tiene la asociación es
        // otra cifra y nadie la ha confirmado.
        '<div class="gr-cifra"><b>' + (m.miembros_canal || 203) + '</b>' +
          '<span>en el canal</span></div>' +
        '<div class="gr-cifra"><b>' + nRubros + '</b><span>rubros hoy</span></div>' +
        '<div class="gr-cifra"><b>Mayorista</b><span>nivel</span></div>' +
      '</div>' +
      '<div class="gr-fecha">Parte del <b>' + esc(fechaLarga(m.fecha)) + '</b></div>';

    /* ---------- agrupar por rubro ----------
       Un renglón por grado se junta bajo su rubro. El orden de los grados
       es prímium → primera → segunda → tercera, que es como los canta el
       mercado, y NO por precio: ordenar por precio pondría la tercera de
       primera cuando está barata y rompería la escalera. */
    var porRubro = {};
    items.forEach(function (i) {
      (porRubro[i.cultivo] = porRubro[i.cultivo] || { nombre: i.nombre, filas: [] })
        .filas.push(i);
    });

    var lista = Object.keys(porRubro).map(function (k) {
      var r = porRubro[k];
      r.cultivo = k;
      // La foto la puso el gremio: es el producto real, en el saco real, el
      // día que se cotizó ese precio. Vale más que una foto de góndola —
      // ahí se ve la calidad de la que están hablando. Cuando el renglón
      // vino en texto (la lista reenviada) se cae a la foto de góndola que
      // ya está en el repo, y se dice, porque atribuirle al gremio una foto
      // de supermercado sería falso.
      var conFoto = r.filas.filter(function (f) { return f.foto; })[0];
      r.foto = conFoto ? conFoto.foto : null;
      r.foto_credito = conFoto ? conFoto.foto_credito : null;
      r.filas.sort(function (a, b) {
        return (ORDEN_CAL[a.calidad] == null ? 9 : ORDEN_CAL[a.calidad]) -
               (ORDEN_CAL[b.calidad] == null ? 9 : ORDEN_CAL[b.calidad]);
      });
      // Comparable = el gremio declaró (o se pudo deducir) la unidad.
      r.comparable = r.filas.some(function (f) { return f.precio_lb_min != null; });
      return r;
    });
    // Primero lo que se puede comparar por libra. Lo que no, al final, con
    // el hueco a la vista.
    lista.sort(function (a, b) {
      return (b.comparable - a.comparable) || a.nombre.localeCompare(b.nombre, 'es');
    });

    /* ---------- la góndola, para el contraste ----------
       Es el argumento entero del sitio: cuánto se le suma al producto entre
       el mostrador del mayorista y el carrito.

       Solo se compara contra el grado ALTO. Un tomate "regular" de a RD$5.55
       la libra contra la góndola daría +746%, pero el supermercado no vende
       tomate regular: vende primera. Comparar grados distintos infla el
       número y lo vuelve indefendible el día que alguien lo revise. */
    var GONDOLA = {};
    try {
      (window.KC.ofertas.rubros || []).forEach(function (r) {
        if (r.valor_lb) GONDOLA[r.cultivo] = r.valor_lb;
      });
    } catch (e) {}

    function contraste(r) {
      var g = GONDOLA[r.cultivo];
      if (!g) return '';
      // Se prefiere el grado alto declarado. Si el rubro no trae grado
      // —el apio, la zanahoria, la remolacha y la papa vienen sin él— se
      // usa igual, pero SE DICE: el supermercado vende primera, así que un
      // "+500%" contra mercancía de grado desconocido no se puede leer
      // como primera contra primera. El comentario de arriba prometía que
      // los grados no se mezclan y en estas cuatro sí se estaban mezclando.
      var conGrado = r.filas.filter(function (f) {
        return f.precio_lb_min != null &&
               (f.calidad === 'primera' || f.calidad === 'premium');
      })[0];
      var sinGrado = r.filas.filter(function (f) {
        return f.precio_lb_min != null && f.calidad == null;
      })[0];
      var alto = conGrado || sinGrado;
      if (!alto) return '';
      var may = (alto.precio_lb_min + alto.precio_lb_max) / 2;
      var pct = Math.round((g - may) / may * 100);
      if (pct <= 0) return '';
      return '<div class="gr-contraste">' +
        'En góndola: <b>' + rd(g, 2) + '/lb</b> ' +
        // "sobre el mayorista" a secas se confundía con la referencia del
        // Ministerio que enseña el mercado. Aquí el mayorista es ESTE
        // gremio, y conviene decirlo.
        '<span class="marca sube">+' + pct + '% sobre la plaza</span>' +
        (conGrado ? '' : '<span class="gr-aviso-grado silencio">' +
          'el gremio no declaró grado; el supermercado vende primera</span>') +
        '</div>';
    }

    /* ---------- pintar ---------- */
    function fila(f) {
      var etiq = f.calidad ? ETIQ_CAL[f.calidad] || f.calidad : 'Precio del día';
      var porLb = f.precio_lb_min != null;
      return '<li class="gr-fila">' +
        '<div class="gr-grado">' +
          '<b class="cal cal-' + esc(f.calidad || 'unica') + '">' + esc(etiq) + '</b>' +
          (f.procedencia ? '<span class="silencio gr-proc">' + esc(f.procedencia) + '</span>' : '') +
        '</div>' +
        '<div class="gr-precio">' +
          '<span class="cifra">' + rango(f.precio_min, f.precio_max, 0) + '</span>' +
          '<span class="gr-u">' + (f.unidad ? ' / ' + esc(f.unidad) : '') + '</span>' +
          // Dos huecos distintos, y decían lo mismo. La chinola SÍ trae
          // unidad —se vende por unidad— lo que no tiene es peso, así que
          // no hay libra a la cual convertir. Rotularla "sin unidad
          // declarada" era falso y hacía dudar de un dato que está bien.
          (porLb
            ? '<span class="gr-lb">' + rango(f.precio_lb_min, f.precio_lb_max, 2) + '/lb</span>'
            : f.unidad
              ? '<span class="gr-lb silencio">no se vende por peso</span>'
              : '<span class="gr-lb silencio">sin unidad declarada</span>') +
        '</div>' +
      '</li>';
    }

    // Las notas se enseñan. Cuando la unidad se dedujo en vez de venir
    // declarada, quien lee tiene derecho a saberlo — es la diferencia entre
    // un dato y una cuenta nuestra.
    function notas(r) {
      var ns = r.filas.filter(function (f) { return f.nota; })
                      .map(function (f) { return f.nota; });
      var u = {}; ns = ns.filter(function (n) { return u[n] ? false : (u[n] = 1); });
      if (!ns.length) return '';
      return '<div class="gr-notas silencio">' +
        ns.map(function (n) { return '<div>' + esc(n) + '</div>'; }).join('') +
      '</div>';
    }

    document.getElementById('rejilla').innerHTML = lista.map(function (r) {
      var dudosa = r.filas.some(function (f) { return f.unidad_confianza === 'a confirmar'; });
      return '<article class="rubro gremio-rubro' + (r.comparable ? '' : ' sin-unidad') + '"' +
             ' data-cal="' + esc(r.filas.map(function (f) { return f.calidad || ''; }).join(' ')) + '">' +
        // La foto es su propia COLUMNA y va a todo lo alto de la tarjeta.
        // Puesta como miniatura al lado del nombre se quedaba en 60px, y
        // agrandarla ahí empujaba la tarjeta hacia abajo. Como columna
        // crece con las filas de grado sin costar un pixel de alto: la
        // tarjeta de la chinola, que trae tres grados, le da a la foto
        // ~150px sin ocupar más pantalla que antes.
        (r.foto
          ? '<div class="gr-foto"><img src="' + esc(r.foto) + '?v=10" alt="' + esc(r.nombre) +
              '" loading="lazy" width="280" height="373">' +
              (r.foto_credito === 'foto de la asociación'
                ? '<span class="gr-foto-sello" title="Foto de la Asociación Mercaderes Unidos, tomada en el Mercado Nuevo">🤝</span>'
                : '') +
            '</div>'
          : '<div class="gr-foto sin-foto"><span>' + esc(r.nombre.charAt(0)) + '</span></div>') +
        '<div class="gr-cuerpo">' +
          '<div class="gr-cab">' +
            '<div class="gr-rubro-nom">' + esc(r.nombre) + '</div>' +
            (dudosa ? '<span class="gr-flag" title="Falta confirmar la unidad">unidad por confirmar</span>' : '') +
          '</div>' +
          '<ul class="gr-lista">' + r.filas.map(fila).join('') + '</ul>' +
          contraste(r) +
          notas(r) +
        '</div>' +
      '</article>';
    }).join('');

    /* ---------- pie y crédito ---------- */
    var conUnidad = items.filter(function (i) { return i.precio_lb_min != null; }).length;
    document.getElementById('pie-parte').innerHTML =
      '<p class="silencio">' +
        items.length + ' renglones · ' + nRubros + ' rubros · ' +
        conUnidad + ' comparables por libra. ' +
        'Los que no traen unidad declarada se muestran tal cual se publicaron y ' +
        '<b>no se comparan</b>: un hueco se ve, un supuesto no.' +
      '</p>';

    // El crédito no es cortesía, es el trato. Lo que hace que publicar esto
    // le sirva a la asociación es que su nombre vaya en cada pantalla donde
    // salgan sus números.
    document.getElementById('credito-pie').innerHTML =
      'Precios al por mayor publicados por la <b>' + esc(m.fuente) + '</b> ' +
      '(' + esc(m.canal) + '), reproducidos en Kcuesta con su permiso.';
  }).catch(function (e) {
    document.getElementById('rejilla').innerHTML =
      '<div class="vacio"><h3>No se pudo cargar el parte</h3></div>';
  });

})();
