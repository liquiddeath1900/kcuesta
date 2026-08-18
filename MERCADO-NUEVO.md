# Mercado Nuevo — lo que dijo alguien que trabaja adentro

Notas del 17 de agosto 2026, a partir del grupo de la **Asociación
Dominicana Mercaderes Unidos** (203 miembros, publican solo los
administradores). Transcripción completa en
`archivo/2026/08/17/mercaderes-unidos-whatsapp.md`.

Esto no es un dato más. Cambia supuestos que están metidos en el diseño del
sitio, así que va escrito antes de tocar código.

---

## 1. No existe "el precio". Existe una banda, y el mercado lo sabe

Palabras del administrador:

> hay que recordar que el mercado nuevo de la Duarte hay **cientos de
> vendedores y muchos mayoristas qué venden según la calidad y dependiendo
> de la plaza**

Y por eso publican rangos, no cifras: "Chinola de primera entre 12 y 14".
Nunca un número solo.

**Qué valida.** La banda p25/mediana/p75 de `ESCALA.md` no era una
delicadeza de diseño nuestra — es cómo habla el mercado de verdad. La
decisión de nunca rankear vendedores por precio y compararlos contra un
rango queda respaldada por la gente que hace el precio.

**Qué rompe.** El sitio dice hoy "valor de referencia" con UNA cifra
mediana. Contra tres supermercados en línea eso se sostiene. Contra el
Mercado Nuevo no: ahí una mediana esconde justamente lo que el comerciante
necesita ver. Si algún día entran estos precios, entran **como banda**, no
como mediana.

## 2. La calidad es una dimensión que no tenemos, y sin ella la comparación miente

Todo lo que publican viene en escalera:

| Producto | 1ª | 2ª | 3ª |
|---|---|---|---|
| Chinola (unidad) | 12–14 | 8–10 | 5–7 |
| Plátano blanco | 15–18 | 12–14 | 7–10 |
| Cilantro | 30 | 25–20 | 15 |
| Lechoza (unidad) | 60–80 | 40–50 | — |
| Cebolla roja (saco 50 lb) | 1,900–2,100 | 1,500–1,800 | — |

Un plátano de primera a 18 y uno de tercera a 7 **no son un mercado con
157% de dispersión**. Son dos productos distintos con dos precios
correctos. Meterlos en la misma mediana produce un número que no describe
nada — exactamente el mismo error que ya cometimos mezclando la libra
suelta con el saco de 50, y que se arregló normalizando por libra.

`cultivos.calidad` ya existe en el esquema (`'Grande'`, `'Primera'`) y hoy
**no se usa como eje de comparación**. Ese es el trabajo.

## 3. "Plaza" es la variable que explica el precio

> No hay control de precios con los productos agrícolas de corto y medio
> ciclo, el precio los establece la plaza
>
> **Plaza = cantidad de productos que entre ese día al mercado y la oferta
> que halla del mismo**

Con su propio ejemplo: 100 camiones de plátano para 1,000 vendedores fija un
precio; 50 camiones para los mismos 1,000 vendedores fija otro.

Es oferta y demanda diaria, y es la razón de que MERCADOM sobreescriba su
archivo sin histórico: para ellos el precio de ayer no sirve. Para nosotros
sí — la serie es justamente lo que nadie guarda. Refuerza que la captura
diaria es el activo, no el sitio.

No tenemos conteo de camiones ni forma de conseguirlo. No se inventa una
métrica de "plaza"; se registra que es la causa y ya.

## 4. La advertencia, que es la parte incómoda

> El sistema comercial es muy complicado en el mercado por eso **la mayoría
> de comerciantes no le gusta que se publiquen los precios**

Hay que leerla completa. No dice que publicar esté prohibido: dice que al
comerciante individual **le quita margen de negociación**. Y sin embargo
una asociación de 203 miembros los publica todos los días.

La diferencia explica con quién se trabaja:

- Al **comerciante individual** la transparencia le quita ventaja sobre el
  que compra.
- A la **asociación** le sirve, porque evita que a sus propios miembros los
  engañen y le da autoridad al grupo.

Es la misma estructura que con los productores. **El aliado natural de
Kcuesta es la asociación, no el intermediario suelto.** Cualquier
acercamiento al Mercado Nuevo que se sienta como "les vamos a transparentar
los precios a ustedes" se cae; el que funciona es "esto le da autoridad al
grupo y protege a sus miembros".

## 5. Qué NO se ha hecho, y por qué

**Estos precios no están en el sitio y no deben entrar todavía.**

El grupo es privado y de publicación restringida a administradores.
Republicar en una web pública lo que se comparte en un grupo cerrado es un
acto distinto a leer un catálogo abierto de supermercado, aunque los dos
sean "datos que alguien publicó". Sin permiso explícito de la asociación,
no entran — y menos después de que ellos mismos avisaran que al gremio no
le gusta que se publiquen.

Tampoco están cargados a `precios_oficiales`: esa tabla exige `fuente` y
`fuente_url` verificables, y un mensaje de WhatsApp no lo es.

## 6. Lo que sí vale la pena, en orden

1. **Preguntar las unidades que faltan.** El administrador ofreció orientar
   por privado. La lista reenviada de la Asociación de Mayoristas de
   Vegetales ("Bugalu 500/400", "Limón 4000/3500") es inservible sin saber
   si es caja, huacal o quintal. Es una pregunta corta y desbloquea todo lo
   demás.
2. **Meter la calidad como eje.** Es trabajo nuestro, no depende de nadie, y
   hay que hacerlo aunque estos precios nunca entren: el día que publique un
   productor va a publicar primera o segunda, no "plátano".
3. **Decidir la relación antes que los datos.** Fuente, canal de
   distribución, o las dos. No es lo mismo pedirles precios que pedirles que
   sus 203 miembros conozcan el sitio.
4. **Anotar el cambio en MERCADOM.** Nueva directora general, Mariana
   Tavarez de Santos. Importa el día que se pida acceso oficial a la serie
   —que es la que hoy se pierde todos los días— no antes.
