# Cómo escala esto cuando entren productores

Nota de diseño, no de implementación. Nada de esto está construido todavía.

Hoy Kcuesta es una fuente de precios. El día que entren productores a
publicar, la página del mercado pasa de mostrar tres cadenas a mostrar
cientos de vendedores, y varios van a estar vendiendo lo mismo. Ese es el
momento en que se decide si esto le sirve al productor o se le voltea en
contra.

---

## 1. El problema: la guerra de precios

La forma obvia de mostrar N vendedores del mismo rubro es ordenarlos por
precio, más barato arriba. Es lo que hace todo comparador —y lo que hace
esta misma página hoy con los supermercados.

**Con productores eso sería un error, y de los caros.**

Ordenar por precio le enseña dos cosas a la gente. Al comprador, que el de
arriba es el que hay que llamar. Al productor, que la única forma de que lo
llamen es bajar. En dos meses todos cotizan al costo y el que aguanta es el
que más tierra tiene, que es exactamente el productor que menos necesita a
Kcuesta.

Y se lleva por delante el activo del proyecto. El índice de precio en finca
—lo único que Kcuesta va a medir y nadie más mide— dejaría de medir el
mercado para medir quién estuvo más desesperado esa semana. Un índice así no
le sirve a nadie: ni al productor para negociar, ni al comprador para
planificar, ni a Kcuesta para venderlo.

Segundo problema, más simple: **la cosecha no es mercancía idéntica.** Dos
sacos de plátano barahonero se distinguen por calidad (Primera, Segunda,
Rabiza), por fecha de corte, por provincia, por volumen disponible y por si
va puesto en finca o puesto en mercado. Amazon puede alinear diez vendedores
del mismo libro porque el libro es el mismo. Aquí no lo es, y alinearlos en
una columna de precios finge que sí.

---

## 2. La salida: comparar contra el mercado, no contra el vecino

El movimiento central es cambiar el punto de referencia.

En vez de **“este productor es más barato que aquel”**, la tarjeta dice
**“este precio está dentro del rango del mercado para este rubro hoy”**.

La referencia deja de ser el competidor y pasa a ser el índice: mediana,
p25 y p75 de `indice_precios`, que el esquema ya contempla. Eso cambia el
incentivo por completo. Bajar el precio ya no te sube en la lista, porque la
lista no está ordenada por precio; solo te saca del rango y te marca como
alguien que está regalando su cosecha.

En concreto, sobre cada oferta de productor:

- **En rango** — entre p25 y p75. Es el estado normal y no se premia ni se castiga.
- **Bajo el mercado** — debajo de p25. Se muestra, pero como advertencia
  para el vendedor, no como medalla para el comprador.
- **Sobre el mercado** — encima de p75. También se muestra; puede estar
  justificado por calidad o por cercanía.

Nada de esto se publica mientras no haya muestra suficiente. `indice_config`
ya trae los mínimos (5 anuncios para la serie de oferta, 3 ventas
confirmadas para la de cerrado) y esa compuerta hay que respetarla: un
“rango de mercado” calculado con dos anuncios es una cifra inventada con
apariencia de dato.

### Lo que hay que quitar cuando entren productores

La insignia **“Mejor precio”** que hoy corona la oferta más barata. Está
bien para supermercados —son cadenas, no son los usuarios de Kcuesta— y
estaría muy mal para un productor. Es la guerra de precios convertida en
premio visual.

---

## 3. Que no compitan de frente cuando no compiten de verdad

Buena parte del choque desaparece segmentando por lo que ya distingue a una
oferta de otra:

- **Provincia.** Un comprador en Santiago y un vendedor en Barahona rara vez
  son la misma operación: el flete se come la diferencia. Ordenar por
  cercanía antes que por precio es más útil y de paso reparte la demanda.
- **Volumen.** Quien necesita 5,000 unidades no compite por el que tiene 200.
- **Fecha de corte.** Lo que está listo el jueves no compite con lo de dentro
  de tres semanas.
- **Calidad.** Primera, Segunda y Rabiza son productos distintos y ya están
  en el esquema. Mezclarlos en una lista de precios hace ver barato lo que
  simplemente es Segunda.

Orden por defecto: **mejor coincidencia**, compuesto de cercanía, calce de
volumen, frescura del anuncio (`confirmado`) y si el perfil está verificado.
El precio se ve siempre y se puede ordenar por él a propósito —esconderlo
sería traicionar el punto entero del sitio— pero no es el orden que viene
puesto.

---

## 4. El otro sentido: que el comprador publique

`CONCEPTO.md` ya lo tiene en el plan como paso 4 y vale la pena adelantarlo,
porque es el antídoto más limpio contra la subasta a la baja.

El comprador publica lo que necesita —rubro, volumen, calidad, para cuándo,
dónde— y los productores responden **en privado**. Nadie ve la oferta del
otro, así que no hay a quién quitarle el puesto bajando cinco pesos. El
comprador escoge por precio, cercanía y confianza, todo junto.

Para el productor pequeño esto es mejor que la vitrina: no compite por
aparecer de primero en una lista, responde a una necesidad concreta.

---

## 5. Cuando sean muchos: lo técnico

Lo de hoy no aguanta miles de anuncios, y conviene saber exactamente dónde
se rompe.

**Se rompe primero el JSON estático.** El sitio pinta desde
`assets/js/datos.js`, que hoy son 84 KB con 44 rubros. Con anuncios reales
crece sin techo y todo el mundo se descarga el mercado entero para ver seis
tarjetas. El corte natural está por los pocos miles de anuncios.

La migración, cuando toque:

- **`mercado.html` pasa a leer de Supabase** con paginación de cursor sobre
  `(publicado, id)` —no `OFFSET`, que se degrada— y los filtros
  (rubro, provincia, calidad) resueltos en la base, no en el navegador.
- **`precios.html` se queda estático.** Son 79 rubros, cambia una vez al
  día y así sigue abriendo sin pedirle nada a nadie.
- **Un índice más**: `anuncios (cultivo_id, provincia, estado, publicado desc)`.
  Los tres que hay cubren cada filtro por separado; el compuesto es el que
  va a pedir la pantalla real.
- **`indice_precios` se calcula en la base**, no en el cliente, y en un
  trabajo aparte del de captura.

Lo que **ya está bien** y no hay que rehacer: la partición de
`perfiles` / `perfiles_contacto` (el teléfono no se filtra ni con la consulta
mal escrita), las políticas RLS, y la compuerta `publicable` del índice.

Lo que **falta** y no es opcional el día que se abra:

- Subida de fotos por el productor, a Storage y con cuota por usuario.
- Límite de publicación por cuenta, o el primer vivo llena el mercado.
- Búsqueda por texto (`pg_trgm` sobre título y cultivo).
- Moderación mínima: reportar anuncio, y poder bajarlo sin borrar el histórico.

---

## 6. Lo que no se debe hacer

- **Cobrar por aparecer más arriba.** Convierte el orden en publicidad y
  mata la confianza en el índice, que es el activo.
- **Esconder el precio hasta que el comprador escriba.** Es la trampa clásica
  de los portales de fincas; el sitio entero se sostiene en lo contrario.
- **Un solo “ganador” por rubro tipo Buy Box.** Amazon puede porque el
  producto es idéntico. Aquí elegiría por el comprador entre cosas que no
  son iguales, y dejaría a todos los demás productores invisibles.
