# HarvestMap AI

A complete, local-run, full-stack discovery platform for local businesses and seasonal agricultural products. The application interface is in Kazakh. This repository includes the actual FastAPI backend, database migrations, responsive frontend, vendored browser libraries, sample data, and automated API/browser checks. No frontend build step, paid map token, or AI credential is required.

> **Demo, not verified market data.** All seeded businesses, offers, addresses and price histories are fictional educational examples. City names and approximate city coordinates are used only to make the map meaningful. Nothing in this project represents verified businesses, real availability, national economic statistics, or a forecast. Newly submitted listings are explicitly described as user-entered data, not externally verified facts.

## What works

- Responsive landing page, business directory, marketplace, product/business profiles and account pages; Kazakh labels, loading/error/empty states, notifications, keyboard navigation, responsive menus and reduced-motion support.
- Search, categories, locations, price ranges, unit filters, sorting and server-side catalog pagination. Unicode-aware Kazakh search in SQLite and PostgreSQL.
- Leaflet map with zoom, separate business/product overlay layers, markers, details/popups, category and stored-location search, viewport bounding-box filters and nearby search using browser geolocation. OSM attribution is always visible.
- Price comparison for up to four offers, with warnings against comparing incompatible units/products; per-product price-history charts and accessible data tables.
- Registration, login, cookie sessions, profile edits, password changes and logout; user, owner and admin permissions. Owners create/edit/delete businesses and products through real API-connected forms.
- Admin moderation of businesses/products, user role and active-state management, location CRUD. New or edited listings return to pending status; public APIs exclude them until approved.
- Data-derived statistics, category/region charts, same-name/same-unit price summaries, actual recorded-price trend endpoints.
- Controlled, read-only assistant functions: public catalog search, platform statistics and recorded-price trends. No-key mode queries the database; an optional OpenAI-compatible provider receives only selected public application data. Provider failures automatically fall back to database search.
- PostgreSQL/PostGIS geography columns and GiST indexes; native `ST_DWithin` candidate filtering. Credential-free SQLite alternative with validated numeric coordinates, bounding-box filters and Haversine distance.
- Alembic upgrade/downgrade migrations, idempotent demo seed, interactive local Swagger documentation, health check, Docker Compose, tests, CI and packaging script.

## Prerequisites

**Recommended and tested:** Python 3.12, pip, and a modern browser. Tested database engines: SQLite (bundled with Python) and PostgreSQL 16 with PostGIS 3.4. Node.js is not needed to install or run the application. Docker and Docker Compose v2 are optional. Internet is needed to install Python dependencies and load the OSM tile background; the app's JavaScript/CSS, charts, API docs and data do not use a runtime CDN.

Use commands from the extracted **`HarvestMap_AI/`** directory. Do not open `index.html` directly: use the FastAPI server so APIs, cookie security and local assets work correctly.

## Local installation — SQLite, no external credentials

### macOS / Linux

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
python scripts/configure.py
python -m alembic upgrade head
python -m scripts.seed
python -m scripts.create_admin --email your-admin@example.com --name 'Әкімші'
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

`create_admin` prompts privately for your own password twice. The email is an example argument: replace it with yours. There are **no default login credentials**. The demo-data owner is intentionally inactive and has a cryptographically random, undisclosed password. The seed does not create usable admin or owner login accounts.

### Windows PowerShell

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python scripts/configure.py
python -m alembic upgrade head
python -m scripts.seed
python -m scripts.create_admin --email your-admin@example.com --name 'Әкімші'
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

If PowerShell activation is restricted, invoke `.\.venv\Scripts\python.exe` in place of `python`; activation itself is not required. `scripts/start.sh` and `scripts/start.ps1` are convenience launchers after dependencies and `.env` exist. They run migrations but do not silently insert demo data.

Open **http://127.0.0.1:8000**. Use one hostname consistently: switching between `localhost` and `127.0.0.1` changes the cookie origin. Interactive API docs: **http://127.0.0.1:8000/docs**. Raw OpenAPI: `/openapi.json`. Readiness: `/health`.

`python scripts/configure.py` creates `.env` from `.env.example`, inserting fresh random application and database secrets. It will never overwrite an existing `.env`. Keep `.env` private. A missing, short or unmodified placeholder `SECRET_KEY` stops startup with a configuration error. No application database is included in the ZIP; migrations and the seed create it locally.

The sample seed is optional and repeatable. Omit it to start empty. On an empty database, create an admin, then add locations in the admin panel before owners submit businesses. To reset a **disposable SQLite installation only**, stop the app, remove your local `harvestmap.db`, rerun migrations and optionally the seed. This permanently deletes that local database; back it up first.

## PostgreSQL + PostGIS without Docker

Create a database and a suitable application role in your own PostgreSQL instance. Install PostGIS 3 and have an authorized database administrator enable it:

```sql
CREATE EXTENSION IF NOT EXISTS postgis;
```

Change `.env`:

```dotenv
DATABASE_URL=postgresql+psycopg://YOUR_USER:URL_ENCODED_PASSWORD@127.0.0.1:5432/YOUR_DATABASE
```

Then run the same migration, seed and admin-creation commands. Passwords containing URL-reserved characters must be URL-encoded. No credentials above are usable secrets. Migration `0002_postgis` enables the extension if permitted, creates SRID-4326 generated geography points for locations/businesses, and GiST indexes. On managed databases, provision the extension first if the app role cannot create extensions. The generated geometry automatically follows coordinate updates. SQLite skips PostGIS-specific DDL and needs no spatial extensions.

PostGIS accelerates nearby candidates using geography meters. Application responses use spherical Haversine kilometers for portable, consistent distance presentation/filtering. Tiny boundary differences between geodesic and spherical distances can occur. All API coordinates are validated: latitude −90…90, longitude −180…180. GeoJSON is **[longitude, latitude]**; Leaflet is **[latitude, longitude]**. `bbox` is `west,south,east,north` and supports antimeridian-crossing bounds.

## Optional Docker Compose

Docker Compose configuration is supplied but was **not executed in the build environment**, because Docker was unavailable there. PostgreSQL/PostGIS migrations, seed and integration checks were separately executed against a real local PostgreSQL/PostGIS instance.

```sh
python scripts/configure.py
docker compose up --build -d
docker compose exec web python -m scripts.seed
docker compose exec web python -m scripts.create_admin --email your-admin@example.com
```

The web service runs migrations on startup and waits for PostgreSQL's health check. It uses `postgis/postgis:16-3.4`, persists data in the `postgres_data` named volume, and only publishes the web port on `127.0.0.1:8000`; it does not publish the database port. The generated `POSTGRES_PASSWORD` contains URL-safe characters. Compose overrides `DATABASE_URL` inside the container, so your local SQLite setting is not accidentally used. No AI key is necessary.

`docker compose down` stops services and retains the database. `docker compose down -v` **permanently removes** the Compose database volume. Back up data before destructive operations. Build/update this container yourself before production use; container build behavior is not claimed to have been tested here.

## Core workflows

1. Register with **Кәсіп иесімін** to create an owner account; ordinary users select **Өнім іздеймін**. Self-registration can never grant admin rights.
2. Open **Жеке кабинет → Кәсіптерімді басқару**. Add a business, selecting an existing location and valid coordinates. New businesses are pending.
3. Add products with price, unit, stock and start/end months. December-to-March seasons work. Price and stock accept at most two decimals. KZT is the sole supported currency.
4. Sign in separately with your locally created admin. **Әкімші панелі** lists pending/rejected records; approve the business and its products independently. A product is visible only if both it and its parent business are approved.
5. Explore approved records in the directory, marketplace and map. Add up to four products to compare. Business profiles show the seller's details; no purchase/payment is implied.
6. Owner edits automatically reset approval. A changed price appends a history row; an unchanged price does not. Deleting a business deletes its products and history. The UI requires confirmation before deletion.
7. Administrators may change other users' roles or deactivate accounts. They cannot demote/deactivate themselves through this screen. Changes revoke the user's previous sessions. Admins can open **Барлық жазбаны өңдеу** to inspect/edit any full record.
8. Admins add/edit/delete locations. Deleting a location referenced by a business returns 409 rather than orphaning the business.

## AI assistant

The default is **no-key deterministic retrieval**, not an LLM pretending to answer. It uses Unicode word/prefix matching over public names/descriptions/locations, optional current-season filtering, and controlled statistics/trend functions. It shows product/business links and demo labels. It can answer questions such as `Қызанақ бағасы`, `Алматыда қандай кәсіптер бар`, `Маусымдық өнімдер`, `Платформа статистикасы`, or `Қызанақ баға тренді` using stored values. It is a lightweight keyword assistant, not a general conversational agent; rephrase with a product or location name if no results match. Conversation history is visible only in the current browser view and is not stored server-side.

Optional `.env` settings:

```dotenv
AI_API_KEY=
AI_BASE_URL=https://api.openai.com/v1
AI_MODEL=gpt-4o-mini
```

Supply your own key/model only if desired. The provider must implement `POST /chat/completions` with the usual `messages`, `choices`, `temperature` and `max_tokens` fields. No model key or private user record reaches browser JavaScript. The backend computes the evidence itself: the model cannot execute SQL, call arbitrary tools, access private accounts, make writes, or choose request URLs. Selected public listing content and your question are sent to the provider, so do not put personal information in questions. Provider behavior can vary; unsupported parameters, timeouts or malformed responses trigger fallback.

No real external AI request was made during verification. Success/failure provider branches were tested with mocks; actual account/model availability is not asserted. Even evidence-grounded LLM text may be inaccurate, so the UI advises checking source records. Retrieval-only mode avoids generative claims entirely.

## API quick reference

All application routes use `/api`. Detailed parameter schemas and bodies are in the locally bundled `/docs` interface; no CDN is needed to open it. Swagger's developer-tool chrome is the upstream English interface; the actual application is Kazakh.

| Area | Endpoints |
|---|---|
| Authentication | `POST /auth/register`, `POST /auth/login`, `GET/PATCH /auth/me`, `POST /auth/password`, `POST /auth/logout` |
| Locations | `GET/POST /locations`, `PUT/DELETE /locations/{id}` |
| Businesses | `GET/POST /businesses`, `GET/PUT/DELETE /businesses/{id}` |
| Products | `GET/POST /products`, `GET/PUT/DELETE /products/{id}` |
| Owner | `GET /owner/catalog` (all statuses for that owner; admin sees all) |
| Map | `GET /map` returns GeoJSON FeatureCollection |
| Analytics | `GET /statistics`, `GET /statistics/trends?product_id=ID` |
| Assistant | `POST /assistant` with `{"message":"Қызанақ бағасы"}` |
| Admin | `GET /admin/queue`, `PATCH /admin/{businesses\|products}/{id}/status`, `GET /admin/users`, `PATCH /admin/users/{id}` |

Examples of public queries (relative URLs):

```text
/api/products?q=алма&category=fruit&sort=price_asc&page=1&size=12&unit=кг
/api/products?seasonal=true&min_price=100&max_price=900
/api/businesses?category=farm&location_id=1&sort=newest
/api/map?kind=product&lat=43.2389&lon=76.8897&radius_km=25
/api/map?bbox=76.5,43.0,77.5,43.6&kind=business
/api/statistics/trends?product_id=1
```

Product sorting is `name`, `price_asc`, `price_desc`, or `newest`; business sorting is `name` or `newest`. Catalog pages start at 1 and sizes are 1…100. Stats cover only approved records. Trend changes compare the first and latest recorded prices for each individual listing; they are not national inflation, seasonal forecasts, or a standardized historical index. Seasons use the current UTC month.

For programmatic protected requests, use `Authorization: Bearer <access_token>` returned by login/register. Browser sessions use `harvest_session` (HttpOnly, SameSite Strict) and double-submit CSRF: mutating cookie-authenticated requests need the `harvest_csrf` cookie value in `X-CSRF-Token`. The frontend and Swagger request interceptor do this automatically. Tokens expire after `ACCESS_TOKEN_MINUTES` (120 by default). Logout/password/role changes revoke old tokens with a server-side token version. There is no silent refresh token: log in again after expiration.

Errors use appropriate HTTP statuses and Kazakh `detail` messages. Validation errors also include an `errors` array naming fields. `409` signals a duplicate account, referenced location, or protected self-role change. Missing or hidden listings return `404`. Public documentation is intentional for local development.

## Project structure

```text
HarvestMap_AI/
  app/
    main.py                 FastAPI app, headers/CSRF, local frontend and docs
    config.py               validated environment configuration
    database.py             SQLAlchemy sessions, SQLite Unicode support
    models.py               users, locations, businesses, products, price history
    schemas.py              typed input validation
    security.py             Argon2, JWTs, RBAC, bounded rate limiter
    services.py             serialization, analytics, trends, geography
    routes/                 auth, catalog/map, admin, assistant
    templates/              application shell and API documentation page
    static/css/             responsive design and animations
    static/js/              SPA, API client, forms, Leaflet, Chart.js, docs setup
    static/vendor/          pinned local libraries and their licenses
  migrations/               portable schema and optional PostGIS migration
  scripts/                  configure, seed, admin, start, checks, packaging
  tests/                    pytest API/security/migration/analytics tests
  docs/                     verification report, limitations and security notes
  .github/workflows/        repeatable CI checks
  requirements*.txt         exact versions used in verification
  requirements-lock.txt     clean-environment transitive dependency lock
  .env.example              configuration template, no usable secrets
  Dockerfile / compose.yaml optional local containers
  alembic.ini / pyproject.toml
  LICENSE / THIRD_PARTY_NOTICES.md
```

The single-page frontend is plain maintainable JavaScript/HTML/CSS. Hash routes allow page refreshes without an SPA rewrite proxy. Vendor code is isolated and unmodified. SQLAlchemy relationships implement deletion cascades; Alembic owns schema creation, not a hidden `create_all()` on app startup. Tests use an isolated in-memory DB and an isolated migrated on-disk DB, never your own configured database for destructive tests. `scripts.postgres_check` explicitly requires a pre-migrated/seeded PostgreSQL database and rolls back its single temporary coordinate write.

## Tests and repeatable quality checks

```sh
python -m pip install -r requirements-dev.txt
python -m pytest -q --cov=app --cov-report=term-missing
python -m ruff check app scripts tests migrations
python -m compileall -q app scripts tests migrations
```

Real Chromium browser checks:

```sh
python -m playwright install chromium
# On a supported Linux desktop/server, install OS libraries if Playwright requests them:
# sudo .venv/bin/python -m playwright install-deps chromium
python -m scripts.browser_check
```

The browser check creates a temporary DB, runs migrations and seed, generates disposable credentials, starts a local server on a free port, checks actual workflows and removes its test database afterward. It intentionally blocks external OSM tiles to check offline-background behavior while still testing real Leaflet markers, layers, popups, geolocation and viewport requests. Run the app normally with internet to obtain map tiles. Browser tests do not depend on a real AI provider. Optional `HARVEST_SCREENSHOT_DIR` saves screenshots outside the source tree.

For an already migrated and demo-seeded test PostgreSQL DB:

```sh
# Set DATABASE_URL in your environment to the intended test database.
python -m scripts.postgres_check
```

See **`docs/VERIFICATION.md`** for the checks actually executed and their results, and **`docs/LIMITATIONS.md`** for what is deliberately not claimed. `requirements-lock.txt` was resolved in a clean Python 3.12 environment; for exact runtime dependency reproduction install it instead of `requirements.txt`. Development/test tools remain in `requirements-dev.txt`.

## Security and operational boundaries

This is a complete local application, not a claim of audited production readiness. Argon2 passwords, expiring HS256 tokens, per-user token revocation, role/ownership checks, CSRF, escaping, safe HTTP(S) links, parameterized queries, host validation, input bounds and protective headers are implemented. No token is persisted in browser localStorage. Registration/login and assistant endpoints have bounded per-IP, in-process rate limiting. Use a shared gateway/Redis limiter if deploying multiple workers.

Before any public deployment: terminate TLS; set `ENVIRONMENT=production`, `SECURE_COOKIES=true`, strong unique `SECRET_KEY`, and exact `ALLOWED_HOSTS`; use a least-privilege database user after provisioning PostGIS; add backups/monitoring, an external limiter, trusted proxy configuration, secrets management and abuse controls. The current local Docker setup is not a hardened production deployment. See `docs/SECURITY.md`.

No payment processing, orders, messaging, email verification/recovery, real-world verification, file uploads, live price feeds, public geocoder, business opening hours or national statistics feed is included. These were not silently replaced with inert buttons. The implemented product is a discovery/listing/analysis application: contact the seller separately. Map performance and aggregation are designed for local/small datasets; the API caps returned map features at 1000 and the sidebar at 40. Admin queues are not paginated. Add clustering, SQL aggregation and pagination for large production datasets.

## License, attribution and reproducible archive

Project-authored code is MIT-licensed; upstream libraries retain their own licenses in `app/static/vendor/`. Map data is credited to OpenStreetMap contributors. Follow the OSM tile-use policy if you host this beyond local testing; do not bulk-download or prefetch standard tiles. Emoji appearance follows the host system; no external stock imagery is required. See `THIRD_PARTY_NOTICES.md`.

To regenerate an archive excluding `.env`, databases, caches, virtual environments and test artifacts:

```sh
python -m scripts.package
```

It creates `HarvestMap_AI.zip` beside this directory, includes a SHA-256 file manifest and checks archive integrity. The delivery archive contains source, configuration examples and documentation, not a preinstalled Python interpreter, dependencies, login accounts, private keys, or a database with hidden state.
