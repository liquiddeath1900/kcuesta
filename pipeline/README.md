# Pipeline de precios

Captura los precios agrícolas de todas las fuentes públicas dominicanas, los
guarda en Supabase y regenera los JSON que sirve el sitio.

## Por qué corre a diario

MERCADOM publica en una sola ranura que se sobrescribe. No hay histórico, no
hay archivo, no se puede pedir el de ayer. **El día que esto no corra, ese día
se pierde para siempre.** Por eso cada fuente corre aislada y el archivo crudo
se guarda en disco *antes* de intentar interpretarlo.

## Fuentes

| Fuente | Acceso | Qué da |
|---|---|---|
| MERCADOM | PDF en `?download=11:precios` | Diario. Mayor y detalle de ~34 rubros |
| Ministerio de Agricultura | PDF interdiario | Mayorista + 6 mercados minoristas + supermercado + colmados |
| datos.gob.do (CKAN) | CSV | Serie histórica 2017→, ~44 mil filas. Rezago de ~1 mes |
| La Sirena | API VTEX | SKU, precio, unidad, foto |
| Supermercados Nacional | GraphQL de Magento | SKU, precio, foto |
| Fruttissimo | Store API de WooCommerce | SKU, precio, foto |
| Jumbo, Plaza Lama, PriceSmart, AgroExpress | Firecrawl | Sin API abierta |

Ninguna publica **precio en finca**. Ese hueco es el producto: cada cosecha
que se publique en Kcuesta es un dato que no existe en ningún otro lado.

### Aparte: el IPC del Banco Central

`pipeline/ipc.py` no entra en `pipeline.run` y no toca ninguna tabla de
precios. Baja el Excel mensual del **Índice de Precios al Consumidor por
artículos** y escribe `data/ipc.json`, que solo lee `inflacion.html`.

Corre aparte porque **no es un precio**: es un índice base octubre 2019 –
septiembre 2020 = 100, de precio al **consumidor** (colmado y supermercado,
promedio nacional). Si entrara por el mismo camino que MERCADOM, tarde o
temprano un 228.5 de yuca acabaría pintado como RD$228.50 en una tarjeta.
Tampoco se puede restar contra el parte del Mercado Nuevo: son dos varas.

Lo que sí aporta: la tendencia larga (seis años), la temporada de cada rubro
—en qué meses suele aflojar el precio— y la **ponderación**, que dice cuánto
pesa cada rubro en el gasto del hogar dominicano y por lo tanto a cuáles
conviene darles los mejores datos primero.

De los 364 artículos de la canasta solo entran los ~35 que son cosecha, con
un mapa escrito a mano por la misma razón que el de cultivos: el IPC tiene
un solo «Ajíes» donde Kcuesta tiene cuatro ajíes, y un solo «Aguacate» donde
tenemos benny, carla, criollo y popenoe. Por eso el número es del rubro
entero y **no se le puede colgar a una variedad**.

```bash
python -m pipeline.ipc            # baja el Excel y regenera data/ipc.json
python -m pipeline.ipc --local    # reusa el que ya está en archivo/bcrd/
```

## Uso

```bash
pip install -r pipeline/requirements.txt      # necesita también poppler-utils
export SUPABASE_SERVICE_KEY=...

python -m pipeline.run --seco                 # no escribe; imprime no mapeados
python -m pipeline.run                        # captura, carga, exporta
python -m pipeline.run --fuente=mercadom      # una sola fuente
python -m pipeline.run --sin-base             # exporta sin Supabase
python -m pipeline.fotos --revisar            # hoja de contactos de fotos
python -m pytest pipeline/pruebas -q
```

`--sin-base` es la salida de emergencia: si Supabase está pausado el día que
toca capturar, igual se descarga MERCADOM, se archiva y se regenera el sitio.

## El mapeo de nombres es la parte frágil

El mismo plátano llega como `PLATANO VERDE`, `Platano Verde Und` y
`Plátano (Barahona), grande`. `normalizar.clave()` los canoniza y
`data/alias.json` los amarra a un `cultivo_id`.

**Ese archivo se escribe a mano, a propósito.** Emparejar por parecido de
cadena junta *ají cubanela* con *ají gustoso*, que son precios distintos. Un
alias equivocado mete un precio ajeno en la serie y nadie lo nota; un hueco sí
se ve. Lo que no está mapeado se reporta y se queda fuera.

Cuando una fuente estrene un rubro:

1. `python -m pipeline.run --seco` y mirar la lista de no mapeados
2. Si es un cultivo nuevo, agregarlo a `data/cultivos_extra.json`
3. Amarrar sus nombres en `data/alias.json`
4. Repetir hasta que la lista quede en cero

## Cómo se muestra el mercado

Una tarjeta por **rubro**, no por oferta. 147 ofertas son 43 rubros: el arroz
selecto trae 15 y el ají morrón 13, y en lista plana la página repetía "Ají"
trece veces seguidas.

La tarjeta cerrada carga la decisión completa —mejor precio, cuántas tiendas,
el rango y el sobreprecio contra el mayorista— y se abre con `<details>`
nativo, que ya trae semántica de botón y estado para lectores de pantalla sin
una línea de ARIA. Los rubros de una sola tienda usan la misma cáscara sin
control, para que no parezcan datos rotos.

Dos ejes sobre los mismos datos, porque son dos preguntas distintas:

- **Por rubro** — "¿a cómo está el ají?" Comparación entre cadenas.
- **Por vendedor** — "¿qué tiene este vendedor?" Cuando entren productores,
  una finca con plátano, yuca y ají cae aquí sin cambiar nada.

### Todo se compara por libra

`normalizar.libras_de_titulo()` saca el peso del empaque del nombre del
producto. Sin eso la comparación miente: la cebolla suelta a RD$46 la libra y
el saco de 50 lb a RD$10,750 daban un rango de "RD$46 – RD$10,750", como si el
saco fuera 234 veces más caro. Por libra son RD$46 contra RD$215 — más caro
igual, pero 4.7 veces.

Cuando el título no dice cuánto trae, devuelve `None` y esa oferta se muestra
sin comparar. Igual que con las unidades del mayorista: un hueco se ve, un
supuesto no.

Los porcentajes se reservan para el mayorista, donde son grandes y cuentan la
historia (+161% el tomate). Entre cadenas la diferencia es de RD$4 a RD$25 y
ahí va en pesos por libra, porque un "+7%" no dice nada.

## Fotos de cultivo

`python -m pipeline.imagenes` baja una foto por cultivo de Wikimedia Commons
buscando por **binomio científico**. El banco viejo tenía 16 fotos para 81
cultivos, así que `habichuela.jpg` salía en 47 tarjetas y `aji.jpg` en 31.

Dos cosas se aprendieron mirando la primera tanda, no leyendo la API:

1. **La categoría no basta.** Con el bono de categoría por encima del castigo,
   los cuatro aguacates salieron con la misma foto de un árbol lejano.
   CREDITOS.md pide "el producto de cerca, no el paisaje", así que
   `tree/plant/field/flower` ahora resta más de lo que cualquier bono suma.
2. **Hay que deduplicar.** Cuatro aguacates comparten *Persea americana*, así
   que compartían el primer candidato. Ningún archivo se usa dos veces.

Commons exige un User-Agent con contacto y tumba con 429 al cliente genérico
de requests; va con pausa de 1.1s y reintento exponencial.

`--hoja` arma una hoja de contactos para revisar a ojo. **Hace falta**: la
búsqueda por texto devuelve basura con confianza — un candidato de aguacate
era "Huskies by the Congo River enjoying the shade of the Avocado Tree".

## Fotos de supermercado

Regla: **se espeja fotografía de producto limpia; lo que trae marca de agua o
logo encima se deja quieto.** Tres capas:

1. **Categoría** — solo fresco a granel. El arroz o el huevo se capturan de
   precio pero su foto es el saco o el cartón de marca: ni se descargan.
2. **Heurística** — se miran las esquinas. Dos o más con varianza alta sobre
   fondo plano huele a sello o badge, y se marca `rechazada`.
3. **Ojo humano** — nada se sirve en `pendiente`. `--revisar` arma una hoja de
   contactos para aprobar el primer lote de una pasada.

Mientras una foto no esté `aprobada`, la tarjeta usa el banco Creative Commons
de `assets/img/` (créditos en `assets/img/CREDITOS.md`). `USAR_FOTOS_RETAIL=false`
revierte todo a CC sin tocar código.

## Puesta en marcha (pendiente)

Tres pasos, todos requieren manos:

1. **Aplicar el esquema.** En el editor SQL de Supabase, correr `db/03_retail.sql`
   y luego `db/04_retail_rls.sql`. Crean las tablas de retail, sus políticas y el
   bucket `retail-fotos`.
2. **Instalar el workflow.** `pipeline/precios.workflow.yml` va copiado a
   `.github/workflows/precios.yml`. Vive aquí y no allá porque el token de
   acceso de esta máquina no tiene alcance `workflow` y GitHub rechaza el push;
   se sube desde la web o con un token que sí lo tenga.
3. **Cargar los secretos** del repo: `SUPABASE_URL`, `SUPABASE_SERVICE_KEY` y
   `FIRECRAWL_API_KEY`.

Mientras tanto, `python -m pipeline.run --sin-base` regenera el sitio sin tocar
Supabase.

## Tablas

- `precios_oficiales` — serie oficial, grano de cultivo. Ya existía.
- `productos_retail` / `precios_retail` — grano de SKU, con foto y cadena.
- `cultivo_alias` — mapeo de nombres, editable desde la base.
- `capturas` — bitácora. Un hueco aquí es un día de MERCADOM perdido.

Todas se leen en público y **solo `service_role` escribe**, por ausencia de
política de INSERT. Es más difícil de romper por accidente que una política
permisiva mal escrita: en Postgres las políticas permisivas se suman con OR,
así que una de deny no sirve de nada mientras exista una permisiva.
