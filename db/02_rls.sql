-- ============================================================
-- Kcuesta — Row Level Security
--
-- Modelo acordado: "gatear el contacto, no la existencia".
--   ANÓNIMO  ve: precios oficiales, catálogo, anuncios activos, índice.
--   ANÓNIMO  NO ve: teléfono, whatsapp, email, mensajes, ventas.
--   SESIÓN   ve: contacto del vendedor de un anuncio activo, su propio inbox.
--
-- Nota de diseño: NO se usa SECURITY DEFINER para leer identidad.
-- auth.uid() es estable dentro de RLS; SECURITY DEFINER ha causado
-- fallos silenciosos antes en este stack.
-- ============================================================

alter table cultivos            enable row level security;
alter table precios_oficiales   enable row level security;
alter table perfiles            enable row level security;
alter table perfiles_contacto   enable row level security;
alter table auth_eventos        enable row level security;
alter table anuncios            enable row level security;
alter table ventas              enable row level security;
alter table conversaciones      enable row level security;
alter table mensajes            enable row level security;
alter table indice_precios      enable row level security;
alter table indice_config       enable row level security;

-- ------------------------------------------------------------
-- PÚBLICO SIN SESIÓN — el embudo de SEO depende de esto
-- ------------------------------------------------------------
create policy "cultivos visibles para todos"
  on cultivos for select using (activo = true);

create policy "precios oficiales visibles para todos"
  on precios_oficiales for select using (true);

-- Solo se publica la cifra del índice cuando hay muestra suficiente.
create policy "indice visible solo si publicable"
  on indice_precios for select using (publicable = true);

create policy "config del indice visible"
  on indice_config for select using (true);

-- Perfiles: los campos públicos viven en esta tabla, así que se puede abrir.
create policy "perfiles publicos visibles"
  on perfiles for select using (true);

-- Anuncios activos visibles sin sesión. El contacto NO está aquí.
create policy "anuncios activos visibles"
  on anuncios for select using (estado = 'activo');

-- ------------------------------------------------------------
-- CONTACTO — el muro real
-- ------------------------------------------------------------
-- El dueño siempre ve lo suyo.
create policy "dueño ve su contacto"
  on perfiles_contacto for select
  using (auth.uid() = id);

-- Un usuario autenticado ve el contacto de un vendedor SOLO si ese
-- vendedor tiene un anuncio activo. Anónimo nunca entra aquí.
create policy "usuario con sesion ve contacto de vendedor activo"
  on perfiles_contacto for select
  using (
    auth.uid() is not null
    and exists (
      select 1 from anuncios a
      where a.vendedor_id = perfiles_contacto.id
        and a.estado = 'activo'
    )
  );

create policy "dueño edita su contacto"
  on perfiles_contacto for update
  using (auth.uid() = id) with check (auth.uid() = id);

create policy "dueño crea su contacto"
  on perfiles_contacto for insert
  with check (auth.uid() = id);

-- ------------------------------------------------------------
-- PERFIL PROPIO
-- ------------------------------------------------------------
create policy "usuario crea su perfil"
  on perfiles for insert with check (auth.uid() = id);

create policy "usuario edita su perfil"
  on perfiles for update
  using (auth.uid() = id) with check (auth.uid() = id);

-- ------------------------------------------------------------
-- ANUNCIOS — escritura solo del dueño
-- ------------------------------------------------------------
create policy "vendedor ve todos sus anuncios"
  on anuncios for select
  using (auth.uid() = vendedor_id);

create policy "vendedor publica"
  on anuncios for insert
  with check (
    auth.uid() = vendedor_id
    and exists (
      select 1 from perfiles p
      where p.id = auth.uid() and p.tipo in ('vendedor','ambos')
    )
  );

create policy "vendedor edita lo suyo"
  on anuncios for update
  using (auth.uid() = vendedor_id) with check (auth.uid() = vendedor_id);

create policy "vendedor retira lo suyo"
  on anuncios for delete
  using (auth.uid() = vendedor_id);

-- ------------------------------------------------------------
-- VENTAS — alimenta el índice; nunca públicas en crudo.
-- Se publica solo el agregado en indice_precios.
-- ------------------------------------------------------------
create policy "partes ven la venta"
  on ventas for select
  using (auth.uid() = vendedor_id or auth.uid() = comprador_id);

create policy "vendedor confirma la venta"
  on ventas for insert
  with check (auth.uid() = vendedor_id);

-- ------------------------------------------------------------
-- MENSAJERÍA — solo las dos partes
-- ------------------------------------------------------------
create policy "partes ven su conversacion"
  on conversaciones for select
  using (auth.uid() = comprador_id or auth.uid() = vendedor_id);

-- Solo un comprador con sesión abre conversación, y no consigo mismo.
create policy "comprador abre conversacion"
  on conversaciones for insert
  with check (
    auth.uid() = comprador_id
    and comprador_id <> vendedor_id
    and exists (
      select 1 from anuncios a
      where a.id = anuncio_id
        and a.vendedor_id = conversaciones.vendedor_id
        and a.estado = 'activo'
    )
  );

create policy "partes leen mensajes"
  on mensajes for select
  using (exists (
    select 1 from conversaciones c
    where c.id = mensajes.conversacion_id
      and (auth.uid() = c.comprador_id or auth.uid() = c.vendedor_id)
  ));

create policy "parte escribe en su conversacion"
  on mensajes for insert
  with check (
    auth.uid() = autor_id
    and exists (
      select 1 from conversaciones c
      where c.id = conversacion_id
        and (auth.uid() = c.comprador_id or auth.uid() = c.vendedor_id)
    )
  );

-- Marcar leído: solo el receptor, y solo esa bandera.
create policy "receptor marca leido"
  on mensajes for update
  using (
    auth.uid() <> autor_id
    and exists (
      select 1 from conversaciones c
      where c.id = mensajes.conversacion_id
        and (auth.uid() = c.comprador_id or auth.uid() = c.vendedor_id)
    )
  );

-- ------------------------------------------------------------
-- BITÁCORA DE ACCESOS — el usuario quiere saber quién entra.
-- Se escribe desde el cliente al iniciar sesión; nadie la lee salvo
-- el service_role (dashboard/admin). Sin política de SELECT = nadie lee.
-- ------------------------------------------------------------
create policy "usuario registra su propio acceso"
  on auth_eventos for insert
  with check (auth.uid() = user_id);

-- ------------------------------------------------------------
-- Alta automática de perfil al registrarse.
-- SECURITY DEFINER es correcto AQUÍ (corre fuera de sesión, en el hook
-- de auth) y no consulta el rol actual — que es lo que rompía antes.
-- ------------------------------------------------------------
create or replace function public.crear_perfil_al_registrarse()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
begin
  insert into public.perfiles (id, nombre, tipo)
  values (
    new.id,
    coalesce(
      new.raw_user_meta_data->>'full_name',
      new.raw_user_meta_data->>'name',
      split_part(coalesce(new.email, ''), '@', 1),
      'Usuario'
    ),
    'comprador'
  )
  on conflict (id) do nothing;

  insert into public.perfiles_contacto (id, email, telefono, metodo_registro)
  values (
    new.id,
    new.email,
    new.phone,
    case
      when new.raw_app_meta_data->>'provider' = 'google' then 'google'
      when new.phone is not null then 'telefono'
      else 'email'
    end
  )
  on conflict (id) do nothing;

  return new;
end $$;

drop trigger if exists t_usuario_nuevo on auth.users;
create trigger t_usuario_nuevo
  after insert on auth.users
  for each row execute function public.crear_perfil_al_registrarse();
