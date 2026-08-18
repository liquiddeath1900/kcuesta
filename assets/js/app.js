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


  /* ---------- cita de fuente ----------
     Los enlaces "Ver →" salieron de la vista pública. Mandaban a la ficha
     de la cadena, que es la góndola de otro: el sitio terminaba siendo un
     embudo hacia el supermercado en vez de la foto del mercado que dice
     ser, y encima con seis destinos distintos por tarjeta.

     Lo que sí hace falta es poder AUDITAR la cifra, y para eso no hace
     falta un enlace: hace falta decir de dónde salió y qué clase de precio
     es. Ninguna de estas cadenas publica precio por sucursal —lo que se
     captura es su tienda en línea, un solo precio para todo el país— así
     que la "ubicación" honesta es justo esa, y no un barrio inventado.

     Las URL siguen en los datos, sin pintarse. Son la herramienta de
     verificación de la casa, no un botón para el visitante. */

  /* ---------- de qué mercado es la referencia mayorista ----------
     No es siempre el mismo. `precios_oficiales` recibe filas mayoristas de
     dos fuentes que son dos LUGARES distintos:

       Ministerio de Agricultura -> Mercado Nuevo de la Duarte
       MERCADOM                  -> Merca Santo Domingo (km 22, Aut. Duarte)

     Aquí se rotulaba "Mercado Nuevo, Santo Domingo" en todas las tarjetas,
     y era falso en 14 de 32 rubros. Ahora la fuente viaja con el dato y
     cada tarjeta dice de dónde salió la suya.

     Mientras el pipeline no vuelva a correr, los datos ya publicados no
     traen `mercado_ref_fuente`. En ese caso NO se inventa un mercado: se
     dice lo único que es cierto de todos, que son los mayoristas de Santo
     Domingo. Vago, pero no falso. */
  var MERCADO_DE = {
    'Ministerio de Agricultura': 'Mercado Nuevo, Santo Domingo',
    'MERCADO NUEVO': 'Mercado Nuevo, Santo Domingo',
    'MERCADOM — Merca Santo Domingo': 'Merca Santo Domingo (MERCADOM)',
    'MERCADOM': 'Merca Santo Domingo (MERCADOM)'
  };
  var SEDE_GENERICA = 'mayoristas de Santo Domingo';

  function sedeMayorista(r) {
    var f = r.mercado_ref_fuente;
    if (!f) return SEDE_GENERICA;
    if (MERCADO_DE[f]) return MERCADO_DE[f];
    // Fuente nueva que nadie mapeó: se enseña su nombre tal cual antes que
    // asignarle un mercado a dedo.
    return f;
  }

  function cita(id) {
    var c = O.cadenas[id] || {};
    return '<b>' + esc(c.nombre || id) + '</b>' +
           '<span class="rb-sede"> · ' + esc(c.sede || 'Tienda en línea') +
             (c.alcance ? ' · ' + esc(c.alcance) : '') + '</span>';
  }

  // Dentro de una tarjeta el "de dónde" es el MISMO en todas las filas:
  // trece veces "Tienda en línea · Precio nacional, sin sucursal" convertía
  // la tarjeta en un muro y cada fila pasaba de una línea a cuatro. La
  // procedencia se dice una sola vez, en el rótulo de la lista; la fila se
  // queda con el nombre, que es lo único que cambia de una a otra.
  function rotuloFuentes(r) {
    var sedes = {};
    r.ofertas.forEach(function (o) {
      var c = O.cadenas[o.cadena] || {};
      sedes[(c.sede || 'Tienda en línea') + ' · ' + (c.alcance || '')] = 1;
    });
    var claves = Object.keys(sedes);
    return 'De dónde sale este número' +
      (claves.length === 1 ? ' — ' + esc(claves[0].replace(/ · $/, '')) : '');
  }


  function etiquetaFuentes(r) {
    var cadenas = {};
    r.ofertas.forEach(function (o) { cadenas[o.cadena] = 1; });
    var total = Object.keys(cadenas).length;
    var comp = r.n_fuentes || 0;

    if (comp === 0) return 'Precio sin peso declarado · ' + total +
      (total === 1 ? ' tienda' : ' tiendas');
    if (comp === total) {
      return comp === 1 ? 'Un solo precio observado'
                        : 'Valor de referencia · ' + comp + ' fuentes';
    }
    // Hay tiendas que no se pudieron comparar: se dice cuántas de cuántas.
    return (comp === 1 ? 'Un solo precio comparable' : 'Valor de referencia · ' + comp + ' fuentes') +
           ' de ' + total + ' tiendas';
  }

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

    // TITULAR = VALOR DE REFERENCIA, no el más barato.
    //
    // Antes encabezaba `precio_lb_min`. Eso contesta "¿dónde está más
    // barato hoy?", que es la pregunta de un directorio de tiendas. Kcuesta
    // no es eso: la información pública que se captura sirve para dibujar
    // cómo está el mercado, y lo que alguien viene a saber es a cómo está
    // la cosa. Encabezar el mínimo además premia al más barato, que es lo
    // que ESCALA.md prohíbe para el día que quien publique sea un
    // productor. La mediana no premia a nadie.
    //
    // El dónde no va aquí. Estas cifras son de la tienda EN LÍNEA de cada
    // cadena —un precio nacional, sin sucursal— así que poner una
    // ubicación sería inventarla. La ubicación llega cuando publique gente
    // de verdad y la ponga en su perfil.
    var valor  = porLb ? r.valor_lb : r.valor_unidad;
    var unidad = porLb ? '/lb' : '/' + esc(r.unidad_valor || mejor.unidad);

    // Al filtrar por cadena puede quedar un rubro cuyas ofertas de ESA
    // tienda no declaran peso: no hay mediana por libra ni valor por unidad
    // que enseñar. Antes reventaba el render entero de la página con un
    // null.toLocaleString(). Se cae al precio de etiqueta, que es lo único
    // que sí se sabe, y se dice que es del empaque.
    if (valor == null) {
      valor = r.precio_min;
      unidad = ' el empaque';
    }

    // Encabezado: nombre a la izquierda, precio a la derecha en la misma
    // línea base. Es la franja que se escanea con el pulgar.
    // La referencia mayorista va en su PROPIA fila, a todo el ancho. Metida
    // en la columna de texto la dejaba en 111px y todo se partía en cinco
    // líneas: la cabecera medía 218px de alto en un teléfono.
    var cabecera =
      '<div class="rb-foto">' + foto + '</div>' +
      '<div class="rb-txt">' +
        '<div class="rb-nom">' + esc(r.nombre) + '</div>' +
      '</div>' +
      // El meta sale de la columna de texto y se lleva el ancho completo.
      // Encajonado entre la foto y el precio le quedaban ~110px y "Valor de
      // referencia · 2 fuentes" se partía en tres líneas.
      '<div class="rb-meta">' +
          // Con una sola fuente no hay mediana ni valor de mercado: hay
          // un precio visto una vez. Llamarlo "valor de referencia" le
          // daría un peso que no tiene, y el sitio vive de que el número
          // se pueda defender.
          //
          // `n_fuentes` cuenta solo las cadenas COMPARABLES —las que
          // declararon peso— y la lista de abajo las enseña todas. La
          // naranja agria decía "un solo precio observado" y acto seguido
          // listaba tres tiendas, que se lee como que el sitio no sabe
          // contar. Cuando los dos números no coinciden, se dicen los dos.
          etiquetaFuentes(r) +
          (rango ? '<span class="rb-rango"> · ' + rd(r.precio_lb_min, 2) +
                   ' – ' + rd(r.precio_lb_max, 2) + '/lb</span>' : '') +
      '</div>' +
      '<div class="rb-precio">' +
        '<span class="cifra">' + rd(valor, 2) + '</span>' +
        '<span class="rb-u">' + unidad + '</span>' +
      '</div>' +
      '';

    // La referencia mayorista baja al PIE de la tarjeta. Arriba competía
    // con el valor por la atención y la tarjeta arrancaba con dos cifras
    // distintas en la misma pantalla. El orden ahora es el del argumento:
    // primero cuánto vale la cosa, y de último contra qué se está midiendo.
    var pieRef = (r.mercado_ref_unidad && porLb)
      ? '<div class="rb-ref">Referencia: mayorista ' + rd(r.mercado_ref_unidad, 2) +
          '/lb · ' + esc(sedeMayorista(r)) +
          (r.mercado_ref_fecha ? ' · ' + esc(r.mercado_ref_fecha) : '') +
          ' ' + marca + '</div>'
      : '<div class="rb-ref silencio">Sin referencia mayorista comparable</div>';

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
        '<div class="rb-cab">' + cabecera + '</div>' +
        '<div class="rb-fuente-una silencio">Fuente: ' + cita(mejor.cadena) + '</div>' +
        pieRef +
      '</article>';
    }

    return '<article class="rubro">' +
      '<details>' +
        '<summary class="rb-cab">' + cabecera +
          '<span class="rb-flecha" aria-hidden="true">▾</span>' +
        '</summary>' +
        filasOfertas(r) +
      '</details>' +
      pieRef +
    '</article>';
  }


  /* ---------- qué distingue una oferta de otra ----------
     Dentro de una tarjeta de rubro la CADENA se repite: el arroz selecto
     trae quince ofertas de solo dos tiendas. Lo que cambia es la marca y el
     tamaño del empaque —Líder, Wala, Bisonó, Pimco, de 1 a 20 libras— y eso
     estaba en gris chiquito debajo del nombre de la tienda en negrita. Se
     leía como nueve veces "Supermercados Nacional" repetido, como si fueran
     datos duplicados o nueve sucursales distintas.

     Se invierte: primero lo que distingue, después de quién es.

     Del título se le quita el nombre del rubro, que ya lo dice la cabecera.
     "Arroz Selecto Wala 20 Lb" adentro de la tarjeta de Arroz selecto
     sobra la mitad; lo que hace falta es "Wala 20 Lb". */
  function distintivo(titulo, rubro) {
    var t = String(titulo || '').trim();
    var pal = String(rubro || '').trim().split(/\s+/);
    // Se quitan las palabras del rubro SOLO si van al principio y en orden.
    // Quitarlas donde caigan borraría "Selecto" de "Súper Selecto".
    for (var i = 0; i < pal.length; i++) {
      var re = new RegExp('^' + pal[i].replace(/[.*+?^${}()|[\]\\]/g, '\\$&') + '\\s+', 'i');
      var sinTilde = sinAcento(t), objetivo = sinAcento(pal[i]);
      if (sinTilde.toLowerCase().indexOf(objetivo.toLowerCase() + ' ') === 0) {
        t = t.slice(pal[i].length).replace(/^[\s,·-]+/, '');
      } else if (re.test(t)) {
        t = t.replace(re, '');
      } else break;
    }
    // Si no quedó nada, el título era solo el nombre del rubro: se devuelve
    // entero antes que una fila vacía.
    return t.trim() || String(titulo || '').trim();
  }

  function sinAcento(x) {
    return String(x).normalize ? String(x).normalize('NFD').replace(/[\u0300-\u036f]/g, '') : String(x);
  }

  function filasOfertas(r) {
    var cad = function (id) { return (O.cadenas[id] || {}).nombre || id; };
    var base = r.precio_lb_min;

    // La lista dejó de ser una góndola y pasó a ser la evidencia: de dónde
    // sale el valor del titular. Por eso se rotula. Sin rótulo, abrir la
    // tarjeta parecía "escoge dónde comprar", que no es lo que el sitio
    // hace ni lo que puede prometer con precios en línea sin sucursal.
    return '<div class="rb-fuente-tit silencio">' + rotuloFuentes(r) + '</div>' +
      '<ul class="rb-lista">' + r.ofertas.map(function (o, i) {
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
          '<b>' + esc(distintivo(o.titulo, r.nombre)) + '</b>' +
          '<span class="silencio rb-desc">' + esc(cad(o.cadena)) + '</span>' +
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
      '</li>';
    }).join('') + '</ul>' +
    '<div class="rb-pie silencio">Precio al consumidor, no de finca · ' +
      'tienda en línea, precio nacional sin sucursal · ' +
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
          '</li>';
        }).join('') + '</ul>' +
      '</details>' +
    '</article>';
  }


  /* ---------- recortar un rubro a una sola cadena ----------
     Todo se recalcula POR LIBRA, igual que en el pipeline.

     Antes esto comparaba `o.precio` —el precio del empaque— contra
     `mercado_ref_unidad`, que es por libra. El resultado: la tarjeta de
     arroz súper selecto decía "+21% sobre mayorista" sin filtro y "+522%"
     al tocar la pastilla de Sirena, con los mismos datos. Y como tampoco
     se recalculaba `valor_lb`, la cifra grande seguía siendo la del rubro
     completo mientras la lista de abajo ya estaba filtrada.

     La mediana es la misma cuenta que `resumen_valor()` en
     pipeline/exportar.py —cuantil con interpolación lineal— para que el
     número no cambie según quién lo calcule. */
  function cuantil(xs, q) {
    if (!xs.length) return null;
    if (xs.length === 1) return xs[0];
    var pos = q * (xs.length - 1), bajo = Math.floor(pos),
        alto = Math.min(bajo + 1, xs.length - 1);
    return Math.round((xs[bajo] + (xs[alto] - xs[bajo]) * (pos - bajo)) * 100) / 100;
  }

  function recortarACadena(r, cadena) {
    var solo = r.ofertas.filter(function (o) { return o.cadena === cadena; });
    var conLb = solo.filter(function (o) { return o.precio_lb; });
    var lbs = conLb.map(function (o) { return o.precio_lb; })
                   .sort(function (a, b) { return a - b; });
    var precios = solo.map(function (o) { return o.precio; });
    var valor = lbs.length ? cuantil(lbs, 0.5) : null;
    var ref = r.mercado_ref_unidad;

    return Object.assign({}, r, {
      ofertas: solo,
      n: solo.length,
      n_comparables: conLb.length,
      // Una sola cadena es UNA fuente, diga lo que diga el rubro completo.
      n_fuentes: conLb.length ? 1 : 0,
      precio_min: Math.min.apply(null, precios),
      precio_max: Math.max.apply(null, precios),
      precio_lb_min: lbs.length ? lbs[0] : null,
      precio_lb_max: lbs.length ? lbs[lbs.length - 1] : null,
      valor_lb: valor,
      p25_lb: lbs.length ? cuantil(lbs, 0.25) : null,
      p75_lb: lbs.length ? cuantil(lbs, 0.75) : null,
      sobreprecio: (ref && valor) ? Math.round((valor - ref) / ref * 100) : null
    });
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
        lista = lista.map(function (r) { return recortarACadena(r, cadenaActiva); });
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
        // Un gremio está en el registro de fuentes pero NO es una tienda
        // donde comprar: la Asociación Mercaderes Unidos reporta la plaza,
        // no vende. Como pastilla de filtro le prometería al usuario que
        // puede comprarle. Hoy además no tiene ofertas en los rubros, así
        // que el segundo filtro ya la deja fuera — esto es para el día que
        // sí las tenga.
        if ((O.cadenas[id] || {}).tipo === 'gremio') return false;
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

    // Las tarjetas de rubro ya no llevan enlace a la cadena —salieron de la
    // vista pública— así que aquí no queda nada que redirigir. El corte de
    // la vitrina más abajo sigue aplicando igual.

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
