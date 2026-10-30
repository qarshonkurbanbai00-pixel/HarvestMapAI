# Security design and deployment checklist

## Implemented controls

Argon2id via pwdlib; random required HS256 signing secret; expiring JWTs with per-user version revocation; HttpOnly SameSite=Strict session cookies; double-submit CSRF for cookie-authenticated writes; independent bearer authentication for API clients; ownership checks on both source and destination business when editing a product; admin-only moderation/location writes/role changes; hidden unapproved catalog entries; role validation preventing self-registration as admin; inactive-account rejection; generic login errors with dummy-hash verification; field/range/precision validation; SQLAlchemy-bound queries; strict HTTP(S) website validation and frontend HTML escaping; restrictive CSP, frame denial, no-sniff, referrer policy and trusted hosts. API secrets are server-only. No private credentials are shipped.

Logout invalidates all sessions for that user, not only the current browser. Password changes reissue the current session and revoke older ones. Admin role/active-state changes revoke existing tokens. Users cannot mutate their own role; an admin cannot demote/deactivate their own account from the API. Cookies are Secure only with SECURE_COOKIES=true; local HTTP intentionally uses false. Keep the default single-origin architecture rather than opening CORS broadly.

The assistant has no write tools, SQL execution tool, arbitrary URL fetcher or access to private users. The backend selects read-only catalog/statistics/trend evidence. Listing descriptions and questions are treated as untrusted content in the provider system prompt. That reduces but cannot mathematically eliminate prompt injection or hallucinations. Deterministic fallback is available without any provider.

## Before public use

1. Use TLS and exact host/proxy settings; ENVIRONMENT=production requires SECURE_COOKIES=true.
2. Generate independent secrets per installation; never commit .env, DB backups or login tokens. Rotate SECRET_KEY to invalidate all issued tokens if leaked.
3. Provision PostGIS as DBA, then use a least-privilege app role; do not copy the local Compose superuser setup into production.
4. Configure DB backups, restore drills, encryption/access control and log retention. Migrations may be destructive when downgraded.
5. Place shared rate limiting, request-body limits, bot/abuse protection and model-budget controls at a trusted gateway. In-process rate limits are not distributed.
6. Add email ownership verification, recovery and MFA if the business context needs them. None is claimed here.
7. Review public documentation exposure, dependency updates, privacy/provider terms, OSM tile policy, data retention and moderation procedures.
8. Add a transactional audit log for administrative/price changes if regulatory or commercial use requires one.

Health verifies application schema reachability, not external providers or tile services. Production readiness is not a security certification. Report issues to your own project maintainer through a private channel; no fictional security email is supplied.
