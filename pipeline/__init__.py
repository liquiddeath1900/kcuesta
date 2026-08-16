"""Pipeline de captura de precios de Kcuesta.

Recoge precios agrícolas de todas las fuentes públicas dominicanas y los
deja en Supabase (`precios_oficiales`, `productos_retail`, `precios_retail`),
además de regenerar los JSON estáticos que consume el sitio.

Corre a diario. La razón del "a diario" no es refresco: MERCADOM publica un
solo archivo que se sobrescribe sin histórico, así que el día que no se
capture se pierde de forma definitiva.
"""

__version__ = "1.0.0"
