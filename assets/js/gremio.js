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
  var V = '?v=12';
  var INDICE = 'data/partes.json' + V;
  var CATALOGO = 'data/gremio-rubros.json' + V;

  function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }
  function num(n, d) {
    return Number(n).toLocaleString('es-DO', {
      minimumFractionDigits: d == null ? 2 : d, maximumFractionDigits: d == null ? 2 : d });
  }
  function rd(n, d) {
    if (n == null) return '—';
    return 'RD$ ' + num(n, d);
  }
  // Un rango donde los dos extremos son iguales no es un rango: es un
  // número. Enseñar "12 – 12" hace dudar del dato.
  // El "RD$" va UNA vez. "RD$ 5,000 – RD$ 6,000" pide 40px más de los que
  // hay en un teléfono de 320px y el rango se salía de la tarjeta; repetir
  // la moneda dentro del mismo rango tampoco aclara nada.
  function rango(a, b, d) {
    return a === b ? rd(a, d) : rd(a, d) + ' – ' + num(b, d);
  }
  function fechaLarga(iso) {
    var M = ['enero','febrero','marzo','abril','mayo','junio','julio',
             'agosto','septiembre','octubre','noviembre','diciembre'];
    var p = String(iso).split('-');
    return Number(p[2]) + ' de ' + M[Number(p[1]) - 1] + ' ' + p[0];
  }

  var ORDEN_CAL = { premium: 0, primera: 1, segunda: 2, regular: 2, tercera: 3,
                    inferior: 4 };
  // Los grados se rotulan con la palabra del gremio. 'Inferiores y viejos' no
  // es 'tercera': el gremio distingue mercancía de grado bajo de mercancía
  // pasada, y traducirlo a la escalera limpia le quitaría la advertencia.
  var ETIQ_CAL = { premium: 'Prímium', primera: 'Primera', segunda: 'Segunda',
                   tercera: 'Tercera', regular: 'Regular',
                   inferior: 'Inferiores y viejos' };

  // Identidad de un renglón para poder buscarlo en el parte anterior. Entra
  // la UNIDAD a propósito: el morrón de ayer iba 'la caja' a 300–500 y el de
  // hoy va sin unidad a 20–25. Comparar eso daría un −94% inventado. Si la
  // unidad cambió, no es el mismo renglón y no se compara.
  function llave(f) {
    return [f.cultivo, f.calidad || '', f.unidad || '', f.detalle || ''].join('|');
  }

  function traer(u) { return fetch(u).then(function (r) { return r.json(); }); }

  Promise.all([traer(INDICE), traer(CATALOGO)]).then(function (res) {
    var publicados = (res[0].partes || []).filter(function (p) {
      return p.estado === 'publicado';
    });
    if (!publicados.length) throw new Error('sin partes publicados');
    // El índice viene con el más reciente de primero, pero se ordena igual:
    // un archivo mal puesto no debería hacer que la página enseñe ayer.
    publicados.sort(function (a, b) { return a.fecha < b.fecha ? 1 : -1; });
    // Se carga TAMBIÉN el parte anterior. Es lo único que convierte un
    // número en una noticia: 1,100 la berenjena no dice nada; 1,100 cuando
    // ayer estaba en 1,400 dice que entró mercancía. El gremio mismo lo
    // explica en la nota de plaza.
    var previo = publicados[1]
      ? traer(publicados[1].archivo + V).catch(function () { return null; })
      : Promise.resolve(null);
    return Promise.all([traer(publicados[0].archivo + V), previo])
      .then(function (ps) {
        return [ps[0], res[1].rubros || {}, ps[1], publicados[1] || null];
      });
  }).then(function (par) {
    var d = par[0], CAT = par[1], ANT = par[2], ANT_INFO = par[3];
    var m = d._meta;

    /* ---------- el parte de ayer, indexado por renglón ---------- */
    var PREV = {}, PREV_CULTIVO = {};
    if (ANT && ANT.items) {
      ANT.items.forEach(function (i) {
        var c = CAT[i.cultivo] || {};
        var u = i.unidad !== undefined ? i.unidad : c.unidad;
        var k = llave({ cultivo: i.cultivo, calidad: i.calidad, unidad: u,
                        detalle: i.detalle });
        PREV[k] = i;
        PREV_CULTIVO[i.cultivo] = 1;
      });
    }
    var PREV_FECHA = ANT && ANT._meta ? ANT._meta.fecha : (ANT_INFO && ANT_INFO.fecha);

    // "desde ayer" solo si de verdad fue ayer. Si el gremio no publicó el
    // lunes, el cambio es contra el viernes y hay que decirlo.
    function desdeCuando() {
      if (!PREV_FECHA) return '';
      var a = new Date(m.fecha + 'T00:00:00');
      var b = new Date(PREV_FECHA + 'T00:00:00');
      var dias = Math.round((a - b) / 86400000);
      return dias === 1 ? 'desde ayer' : 'desde el ' + fechaLarga(PREV_FECHA);
    }
    var DESDE = desdeCuando();

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
        detalle: i.detalle || null,
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

    /* ---------- frescura ----------
       Se compara la fecha del parte contra el día de quien lee. Si el gremio
       no publica un día, la página no puede seguir diciendo "el parte" como
       si fuera de hoy: enseña cuántos días tiene y quien lee decide. */
    function frescura(iso) {
      var hoy = new Date(); hoy.setHours(0, 0, 0, 0);
      var f = new Date(iso + 'T00:00:00');
      var dias = Math.round((hoy - f) / 86400000);
      if (dias < 0) return '';
      if (dias === 0) return '<span class="sello-fresco hoy">Hoy</span>';
      if (dias === 1) return '<span class="sello-fresco ayer">Ayer</span>';
      return '<span class="sello-fresco viejo">Hace ' + dias + ' días</span>';
    }

    /* ---------- lo que hoy no se cotizó ----------
       El gremio no publica los mismos rubros todos los días: hoy mandó solo
       la lista de vegetales y no la tanda de chinola, plátano y cebolla.
       Borrarlos de la página deja al que entra sin saber a cómo está el
       plátano; enseñarlos como si fueran de hoy sería mentir.

       Se quedan, con la FECHA DEL DÍA QUE SE COTIZARON pegada al renglón.
       El precio nunca se despega de su fecha: eso es lo que lo hace un dato
       y no un número suelto. Van al final y con el sello a la vista. */
    var hoyCultivos = {};
    items.forEach(function (i) { hoyCultivos[i.cultivo] = 1; });
    var nRubros = Object.keys(hoyCultivos).length;

    // Se arrastra por RENGLÓN, no por rubro. Arrastrar por rubro borraba
    // grados enteros sin decirlo: hoy el gremio cotizó berenjena prímium y
    // regular pero no la tercera, y la tercera de ayer (500–700) desaparecía
    // de la página como si no existiera. Igual el morrón regular "la caja"
    // 300–500, tapado por el renglón de hoy "inferiores y viejos". El grado
    // que hoy no se cotizó se queda, con su fecha, como cualquier otro.
    var hoyLlaves = {};
    items.forEach(function (i) { hoyLlaves[llave(i)] = 1; });

    if (ANT && ANT.items) {
      ANT.items.forEach(function (i) {
        var c0 = CAT[i.cultivo] || {};
        var u0 = i.unidad !== undefined ? i.unidad : c0.unidad;
        if (hoyLlaves[llave({ cultivo: i.cultivo, calidad: i.calidad,
                              unidad: u0, detalle: i.detalle })]) return;
        var c = CAT[i.cultivo] || {};
        var unidad = i.unidad !== undefined ? i.unidad : c.unidad;
        var libras = i.libras_unidad !== undefined ? i.libras_unidad : c.libras_unidad;
        items.push({
          cultivo: i.cultivo,
          nombre: c.nombre || i.cultivo,
          calidad: i.calidad,
          detalle: i.detalle || null,
          procedencia: i.procedencia,
          unidad: unidad,
          libras_unidad: libras,
          unidad_confianza: c.unidad_confianza,
          nota: i.nota || c.nota_unidad,
          precio_min: i.precio_min,
          precio_max: i.precio_max,
          precio_lb_min: libras ? +(i.precio_min / libras).toFixed(2) : null,
          precio_lb_max: libras ? +(i.precio_max / libras).toFixed(2) : null,
          foto: i.foto || c.foto || null,
          foto_credito: i.foto ? (i.foto_credito || 'foto del día')
                               : (c.foto ? c.foto_credito : null),
          arrastrado: true,
          fecha_origen: PREV_FECHA
        });
      });
    }

    /* ---------- cabecera ---------- */

    document.getElementById('cab').innerHTML =
      '<div class="gr-id">' +
        '<div class="gr-avatar" aria-hidden="true">🤝</div>' +
        '<div class="gr-txt">' +
          '<p class="gr-nom">' + esc(m.fuente) + '</p>' +
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
        '<div class="gr-cifra"><b>' + esc(m.miembros_canal || 203) + '</b>' +
          '<span>en el canal</span></div>' +
        '<div class="gr-cifra"><b>' + nRubros + '</b><span>rubros hoy</span></div>' +
        '<div class="gr-cifra"><b>Mayorista</b><span>nivel</span></div>' +
      '</div>' +
      // Cuándo se actualizó, a la vista. Un precio de plaza envejece en horas
      // y el visitante tiene que poder saber si está mirando lo de hoy o lo
      // del viernes SIN hacer la cuenta. La frescura se calcula contra el
      // reloj de quien lee, no se escribe a mano en el archivo.
      '<div class="gr-fecha">Parte del <b>' + esc(fechaLarga(m.fecha)) + '</b>' +
        frescura(m.fecha) +
        '<div class="gr-actualizado silencio">Actualizado el ' +
          esc(fechaLarga(m.actualizado || m.fecha)) +
          (m.momento ? ' ' + esc(m.momento) : '') +
          ', con lo que publicó el gremio ese día.' +
        '</div>' +
      '</div>';

    /* ---------- la nota de plaza ----------
       El gremio escribe una línea diaria diciendo de qué entró mucho. Es la
       CAUSA del precio, no un adorno: el día que dijo "plaza full berenjenas"
       la berenjena cayó 25%. Ninguna otra fuente que tenemos trae esto, así
       que va arriba, con su fecha, y textual. */
    if (m.nota_plaza) {
      var cab = document.getElementById('cab');
      var np = document.createElement('div');
      np.className = 'gr-plaza';
      np.innerHTML = '<b>Nota de plaza</b> · ' + esc(fechaLarga(m.fecha)) +
        '<div class="gr-plaza-txt">' + esc(m.nota_plaza) + '</div>' +
        '<div class="silencio">A mayor oferta, el precio baja: es lo que ' +
        'explica el gremio y lo que se ve en las flechas de abajo.</div>';
      cab.appendChild(np);
    }

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
      // El renglón sin grado va PRIMERO (-1), no último. El gremio publicó
      // "Pepino 1400/1300" y debajo "Pepino regular 1100/1000": el que no
      // trae grado es el de arriba de la escalera, y mandarlo al final
      // dejaba el regular más barato en el primer renglón, que se lee como
      // un error de datos. Mismo caso de la lechoza por quintal.
      r.filas.sort(function (a, b) {
        // Lo de hoy arriba, lo arrastrado abajo, y dentro de cada bloque la
        // escalera de calidad.
        return ((a.arrastrado ? 1 : 0) - (b.arrastrado ? 1 : 0)) ||
               ((ORDEN_CAL[a.calidad] == null ? -1 : ORDEN_CAL[a.calidad]) -
                (ORDEN_CAL[b.calidad] == null ? -1 : ORDEN_CAL[b.calidad]));
      });
      // Comparable = el gremio declaró (o se pudo deducir) la unidad.
      r.comparable = r.filas.some(function (f) { return f.precio_lb_min != null; });
      r.arrastrado = r.filas.every(function (f) { return f.arrastrado; });
      // Rubro entero nuevo: UN sello arriba, no uno por grado. El ají
      // cubanela trae cuatro renglones y cuatro "Nuevo en este parte"
      // seguidos se leen como un error de la página, no como una novedad.
      r.nuevo = !r.arrastrado && ANT &&
                r.filas.every(function (f) { return !PREV_CULTIVO[f.cultivo]; });
      if (r.nuevo) r.filas.forEach(function (f) { f.rubroNuevo = true; });
      // Tarjeta mixta —parte de hoy y parte de ayer en el mismo rubro—: el
      // sello de fecha no puede ir arriba porque no aplica a toda la
      // tarjeta. Va pegado al renglón viejo.
      if (!r.arrastrado) {
        r.filas.forEach(function (f) { if (f.arrastrado) f.selloFila = true; });
      }
      r.fecha_origen = r.arrastrado ? r.filas[0].fecha_origen : null;
      return r;
    });
    // Primero lo que se puede comparar por libra. Lo que no, al final, con
    // el hueco a la vista.
    // Primero lo de HOY, después lo arrastrado. Dentro de cada bloque,
    // primero lo comparable por libra.
    lista.sort(function (a, b) {
      return (a.arrastrado - b.arrastrado) ||
             (b.comparable - a.comparable) ||
             a.nombre.localeCompare(b.nombre, 'es');
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

    /* ---------- subió o bajó ----------
       Contra el MISMO renglón del parte anterior: mismo rubro, mismo grado,
       misma unidad. Se compara el punto medio del rango porque los dos
       extremos se mueven por separado —el bugalú regular subió el piso 50%
       y el techo 17%— y una sola flecha tiene que representar el renglón
       entero.

       No se compara: renglón nuevo, renglón que ayer venía con otra unidad,
       o rubro que ayer no se cotizó. En esos tres casos el hueco se dice. */
    function medio(f) { return (f.precio_min + f.precio_max) / 2; }

    function cambio(f) {
      // Un renglón arrastrado no cambió de precio: es el MISMO renglón de
      // otro día. Ponerle "igual" diría que hoy se cotizó igual, y hoy no
      // se cotizó. Lleva su sello de fecha en vez de flecha.
      if (f.arrastrado) {
        return f.selloFila
          ? '<span class="gr-cambio viejo" title="El gremio no cotizó este ' +
            'grado hoy">Precio del ' + esc(fechaLarga(f.fecha_origen)) + '</span>'
          : '';
      }
      if (!ANT) return '';
      var ant = PREV[llave(f)];
      if (!ant) {
        // Distinguir "producto nuevo en la lista" de "hoy vino distinto".
        // Son dos cosas y la segunda es una advertencia, no una novedad.
        if (!PREV_CULTIVO[f.cultivo]) {
          if (f.rubroNuevo) return '';   // ya lo dice el sello del rubro
          // "Nuevo" a secas. Decía "Nuevo ayer", que se leía como que el
          // renglón entró ayer cuando lo que pasa es lo contrario: entró
          // hoy y ayer no estaba.
          return '<span class="gr-cambio nuevo" title="No estaba en el parte ' +
                 'anterior">Nuevo en este parte</span>';
        }
        return '<span class="gr-cambio sin-base" title="Ayer este rubro se cotizó con otro grado o con otra unidad">sin comparación</span>';
      }
      var hoy = medio(f), ayer = medio(ant);
      if (!ayer) return '';
      var pct = Math.round((hoy - ayer) / ayer * 100);
      var t = 'Ayer: ' + rango(ant.precio_min, ant.precio_max, 0) +
              (ant.unidad ? ' / ' + ant.unidad : '');
      var arriba = hoy > ayer;
      if (hoy === ayer) {
        return '<span class="gr-cambio igual" title="' + esc(t) + '">Igual ' +
               esc(DESDE) + '</span>';
      }
      // Se movió, pero redondea a 0%. Decir "Igual" sería afirmar que no se
      // movió. Se dice que se movió poco.
      if (pct === 0) {
        return '<span class="gr-cambio ' + (arriba ? 'sube' : 'baja') +
               '" title="' + esc(t) + '">' + (arriba ? '▲' : '▼') +
               ' menos de 1% ' + esc(DESDE) + '</span>';
      }
      return '<span class="gr-cambio ' + (arriba ? 'sube' : 'baja') +
             '" title="' + esc(t) + '">' +
             (arriba ? '▲ +' : '▼ ') + pct + '% ' + esc(DESDE) + '</span>';
    }

    /* ---------- pintar ---------- */
    function fila(f) {
      var etiq = f.calidad ? ETIQ_CAL[f.calidad] || f.calidad : 'Precio del día';
      var porLb = f.precio_lb_min != null;
      return '<li class="gr-fila">' +
        '<div class="gr-grado">' +
          '<b class="cal cal-' + esc(f.calidad || 'unica') + '">' + esc(etiq) + '</b>' +
          (f.detalle ? '<span class="silencio gr-proc">' + esc(f.detalle) + '</span>' : '') +
          (f.procedencia ? '<span class="silencio gr-proc">' + esc(f.procedencia) + '</span>' : '') +
          cambio(f) +
        '</div>' +
        '<div class="gr-precio">' +
          '<span class="cifra">' + rango(f.precio_min, f.precio_max, 0) + '</span>' +
          // El espacio va FUERA del span. Adentro, junto a la unidad que es
          // `nowrap`, no había dónde partir la línea y "/ Saco/22 lb" se
          // salía de la tarjeta en vez de bajar al renglón de abajo.
          (f.unidad ? ' <span class="gr-u">/ ' + esc(f.unidad) + '</span>' : '') +
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
      return '<article class="rubro gremio-rubro' + (r.comparable ? '' : ' sin-unidad') +
             (r.arrastrado ? ' arrastrado' : '') + '"' +
             ' data-cal="' + esc(r.filas.map(function (f) { return f.calidad || ''; }).join(' ')) + '">' +
        // La foto es su propia COLUMNA y va a todo lo alto de la tarjeta.
        // Puesta como miniatura al lado del nombre se quedaba en 60px, y
        // agrandarla ahí empujaba la tarjeta hacia abajo. Como columna
        // crece con las filas de grado sin costar un pixel de alto: la
        // tarjeta de la chinola, que trae tres grados, le da a la foto
        // ~150px sin ocupar más pantalla que antes.
        (r.foto
          ? '<div class="gr-foto"><img src="' + esc(r.foto) + '?v=12" alt="' + esc(r.nombre) +
              '" loading="lazy" width="280" height="373">' +
              (r.foto_credito === 'foto de la asociación'
                ? '<span class="gr-foto-sello" title="Foto de la Asociación Mercaderes Unidos, tomada en el Mercado Nuevo">🤝</span>'
                : '') +
            '</div>'
          : '<div class="gr-foto sin-foto"><span>' + esc(r.nombre.charAt(0)) + '</span></div>') +
        '<div class="gr-cuerpo">' +
          '<div class="gr-cab">' +
            '<div class="gr-rubro-nom">' + esc(r.nombre) + '</div>' +
            (r.nuevo ? '<span class="gr-cambio nuevo" title="No estaba en el ' +
              'parte anterior">Nuevo en este parte</span>' : '') +
            (dudosa ? '<span class="gr-flag" title="Falta confirmar la unidad">unidad por confirmar</span>' : '') +
          '</div>' +
          // El sello de fecha. Nunca se enseña un precio de otro día sin
          // decir de qué día es, en el mismo bloque donde está el número.
          (r.arrastrado
            ? '<div class="gr-sello-viejo">Precio del <b>' +
                esc(fechaLarga(r.fecha_origen)) + '</b>' +
                '<span class="silencio"> · el gremio no lo cotizó hoy</span></div>'
            : '') +
          '<ul class="gr-lista">' + r.filas.map(fila).join('') + '</ul>' +
          contraste(r) +
          notas(r) +
        '</div>' +
      '</article>';
    }).join('');

    /* ---------- pie y crédito ---------- */
    var deHoy = items.filter(function (i) { return !i.arrastrado; });
    var conUnidad = deHoy.filter(function (i) { return i.precio_lb_min != null; }).length;
    var nArrastrados = items.length - deHoy.length;
    document.getElementById('pie-parte').innerHTML =
      '<p class="silencio">' +
        deHoy.length + ' renglones cotizados hoy · ' + nRubros + ' rubros · ' +
        conUnidad + ' comparables por libra. ' +
        'Los que no traen unidad declarada se muestran tal cual se publicaron y ' +
        '<b>no se comparan</b>: un hueco se ve, un supuesto no.' +
      '</p>' +
      // Qué NO trae el parte de hoy. Sin esto, un rubro que ayer estaba y hoy
      // no queda como si hubiera desaparecido del mercado, cuando lo que pasó
      // es que el gremio no lo cotizó. Callarlo se leería como dato.
      (nArrastrados
        ? '<p class="gr-cobertura">Otros ' + nArrastrados + ' renglones ' +
          'llevan la fecha del día en que se cotizaron —unos en su propio ' +
          'rubro más abajo, otros dentro de un rubro que hoy sí se cotizó ' +
          'pero sin ese grado—. Se dejan porque un precio de mayoreo de hace ' +
          'un día sigue orientando, pero no cuentan como precio de hoy ni se ' +
          'les calcula subida o bajada.</p>'
        : '') +
      (m.nota_cobertura
        ? '<p class="gr-cobertura">' + esc(m.nota_cobertura) + '</p>'
        : '') +
      (PREV_FECHA
        ? '<p class="silencio">El cambio de precio se calcula contra el parte del <b>' +
          esc(fechaLarga(PREV_FECHA)) + '</b>.</p>'
        : '');

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
