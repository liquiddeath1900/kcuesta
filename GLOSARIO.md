# Glosario del mercado

Cómo habla el Mercado Nuevo. Escrito porque sin esto no se puede leer un
mensaje de la Asociación de Mercaderes Unidos, y porque el día que publique
un productor va a escribir así y no como el catálogo de un supermercado.

Cada término lleva de dónde salió. **Verificado** = está en una fuente
oficial o lo dijo el propio gremio. **Inferido** = deducido con evidencia,
hay que confirmarlo. Lo que no se sabe se deja marcado y no se usa.

---

## 1. Cómo se cotiza: la escalera de calidad

Casi nada se cotiza con un número. Se cotiza en escalera:

> Chinola de **primera** entre 12 y 14 · **Segunda** 8 10 · **Tercera** 5 7

- **Primera** — la mejor calidad. Tamaño parejo, sin daño.
- **Segunda** — comercial pero con defectos.
- **Tercera** — lo que queda. Sirve para procesar o vender barato.
- **Prímium / primiun** — como lo escribe el gremio. Por encima de primera,
  o primera de verdad frente a una "regular" del mismo rubro.
- **Regular / corriente** — el grado común, el de todos los días.
- **Interiores** — grado más bajo aún ("Berrenjenas interiores 700/500").
  *Inferido:* fruto pequeño o de segunda selección. **Confirmar.**
- **Buenas** — grado intermedio informal ("Berrnjena buenas 1100/800").

**Por qué importa para el sitio.** Un plátano de primera a 18 y uno de
tercera a 7 no son un mercado con 157% de dispersión: son dos productos con
dos precios correctos. Meterlos en la misma mediana es el mismo error que
mezclar la libra suelta con el saco de 50. `cultivos.calidad` ya existe en
el esquema y hoy no se usa como eje. *Verificado — el Ministerio también
separa "primera" y "segunda" en su propio informe.*

## 2. Cómo se escribe el rango

El gremio escribe el rango de dos formas y significan lo mismo:

- `entre 1200 y 1500` — explícito.
- `500/400` — comprimido, **alto/bajo**. *Inferido* de que todos los demás
  mensajes usan "entre X y Y" y de que "Morrones corrientes 500/300 la
  caja" solo tiene sentido como rango. **Confirmar** — la otra lectura
  posible es primera/segunda, y las dos dan números muy distintos.

Nunca es un precio único, y es a propósito:

> hay que recordar que el mercado nuevo de la Duarte hay cientos de
> vendedores y muchos mayoristas qué venden según la calidad y dependiendo
> de la plaza

## 3. Plaza

Palabra clave y la definieron ellos mismos:

> **Plaza = cantidad de productos que entre ese día al mercado y la oferta
> que halla del mismo**

> Si hoy lunes entro 100 camiones de Plátanos para 1,000 vendedores se
> estable precio osea ley oferta y demanda pero si mañana martes entran 50
> camiones para lo mismo 1.000 vendedores que va a pasar?

> A mayor oferta los precios bajan · Mayor demanda misma oferta los precios
> se elevan

O sea: **el precio no lo fija nadie, lo fija cuánto entró ese día.** De ahí
que no haya "precio del plátano" sino precio del plátano *hoy*, y que
MERCADOM sobreescriba su archivo sin histórico — para ellos el precio de
ayer no sirve. Para nosotros la serie es justamente lo que nadie guarda.

También explica el segundo sentido de la palabra, "según la plaza": el
puesto o zona del mercado donde se está vendiendo. *Verificado (el primero
lo definió el gremio; el segundo es uso corriente en la misma frase).*

## 4. Unidades de venta al por mayor

Esta es la tabla que desbloquea todo. Sale del **informe interdiario del
Ministerio de Agricultura**, que publica la unidad mayorista canónica de
cada rubro en el Mercado Nuevo. Con ella, un mensaje de WhatsApp que solo
dice "Bugalu primiun 500/400" se vuelve comparable.

| Unidad | Qué es | Rubros |
|---|---|---|
| **Quintal** | 100 lb | Batata, ñame, yautía, yuca, vainita, rábano, carnes |
| **Saco/100 lb** | | Arroz, habichuelas, guandul en vaina, remolacha, zanahoria |
| **Saco/50 lb** | | Ají cubanela, ají gustoso, cebolla roja |
| **Saco/90 lb** | | Pepino |
| **Saco/22 lb** | | Ajo |
| **Huacal/100 lb** | Cajón de madera | Ají morrón |
| **Huacal/45 lb** | | Tomate de ensalada, tomate bugalú |
| **Huacal/30 lb** | | Coliflor, brócoli |
| **Huacal/20 lb** | | Lechuga repollada |
| **Huacal/15 lb** | | Lechuga en hojas (se cotiza por **mata**) |
| **Ciento** | 100 unidades | Huevos |
| **Millar** | 1,000 unidades | Plátano al por mayor |

*Verificado — Informe de Precios del Ministerio de Agricultura, ediciones
del 8 de enero y 11 de febrero 2026.*

Las tres unidades que el gremio declaró en WhatsApp **cuadran exactamente**
con esta tabla: ajo saco de 22 lb, cebolla saco de 50 lb, zanahoria y
remolacha saco de 100 lb. Eso da confianza para usar la tabla en los rubros
donde no declararon unidad.

- **Quintal** = 100 lb. No es la tonelada métrica ni el quintal español.
- **Huacal** = cajón/jaba de madera. Su peso **cambia según el rubro** — 45
  lb para tomate, 100 lb para morrón. Un "huacal" a secas no es una unidad.
- **Mata** = la pieza entera de lechuga (la cabeza), no un peso.

## 5. Nombres de rubros

Lo que en el mercado se llama distinto a como lo llamaría un catálogo:

| En el mercado | Qué es |
|---|---|
| **Víveres** | El grupo de almidones: plátano, yuca, batata, ñame, yautía, papa |
| **Chinola** | Maracuyá / parchita |
| **Lechoza** | Papaya |
| **Auyama** | Calabaza / zapallo |
| **Molondrón** | Okra / quimbombó |
| **Tayota** | Chayote |
| **Guandul** | Gandul. Se cotiza *en vaina* o *en grano* — precios muy distintos |
| **Guineo** | Banano. **No es plátano** |
| **Rulo** | Tercer tipo de musácea (Bluggoe), aparte de plátano y guineo |
| **Bugalú** | Variedad de tomate de mesa. Se cotiza aparte del de ensalada |
| **Ensalada** | Tomate de ensalada. *Invernadero* y *campo abierto* son precios distintos |
| **Morrón** | Pimiento morrón / campana |
| **Cubanela** | Ají largo verde, el de cocinar. **No confundir con gustoso** |
| **Gustoso** | Ají pequeño aromático, otro precio y otro rubro |
| **Maduro** | Plátano maduro. Rubro aparte del verde |

*Verificado — todos aparecen como rubros separados en el informe del
Ministerio.*

⚠️ Cubanela y gustoso son rubros **distintos** con precios distintos. Por
eso el mapa de alias de `data/alias.json` está escrito a mano: un
emparejamiento difuso los junta y mete un precio equivocado en silencio.

## 6. Procedencia — no es lo mismo que calidad

> Plátanos blancos osea plátanos **Barahoneros Azuanos y maeños**

Estos **no son variedades**: son las zonas donde se produjo.

- **Barahonero** — de la región agrícola de Barahona (el sur; Tamayo es el
  municipio que más produce).
- **Azuano** — de Azua.
- **Maeño** — de Mao, Valverde.
- **Mocano** — de Moca ("la mejor yuca del mundo mocana pecho rojo").

*Verificado para barahonero — el nombre viene de que el municipio pertenece
a la región agrícola de Barahona, no de una variedad botánica. Ojo con la
trampa: existe además un cultivar llamado **Macho Barahonero**, que sí es
una variedad. En boca de un comerciante "barahonero" casi siempre es la
procedencia.*

- **Pecho rojo** — tipo de yuca. *Inferido* por el color de la corteza.
  **Confirmar.**

**Para el modelo:** procedencia y calidad son **dos ejes distintos**. Un
plátano puede ser barahonero de tercera. Meter la procedencia en el mismo
campo que el grado los vuelve incomparables.

## 7. Ciclo

> No hay control de precios con los productos agrícolas de **corto y medio
> ciclo**

Tiempo de siembra a cosecha. Los de ciclo corto (hortalizas, tomate, ají)
se replantan rápido, así que la oferta cambia semana a semana y el precio
salta. Es la razón estructural de que no haya precio fijo en estos rubros.
*Verificado — lo dijo el gremio.*

---

## Preguntas para el contacto

Cortas y concretas. Cada una desbloquea datos que hoy no se pueden usar:

1. **¿`500/400` es un rango alto/bajo, o es primera/segunda?** Es la
   diferencia entre poder leer la lista de la Asociación de Mayoristas de
   Vegetales y no poder.
2. **¿En qué unidad va esa lista?** Solo declararon "la caja" en morrones.
   ¿Bugalú, ensalada, berenjena y limón van en huacal?
3. **¿"Limón 4000/3500" es por saco o por millar?** El número no cuadra con
   nada más de la lista.
4. **¿"Maduro 150/200" va por ciento, por racimo o por unidad?**
5. **¿"Interiores" es tamaño pequeño o segunda selección?**
6. **La yuca mocana a "28 y 30" — ¿por libra o por quintal?**
7. **¿"Auyama el kilo entre 80 y 90" es kilo de verdad?** Sería el único
   rubro cotizado en kilo; todo lo demás va en libra.
