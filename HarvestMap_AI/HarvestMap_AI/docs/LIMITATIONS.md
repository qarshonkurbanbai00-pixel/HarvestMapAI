# Honest implementation boundaries

## Implemented alternatives

- **No AI credential:** deterministic data retrieval with sources, demo labels, statistics and actual stored-price changes. Natural-language understanding is keyword/prefix based. Optional provider summarization is constrained to public evidence but cannot be guaranteed hallucination-free.
- **No PostgreSQL:** SQLite with Unicode search and Haversine/bounding-box map queries is fully functional. PostgreSQL/PostGIS additionally has generated SRID-4326 geography columns, GiST indexes and native `ST_DWithin` candidate queries.
- **No map network:** the local Leaflet runtime, markers, filters, lists and popups still work, but the OSM background cannot display. City/location search uses application records, not an external global address geocoder. No map token is needed.
- **Economic statistics:** actual counts/distributions and recorded listing prices within this database only. No invented employment, GDP, sales volume or verified national indicators. Demo price changes are labeled synthetic.

## Deliberately not included

Payments/orders/checkout; fulfillment; email verification or reset email; user email changes; product image upload/storage; live data ingestion; externally verified business identities; global geocoding/routing; automatic stock reservations; multiple currencies; persistent assistant history; business review ratings; a general-purpose autonomous AI agent. There are no nonfunctional controls promising these operations.

Product illustrations are Unicode emoji with local CSS rather than actual seller photos. Prices and stock are entered by owners and may be stale. Moderation approves publication; it does not authenticate external commercial reality. A product's historical rows become public again after an edit is approved; a history row is not independently moderated. Changing a listing's name/unit does not rewrite its old history, so use a new listing for a materially different product/unit. Same-name/unit comparisons do not establish identical quality or variety.

The map returns at most 1000 features and explicitly reports truncation. Sidebar details show the first 40; zoom/filter further to narrow results. Products may overlap with their business marker at exactly the same coordinates; separate overlay controls let you inspect each layer. Marker clustering is not implemented. Statistics and assistant retrieval load public records for local-scale aggregation. Admin queues/user lists and owner catalogs are not paginated. Do not treat this as a large-dataset performance benchmark.

In-process rate limits are single-worker only, tied to request-client IP, and are cleared on restart. No password reset, MFA or persistent audit trail is claimed. Cookie sessions expire; the frontend has no refresh-token mechanism. HTTPS is required for public deployment and non-local browser geolocation. Public provider requests are rate-limited but have no per-account billing quota. Production hardening and an independent security review are still needed.

## Testing limits

See VERIFICATION.md for observed results. SQLite API and real Chromium workflows, PostgreSQL 16/PostGIS 3.4 migrations/native geography and generated-column edits were executed. Docker Compose was supplied but could not be built/run because Docker was unavailable. Real external AI-provider calls were not made; provider success/failure paths used mocks. OSM network tile delivery and actual device GPS were not verified: browser geolocation was simulated and tile requests intentionally blocked. Native Safari/Firefox, real mobile devices and Windows/macOS execution were not tested. Responsive checks used Chromium viewports. No load test, penetration test, external accessibility audit, production deployment or formal linguistic review is claimed.
