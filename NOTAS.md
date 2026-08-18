# Notas: qué falta, qué está roto, qué hay que decidir

Lista viva. Se edita a mano. Lo que se resuelve se marca con `[x]` y se deja
un rato antes de borrarlo, para no volver a discutir lo mismo.

Las decisiones de fondo sobre el mercado con productores están en
`ESCALA.md`. Esto es la lista de pendientes concretos.

---

## Lo primero de mañana

1. **Crear el bucket de Supabase para las fotos.** Acordado el 16/08. Es el
   que va a guardar las fotos que suba el productor. No pueden ir al repo:
   GitHub Pages tiene límite blando de 1 GB por sitio, ~6,600 fotos. Hace
   falta el bucket, sus políticas RLS y la cuota por usuario **antes** de
   abrir la publicación en octubre.
2. **Rediseñar la parrilla según elboletoganador.com** (ver abajo).
3. Lo de "Bloqueado en manos del dueño", que sigue frenando el pipeline.

---

## Referencia de diseño: elboletoganador.com

El dueño lo trajo el 16/08 y le gusta el layout. Lo que de verdad sirve
para Kcuesta, separado de lo que es marca ajena:

**Vale la pena copiar**

- **Parrilla de varias columnas en escritorio.** Ellos ponen cuatro
  tarjetas por fila; Kcuesta hoy usa una sola columna a todo el ancho, que
  en un monitor desperdicia media pantalla y obliga a bajar por 44 rubros.
  En teléfono se queda en una columna.
- **Panel de filtros en una tarjeta blanca elevada**, con los campos
  rotulados uno al lado del otro, en vez de tres filas de pastillas
  apiladas. Para Kcuesta serían: rubro, provincia (cuando haya
  productores) y cadena.
- **Barra de servicio arriba** con la tasa del dólar. Kcuesta ya la tiene
  en `_meta.tasa_cambio` del Banco Central y hoy solo se usa en una nota al
  pie de precios.html. Ahí arriba tiene más sentido, junto a la fecha del
  dato.
- **Encabezado de sección con barra de acento a la izquierda** y el
  selector de orden a la derecha, en la misma línea.
- **Insignia de frescura tipo "HOY"** pegada a la fecha. Kcuesta ya calcula
  `diasDesde()` y hoy lo entierra en el pie de la tarjeta.
- **Jerarquía de la tarjeta**: número principal grande con su rótulo
  debajo, y los secundarios más pequeños al lado. Calza con precio por
  libra grande + mayorista y rango en chico.
- **Chips de acción al pie de la tarjeta** ("Historial", "Predicciones").
  Para Kcuesta: "Historial" —que ya se puede, hay serie desde 2017— y
  "Comparar".

**No copiar**

- El morado, los degradados y las sombras fuertes. Kcuesta es tierra
  cálida y esa decisión ya está tomada en el sistema de diseño.
- Meter todo arriba del pliegue a la fuerza. Su tarjeta cabe en poco
  porque son tres números; la de Kcuesta lleva comparación contra el
  mayorista, que es el argumento.

---

## Bloqueado en manos del dueño

- [ ] **Aplicar el esquema en Supabase.** `db/03_retail.sql` y luego
      `db/04_retail_rls.sql` en el editor SQL. Hasta que no corran, el
      pipeline no puede escribir nada y el sitio vive del JSON.
- [ ] **Instalar el workflow.** Copiar `pipeline/precios.workflow.yml` a
      `.github/workflows/precios.yml` desde la web de GitHub. El token de
      la máquina no tiene alcance `workflow` y el push se rechaza.
- [ ] **Cargar los secretos** del repo: `SUPABASE_URL`,
      `SUPABASE_SERVICE_KEY`, `FIRECRAWL_API_KEY`.

> Mientras el workflow no esté puesto **nada se refresca**. El snapshot de
> hoy se queda congelado, y cada día que MERCADOM no se captura se pierde
> para siempre: publican un solo archivo que se sobrescribe.

---

## Para poder abrir a productores (antes de promocionar en octubre)

- [ ] **`vender.html` no publica nada.** Hoy el formulario dibuja una
      tarjeta de vista previa y se esconde. No hay `insert` a `anuncios`.
      Es lo primero que hay que construir; sin eso no hay plataforma, hay
      página de precios.
- [ ] **Subida de fotos del productor.** No existe bucket ni código de
      subida. **No pueden ir al repo** (ver límites abajo): van a Supabase
      Storage, con cuota por usuario y las mismas políticas RLS.
- [ ] **Límite de publicación por cuenta.** Sin esto, el primer vivo llena
      el mercado.
- [ ] **Moderación mínima:** reportar un anuncio y poder bajarlo sin borrar
      el histórico (el histórico es el índice).
- [ ] **Quitar el teléfono falso.** `(809) 555-0100` sigue en el código de
      contacto de los anuncios de productor.
- [ ] **Búsqueda por texto** (`pg_trgm` sobre título y cultivo).
- [ ] **Índice compuesto** `anuncios (cultivo_id, provincia, estado, publicado desc)`.
      Los tres que hay cubren cada filtro por separado, no el combinado.

---

## Techo actual: cuánta gente aguanta esto hoy

Tres números distintos, y el que duele no es el que parece.

### Cuentas: no es el problema
Supabase Pro incluye **100,000 usuarios activos al mes**. El registro ya
funciona (Google y WhatsApp OTP) y crea el perfil solo. Para lo que se
espera en octubre, sobra de largo.

### Vendedores publicando hoy: **cero**
No por límite técnico, sino porque el formulario no inserta. Cualquiera
puede registrarse; nadie puede publicar nada.

### Anuncios visibles: **~400**, y ahí está el techo real
El sitio pinta desde `assets/js/datos.js`, un bundle que trae el mercado
entero. Hoy pesa **149 KB** con 148 ofertas — cerca de **1 KB por oferta**.
Cada visitante se lo descarga completo para ver seis tarjetas.

El propio CSS declara el presupuesto: *"la página tiene que abrir a
384 Kbps"*. Contra eso:

| Anuncios | Bundle  | Abrir a 384 Kbps |
|---------:|--------:|-----------------:|
| 148 (hoy)| 149 KB  | 3 s              |
| ~400     | 200 KB  | 4 s              |
| ~1,000   | 500 KB  | 10 s             |
| ~2,000   | 1 MB    | 21 s             |

**Alrededor de 400 anuncios se rompe el presupuesto propio.** Pasados los
mil, la página deja de abrir en un teléfono con señal mala del campo, que
es exactamente el usuario del proyecto.

La salida está escrita en `ESCALA.md`: `mercado.html` pasa a leer de
Supabase con paginación de cursor y filtros en la base; `precios.html` se
queda estático porque son 79 rubros y cambian una vez al día.

### Fotos: NO van al repo
GitHub Pages tiene **límite blando de 1 GB por sitio** y 100 GB de tráfico
al mes. Hoy el sitio pesa ~3 MB. A ~150 KB por foto, el repo reventaría a
las **~6,600 fotos** — y eso es un productor con tres fotos por anuncio y
dos mil anuncios. Las fotos de usuario van a Supabase Storage (100 GB en
Pro, ~660,000 fotos) desde el primer día.

### Resumen
| Recurso | Límite | ¿Aprieta? |
|---|---|---|
| Cuentas | 100k MAU (Supabase Pro) | No |
| Base de datos | 8 GB (~millones de filas) | No |
| Fotos en Storage | 100 GB (~660k) | No |
| Fotos en el repo | 1 GB (~6.6k) | **Sí — no usar** |
| Bundle estático | ~400 anuncios | **Sí — primer techo** |
| Publicar | no existe | **Sí — bloqueante** |

---

## Deuda conocida

- [ ] **El sobreprecio se calcula contra el mayorista del rubro, no del
      empaque.** Cuando el Ministerio publica el mayorista en una unidad
      rara, el porcentaje sale raro. Se ve en Cebolla roja: RD$46 – RD$231
      por libra en el mismo rubro.
- [ ] **Los rubros sin peso declarado no se comparan.** Correcto, pero hoy
      solo se dice "empaque sin peso declarado" en la fila; no hay forma de
      filtrarlos.
- [ ] **`ckan` y `firecrawl` no se han corrido de verdad.** El histórico de
      2017 y las cuatro cadenas bloqueadas están escritos y sin estrenar.
- [ ] **Fotos de despensa con marca del fabricante.** Arroz, habichuela y
      leche muestran el empaque (Lider, Bisonó, Wala). Es exacto, pero es
      arte del fabricante. Decidir si se dejan o se cambian por neutras.
- [ ] **`diasDesde()` ya usa la fecha real**, pero el aviso "Prototipo" de
      arriba sigue diciendo que los anuncios de productores son
      ilustrativos. Hay que quitarlo cuando entren productores de verdad.

## Preguntas abiertas

- [ ] ¿Qué pasa con un anuncio que nadie confirma? Existe la columna
      `confirmado` y la idea de "precio de hace N días", pero no hay regla
      de cuándo se vence ni quién lo baja.
- [ ] ¿El comprador necesita cuenta para ver teléfonos, o solo para
      escribir? Hoy la vitrina pide cuenta para todo.
- [ ] ¿Se cobra algo alguna vez? Si sí, **no puede ser por aparecer más
      arriba** (ver ESCALA.md).

---

## 2026-08-17 — La tarjeta pasó de góndola a valuación

### Lo que cambió

El titular de la tarjeta era `precio_lb_min`: el más barato. Eso contesta
"¿dónde está más barato hoy?", que es la pregunta de un directorio de
tiendas. Kcuesta no es eso. La información pública que se captura está para
dibujar **cómo está el mercado**, y el titular ahora es el **valor de
referencia** — la mediana por libra de lo que cobran las fuentes — con el
rango debajo y la **referencia mayorista al pie**, no en la cabecera.

Mediana y no promedio: un saco mal etiquetado mueve el promedio y no mueve
la mediana. Con la cebolla real (46.00 / 46.75 / 229.00 por libra) el
promedio da RD$107 y la mediana da RD$46.75.

Se guardan dos lecturas del sobreprecio a propósito:

- `sobreprecio` — el VALOR contra el mayorista. Es el que enseña la
  tarjeta, porque el titular ya es el valor y mezclar bases haría que el
  porcentaje no cuadre con la cifra de al lado.
- `sobreprecio_min` — la góndola más barata contra el mayorista. Es el que
  usa la **portada**, donde el número es un argumento delante de alguien
  que todavía no confía en el sitio: si hasta el más barato está +X%, no
  hay discusión. Dentro del mercado manda el otro, que describe en vez de
  argumentar.

### Los enlaces a la cadena salieron de la vista pública

Mandaban a la ficha del supermercado. El sitio terminaba siendo un embudo
hacia la góndola de otro —con seis destinos distintos por tarjeta— en vez
de la foto del mercado que dice ser.

**Las URL siguen en los datos, sin pintarse.** Son la herramienta de
verificación de la casa: sirven para auditar una cifra rara, no son un
botón para el visitante. Si alguna vez se pintan otra vez, que sea detrás
de sesión y para el dueño.

En su lugar cada tarjeta **cita la fuente**: qué cadena, de qué clase de
tienda y con qué alcance. Se dice UNA vez por tarjeta y no por fila —
repetir "Tienda en línea · Precio nacional, sin sucursal" trece veces
convertía la tarjeta en un muro y cada fila pasaba de una línea a cuatro.

### Por qué no hay sucursal (y no la va a haber por este camino)

Ninguna de estas cadenas publica precio por sucursal. Lo que se captura es
su **tienda en línea**, que cotiza un solo precio para todo el país.
Ponerle "Naco" o "Santiago" a esa cifra sería inventarlo. Se agregaron
`cadenas.sede` y `cadenas.alcance` para poder decir eso en la tarjeta en
vez de callarlo.

La única fuente con lugar físico real es la referencia mayorista: el
mostrador del **Mercado Nuevo, Santo Domingo**. Ya se cita al pie.

**La ubicación de verdad llega con los usuarios reales**, que la ponen en su
perfil. Eso está fuera de este cambio.

## Pendiente — identidad y ubicación cuando entren usuarios

Hay que resolverlo **antes** de abrir la publicación. Después de que haya
cuentas creadas es una migración.

- [ ] **Dos negocios con el mismo nombre.** Nada impide que entren tres
      "Finca El Cerro". Hoy `perfiles` tiene `nombre`, `negocio`,
      `provincia`, `municipio` y `verificado`, pero ninguna restricción de
      unicidad y nada que obligue a llenar la provincia. Las tres piezas
      que se discutieron: mostrar siempre provincia · municipio debajo del
      nombre, un identificador único permanente por vendedor con su propia
      página, y el badge de `verificado` — que existe en la tabla y hoy no
      lo pone nadie.
- [ ] **Puntos de venta compartidos.** Mucha gente no vende desde su finca
      sino desde un mercado donde vende **mucha gente a la vez** — el
      Mercado Nuevo en Santo Domingo es el caso obvio. Eso no es un campo
      de texto libre: si cada quien lo escribe a su manera, "Mercado
      Nuevo", "mercado nuevo SD" y "M. Nuevo" salen como tres lugares
      distintos y el filtro por ubicación deja de servir. Necesita una
      lista de plazas conocidas, con el mismo criterio que el mapa de
      alias de cultivos: escrita a mano, no adivinada.
- [ ] **Un vendedor puede estar en varios sitios.** Finca en Yamasá, puesto
      en el Mercado Nuevo los sábados. Un solo par provincia/municipio en
      `perfiles` no lo aguanta; probablemente sea una tabla aparte de
      puntos de venta.

---

## 2026-08-17 — El Mercado Nuevo entra como fuente

Victorius habló con alguien que trabaja con la **Asociación Dominicana
Mercaderes Unidos** (203 miembros, Mercado Nuevo de la Duarte) y consiguió
permiso del administrador del canal para publicar sus precios. Notas de
mercado en `MERCADO-NUEVO.md`, vocabulario en `GLOSARIO.md`, transcripción
del día en `archivo/2026/08/17/`.

### Es una FUENTE, no un vendedor

El gremio no vende: reporta a cómo está vendiendo la plaza. Todo el diseño
sale de ahí. `perfiles.tipo` gana `'asociacion'`, la tarjeta dice "Reporta
la plaza · no vende", la métrica de arriba es a cuánta gente representa, y
en el registro de fuentes lleva `tipo: 'gremio'` para que **no** aparezca
como pastilla de filtro en el mercado — una pastilla le prometería al
usuario que puede comprarle.

### Cómo se resolvió "muchos artículos, un solo usuario"

Con el **parte del día**: catorce rubros publicados una mañana son UNA cosa,
no catorce anuncios con el mismo nombre repetido. La tarjeta es el rubro y
adentro va la escalera de calidad. Es la misma solución que se aplicó al
mercado cuando repetía "Ají" trece veces.

### Los datos van en tres archivos, no en uno

Los rubros vuelven todos los días y lo único que cambia es el precio y la
foto, así que:

- `data/gremio-rubros.json` — lo estable: nombre, unidad, libras, foto de
  respaldo.
- `data/partes/<fecha>.json` — lo del día: precio y foto.
- `data/partes.json` — el índice; la página carga el más reciente sola.

Publicar el parte de mañana es escribir un archivo de precios. No hay que
volver a tocar nombres ni unidades, y los partes viejos quedan intactos.

### Lo que hubo que aprender del mercado

- **El precio es un RANGO con escalera de calidad**, nunca un número.
  Primera, segunda, tercera. `parte_items` guarda `precio_min`/`precio_max`
  siempre; cuando dan un solo número, min = max y se ve.
- **Calidad y procedencia son ejes DISTINTOS.** Barahonero, azuano, maeño y
  mocano no son variedades: son las zonas donde se produjo. Un plátano puede
  ser barahonero de tercera.
- **Solo se compara el grado alto contra la góndola.** El tomate "regular"
  del gremio contra el supermercado daba +746%, pero el supermercado no
  vende tomate regular. Contra prímium da +370%, que es defendible.
- **El informe del Ministerio publica la unidad mayorista canónica** de cada
  rubro. Con esa tabla, "Bugalu primiun 500/400" pasa a ser RD$8.89–11.11/lb
  y se vuelve comparable. Las tres unidades que el gremio sí declaró cuadran
  exactamente con ella.

## Pendiente del gremio

- [ ] **Siete preguntas de unidades** listadas al final de `GLOSARIO.md`. La
      más importante: si `500/400` es rango alto/bajo o primera/segunda. Sin
      eso, la lista reenviada de la Asociación de Mayoristas de Vegetales no
      se puede comparar.
- [ ] **Confirmar la papa.** El mensaje de las 8:35 AM no dijo qué producto
      era; se identificó por la foto (sacos amarillos de papa, con los de
      cebolla roja al lado). El precio se publicó con esa lectura.
- [ ] **Que el parte entre solo.** Hoy se transcribe a mano de capturas de
      pantalla. El gremio publica a lo largo de la mañana, así que lo que se
      quiere es que los precios entren según van saliendo, no una foto del
      día completo a las 9 PM.
- [ ] **Que publiquen los propios vendedores.** El objetivo real: que cada
      mayorista del Mercado Nuevo suba su precio y quien va al mercado
      llegue sabiendo. Ojo con lo que advirtió el gremio — "la mayoría de
      comerciantes no le gusta que se publiquen los precios"— y con
      `ESCALA.md`: la lista no puede ordenarse por precio ni premiar al más
      barato, o los pone a competir a la baja entre ellos. La entrada es la
      ASOCIACIÓN, no el comerciante suelto.
