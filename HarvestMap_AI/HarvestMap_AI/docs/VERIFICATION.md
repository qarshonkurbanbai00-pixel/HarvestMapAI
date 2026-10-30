# Executed verification report

Build verification date: **2026-10-28**. This report distinguishes executed checks from supplied but untested options. It is not a security audit or production-readiness certificate.

## Environment and dependency checks

- Python 3.12.3 and Node.js 22.23.4 on Linux.
- Installed the exact `requirements-dev.txt` dependency set into a **new Python virtual environment**; installation succeeded.
- Separately installed only `requirements.txt` into a **second clean virtual environment** and generated `requirements-lock.txt` from its complete runtime dependency set.
- Browser libraries are bundled locally: Leaflet 1.9.4, Chart.js 4.4.9 and Swagger UI 5.17.14, including upstream licenses and Leaflet UI assets.
- Application JavaScript was syntax-checked with `node --check`; all application Python, migrations and test modules were compiled successfully.
- `ruff check app scripts tests migrations`: **passed**. This is the configured fatal/syntax/undefined-name ruleset, not an assertion of comprehensive style or security linting.

## Automated Python suite

Command actually executed in the clean verification environment:

```text
python -m pytest -q --cov=app --cov-report=term-missing
37 passed, 1 warning
TOTAL: 94% application statement coverage
```

Covered behaviors include Argon2 password storage, registration, login, duplicate-email rejection, non-admin self-registration, password length, profile edits, token revocation, logout, password changes, double-submit CSRF, authorization/ownership, rate limits, security headers, Unicode search, sorting/filtering/pagination, location CRUD and referenced-location protection, pending-listing visibility, parent/product moderation, role changes and deactivation, product/business CRUD, deletion cascades, validation and decimal precision, actual price history, GeoJSON coordinate order, layers, radius and bbox queries, antimeridian bounds, seasonal products and cross-year seasons, platform statistics, recorded-price trends, no-key assistant answers and source links, mocked provider success/failure, local assets/OpenAPI, and migration upgrade/downgrade/seed idempotency.

The upstream Starlette test client emits a deprecation warning about its `httpx` compatibility path. The test suite still completes successfully; this is not suppressed or represented as a zero-warning run. Optional `httpx2` was not required for this verified dependency set.

Coverage is statement coverage of application modules during pytest. It does not measure browser test coverage, production load, every possible input, or external-service behavior.

## Real Chromium integration checks

`python -m scripts.browser_check` was executed successfully against its own temporary migrated/seeded SQLite database, using random disposable credentials and a live local FastAPI server. It passed these workflow groups:

1. Desktop landing, navigation, seeded cards and Kazakh document language.
2. Actual server pagination, Kazakh search, two-offer comparison dialog and product history chart.
3. Leaflet overlay/category requests, marker popup, simulated nearby geolocation, viewport filtering and visible OSM attribution.
4. Business profile with embedded Leaflet map and locally served interactive Swagger/OpenAPI documentation.
5. Dashboard chart canvases/data and the database-backed no-key assistant with actual stored prices.
6. Owner registration, HttpOnly-cookie login, profile edit and business/product form submissions.
7. Separate admin login, business/product approval and location creation.
8. Public visibility after moderation, owner price update, return-to-pending behavior and confirmed product deletion.
9. Password change, logout, login with the new password and session persistence across page reload.
10. Mobile menu/navigation and horizontal-overflow checks for home, map, products, businesses, dashboard, assistant and account at 390px; tablet dashboard at 820px. Desktop used 1440px.
11. **Zero uncaught browser JavaScript errors** in the final successful run.

An earlier run exposed a Leaflet zoom-transition callback firing after map teardown. The implementation was corrected to disable animated map zoom transitions and stop/remove the map on route changes; the entire browser check was rerun successfully afterward. Normal map zoom and page/CSS animations remain functional.

Screenshots of desktop/mobile landing pages were generated and visually inspected during verification. They are not required runtime assets. Browser geolocation was simulated and external tile requests were deliberately blocked, exercising the documented no-background map fallback rather than claiming verified network tile delivery.

## Database installation and geography

- Fresh SQLite `alembic upgrade head`: **passed**.
- Idempotent demo seed executed twice: **passed**, 6 locations, 8 businesses, 16 products, 96 history entries and no usable seeded login accounts.
- SQLite migration downgrade to base and schema removal: **passed** in an isolated test database.
- `alembic check` against the migrated SQLite database: **no new upgrade operations detected**.
- Installed a real local PostgreSQL 16 server with PostGIS 3.4 in the verification environment.
- PostgreSQL/PostGIS `alembic upgrade head` and demo seed: **passed**.
- `python -m scripts.postgres_check`: **passed** for the extension, generated geography columns, GiST indexes, SRID 4326, Unicode search, native `ST_DWithin` candidate queries, bounding-box queries, GeoJSON, statistics/trends and health endpoint.
- A temporary PostgreSQL coordinate edit was flushed, the corresponding generated geography coordinate checked, and the transaction rolled back: **passed**.
- `alembic check` against PostgreSQL: **no new upgrade operations detected**. Reflection emits a SQLAlchemy warning for the intentionally unmapped `geography` type; migration-owned spatial columns/indexes and PostGIS's `spatial_ref_sys` are explicitly excluded from portable ORM autogeneration so they are not accidentally removed.

## Delivery checks

`scripts/package.py` checks the required-file list, excludes `.env`, databases, virtual environments, caches and generated artifacts, writes a SHA-256 source manifest, reopens the ZIP, runs CRC validation and verifies every manifest hash. The archive is rooted at `HarvestMap_AI/` and named `HarvestMap_AI.zip`. The final delivery also receives an extraction/fresh-setup smoke check; no preexisting application database or secrets are required.

## Not executed / not claimed

Docker image build and Compose startup (Docker was unavailable); actual paid/external AI calls; real GPS/device permission behavior; successful external OSM tile delivery; Windows/macOS setup; Safari/Firefox; native mobile devices; production deployment; formal linguistic/accessibility review; load or penetration testing. AI provider branches were mocked, not represented as real model-service tests. See LIMITATIONS.md and SECURITY.md for scope and operational boundaries.
