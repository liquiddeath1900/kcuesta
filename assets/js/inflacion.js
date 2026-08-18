/* ¿Está más caro? — IPC por artículos del Banco Central.
   Lee data/ipc.json (lo genera pipeline/ipc.py).

   Regla de la página: primero la frase, después el número, y el índice de
   último y en chiquito. "228.5" no le dice nada a nadie; "la yuca está 42 %
   más cara que el año pasado" sí. */
(function () {
  'use strict';

  var MES = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio',
             'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre'];
  var CATS = [
    { id: 'todos', nombre: 'Todo' },
    { id: 'viveres', nombre: 'Víveres' },
    { id: 'vegetales', nombre: 'Vegetales' },
    { id: 'frutas', nombre: 'Frutas' },
    { id: 'granos', nombre: 'Granos' }
  ];
  var cat = 'todos', datos = null;

  function esc(s) {
    return String(s).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }
  function mesLargo(clave) {          // '2026-07' -> 'julio 2026'
    var p = String(clave).split('-');
    return MES[Number(p[1]) - 1] + ' ' + p[0];
  }
  function pct(n) { return (n > 0 ? '+' : '') + n.toFixed(1).replace('.', ',') + ' %'; }

  /* "12 % más cara que hace un año". La palabra va delante del signo
     porque es lo que la gente busca: si subió o si bajó. El género viene
     del dato, no del nombre: adivinarlo por la última letra deja "el
     tomate más carA" y "la papa más carO". */
  function frase(n, genero) {
    if (n === null || n === undefined) return 'sin dato';
    if (Math.abs(n) < 1) return 'casi igual que hace un año';
    var adj = (n > 0 ? 'car' : 'barat') + (genero === 'f' ? 'a' : 'o');
    return Math.abs(n).toFixed(0) + ' % más ' + adj + ' que hace un año';
  }
  function clase(n) { return n > 0.5 ? 'sube' : (n < -0.5 ? 'baja' : ''); }

  /* Estacionalidad: la variación promedio de cada mes trae dentro la
     inflación general, que empuja todo hacia arriba y haría que el mes más
     barato fuera siempre enero. Se le resta el promedio de los doce para
     quedarse solo con la forma del año —cuándo entra la cosecha y afloja el
     precio, y cuándo escasea. */
  function forma(est) {
    var claves = Object.keys(est).sort();
    if (claves.length < 12) return null;
    var vals = claves.map(function (k) { return est[k]; });
    var media = vals.reduce(function (a, b) { return a + b; }, 0) / vals.length;
    var nivel = [], acum = 0;
    vals.forEach(function (v) { acum += v - media; nivel.push(acum); });
    var min = 0, max = 0;
    nivel.forEach(function (v, i) { if (v < nivel[min]) min = i; if (v > nivel[max]) max = i; });
    // Un año plano no tiene temporada que contar.
    if (nivel[max] - nivel[min] < 4) return null;
    return { barato: min, caro: max, nivel: nivel };
  }

  /* Línea de 24 meses. Sin ejes ni números: es para ver la forma de un
     vistazo, el dato exacto está en la tarjeta. */
  function linea(serie) {
    var min = Math.min.apply(null, serie), max = Math.max.apply(null, serie);
    var rango = (max - min) || 1, an = 100, al = 30;
    var pts = serie.map(function (v, i) {
      return (i * an / (serie.length - 1)).toFixed(1) + ',' +
             (al - 2 - (v - min) / rango * (al - 4)).toFixed(1);
    }).join(' ');
    return '<svg class="inf-linea" viewBox="0 0 ' + an + ' ' + al + '" preserveAspectRatio="none" ' +
      'role="img" aria-label="Dos años de índice, de ' + min.toFixed(0) + ' a ' + max.toFixed(0) + '">' +
      '<polyline points="' + pts + '" fill="none" stroke="currentColor" stroke-width="1.6" ' +
      'stroke-linejoin="round" stroke-linecap="round" vector-effect="non-scaling-stroke"/></svg>';
  }

  function tarjeta(r) {
    var f = forma(r.estacionalidad);
    var g = r.genero === 'f' ? 'a' : 'o';
    var temporada = f
      ? '<p class="inf-temporada">Suele estar más barat' + g + ' en <b>' + MES[f.barato] +
        '</b> y más car' + g + ' en <b>' + MES[f.caro] + '</b>.</p>'
      : '<p class="inf-temporada silencio">Sin una temporada marcada: se mueve por otra cosa, no por el mes.</p>';

    var mm = r.mensual === null ? '' :
      '<span class="chip ' + clase(r.mensual) + '">' +
      (r.mensual > 0 ? '▲ ' : (r.mensual < 0 ? '▼ ' : '')) + pct(r.mensual) + ' en el mes</span>';

    return '<article class="inf-carta">' +
      '<div class="inf-cab">' +
        '<h3>' + esc(r.nombre) + '</h3>' +
        '<span class="chip ' + clase(r.interanual) + ' inf-aa">' + esc(frase(r.interanual, r.genero)) + '</span>' +
      '</div>' +
      '<div class="inf-graf ' + clase(r.interanual) + '">' + linea(r.serie) + '</div>' +
      '<div class="inf-pie">' + mm + '</div>' +
      temporada +
      '<p class="inf-nota silencio">Índice ' + r.indice.toFixed(1).replace('.', ',') +
        ' — ' + pct(r.desde_base) + ' desde 2020. Artículo «' + esc(r.articulo_bcrd) + '» del Banco Central.</p>' +
    '</article>';
  }

  function extremos(rubros) {
    var con = rubros.filter(function (r) { return r.interanual !== null; });
    var orden = con.slice().sort(function (a, b) { return b.interanual - a.interanual; });
    function lista(l, cls) {
      return l.map(function (r) {
        return '<li><span>' + esc(r.nombre) + '</span>' +
          '<b class="' + cls + '">' + pct(r.interanual) + '</b></li>';
      }).join('');
    }
    document.getElementById('subieron').innerHTML = lista(orden.slice(0, 5), 'sube');
    document.getElementById('bajaron').innerHTML =
      lista(orden.slice(-5).reverse(), 'baja');
  }

  function pastillas() {
    document.getElementById('pastillas').innerHTML = CATS.map(function (c) {
      return '<button class="pastilla' + (c.id === cat ? ' on' : '') + '" data-cat="' + c.id + '">' +
        c.nombre + '</button>';
    }).join('');
  }

  function render() {
    var l = datos.rubros.filter(function (r) { return cat === 'todos' || r.categoria === cat; });
    var o = document.getElementById('orden').value;
    l = l.slice().sort(function (a, b) {
      if (o === 'sube') return (b.interanual || 0) - (a.interanual || 0);
      if (o === 'baja') return (a.interanual || 0) - (b.interanual || 0);
      // La ponderación es cuánto pesa el rubro en el gasto del hogar. Es el
      // orden que contesta "¿esto me toca el bolsillo a mí?".
      if (o === 'peso') return b.ponderacion - a.ponderacion;
      return a.nombre.localeCompare(b.nombre, 'es');
    });
    document.getElementById('cuenta').textContent = l.length + ' rubros';
    document.getElementById('rejilla').innerHTML = l.map(tarjeta).join('');
  }

  function cabecera() {
    var m = datos._meta, a = datos.alimentos || {};
    var caja = document.getElementById('titular');
    if (a.interanual === null || a.interanual === undefined) {
      caja.innerHTML = '<p>No se pudo leer el dato del mes.</p>';
      return;
    }
    caja.innerHTML =
      '<p class="inf-grande ' + clase(a.interanual) + '">' + pct(a.interanual) + '</p>' +
      '<p class="inf-grande-txt">es lo que ha ' + (a.interanual > 0 ? 'subido' : 'bajado') +
      ' la comida en un año, en todo el país.</p>';
    document.getElementById('fuente').innerHTML =
      '<span>📈</span><span><strong>' + esc(m.fuente) + '</strong> — ' + esc(m.serie) +
      '. Dato de <strong>' + mesLargo(a.mes) + '</strong>, base ' + esc(m.base) + '.</span>' +
      '<a href="' + esc(m.url) + '" target="_blank" rel="noopener">Ver el archivo oficial →</a>';
  }

  document.addEventListener('click', function (e) {
    var p = e.target.closest('[data-cat]');
    if (p) { cat = p.dataset.cat; pastillas(); render(); }
  });

  fetch('data/ipc.json').then(function (r) { return r.json(); }).then(function (d) {
    datos = d;
    cabecera();
    extremos(d.rubros);
    pastillas();
    render();
    document.getElementById('orden').addEventListener('change', render);
  }).catch(function () {
    document.getElementById('rejilla').innerHTML =
      '<p class="vacio">No se pudo cargar el dato del Banco Central. Intenta de nuevo.</p>';
  });
})();
