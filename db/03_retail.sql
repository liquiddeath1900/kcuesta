-- ============================================================
-- Kcuesta — capa de retail y normalización de nombres
-- Ejecutar después de 02_rls.
--
-- Por qué una tabla aparte y no ensanchar precios_oficiales:
-- precios_oficiales tiene grano CULTIVO (plátano barahonero, mayorista, hoy).
-- El supermercado tiene grano SKU (una referencia concreta, con su foto, su
-- empaque y su código interno). Mezclarlos rompe el unique de la serie
-- oficial y ensucia el índice. Son dos granos distintos: dos tablas.
-- ============================================================

-- ------------------------------------------------------------
-- Cadenas de las que capturamos precio.
-- ------------------------------------------------------------
create table cadenas (
  id              text primary key,              -- 'sirena', 'nacional'
  nombre          text not null,
  tipo            text not null check (tipo in ('supermercado','mayorista_online')),
  url             text not null,
  metodo          text not null check (metodo in ('api','firecrawl')),
  -- De DÓNDE sale el precio, para poder citarlo en la tarjeta. Ninguna de
  -- estas cadenas publica precio por sucursal: lo que se captura es su
  -- tienda en línea, que cotiza un solo precio para todo el país. Escribir
  -- "Naco" o "Santiago" al lado de una de estas cifras sería inventarlo.
  sede            text not null default 'Tienda en línea',
  alcance         text not null default 'Precio nacional, sin sucursal',
  activo          boolean not null default true,
  creado          timestamptz not null default now()
);
comment on column cadenas.metodo is
  'api = endpoint JSON abierto y estable. firecrawl = requiere render de '
  'navegador; cuesta créditos y se rompe con cada rediseño.';

insert into cadenas (id, nombre, tipo, url, metodo, sede, alcance) values
  ('sirena',      'La Sirena',                'supermercado',     'https://www.sirena.do',            'api',
     'Tienda en línea',           'Precio nacional, sin sucursal'),
  ('nacional',    'Supermercados Nacional',   'supermercado',     'https://supermercadosnacional.com','api',
     'Tienda en línea',           'Precio nacional, sin sucursal'),
  ('fruttissimo', 'Fruttissimo Market',       'supermercado',     'https://fruttissimodr.com',        'api',
     'Tienda en línea',           'Precio nacional, sin sucursal'),
  ('jumbo',       'Jumbo',                    'supermercado',     'https://www.jumbo.com.do',         'firecrawl',
     'Tienda en línea',           'Precio nacional, sin sucursal'),
  ('plaza-lama',  'Plaza Lama',               'supermercado',     'https://www.plazalama.com.do',     'firecrawl',
     'Tienda en línea',           'Precio nacional, sin sucursal'),
  ('pricesmart',  'PriceSmart',               'supermercado',     'https://www.pricesmart.com/es-do', 'firecrawl',
     'Tienda en línea (socios)',  'Precio nacional, sin sucursal'),
  ('agroexpress', 'AgroExpress RD',           'mayorista_online', 'https://agroexpressrd.com',        'firecrawl',
     'Mayorista en línea',        'Precio nacional, sin sucursal');

-- ------------------------------------------------------------
-- ALIAS DE CULTIVO — el punto donde todo se cae si se hace mal.
--
-- La misma cosa se llama distinto en cada fuente:
--   'PLATANO VERDE'              (MERCADOM, mayúsculas sin tilde)
--   'Platano Verde Und'          (Sirena, con empaque pegado)
--   'Plátano (Barahona), grande' (Ministerio, calidad entre paréntesis)
-- Sin esta tabla, cada fuente produce un cultivo distinto y el promedio
-- deja de significar algo. Se llena A MANO desde la lista de no-mapeados
-- que imprime la corrida en seco. NO adivinar con fuzzy match.
-- ------------------------------------------------------------
create table cultivo_alias (
  alias           text primary key,              -- minúsculas, sin tildes, sin puntuación
  cultivo_id      text not null references cultivos(id) on delete cascade,
  origen          text not null,                 -- 'mercadom', 'sirena', 'manual'
  confianza       text not null default 'alta' check (confianza in ('alta','media')),
  creado          timestamptz not null default now()
);
create index on cultivo_alias (cultivo_id);

-- ------------------------------------------------------------
-- Un producto concreto de una cadena. Vive entre capturas: el precio
-- cambia a diario, el producto no.
-- ------------------------------------------------------------
create table productos_retail (
  id              bigserial primary key,
  cadena_id       text not null references cadenas(id) on delete cascade,
  sku_externo     text not null,                 -- id del producto EN la cadena
  nombre_externo  text not null,                 -- tal cual lo publica la cadena
  cultivo_id      text references cultivos(id),  -- NULL hasta que el alias lo resuelva
  categoria_externa text,
  unidad_externa  text,                          -- 'un', 'lb', 'kg'
  url_producto    text,

  -- Fotos. Ver 04_storage.sql para el bucket y la política.
  foto_url        text,                          -- ruta en Storage, ya nuestra
  foto_origen_url text,                          -- de dónde salió
  foto_fuente     text,                          -- nombre de la cadena, para el crédito
  foto_estado     text not null default 'pendiente'
                    check (foto_estado in ('pendiente','aprobada','rechazada')),
  foto_motivo     text,                          -- por qué se rechazó

  visto_primero   timestamptz not null default now(),
  visto_ultimo    timestamptz not null default now(),
  unique (cadena_id, sku_externo)
);
create index on productos_retail (cultivo_id);
create index on productos_retail (cadena_id, cultivo_id);
comment on column productos_retail.foto_estado is
  'Ninguna foto se sirve en pendiente. La regla es: espejamos fotografía de '
  'producto limpia; lo que trae marca de agua o logo encima se deja quieto y '
  'la tarjeta cae al banco Creative Commons de assets/img/.';

-- ------------------------------------------------------------
-- Serie de precio por SKU. Una fila por producto y día.
-- ------------------------------------------------------------
create table precios_retail (
  id              bigserial primary key,
  producto_retail_id bigint not null references productos_retail(id) on delete cascade,
  fecha           date not null,
  capturado       timestamptz not null default now(),
  precio          numeric(12,2) not null check (precio >= 0),
  precio_lista    numeric(12,2) check (precio_lista >= 0),  -- antes de descuento
  disponible      boolean not null default true,
  unique (producto_retail_id, fecha)
);
create index on precios_retail (producto_retail_id, fecha desc);
create index on precios_retail (fecha desc);

-- ------------------------------------------------------------
-- Bitácora de capturas. Sin esto no hay forma de saber que una fuente
-- lleva tres semanas fallando en silencio.
-- ------------------------------------------------------------
create table capturas (
  id              bigserial primary key,
  fuente          text not null,                 -- 'mercadom', 'sirena', 'ckan'
  fecha           date not null default current_date,
  iniciado        timestamptz not null default now(),
  terminado       timestamptz,
  estado          text not null default 'corriendo'
                    check (estado in ('corriendo','ok','fallo','vacio')),
  filas           integer not null default 0,
  no_mapeados     integer not null default 0,
  artefacto       text,                          -- ruta en archivo/YYYY/MM/DD/
  error           text
);
create index on capturas (fuente, fecha desc);
create index on capturas (fecha desc);
comment on table capturas is
  'MERCADOM sobrescribe un solo archivo sin histórico. Si esta tabla muestra '
  'un hueco, ese día se perdió para siempre — no se puede volver a pedir.';
