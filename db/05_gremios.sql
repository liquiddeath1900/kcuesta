-- ============================================================
-- Kcuesta — plazas, gremios y partes de precio
-- Ejecutar después de 04_retail_rls.
--
-- Sale de hablar con alguien que trabaja en el Mercado Nuevo (notas en
-- MERCADO-NUEVO.md, vocabulario en GLOSARIO.md). Tres cosas que el esquema
-- de hoy no puede representar y que hay que resolver ANTES de abrir la
-- publicación, porque después son migración:
--
--   1. Quien reporta no siempre vende. La Asociación Dominicana Mercaderes
--      Unidos publica todos los días los precios de la plaza a 203
--      miembros, y NO vende nada. Modelarla como 'vendedor' haría que el
--      sitio dijera que ella vende chinola a 12–14. Vende la plaza.
--   2. El precio de campo es un RANGO con escalera de calidad, nunca un
--      número. "Chinola de primera entre 12 y 14, segunda 8 10, tercera
--      5 7". Un solo `precio numeric` no lo aguanta.
--   3. Mucha gente vende desde un sitio COMPARTIDO. Si cada quien escribe
--      dónde, "Mercado Nuevo", "mercado nuevo SD" y "M. Nuevo" salen como
--      tres lugares y el filtro por ubicación deja de servir.
-- ============================================================

-- ------------------------------------------------------------
-- PLAZAS — lista curada, nunca texto libre.
--
-- Mismo criterio que el mapa de alias de cultivos: escrita a mano. Un
-- desplegable con 30 plazas conocidas más "otro lugar" da un dato que se
-- puede filtrar; un campo de texto da basura desde el primer día.
-- ------------------------------------------------------------
create table plazas (
  id              text primary key,              -- 'mercado-nuevo'
  nombre          text not null,                 -- 'Mercado Nuevo de la Duarte'
  alias           text[] not null default '{}',  -- cómo más le dicen
  provincia       text not null,
  municipio       text,
  tipo            text not null check (tipo in ('mercado','merca','finca','colmado','otro')),
  -- Un mercado donde venden cientos de personas NO es la dirección de un
  -- vendedor: es un lugar compartido. La diferencia importa para la
  -- privacidad —publicar "vende en el Mercado Nuevo" no ubica a nadie en
  -- particular— y para el filtro.
  compartida      boolean not null default false,
  activo          boolean not null default true,
  creado          timestamptz not null default now()
);
comment on column plazas.alias is
  'Las formas en que la gente la escribe. Se usan para emparejar al leer, '
  'nunca para mostrar: la tarjeta enseña siempre el nombre canónico.';

insert into plazas (id, nombre, alias, provincia, municipio, tipo, compartida) values
  ('mercado-nuevo', 'Mercado Nuevo de la Duarte',
     array['Mercado Nuevo','mercado nuevo','M. Nuevo','Mercado Nuevo SD','Nuevo de la Duarte'],
     'Santo Domingo', 'Santo Domingo Norte', 'mercado', true),
  ('merca-santo-domingo', 'Merca Santo Domingo',
     array['MERCADOM','Merca SD','Mercadom'],
     'Santo Domingo', 'Santo Domingo Norte', 'merca', true),
  ('conaprope', 'Mercado CONAPROPE', array['Conaprope'],
     'Distrito Nacional', null, 'mercado', true),
  ('los-mina', 'Mercado de Los Mina', array['Los Mina'],
     'Santo Domingo', 'Santo Domingo Este', 'mercado', true),
  ('villa-consuelo', 'Mercado de Villa Consuelo', array['Villa Consuelo'],
     'Distrito Nacional', null, 'mercado', true),
  ('cristo-rey', 'Mercado de Cristo Rey', array['Cristo Rey'],
     'Distrito Nacional', null, 'mercado', true);

-- ------------------------------------------------------------
-- El tipo de perfil crece: hay quien REPORTA sin vender.
-- ------------------------------------------------------------
alter table perfiles drop constraint if exists perfiles_tipo_check;
alter table perfiles add constraint perfiles_tipo_check
  check (tipo in ('comprador','vendedor','ambos','asociacion'));

comment on column perfiles.tipo is
  'asociacion = gremio o asociación que publica los precios de una plaza '
  'sin vender. Su tarjeta dice "reporta", nunca "vende": la Asociación '
  'Mercaderes Unidos no vende chinola, informa a cómo la está vendiendo '
  'la plaza.';

-- Cuántos representan. Es su autoridad, y es lo que hay que enseñar en la
-- tarjeta de un gremio en vez del número de artículos.
alter table perfiles add column if not exists miembros integer
  check (miembros is null or miembros >= 0);
alter table perfiles add column if not exists plaza_id text references plazas(id);

-- ------------------------------------------------------------
-- PARTES — el reporte de un día.
--
-- La unidad no es "un anuncio": es el parte del día completo. La asociación
-- publica catorce rubros cada mañana y eso es UNA cosa, no catorce cosas
-- sueltas de un mismo usuario. Así se resuelve enseñar muchos productos de
-- un solo perfil sin que la página repita su nombre catorce veces, que es
-- el mismo problema que ya se resolvió agrupando el mercado por rubro.
-- ------------------------------------------------------------
create table partes (
  id              bigserial primary key,
  perfil_id       uuid not null references perfiles(id) on delete cascade,
  plaza_id        text not null references plazas(id),
  fecha           date not null,                 -- fecha del DATO
  capturado       timestamptz not null default now(),
  nivel           text not null default 'mayorista'
                    check (nivel in ('mayorista','minorista','finca')),
  nota            text,
  -- Un parte no se publica solo. Los precios de un gremio son suyos y hay
  -- que tener permiso: 'borrador' es lo que se le enseña a ellos antes de
  -- pedirlo. Ver MERCADO-NUEVO.md §5.
  estado          text not null default 'borrador'
                    check (estado in ('borrador','publicado','retirado')),
  unique (perfil_id, plaza_id, fecha)
);
create index on partes (fecha desc, estado);

-- ------------------------------------------------------------
-- ITEMS DEL PARTE — un rubro, un grado, un rango.
--
-- El precio va SIEMPRE como rango. No es un lujo del modelo: es como habla
-- el mercado, y lo explicaron ellos mismos. "Cundo digo que un producto
-- ronda entre 10 y 15 es que ese es el rango de precio hay que recordar
-- que el mercado nuevo de la Duarte hay cientos de vendedores y muchos
-- mayoristas qué venden según la calidad y dependiendo de la plaza."
-- Cuando dan un solo número, min = max, y se ve que fue un solo número.
-- ------------------------------------------------------------
create table parte_items (
  id              bigserial primary key,
  parte_id        bigint not null references partes(id) on delete cascade,
  cultivo_id      text not null references cultivos(id),

  -- EJE 1: calidad. Un plátano de primera a 18 y uno de tercera a 7 no son
  -- un mercado con 157% de dispersión: son dos productos. Mezclarlos en una
  -- mediana es el mismo error que mezclar la libra suelta con el saco de 50.
  calidad         text check (calidad in ('primera','segunda','tercera','premium','regular')),

  -- EJE 2: procedencia. Barahonero, azuano, maeño y mocano NO son
  -- variedades, son las zonas donde se produjo. Un plátano puede ser
  -- barahonero DE TERCERA: son ejes independientes y en el mismo campo se
  -- vuelven incomparables.
  procedencia     text,

  unidad          text not null,                 -- 'Saco/50 lb', 'Unidad', 'Quintal'
  libras_unidad   numeric,                       -- para normalizar; null = no declarada
  precio_min      numeric(12,2) not null check (precio_min >= 0),
  precio_max      numeric(12,2) not null check (precio_max >= 0),
  check (precio_max >= precio_min),

  -- Cuando la unidad no viene declarada NO se normaliza y no se compara.
  -- Un hueco se ve; un supuesto no. Misma regla que rige el resto del sitio.
  precio_lb_min   numeric(12,4),
  precio_lb_max   numeric(12,4),

  nota            text
);
create index on parte_items (cultivo_id);
create index on parte_items (parte_id);

comment on column parte_items.procedencia is
  'Zona de producción, no variedad: barahonero (región de Barahona), '
  'azuano (Azua), maeño (Mao), mocano (Moca). Ojo: "Macho Barahonero" sí '
  'es un cultivar, pero en boca de un comerciante "barahonero" es de dónde '
  'viene. Ver GLOSARIO.md §6.';

-- ------------------------------------------------------------
-- UNIDAD MAYORISTA CANÓNICA POR RUBRO
--
-- La tabla que vuelve legible un mensaje de WhatsApp. El gremio escribe
-- "Bugalu primiun 500/400" sin decir la unidad; el informe interdiario del
-- Ministerio publica que el tomate bugalú se cotiza en huacal de 45 lb en
-- el Mercado Nuevo, y con eso 500 pasa a ser RD$11.11/lb y se puede
-- comparar con la góndola.
--
-- Las tres unidades que el gremio SÍ declaró cuadran exactamente con esta
-- tabla —ajo saco/22 lb, cebolla saco/50 lb, zanahoria y remolacha
-- saco/100 lb— que es lo que da confianza para usarla donde no la dijeron.
--
-- Fuente: Informe de Precios del Ministerio de Agricultura, ediciones del
-- 8 de enero y 11 de febrero de 2026.
-- ------------------------------------------------------------
alter table cultivos add column if not exists unidad_mayorista text;
alter table cultivos add column if not exists libras_mayorista numeric;

comment on column cultivos.unidad_mayorista is
  'Unidad canónica de venta al por mayor en el Mercado Nuevo, según el '
  'informe del Ministerio. Distinta de unidad_venta, que es la unidad del '
  'catálogo. OJO: el huacal NO tiene un peso fijo — 45 lb para tomate, '
  '100 lb para ají morrón. Un "huacal" a secas no es una unidad.';
