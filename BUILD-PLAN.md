# Kcuesta — Build Plan

**Domain:** kcuesta.com (owned) · +quecuesta.com / qcuesta.com as redirects (next week)
**What it is:** A dead-simple site that turns the DR government's ugly crop-price data into
something anyone can read in 5 seconds — plus WhatsApp alerts and, later, price forecasts.
**Audience:** Dominican producers, sellers, buyers (starting with your mom + her husband).
**Language:** Spanish first. English never needed for v1.
**Standalone** — its own repo, separate from GrowEssential.

---

## The one honest promise
Nobody in the DR has true real-time prices — the official source is weekly-to-inter-daily and
published with a lag. Kcuesta's promise is NOT "live prices." It's:
**"The latest official market prices, shown clearly, refreshed every week, with the trend so you
know which way it's moving."** That alone beats everything that exists.

---

## Stack (all things you already run)
- **Site:** static HTML/CSS/JS on GitHub Pages (same as GrowEssential/Yerramazing). Mobile-first.
- **Prices data:** NO database needed — prices are read-only + small, so the GitHub Action commits
  them as JSON right into the repo and the site reads the JSON. Free, fast, zero infra.
- **Subscribers (needs a writable DB):** Supabase is maxed out, so use **Neon** (free Postgres,
  Postgres like you already know, 10 projects on free tier). One tiny `subscribers` table.
- **Pipeline:** Python script, scheduled (GitHub Actions cron — free, no server).
- **WhatsApp:** Twilio WhatsApp API to start (official, reliable).
- **Charts:** lightweight JS (Chart.js) — no heavy framework.
- **Forecasts (Phase 3):** Python (LightGBM / Prophet) in the same scheduled job.

> **Storage decision:** the only thing that needs a real database is subscriber phone numbers.
> Everything else (prices, trends, forecasts) is generated files committed to the repo. This is why
> maxing out Supabase doesn't block us.

---

## Data sources (all official Ministerio de Agricultura, free, ODbL license)
| Source | Freshness | Format | Role |
|---|---|---|---|
| Mayorista + Minorista CSVs | weekly rows, ~monthly refresh | clean CSV | **launch + trends** |
| "Informe de Precios DD-MM-YYYY" posts | inter-daily | PDF/image | freshest snapshot (Phase 2, needs PDF parse) |
| datos.gob.do mirror | mirror | CSV | backup/history |
| Siembra/Cosecha/Superficie Sembrada | seasonal | tables | **supply signal for forecasts** |

**7 market levels available:** finca (farm-gate), mayorista, minorista, supermercados, colmados,
vendedores ambulantes, carnicerías.
**Key for sellers (your mom):** feature **finca (farm-gate)** — what the producer actually receives.

---

## Repo structure
```
kcuesta/
  index.html            # dashboard: today's prices + up/down arrows + search
  cultivo/              # per-crop SEO pages: /cultivo/platano, /yuca, /arroz ...
  assets/               # css, js, chart, logo
  data/                 # generated JSON the site reads (prices_latest.json, trends.json)
  pipeline/
    fetch.py            # download govt CSVs
    clean.py            # fix encoding, dedupe categories, normalize units
    load.py             # upsert into Supabase
    forecast.py         # (Phase 3) train + predict
    alerts.py           # (Phase 2) detect moves -> queue WhatsApp
  .github/workflows/
    weekly.yml          # cron: run pipeline, commit data JSON, send alerts
```

---

## Build order

### Phase 1 — Data + Site (the weekend build)
1. `fetch.py` + `clean.py` — the govt CSV is a mess (broken encoding `S�per`, duplicate
   categories `Frutas/frutas/Cereal/Cereales/Celeales`, multiple prices per crop). Cleaning it
   IS the product. Output: clean rows {crop, category, market_level, unit, price, week, source_date}.
2. Load into Supabase + export `prices_latest.json` + `trends.json`.
3. `index.html` — searchable table, big up/down arrows vs last week, "precios al [date]" freshness stamp.
4. Deploy to GitHub Pages → point kcuesta.com at it.
**Done = a working, honest, better-than-anything site. Ship this first.**

### Phase 2 — SEO + WhatsApp (week 2)
5. Per-crop pages `/cultivo/platano` etc. — title/H1 "Precio del plátano hoy en RD", trend chart,
   "¿a cómo está?" copy. This is what ranks (govt = PDFs, competitor = an app with no website).
6. Subscribe form → Supabase `subscribers` (crop + phone).
7. `alerts.py` + Twilio — weekly job: if a subscribed crop moved >X%, send WhatsApp.
   Your mom + husband = subscriber #1.
8. Add the inter-daily "Informe de Precios" PDF parse for fresher snapshots (optional).

### Phase 2.5 — Disaster / regional-risk monitor (the early-warning layer)
The insight: **most crops come from specific regions. A disaster there = a price spike 1–3 weeks
later.** Watching disasters is watching the market's future.

**Crop→region map (build this table once):**
- Cibao (La Vega, Espaillat) → plátano, rice, tubers
- Constanza / Jarabacoa → vegetables, potato, strawberry, garlic
- Azua / San Juan → tomato, plátano, banana, beans, rice
- Mao / Valverde → banana, rice
- Barahona / Bahoruco → coffee, plátano
So a flood in Azua ≠ a flood in Constanza — each hits different crops.

**Sources to watch (scheduled scrape + alert):**
- **COE** (coe.gob.do) — official emergency alerts by province (verde/amarilla/roja).
- **ONAMET** (onamet.gob.do) — national weather warnings, storms, drought.
- **NOAA NHC** — Atlantic hurricane tracking (free API/feeds) — DR's biggest supply-shock risk.
- **NASA POWER** — rainfall anomalies per region (same feed used for forecasts).
- **News** (firecrawl search) — "inundación / sequía / plaga" + region names.

**Output:** a "Riesgo del mercado" strip on the site + a WhatsApp warning:
> "⚠️ Alerta roja de lluvias en Azua (COE). Azua produce mucho tomate y plátano — posible subida de
> precios en 1–2 semanas."
This feeds Phase 3 directly: an active disaster in a producing region is a top forecast feature.

### Phase 3 — The prediction engine (the "predict the market" layer)
See below. Build only after Phase 1–2 are live and you have clean history flowing.
The disaster monitor (2.5) becomes one of its strongest real-time inputs.

---

## Phase 3 — Price forecasting (honest version)

**Can we predict crop prices? Yes — partly. And that's still a big edge.**
Crop prices are actually *easier* than the stock market in one way: they're **seasonal and
supply-driven**, not driven by millions of traders' psychology. Plátano, yuca, tomato — each has a
repeating yearly rhythm. 8+ years of history (2017–2026) is enough to learn those rhythms.

But be honest: **it's not a crystal ball.** Weather shocks (a hurricane wipes a harvest) and policy
(import bans) cause spikes no model fully predicts. So the product is a **directional forecast with a
confidence range**, not a guaranteed number:
> "Based on 8 years, plátano usually climbs ~15% heading into [season], and rainfall this month is
> below normal — expect **upward pressure, RD$1,900–2,200 range** over the next 3–4 weeks."

### Features (inputs) — what actually drives DR crop prices
1. **Price history / seasonality** — we have it. The single strongest signal.
2. **Weather** — NASA POWER API (free): rainfall, temperature, drought index. DR is hurricane-prone
   → weather is the #1 supply-shock driver. (You already researched NASA POWER for GrowEssential.)
3. **Planting/supply** — MA's "Superficie Sembrada" + "Siembra/Cosecha/Producción" stats. If everyone
   planted a lot of tomato this season → price will fall at harvest. This is your "amount of people
   growing the crop" input — and it's published data.
4. **Exchange rate (RD$/USD)** — imported inputs (fertilizer, fuel) push prices. Free from central bank.
5. **Fuel/transport cost** — moves everything downstream.
6. **Calendar/demand spikes** — Christmas, Semana Santa, school season → predictable demand jumps
   for specific crops.
7. **Harvest calendar** — when each crop naturally floods the market (derivable from history).

### Model choice (right-sized, not overkill)
- **Baseline:** seasonal average + trend (Prophet). Ships fast, surprisingly good for seasonal crops.
- **Upgrade:** LightGBM/XGBoost gradient boosting with the features above. Handles "low rainfall +
  high planting = X" interactions. This is the correct tier for this data size — NOT deep learning
  (we don't have millions of rows; a neural net would overfit).
- **Always show a confidence band + "why"** (top drivers). Never a naked number — that's how you stay
  honest and trusted.

### Your unfair advantage from this
- **For your mom/husband:** "hold your yuca 3 weeks, price is climbing" = real money.
- **For GrowEssential consulting:** "yuca peaks every March — plant to hit that window" is a paid
  deliverable competitors can't produce.
- **Data moat:** every week you store, the model gets better and the history becomes something
  nobody else has packaged.

---

## What I'd do next
1. Create the `kcuesta` repo + Supabase project.
2. Build Phase 1 (`fetch` + `clean` + `index.html`) — ship a live site this weekend.
3. Then Phase 2 (SEO pages + WhatsApp), then Phase 3 (forecasts).

**Open question for you:** GitHub account — same `liquiddeath1900`? And Supabase — new project or
reuse an existing org?
