-- ============================================================
-- Kcuesta — RLS y Storage para la capa de retail
-- Ejecutar después de 03_retail.
--
-- Mismo modelo que 02_rls: "gatear el contacto, no la existencia".
-- Un precio de supermercado no es dato privado de nadie — es público y
-- verificable contra la web de la cadena. Se abre a lectura.
-- Escribir, en cambio, es exclusivo del service_role: estas tablas las
-- llena el pipeline, nunca el navegador. No se declara ninguna política
-- de INSERT/UPDATE, así que anon y authenticated quedan fuera por
-- ausencia, que es más difícil de romper por accidente que una política
-- permisiva mal escrita.
-- ============================================================

alter table cadenas           enable row level security;
alter table cultivo_alias     enable row level security;
alter table productos_retail  enable row level security;
alter table precios_retail    enable row level security;
alter table capturas          enable row level security;

create policy "cadenas visibles para todos"
  on cadenas for select using (activo = true);

create policy "alias visibles para todos"
  on cultivo_alias for select using (true);

-- Solo se expone el producto cuyo alias ya resolvió a un cultivo. Un SKU
-- sin mapear es ruido de pipeline, no contenido: mostrarlo ensucia la
-- página y delata productos que ni siquiera son agrícolas.
create policy "productos retail mapeados visibles"
  on productos_retail for select using (cultivo_id is not null);

create policy "precios retail visibles para todos"
  on precios_retail for select using (true);

-- La bitácora NO se abre. Deja ver qué fuentes fallan y con qué frecuencia,
-- que es información de operación, no de producto.
-- (Sin política de select ⇒ solo service_role lee.)

-- ------------------------------------------------------------
-- STORAGE — bucket de fotos de producto
--
-- Regla de fotos acordada: se espeja fotografía de producto limpia; lo que
-- trae marca de agua o logo encima se deja quieto. Por eso el pipeline solo
-- recorre categorías de fresco (frutas, vegetales, carnes, lácteos), donde
-- la foto es el producto sobre fondo blanco. El empaquetado de marca queda
-- fuera por filtro de categoría, no por inspección visual.
--
-- Además ninguna foto se sirve mientras esté en 'pendiente'
-- (ver productos_retail.foto_estado): hasta aprobarse, la tarjeta cae al
-- banco Creative Commons de assets/img/.
-- ------------------------------------------------------------
insert into storage.buckets (id, name, public)
  values ('retail-fotos', 'retail-fotos', true)
  on conflict (id) do nothing;

create policy "fotos retail lectura publica"
  on storage.objects for select
  using (bucket_id = 'retail-fotos');

-- Escritura: solo service_role. Igual que arriba, por ausencia de política.
