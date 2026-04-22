# NutriRoll Project Vision

NutriRoll is an app that allows its users to receive recommendations of meals in the bowl-style that are easy to cook/prep, tasty and cheap.
Meal selection features are rich to adhere to the user's desires. A rolled meal can be altered in many possible ways such that the user is content with his recommendation. Recommandations may be altered based on flavor, specific components or nutritional facts.
It provides recipes that are easy to follow and don't cost much time. Most meals can be cooked or 2 to 4 portions. Because of the component simplicity, nutritional facts.
The user is able to rate meals or components in those meals which gets used for better recommendations.
Another great part is that costs and packaging sizes of any component for the nearest grocery store can be saved to exactly calculate a price and best estimate the amount of meals that can be cooked for which price.

## User interface functionalities

### Navigation Architecture
Five bottom tabs, always visible (except in Cooking Companion mode, which goes full-screen):

| Tab | Label | Scope |
|---|---|---|
| 1 | **Roll** | Roll a Meal — main entry point |
| 2 | **Plan** | Planned Meals (default sub-tab), Roll a Week, Saved for Later |
| 3 | **Shop** | Shopping Lists, Supermarket prices |
| 4 | **Cook** | History, Rate a Meal, active Recipe View |
| 5 | **Me** | Pantry, Settings, profile, usage stats |

Key decisions:
- **Roll a Week** lives in the *Plan* tab — it is a planning mode, not a roll variant, and must be easily discoverable without cluttering the main Roll screen.
- **Saved for Later** and **Planned Meals** are two chips inside *Plan* (default: Planned).
- **Recipe View** opens modally over any tab via "Cook now" from *Plan* or *Cook*.
- **Cooking Companion mode** is a full-screen takeover (hides tab bar), entered from within Recipe View.
- Deep links (shared recipes, iCal entries) open the relevant screen regardless of current tab.

### 0. Onboarding Flow
The goal of onboarding is to reach the first roll in under 60 seconds. Every optional step deferred here is surfaced contextually later — prompted at the moment it is relevant, not upfront. The flow is always skippable at any step (sane defaults take over).

**3 mandatory screens** (progress indicator on top):
1. **Welcome / value pitch** — one sentence: "Roll a cheap, tasty bowl in seconds." Primary CTA: *Let's go*. Secondary: *Skip, just roll* (jumps directly to a default first roll).
2. **Dietary mode** — single choice: omnivore / vegetarian / vegan / pescatarian / custom. Largest impact on recommendations; worth asking upfront.
3. **Allergies & hard exclusions** — multi-select chips only (nuts, gluten, lactose, shellfish, soy, egg, …). No free-text field here — "never show me" free-text moves to Settings. These become hard filters, not soft penalties.

After step 3 the user lands immediately on **Roll a Meal** with one pre-rolled bowl already on screen — they should never see an empty state.

**Deferred contextual prompts (never blocking):**
- **Goal** (*eat cheaper / healthier / save time / try new things / just feed me*) — nudged as an inline card on the Roll screen after the first reroll.
- **Budget** — prompted the first time the user taps the price chip on a rolled meal.
- **Kitchen equipment** — prompted the first time a recipe requires equipment the app doesn't know about ("Do you have an oven?").
- **Time budget** — prompted after the first roll if the shown prep time exceeds 30 min.
- **Default portions** — prompted when the user first edits portions on the roll screen; saved as new default.
- **Pantry quick-stock** — available in the *Me* tab; nudged once after the 3rd cook.
- **Supermarket** — prompted the first time the user taps *Shopping List*.
- **Macros** — reachable only via Settings → Profile → "I track macros" expert toggle; never surfaced in onboarding.
- **Account / sync** — optional prompt after 7 days of use, or when the user taps *Sync / Backup* manually.

**Onboarding metric:** track drop-off per step; target > 85% of users who see step 2 completing step 3.

### 1. Roll a Meal (Main Screen)
- Select how many bases/vegetables/toppings/sauces you want
- Press the Roll! button
- Alternatively one can select a **direction** before rolling. Directions are surfaced as tappable chips above the Roll button, grouped into three categories:
  - *Cuisine*: Asian, Mediterranean, Mexican, Middle-Eastern, American, Fusion
  - *Mood*: Quick weekday, Light & fresh, Comfort, Impress someone, Use what I have, Surprise me
  - *Flavor axis*: Bold ↔ Mild, Heavy ↔ Light (two-ended sliders)
  Multiple chips can be combined (e.g. "Asian + Light & fresh"). Selected directions are translated into flavor-tag and cuisine boosts in Step B scoring — they are soft influences, not hard filters, so variety is preserved.
- One meal gets recommended
    - Nutritional Facts are Shown
    - Price for selected Supermarket
    - If Veggie quantities for supermarkets exist, use those to display the minimum portions amount.
    - [Later Feature] Compare supermarkets for best purchases.
- You can reroll the whole meal or only components.
- You can select cooking properties and force them into another direction. For example, below the vegetables a 'steaming' icon is shown. This can be clicked to open up a menu which lets the user force the vegetable selection to be able to be cooked a certain way, e.g. 'Fry' (in a pan), to reroll into a selection that the user is content with.
- **"Can't find / Don't have this"** button per component: instantly re-runs that slot's scoring with the current component excluded for this roll only (not permanently blacklisted). Returns the next-best candidate that passes all active filters. Useful at the supermarket when something is out of stock, or mid-cook when a component is missing.
- Enter a prompt to specify in which direction this should go.

- Pin that recipe by 'I wanna cook' button.
- There is also a 'save for later' button.
- If not saved an rerolled, it can be recovered anyways, there's a history at another menu that keeps track.
- One can enter recipe/shopping list format from here


### 2. Roll a Week
- Inside the Main Menu (Roll a Meal), there is a button that let's you roll a meal prep plan for the week.
- A default meal plan for the week (either app-default or the last meal plan set as default by the user) is shown.
- The user can now select which days of the week to prep how many meals.
- The user may now alter the recommended amount of different meals (and when which meal gets recommended)
- All meals get rolled.
- A similar screen to the Roll a meal screen (after roll) gets drawn.
- Here, the user can swipe left to right between the different rolled meals. This screen has the same functionalities for each of the meals as above.
- At every point one can also save/pin all recipes at once by 'I wanna cook'
- The user is asked if he wants to go shopping all at once or on different days. The shopping lists get adapted accordingly.

### 3. Rate a Meal
- To rate a Meal, the process should be quick but alternatively elaborate.
- All past eaten meals are shown which did not receive a rating yet.
- One can be selected. All four components are displayed
- The user can now give only one number or rate each component inside the meal AND give a total number too.
- There is a button that exludes a component from future meals. It will be moved on the blacklist.

### 4. Pantry & Inventory Tracker
- Invenotry gets asked upon first registration anyways
- Here, cooking equipemnt can be selected/deselected
- [LATER FEATURE] Search for nearby supermarket prices

### 5. Shopping List View
Either a user gets the Shopping list imported into the Phone-intern shopping list [FEATURE FOR LATER] or The in-app shopping list view is presented:
- Each item can be ticked
- For each item there is a modifiable field which tells the quantity of the shoppping item and its price. Both can be altered. While editing one such quantity/price you can select to save it as the new default.

### 6. Cooking Recipe View
- All Ingredients and Inventory required listed at the top
- Steps sorted such that the shortest cooking time is reached
- Base cooking Block with everything to do to cook the base
- Vegetable cooking block to cook all vegetables
  - If vegetables can be cooked in the same item, list all time steps when to add every vegatble in one vegetable cooking block.
  - If vegetables Have multiple ways of being sliced, list all possibilities in parallel.
- Sauce Cooking block
  - Can most of  the times be cooked in parallel to the vegatables.
- Optional Topping block
- Option to cook vegitables in other ways (would result in alternative recipe)
- **"Can't find / Don't have this"** button per ingredient: triggers a single-slot reroll (same logic as on the Roll screen), substituting with the next-best compatible alternative. Only the affected recipe block regenerates; the rest of the recipe is unchanged.

### 7. Component Editor
- Edit or Add Components: Bases, Vegetables, Sauces, Toppings
- Two Options:
  1. Manually Add Component
  2. Let Components be added by a prompt to an LLM. (For the user: Describe your components in words)
- Properties of Components are:
  - Category (Base,Vegetable,etc.)
  - Picture
  - Name
  - Price per kg/unit
  - Nutritional Facts (energy, carbohydrates, protein, fiber)
  - Ways to cook:
    - For each way there will open a new box which which has options for the respecive way of cooking
      - The respecitve Box contains important information for cooking this component.
      - For everything except sauces, boiling, sautéing, blanching, steaming, and roasting for example should contain a table that compares cutting sizes with cooking time
      - For those, there needs to be a box that checks if the ingredient can be cooked together with others. This is checked by default.
      - A default cooking method can be set per component (used as fallback when no preference is forced by the user)
  - Default portion size (in pc, g or ml per serving)
  - Flavor tags (e.g. savory, sweet, spicy, nutty, umami, tangy)
  - Dietary tags (e.g. vegan, vegetarian, gluten-free, dairy-free)
  - Allergens (optional)
  - Typical availability / seasonality (optional)
  - Blacklisted: toggle to exclude this component from all future recommendations

### 8. History / Meal log
A scrollable, filterable timeline of every meal the user *rolled*, *cooked*, *saved*, or *skipped*. The log is the backbone of personalization and trust ("why did it recommend this?").

- Default view: chronological list grouped by week, each row = thumbnail, name, status badge (rolled / cooked / planned / discarded), avg rating.
- Filters: status, rating, date range, ingredient, supermarket, price range, kcal range.
- Tap a row → full meal detail with the *exact* component versions used (snapshotted, so editing a component later doesn't rewrite history).
- Quick actions per row: *cook again*, *roll a variation*, *rate now*, *export recipe*, *delete*.
- Aggregated stats strip on top: meals cooked this month, € spent, avg kcal, top 3 components, longest streak.
- Untracked meals can be added manually ("I cooked something off-app") to keep stats honest.
- Privacy: log is local-first; cloud sync is opt-in.

### 9. Supermarket
Manages the *price & packaging* knowledge base that powers cost calculation and shopping lists.

- List of saved supermarkets, one marked **primary**. Each store has a name, optional location, and a per-component table of `{ pack size, pack price, last updated, source }`.
- Add prices three ways:
  1. **Manual entry** — quick form, persists as new default.
  2. **Receipt scan / photo OCR** *(later feature)* — extracts line items and matches to components.
  3. **Barcode scan** *(later feature)* — looks up packaging size, asks user for current price.
- Per component, show price history (sparkline) so the user notices when a staple gets expensive.
- Cross-store comparison view: pick 2–3 stores, see which is cheapest for the current shopping list and the *delta* in €.
- Stale-price warning: if a price is older than N days (default 30), flag it and prompt to refresh on next visit.
- Stores are local data; sharing/community price pools is a deliberate **non-goal for v1** (privacy + data quality concerns) but considered for later.

### 10. Planned Meals
- Two flavors: **single planned meal** (with portion count and target cook date) and **week plan** (output of *Roll a Week*).
- Calendar view (week / month) with a chip per planned meal; drag to reschedule, long-press to duplicate.
- Each entry tracks: target date, portions, status (planned → shopped → cooking → cooked → eaten → leftover), and links to its shopping list and recipe.
- "Cook now" button opens the Cooking Recipe View directly.
- Leftover tracking: when marked *cooked*, ask "how many portions are left?" → those count as available meals tomorrow and can suppress new rolls ("you already have 2 portions of curry").
- Notifications (opt-in): shopping reminder the day before, prep reminder N hours before cook time.

### 11. Saved for later
- A lightweight wishlist distinct from *Planned Meals* (no date attached).
- Organized by user-defined collections (e.g. "summer", "impress guests", "hangover food") plus a default "Unsorted".
- Each saved meal stores the rolled snapshot so future component edits don't break it.
- One-tap to *promote* a saved meal into Planned Meals (asks for date + portions) or *re-roll a variation* (keeps the bowl direction, rerolls components).
- Sharing: export as a link / image / printable PDF / plain-text recipe.

### X. Settings
- **Profile**: dietary mode, allergies, hard dislikes, goal, target macros, default portions, time budget, skill level — everything from onboarding, editable.
- **Kitchen**: equipment toggles, default cooking-method preferences per category.
- **Stores**: manage supermarkets, set primary, manage price-staleness threshold.
- **Recommendations**: weights for the roll algorithm (price vs nutrition vs novelty vs taste-match), blacklist manager, "forget my last N meals" slider for variety.
- **Notifications**: shopping reminders, cook reminders, weekly recap, rate-your-meal nudge.
- **Data & Privacy**: local-only vs cloud sync, export all data (JSON), delete account, anonymous usage analytics opt-in (off by default).
- **LLM features**: toggle to enable AI-assisted component creation and prompt-based rolls; choose provider (built-in / bring-your-own-key) and disclose what gets sent.
- **Appearance**: light/dark/system, units (metric/imperial), currency, language.
- **Accessibility**: text size, high-contrast palette, reduce motion, screen-reader-friendly recipe mode (one step at a time, large text, voice readout).
- **About**: version, changelog, licenses, feedback link.

## Logic

### 1. Ways of cooking
- Bases, Vegetables & Toppings
  - Boil
  - Steam
  - Blanch
  - Pan-fry
  - Roast
  - Air-fry
  - Grill
  - Bake
  - Toast (e.g. nuts, seeds, breadcrumbs)
  - Raw
  - No prep
  - Custom
- Sauces / Dressings / Dips
  - Blend (cold)
  - Blend (hot)
  - Heat
  - Whisk / mix (cold)
  - Whisk / mix (hot)
  - Reduce
  - Sauté & simmer
  - No prep
  - Custom
- Toppings
  - Boil
  - Toast
  - Pan-fry
  - Crumble
  - No prep
  - Custom

### 2. Roll Algorithm

The roll is the heart of the product. It must feel **surprising but reasonable**, **fast** (<150 ms perceived), and **explainable** (every roll can show "why these ingredients?"). It is also the part that benefits most from clear thinking about trade-offs, so the design is laid out as: hard filters → candidate scoring → assembly → post-roll critique.

#### Step A — Hard filters (must-pass, no exceptions)
Apply per component pool (bases / vegetables / toppings / sauces):
- Dietary mode (vegan, vegetarian, …) and allergens.
- Blacklisted components and components flagged by the user's "never show" list.
- Components incompatible with available kitchen equipment for *every* one of their cooking methods.
- Components whose required cooking time alone exceeds the user's time budget for the meal.
- If a "force this cooking method" constraint is active, drop components that don't support it.
- If pantry-aware mode is on (toggle, default off for v1): allow only components in pantry. (Off by default because it shrinks variety drastically.)

**Empty-result handling (when a slot has zero surviving candidates after all filters):**
Never show a blank roll or a generic error. Instead:
1. Identify which filter(s) eliminated all candidates and surface them by name in the UI.
2. Offer a single-tap relaxation for the most-restrictive filter (e.g. "Your 20-min budget excludes all roasted vegetables — extend to 30 min?" or "No vegan sauces match your equipment — add a blender?").
3. If the user declines all relaxations, fill the slot with the globally top-scored fallback component that passes only dietary + allergen filters (the two non-negotiable hard filters), badged with a "⚠ outside your usual filters" label.
4. Log which filter triggered the empty state so the component library can be expanded to cover the gap over time.

#### Step B — Candidate scoring
Each surviving component gets a score `s = Σ wᵢ · fᵢ` where `wᵢ` are user-tunable weights (defaults seeded by the onboarding *goal*) and `fᵢ` are normalized features in [0, 1]:

| Feature | What it captures | Default weight (goal "just feed me") |
|---|---|---|
| `taste_match` | predicted rating from past ratings + flavor-tag similarity | 0.30 |
| `novelty` | inverse recency (penalize components used in last N meals) | 0.20 |
| `price_fit` | closeness to per-portion budget, penalize going over | 0.20 |
| `nutrition_fit` | distance to user's macro targets (or generic balanced bowl heuristic if untracked) | 0.15 |
| `time_fit` | room left under the time budget (more = better, with diminishing returns) | 0.10 |
| `pantry_bonus` | small boost if component is already in pantry | 0.05 |

Goal presets just rebalance these (e.g. *eat cheaper* pushes `price_fit` to 0.40, *try new things* pushes `novelty` to 0.40).

#### Step C — Assembly
Two viable approaches; v1 picks the first for speed, v2 may experiment with the second:

1. **Greedy + weighted sampling (chosen for v1).** Sample one component per slot proportional to `softmax(s / T)`. Temperature `T` rises with the user's "surprise me" slider. Validate the assembled bowl against meal-level constraints (total kcal/protein band, total cook time, pairing penalties — e.g. don't pair a creamy sauce with a creamy base). If invalid, resample only the violating slot up to K times before falling back to the top-scored alternative. Cheap, deterministic enough, easy to debug.
2. **Constraint solver / beam search (later).** Treat the bowl as an optimization problem with hard nutrition/time/budget constraints and a global objective. Better quality on tight constraints (e.g. strict macros), but slower and harder to make feel "rolled" rather than "computed". Worth revisiting if users complain that rolls feel repetitive or miss their macros.

A third option — **LLM-as-recommender** — is intentionally rejected as the primary engine: too slow, too expensive per roll, non-deterministic, and a privacy concern. The LLM's role is narrower (see §LLM Usage).

#### Step D — Pairing rules (small, hand-curated rule set)
A handful of rules veto or penalize bad combinations the score function won't catch:
- One dominant flavor axis per bowl (don't stack three "spicy" components unless user asked).
- Texture variety: at least one crunchy element if topping slot is enabled.
- Cuisine coherence is *soft*: same-cuisine components get a small bonus, cross-cuisine still allowed (this is a feature, not a bug — fusion bowls are part of the appeal).
- Sauce ↔ base moisture rule: dry base (rice, quinoa) prefers wet sauce; wet base (broth bowl) prefers thicker topping.

#### Step E — Reroll semantics
- **Reroll all**: re-run Steps A–D, but with extra novelty penalty on everything in the previous roll so the user actually sees a change.
- **Reroll one slot**: rerun only that slot, keeping the others' constraints (e.g. matching the chosen base's moisture).
- **Force constraint** (e.g. "vegetable must be pan-fried"): re-runs that slot with an additional hard filter.
- **Prompt-based reroll** (free-text): the LLM translates the prompt into structured constraints (flavor tags, exclusions, cuisine, target macros) which feed back into Steps A–B. The LLM never picks the meal directly.

#### Step F — Explainability
Every rolled meal stores the top 2 reasons each component was chosen ("matches your high rating of roasted sweet potato", "fits €2.10 budget", "you haven't had this in 3 weeks"). Surfaced behind an "ℹ︎ why this?" affordance. Builds trust and gives users a lever to adjust weights.

### 3. Roll a Week algorithm
Variant of the meal roll with extra constraints across the week:
- **Ingredient overlap bonus**: prefer rolls that reuse already-shopped components on consecutive days (cuts cost & waste).
- **Variety constraint**: no component repeats more than X times per week (X depends on perishability — rice can repeat, fresh herbs shouldn't be the limiter).
- **Prep-day awareness**: meals tagged for the same prep day must share equipment-friendly cooking methods (don't ask the user to use the oven for two different temperatures simultaneously).
- **Perishability ordering**: schedule meals using the most perishable ingredients earlier in the week.
- **Leftover absorption**: if a meal cooks N>1 portions, the next 1–2 days can auto-fill with that leftover instead of a new roll (user toggleable).

### 4. Recommendation learning
- Ratings update a per-user *component affinity vector* (simple incremental average with recency decay) and *flavor-tag affinity vector*.
- Component-level rating > meal-level rating when both exist (more signal).
- A "blacklist on 1-star × 2" heuristic prompts the user: "You rated X poorly twice — exclude it?" (opt-in, never automatic).
- Cold start: until the user has rated ~10 meals, lean on onboarding goal + popularity priors derived from the curated component library.
- Collaborative filtering across users is **out of scope for v1** (requires accounts, scale, and privacy work) and revisited only if cloud sync sees meaningful adoption.

### 5. Nutrition model
- Per-portion macros = sum of `(component_grams_per_portion × component_macros_per_100g)` for the rolled portion size.
- Cooking method adjusts macros where it materially matters (oil added during pan-fry, water lost during roast — small lookup table per method).
- Daily/weekly aggregates shown in History; gentle nudge if a week is consistently below protein or fiber target, never a guilt-trip.
- Explicitly **not** a calorie tracker / fitness app: NutriRoll surfaces nutrition for *informed eating*, and integrates with HealthKit / Health Connect (export only) for users who track elsewhere.

### 6. LLM usage (scoped narrowly)
The LLM is a **tool used by features**, not the recommender:
1. Component creation from a free-text description (§7) — produces a structured component the user reviews before saving.
2. Prompt-to-constraints translation for prompt-based rolls and rerolls.
3. Recipe-step phrasing polish in the Cooking Recipe View (optional; deterministic templates are the fallback).
4. Weekly recap summary ("you tried 3 new vegetables, saved €12 vs last week").

Rules: every LLM call is opt-in at the feature level, shows what data is sent, supports a *bring-your-own-key* mode, and degrades gracefully when offline or disabled.

### 7. Pricing & shopping math
- Per-meal price = Σ `(component_grams_per_portion × portions × pack_price / pack_size)`, rounded up to the nearest *whole pack* when the shopping list is generated.
- "Minimum portions for this purchase" = floor of `(pack_size / grams_per_portion)` for the limiting component — answers the user's "how many bowls can I get out of one bag of rice?" question.
- Shopping list de-duplicates across meals in a week plan and rounds packs once at the list level, not per meal.

## Cross-cutting features (consumer value)

### Cooking companion mode
Hands-free, large-text, screen-stays-on view used *while* cooking. Reads steps aloud on tap or voice command ("next"). Auto-starts named timers per parallel block (base / vegetables / sauce / topping) with a single glanceable progress ring per block. Designed for greasy fingers — every interaction works with the back of a knuckle.

### Leftover & waste tracking
After "I cooked it", ask portions actually produced and consumed. Unused portions become *available leftovers* that:
- Suppress new rolls for the next day(s) unless the user overrides.
- Get a dedicated "use up" prompt before they spoil (per-component shelf-life table).

### Notifications (all opt-in, all batchable)
- Shopping reminder the evening before a planned cook day.
- "Rate your meal" nudge ~2 h after a planned cook time.
- Stale-price prompt when entering a saved supermarket's area.
- Weekly recap (Sunday morning by default): cooked, spent, top components, suggestions for next week.

### Sharing & export
- Export any meal/recipe as image, printable PDF, or plain-text.
- Share-link with deep-link import for other NutriRoll users (snapshot, not live reference).
- iCal export of planned meals.
- CSV/JSON export of full history, prices, ratings (data-portability is a feature, not an afterthought).

### Offline & local-first
- Core flows (roll, view recipe, shopping list, rate, history) must work offline.
- Cloud sync is **opt-in** and uses end-to-end-encrypted sync of the user's database (no server-side meal recommendations).
- LLM features clearly mark themselves as online-only.

### Accessibility
- All interactive targets ≥ 44 pt; full VoiceOver / TalkBack labels.
- Cooking companion mode passes WCAG AA contrast even in bright kitchens.
- All color cues paired with icon/text (don't rely on color for "spicy" etc.).
- Translatable strings from day one; locale-aware units & currency.

## Data model (sketch)
Conceptual entities, not a schema — informs both local DB and any future sync:

- **Component** — id, category, name, image, flavor_tags[], dietary_tags[], allergens[], default_portion {value, unit}, macros_per_100g, default_cooking_method, cooking_methods[] (each with cut→time table & co-cookable flag), shelf_life_days, blacklisted.
- **SupermarketPrice** — component_id, store_id, pack_size, pack_price, updated_at, source.
- **Store** — id, name, location?, primary?.
- **Bowl** (rolled meal) — id, components[] (snapshotted), portions, computed {macros, price_per_portion, total_time}, direction_tags[], generation_seed, explanation[] (per-component reasons), created_at.
- **Rating** — bowl_id, component_id?, score 1–5, comment?, created_at.
- **PlannedMeal** — bowl_id, date, portions, status, leftover_portions.
- **WeekPlan** — id, start_date, planned_meal_ids[], shopping_strategy (one-trip / split).
- **ShoppingList** — derived from planned meals + pantry; items[] (component_id, qty, packs, price, ticked).
- **Pantry** — items[] (component_id, qty, opened?, expires_at?).
- **HistoryEvent** — typed log (rolled / saved / planned / cooked / rated / discarded).
- **UserProfile** — dietary mode, allergens, goal, macros, time budget, skill, equipment, weights.

## Tech stack

Decided. Anything not listed here is **out of scope** until a future revision of this section.

### Platform & target
- **Mobile-first installable PWA**, served from any modern mobile browser. **Minimum browser targets: Safari on iOS 16.4+ and Chrome on Android 120+.** iOS 16.4 is the hard floor — it is the first iOS version to support web app manifests for home-screen PWAs, service workers in that context, and Web Push for installed PWAs. Users on older iOS versions will see a banner explaining that they need to update; the app will not attempt to function. Desktop is supported as a side-effect of responsive design but is not a design priority.
- **Online-by-default.** Local-first is downgraded from a goal to a *progressive enhancement*: the app works offline for already-loaded data and queues mutations, but the recommendation engine, LLM features, and shopping math run on the server.
- **No native app, no app stores, no Apple Developer account required.** Distribution is a URL.

### Frontend
- **Next.js 15** (App Router, RSC) on **React 19**, **TypeScript** strict.
- **Tailwind CSS v4** (CSS-first config, no `tailwind.config.js`) + **shadcn/ui** components (Radix primitives, generated into the repo — we own them).
- **State:** server state via **TanStack Query**, client/UI state via **Zustand**. Server Components are used for read paths where possible; mutations go through Query.
- **PWA:** installable manifest + service worker via **Serwist** (Workbox successor, Next-friendly). App-shell cache + IndexedDB for offline reads of the last-loaded data; **background sync** queue replays write mutations when connectivity returns.
- **Routing & nav:** App Router file-based routes. The 5-tab navigation table maps to a persistent bottom-tab layout component; Cooking Companion is a full-viewport route that hides the tab bar.
- **Accessibility:** Radix primitives provide keyboard + ARIA out of the box. All interactive targets ≥ 44×44 px; visible focus rings preserved.

### Backend
- **FastAPI** + **Pydantic v2** + **uvicorn**, Python 3.13, managed by **uv**.
- **PostgreSQL 17** as the only datastore. **SQLAlchemy 2.0 (async)** for the ORM, **Alembic** for migrations (one numbered migration per schema change, never edited after merge).
- **No DuckDB**, no Redis, no message broker in v1. Scheduled tasks (weekly recap, stale-price reminders) use **APScheduler** in-process; if a job ever needs to outlive a single FastAPI worker, that's the trigger to add a real queue.
- **Domain layer is framework-free:** `nutriroll/domain/` contains the roll algorithm, scoring, pairing rules, nutrition + pricing math as pure functions/dataclasses. FastAPI routers and SQLAlchemy repositories are thin adapters around it. This is the test target with the strictest coverage.
- **Single deployable.** One container image, one process per worker, horizontal scale by adding workers (none needed at v1 traffic).

### API contract
- **REST + OpenAPI.** FastAPI emits the spec; the frontend consumes it via a generated typed TS client (**openapi-typescript** + **openapi-fetch**). No hand-written API clients, no drift between server types and TS types.
- **Versioning:** URL prefix `/v1/`. Breaking changes ship under `/v2/`; old versions stay alive for one release.
- **Errors:** RFC 7807 `application/problem+json`, with a stable `code` field the frontend can branch on.

### Auth & identity
- **Anonymous device token** for v1. On first load the client generates a UUID, stores it in `localStorage`, and sends it as `X-Device-Id`. The server keys all data by this token. There are **no accounts, no email, no passwords**.
- A short-lived **HMAC session cookie** (signed `device_id` + issued-at) is set by the server to prevent trivial spoofing. Cookie is `HttpOnly`, `Secure`, `SameSite=Lax`.
- **Account upgrade** (claim a device-token's data into an email-verified account) is designed-for but not built in v1.
- **Rate limits** per `device_id` (sliding window in Postgres) on every mutation and every LLM call.

### LLM features
- **BYO-key.** The user pastes an OpenAI / Anthropic / Gemini API key in Settings.
- **Storage:** keys are encrypted at rest in Postgres using **envelope encryption** — a per-row data key wrapped by a master key held in the server's environment (rotated by deploy). The plaintext key never touches disk and never appears in logs. The server proxies all LLM calls so the key never reaches the browser after submission.
- **Per-feature opt-in**, with a "what gets sent" preview before the first call of each feature.
- All LLM call sites are funneled through a single `LLMClient` service so the provider is swappable and the wire surface is auditable.
- **Deterministic fallback is mandatory** for every LLM-touched flow (template-based recipe phrasing; manual form for component creation; chip UI for constraint inference).

### Localization
- **next-intl**, ICU message format. Launch locales: **English** and **German**. No hard-coded user-facing strings.
- Defaults: **metric** units, **EUR** currency, user-overridable in Settings.
- Server-side error messages localized via the same catalog (translated client-side from a stable `code`).

### Hosting & deployment
- **Frontend → Vercel** (Next.js native; preview deployments per PR; edge runtime where it pays off).
- **Backend → Fly.io** as a containerized FastAPI service in one region (closest to user) + **Fly Postgres** (managed, daily snapshots).
- **Secrets** in Vercel + Fly env stores. Never in the repo.
- **Domain:** single apex (`nutriroll.app` or similar), API at `api.nutriroll.app`. CORS locked to the apex origin.

### Observability
- **Logging:** structured JSON via `structlog` on the backend, request-id propagated from frontend (`X-Request-Id`).
- **Metrics:** Fly's built-in Prometheus + a single Grafana dashboard for p95 latency, error rate, LLM call rate.
- **Errors:** Sentry on both frontend and backend (free tier; off by default for the user — server-only telemetry, no PII, scrubbed payloads).
- **Analytics:** none in v1. If added later, must be self-hosted (Plausible/Umami) and aggregate-only.

### Security baseline (OWASP-aware)
- HTTPS-only, HSTS preload.
- All inputs validated by Pydantic models; SQL exclusively through SQLAlchemy parameterized queries.
- LLM key storage as described above (envelope encryption, never logged).
- CSP with no `unsafe-inline`, strict referrer policy, `X-Content-Type-Options: nosniff`, frame-ancestors `'none'`.
- Rate limits + per-device quotas on LLM endpoints to cap cost-DoS risk.
- Dependency updates via Renovate; `pip-audit` + `npm audit` in CI.

### Testing
- **Backend:** `pytest` + `httpx.AsyncClient` against the FastAPI app, ephemeral Postgres per test session via `testcontainers`. Domain layer tested as pure functions with property-based tests (`hypothesis`) for the roll-algorithm invariants ("every roll passes all hard filters", "scores normalize to 1 after softmax", "week plan never violates variety constraint").
- **Frontend:** **Vitest** + **React Testing Library** for components and hooks. **MSW** for API mocking using the generated OpenAPI types.
- **End-to-end:** **Playwright**, one happy-path test only — onboarding → first roll → "I wanna cook" → recipe view → mark cooked → rate. Runs against a docker-compose stack in CI.

### Tooling & quality gates
- **Monorepo**, no Nx / Turborepo: a `pnpm` workspace for `web/` and `uv` for `server/`, glued by a top-level `Makefile` and `docker-compose.yml` for local dev (Postgres + backend + frontend with one `make dev`).
- **Linters/formatters:** **Biome** for `web/` (lint+format in one tool), **ruff** for `server/` (lint+format), **pyright** strict for the server.
- **Pre-commit** via **lefthook** runs the relevant subset of lint/format/typecheck per changed path.
- **Conventional commits**, enforced by `commitlint`.

### CI/CD
- **GitHub Actions.** Per PR: lint + typecheck + unit tests for both projects, plus the single Playwright e2e against docker-compose.
- **Deploy on push to `main`:** Vercel auto-deploys `web/`; a GH Actions job runs `flyctl deploy` for `server/` after Alembic migrations succeed against a snapshot of prod.
- **Environments:** `preview` (per PR) and `prod`. No staging in v1 — preview deployments cover that need.

### Repository layout
```
NutriRoll/
├── PROJECT_VISION.md
├── Makefile                      # make dev | check | test | seed | deploy
├── docker-compose.yml            # postgres + backend + frontend (local dev)
├── .github/workflows/            # CI
├── web/                          # pnpm workspace root
│   ├── package.json
│   ├── app/                      # Next.js App Router
│   ├── components/               # shadcn/ui generated + bespoke
│   ├── lib/
│   │   ├── api/                  # generated OpenAPI client
│   │   ├── store/                # Zustand stores
│   │   └── pwa/                  # service worker, sync queue
│   ├── messages/                 # next-intl: en.json, de.json
│   ├── public/                   # manifest, icons
│   └── tests/                    # Vitest + Playwright
├── server/                       # uv-managed
│   ├── pyproject.toml
│   ├── nutriroll/
│   │   ├── domain/               # pure: roll algo, scoring, pricing, nutrition
│   │   ├── api/                  # FastAPI routers (thin)
│   │   ├── db/                   # SQLAlchemy models + repositories
│   │   ├── llm/                  # BYO-key proxy + provider adapters
│   │   └── jobs/                 # APScheduler tasks
│   ├── alembic/                  # migrations
│   └── tests/                    # pytest + hypothesis
├── data/
│   └── seed/                     # user-provided CSV/JSON (source of truth)
├── tools/                        # one-off scripts (seed loader, eval harness)
└── docs/
    └── adr/                      # architecture decision records
```

### Explicitly out of scope for v1 (to prevent scope creep)
- Any native app (iOS/Android/desktop), app-store distribution, push notifications via APNs/FCM.
- Multi-user accounts, social features, sharing-with-other-users beyond export to file/link.
- DuckDB, Redis, message brokers, vector DBs, on-device ML.
- Real local-first / CRDT sync. (Offline = cached reads + queued writes only.)
- Third-party product analytics, A/B frameworks.
- Any feature in §"Deferred to v1.1+" of MVP scoping below.

## MVP scoping (what to build first)
A v1 that's actually shippable and lovable:

1. Component library (curated seed of ~80 components across categories) + Component Editor (manual only; LLM creator deferred).
2. Roll a Meal with hard filters, scoring, reroll all/one, force-cooking-method, explainability.
3. Cooking Recipe View (parallel blocks, timers).
4. Shopping List View (single store, manual prices).
5. Rate a Meal + History.
6. Pantry (basic).
7. Onboarding (steps 1–4, 7, 9, 11; rest deferred).
8. Settings essentials (profile, store, blacklist, units, dark mode).

**Deferred to v1.1+**: Roll a Week, prompt-based rolls, LLM component creation, OCR/barcode price entry, multi-store comparison, leftover tracking, notifications, sharing/export, cloud sync, weekly recap.

## Monetization (options, not a decision)
NutriRoll is a daily-use utility — pick a model that doesn't poison the experience:

- **A. Free + optional one-time pro unlock** (recommended). Pro unlocks: Roll a Week, multi-store comparison, weekly recap, cloud sync, LLM features. Aligns incentives, no recurring guilt, respects local-first ethos.
- **B. Freemium subscription**. Higher LTV, but recurring fees feel hostile for a cooking app and subscriber-only recommendations would erode trust.
- **C. Affiliate links to grocery delivery** (Picnic, Rewe, Instacart). Easy to make sleazy; only acceptable as a clearly-labeled optional integration the user *asked for*.
- **D. Anonymous, aggregated price data sale** — explicitly rejected. Violates the privacy stance and would require opt-in that users would (rightly) refuse.

## Privacy & data stance
- Local-first by default; nothing leaves the device unless the user enables sync or an LLM feature.
- No analytics by default. If ever added, must be on-device aggregation with explicit opt-in.
- Full data export and account deletion in Settings. No dark patterns.
- Clear, plain-language disclosure on every screen that contacts a third party (LLM, sync, store APIs).

## Success metrics (how we know it's working)
- D7 / D30 retention of users who completed onboarding.
- Median time from app open → "I wanna cook" tap (target: < 30 s).
- Reroll count per accepted meal (very high = recommendations are bad; very low could mean too rigid — sweet spot ~1–3).
- Share of meals with a post-cook rating (proxy for trust loop closure).
- Median grocery spend per portion vs the user's stated budget.
- Variety: unique components used per active user per month.

## Open questions / explicit non-goals
**Open**
- Community-shared component library: huge content boost, hard moderation/quality problem. Decide after v1 traction.
- Voice-first roll ("Hey NutriRoll, roll me lunch"): cool, but only worth it if companion mode succeeds first.
- Restaurant / takeout integration: tempting, but blurs the product.

**Non-goals (v1)**
- Calorie/fitness tracker.
- Social network features (followers, feeds).
- Full grocery delivery checkout.
- Algorithmic personalization across users (collaborative filtering).

