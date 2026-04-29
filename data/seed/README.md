# Seed data

Source of truth for the NutriRoll component library (~70 components across 4 categories).
Do **not** auto-populate values — every nutrition, price, or cooking-time value must be verified by a human before going to production.

## Files

| File | Purpose |
|---|---|
| `components.csv` | Master component table — macros, portion, tags, allergens |
| `cooking_methods.csv` | Per-(component, method) cook time and notes |
| `flavor_tags.csv` | Controlled vocabulary for `flavor_tags` column |
| `dietary_tags.csv` | Controlled vocabulary for `dietary_tags` column |

The loader (`tools/seed/load.py`, built in Phase 1.2) validates every row against a Pydantic schema and upserts idempotently into Postgres.

---

## Column reference — `components.csv`

| Column | Type | Notes |
|---|---|---|
| `id` | int | Stable seed ID; do not renumber after first load |
| `category` | `Base\|Vegetable\|Sauce\|Topping` | |
| `name` | str | Short display name |
| `default_portion_value` | float | Per-serving amount |
| `default_portion_unit` | `g\|ml\|pc` | |
| `kcal_per_100g` | float | **VERIFY against sources below** |
| `carbs_per_100g` | float | Total carbohydrates |
| `protein_per_100g` | float | |
| `fat_per_100g` | float | Total fat |
| `fiber_per_100g` | float | Dietary fiber |
| `flavor_tags` | pipe-separated | Values from `flavor_tags.csv` |
| `dietary_tags` | pipe-separated | Values from `dietary_tags.csv` |
| `allergens` | pipe-separated | EU 14 major allergens in plain text |
| `default_cooking_method` | str | Must match a method in `cooking_methods.csv` |
| `shelf_life_days` | int | Approximate days; raw/fresh values are conservative |
| `typical_availability` | str | `year_round`, `spring`, `summer`, `autumn_winter`, etc. |
| `blacklisted` | bool | `false` in seed; users toggle per-profile |

## Column reference — `cooking_methods.csv`

| Column | Type | Notes |
|---|---|---|
| `component_id` | int | FK → `components.csv.id` |
| `method` | str | One of the controlled methods in `PROJECT_VISION.md` § "Ways of cooking" |
| `approx_cook_min` | int | Approximate cook time in minutes; 0 = no prep |
| `can_cook_with_others` | bool | Whether this component can share a pan/pot with others |
| `notes` | str | Cut sizes, temperatures, and tips; **VERIFY against sources** |

---

## Current status

All nutritional values and cooking times in this seed dataset are **approximate placeholders** derived from general culinary knowledge. They are suitable for development and algorithm testing only. Before production:

- [ ] Verify every `kcal_per_100g`, `carbs_per_100g`, `protein_per_100g`, `fat_per_100g`, `fiber_per_100g` against at least one authoritative source.
- [ ] Cross-check allergen flags against packaging / official databases.
- [ ] Review `approx_cook_min` values against a culinary reference.

---

## Recommended data sources

### Nutritional values (macros)

1. **USDA FoodData Central** — https://fdc.nal.usda.gov/
   - Free, public, comprehensive. Search by name → "SR Legacy" or "Foundation Foods" entries are most reliable for raw/whole ingredients. API available.

2. **Open Food Facts** — https://world.openfoodfacts.org/ · API: https://world.openfoodfacts.org/api/v2/product/{barcode}
   - Open-source, community-maintained, worldwide. Best for packaged/processed items (teriyaki sauce, furikake, croutons). Download the full DB as CSV/JSONL.

3. **Bundeslebensmittelschlüssel (BLS)** — https://www.blsdb.de/
   - German federal nutrient database. Preferred reference for the DE market. Requires registration but is free for non-commercial use.

4. **DGE (Deutsche Gesellschaft für Ernährung)** — https://www.dge.de/
   - German Nutrition Society reference values and food lists. Good for cross-checking and setting "balanced bowl" heuristics.

5. **Nutritionix** — https://www.nutritionix.com/food
   - Reliable, US-centric, searchable. Commercial API (free tier: 500 req/day).

### Prices (per store)

Prices are **not** stored in `components.csv` — they live in `SupermarketPrice` rows. The seed loader does not import prices. Populate them:
- Manually via the in-app Component/Supermarket editor (Phase 1 MVP).
- In bulk via the receipt-scan / barcode flow (deferred to v1.1+).

For German market initial prices, check current Rewe / Edeka / Aldi online catalogues and note the `pack_size` and `pack_price` for each component.

### Cooking times

- **The Food Lab / Serious Eats** — https://www.seriouseats.com — extensively tested times and temperatures.
- **America's Test Kitchen** — https://www.americastestkitchen.com — peer-reviewed culinary methods.
- **On Food and Cooking** (Harold McGee) — authoritative on temperatures and the science behind them.
- Standard chef tables: e.g. roast vegetables 200 °C / 20–25 min for 1 cm dice is a reliable baseline.

