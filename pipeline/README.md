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

## Fotos

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
