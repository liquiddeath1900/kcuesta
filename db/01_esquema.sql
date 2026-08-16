-- ============================================================
-- Kcuesta — esquema base
-- Postgres / Supabase. Ejecutar en orden: 01_esquema → 02_rls → 03_semilla
--
-- Principio de seguridad: el gateo NO ocurre en el navegador.
-- Las páginas públicas pueden renderizarse estáticamente porque RLS decide
-- en la base de datos quién ve el contacto de un vendedor.
-- ============================================================

create extension if not exists "pgcrypto";

-- ------------------------------------------------------------
-- Catálogo de cultivos. La unidad de venta vive AQUÍ, no en el anuncio:
-- el plátano se cotiza por millar, la yuca por quintal, el tomate por
-- huacal de 45 lb. Promediar sin normalizar por unidad no significa nada.
-- ------------------------------------------------------------
create table cultivos (
  id              text primary key,              -- 'platano-barahonero'
  nombre          text not null,
  calidad         text,                          -- 'Grande', 'Primera'
  categoria       text not null check (categoria in ('viveres','vegetales','frutas','granos','pecuario')),
  unidad_venta    text not null,                 -- 'Millar', 'Quintal', 'Huacal de 45 lb'
  unidades_por_empaque numeric,                  -- 1000 para millar, 100 para quintal
  libras_por_empaque   numeric,                  -- para normalizar entre empaques
  activo          boolean not null default true,
  creado          timestamptz not null default now()
);
comment on column cultivos.unidades_por_empaque is
  'Divisor para normalizar precio por unidad comparable. Crítico para el índice.';

-- ------------------------------------------------------------
-- Precios oficiales (Ministerio de Agricultura / MERCADOM).
-- Se captura A DIARIO porque MERCADOM sobrescribe un solo archivo sin
-- histórico: lo que no se guarde hoy se pierde para siempre.
-- ------------------------------------------------------------
create table precios_oficiales (
  id              bigserial primary key,
  cultivo_id      text not null references cultivos(id),
  fecha           date not null,                 -- fecha del DATO, no de la captura
  capturado       timestamptz not null default now(),
  nivel           text not null check (nivel in ('mayorista','minorista','supermercado','colmado','finca')),
  unidad          text not null,
  precio          numeric(12,2) not null check (precio >= 0),
  precio_por_unidad numeric(12,4),               -- normalizado
  fuente          text not null,                 -- 'Ministerio de Agricultura'
  fuente_url      text not null,
  unique (cultivo_id, fecha, nivel, unidad)
);
create index on precios_oficiales (cultivo_id, fecha desc);
comment on table precios_oficiales is
  'Serie oficial. Nótese que nivel=''finca'' NO existe en ninguna fuente pública '
  'dominicana — esa columna la llenará Kcuesta con datos propios.';

-- ------------------------------------------------------------
-- PERFILES — dividido en dos tablas a propósito.
-- Postgres RLS es por FILA, no por columna. Separar el contacto en su
-- propia tabla es la forma robusta de que un anónimo vea el anuncio
-- pero jamás el teléfono, sin depender de vistas ni SECURITY DEFINER.
-- ------------------------------------------------------------
create table perfiles (                          -- PÚBLICO
  id              uuid primary key references auth.users(id) on delete cascade,
  tipo            text not null default 'comprador'
                    check (tipo in ('comprador','vendedor','ambos')),
  nombre          text not null,
  negocio         text,                          -- 'Finca La Esperanza'
  provincia       text,
  municipio       text,
  tareas          integer check (tareas >= 0),
  cultivos        text[] default '{}',
  verificado      boolean not null default false,
  verificado_en   timestamptz,
  creado          timestamptz not null default now(),
  actualizado     timestamptz not null default now()
);

create table perfiles_contacto (                 -- PRIVADO
  id              uuid primary key references perfiles(id) on delete cascade,
  telefono        text,
  whatsapp        text,
  email           text,
  metodo_registro text check (metodo_registro in ('google','telefono','email')),
  creado          timestamptz not null default now()
);
comment on table perfiles_contacto is
  'Nunca legible por anónimos. Solo el dueño y la contraparte de una '
  'conversación abierta.';

-- ------------------------------------------------------------
-- Bitácora de accesos — el usuario pidió saber quién entra.
-- ------------------------------------------------------------
create table auth_eventos (
  id              bigserial primary key,
  user_id         uuid references auth.users(id) on delete set null,
  evento          text not null,                 -- 'login','signup','logout'
  metodo          text,                          -- 'google','telefono'
  ip              inet,
  user_agent      text,
  creado          timestamptz not null default now()
);
create index on auth_eventos (user_id, creado desc);
create index on auth_eventos (creado desc);

-- ------------------------------------------------------------
-- ANUNCIOS
-- ------------------------------------------------------------
create table anuncios (
  id              uuid primary key default gen_random_uuid(),
  vendedor_id     uuid not null references perfiles(id) on delete cascade,
  cultivo_id      text not null references cultivos(id),
  titulo          text not null,
  calidad         text not null default 'Primera'
                    check (calidad in ('Primera','Segunda','Rabiza')),
  cantidad        numeric(12,2) not null check (cantidad > 0),
  unidad_venta    text not null,
  precio          numeric(12,2) not null check (precio >= 0),
  precio_por_unidad numeric(12,4) not null,      -- comparable contra el oficial
  entrega         text not null default 'Puesto en finca',
  pago            text not null default 'Al contado',
  provincia       text not null,
  municipio       text,
  corte           date,
  corte_texto     text,
  nota            text,
  foto_url        text,
  estado          text not null default 'activo'
                    check (estado in ('activo','vendido','vencido','retirado')),
  publicado       timestamptz not null default now(),
  actualizado     timestamptz not null default now(),
  confirmado      timestamptz not null default now()  -- último "sigue igual"
);
create index on anuncios (estado, publicado desc);
create index on anuncios (cultivo_id, estado);
create index on anuncios (provincia, estado);
comment on column anuncios.confirmado is
  'Cuándo el vendedor confirmó por última vez que el precio sigue vigente. '
  'La tarjeta muestra "Precio de hace N días" a partir de aquí. Un precio '
  'sin confirmar NO significa que esté errado — puede ser un mercado quieto.';

-- ------------------------------------------------------------
-- VENTAS — la confirmación posterior. Un precio pedido NO es un precio
-- pagado; sin esto el índice mide optimismo, no mercado.
-- ------------------------------------------------------------
create table ventas (
  id              uuid primary key default gen_random_uuid(),
  anuncio_id      uuid not null references anuncios(id) on delete cascade,
  vendedor_id     uuid not null references perfiles(id) on delete cascade,
  comprador_id    uuid references perfiles(id) on delete set null,
  se_vendio       boolean not null,
  precio_final    numeric(12,2) check (precio_final >= 0),
  precio_final_por_unidad numeric(12,4),
  cantidad_vendida numeric(12,2),
  fecha           date not null default current_date,
  creado          timestamptz not null default now()
);
create index on ventas (anuncio_id);
create index on ventas (fecha desc);

-- ------------------------------------------------------------
-- MENSAJERÍA
-- ------------------------------------------------------------
create table conversaciones (
  id              uuid primary key default gen_random_uuid(),
  anuncio_id      uuid not null references anuncios(id) on delete cascade,
  comprador_id    uuid not null references perfiles(id) on delete cascade,
  vendedor_id     uuid not null references perfiles(id) on delete cascade,
  creada          timestamptz not null default now(),
  ultimo_mensaje  timestamptz not null default now(),
  unique (anuncio_id, comprador_id)
);
create index on conversaciones (comprador_id, ultimo_mensaje desc);
create index on conversaciones (vendedor_id, ultimo_mensaje desc);

create table mensajes (
  id              uuid primary key default gen_random_uuid(),
  conversacion_id uuid not null references conversaciones(id) on delete cascade,
  autor_id        uuid not null references perfiles(id) on delete cascade,
  cuerpo          text not null check (length(cuerpo) between 1 and 4000),
  leido           boolean not null default false,
  creado          timestamptz not null default now()
);
create index on mensajes (conversacion_id, creado);

-- ------------------------------------------------------------
-- ÍNDICE DE PRECIOS — la joya escondida.
-- Dos series distintas y honestas:
--   oferta  = lo que se pide  (grueso, inmediato)
--   cerrado = lo que se pagó  (delgado, real)
-- No se publica ninguna cifra por debajo de n_minimo.
-- ------------------------------------------------------------
create table indice_config (
  clave           text primary key,
  valor           numeric not null,
  nota            text
);
insert into indice_config (clave, valor, nota) values
  ('n_minimo_oferta',   5, 'Anuncios mínimos por cultivo antes de publicar el índice de oferta'),
  ('n_minimo_cerrado',  3, 'Ventas confirmadas mínimas antes de publicar precio cerrado'),
  ('ventana_dias',     14, 'Ventana móvil de cálculo'),
  ('recorte_pct',      10, 'Porcentaje recortado en cada cola contra valores atípicos');

create table indice_precios (
  id              bigserial primary key,
  cultivo_id      text not null references cultivos(id),
  fecha           date not null,
  serie           text not null check (serie in ('oferta','cerrado')),
  n               integer not null check (n >= 0),
  mediana         numeric(12,4),
  p25             numeric(12,4),
  p75             numeric(12,4),
  publicable      boolean not null default false,  -- n >= n_minimo
  calculado       timestamptz not null default now(),
  unique (cultivo_id, fecha, serie)
);
create index on indice_precios (cultivo_id, serie, fecha desc);
comment on table indice_precios is
  'Serie propia de Kcuesta. Es el único dato de precio en finca que existe '
  'en el país: el Estado mide mayorista, minorista, supermercado, colmado '
  'y carnicería — nunca la finca.';

-- ------------------------------------------------------------
-- Disparadores de mantenimiento
-- ------------------------------------------------------------
create or replace function tocar_actualizado() returns trigger
language plpgsql as $$
begin
  new.actualizado := now();
  return new;
end $$;

create trigger t_anuncios_actualizado before update on anuncios
  for each row execute function tocar_actualizado();
create trigger t_perfiles_actualizado before update on perfiles
  for each row execute function tocar_actualizado();

create or replace function tocar_conversacion() returns trigger
language plpgsql as $$
begin
  update conversaciones set ultimo_mensaje = now() where id = new.conversacion_id;
  return new;
end $$;

create trigger t_mensaje_nuevo after insert on mensajes
  for each row execute function tocar_conversacion();
