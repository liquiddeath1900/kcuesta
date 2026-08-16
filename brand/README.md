# Marca

Fuentes originales (Gemini) en `src-*.jpg`. Los archivos que usa el sitio están
en `assets/brand/`, generados desde estos:

| Archivo | Uso |
|---|---|
| `assets/brand/logo.png` | Logo con hoja. Cabecera de todas las páginas. Fondo transparente. |
| `assets/brand/logo-simple.png` | Wordmark sin hoja. Reserva para espacios angostos. |
| `assets/brand/icono.png` | Icono cuadrado, esquinas transparentes. |
| `assets/brand/icono-{16,32,180,192,512}.png` | Favicon, apple-touch-icon, manifest. |
| `assets/brand/og.jpg` | Imagen de 1200×630 al compartir el enlace. |

El fondo se recortó por distancia de color con un umbral suave (18–60), así el
antialias de las letras se conserva y no quedan bordes duros. Las esquinas del
icono se hicieron transparentes con relleno desde el borde, para que el cuadrado
verde se vea limpio también sobre fondo oscuro.

Colores de marca: verde `#1D4A33`, naranja `#C86A22`, hueso `#FBFAF6`.
