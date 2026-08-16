# Notas: qué falta, qué está roto, qué hay que decidir

Lista viva. Se edita a mano. Lo que se resuelve se marca con `[x]` y se deja
un rato antes de borrarlo, para no volver a discutir lo mismo.

Las decisiones de fondo sobre el mercado con productores están en
`ESCALA.md`. Esto es la lista de pendientes concretos.

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
