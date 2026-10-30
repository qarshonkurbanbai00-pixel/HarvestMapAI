from pathlib import Path
import hmac
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.exceptions import RequestValidationError
from starlette.middleware.trustedhost import TrustedHostMiddleware
from sqlalchemy.exc import SQLAlchemyError
from .config import get_settings
from .routes import auth, catalog, admin, assistant

ROOT = Path(__file__).resolve().parent


def get_allowed_hosts():
    settings = get_settings()
    hosts = [host.strip() for host in settings.allowed_hosts.split(",") if host.strip()]
    if settings.environment == "production" or "*" in hosts:
        return ["*"]
    defaults = ["localhost", "127.0.0.1", "testserver", ".vercel.app", ".vercel.dev", ".vercel.live"]
    for host in defaults:
        if host not in hosts:
            hosts.append(host)
    return hosts


app = FastAPI(
    title="HarvestMap AI",
    description="Жергілікті кәсіптер, маусымдық өнімдер және карта API. Демо деректер нақты нарық деректері емес.",
    version="1.0.0",
    docs_url=None,
    redoc_url=None,
)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=get_allowed_hosts())


@app.middleware("http")
async def security_headers(request: Request, call_next):
    if (
        request.method in ("POST", "PUT", "PATCH", "DELETE")
        and request.cookies.get("harvest_session")
        and not request.headers.get("authorization")
    ):
        cookie = request.cookies.get("harvest_csrf", "")
        header = request.headers.get("x-csrf-token", "")
        if not cookie or not hmac.compare_digest(cookie, header):
            return JSONResponse({"detail": "Қауіпсіздік белгісі жарамсыз. Бетті жаңартыңыз."}, status_code=403)
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "geolocation=(self)"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https://*.tile.openstreetmap.org; connect-src 'self'; font-src 'self'; object-src 'none'; base-uri 'self'; frame-ancestors 'none'; form-action 'self'"
    )
    if request.url.path.startswith("/api/auth") or request.url.path.startswith("/api/admin") or request.url.path.startswith("/api/owner"):
        response.headers["Cache-Control"] = "no-store"
    return response


@app.exception_handler(RequestValidationError)
async def validation_error(request, exc):
    return JSONResponse(
        {
            "detail": "Енгізілген деректерді тексеріңіз",
            "errors": [
                {"field": ".".join(str(x) for x in e["loc"][1:]), "message": "Мәннің пішімі немесе ұзындығы жарамсыз"} for e in exc.errors()
            ],
        },
        status_code=422,
    )


@app.exception_handler(SQLAlchemyError)
async def database_error(request, exc):
    import logging

    logging.getLogger("harvestmap").exception("Database operation failed", exc_info=exc)
    return JSONResponse({"detail": "Дерекқор қатесі. Орнатуды және миграцияларды тексеріңіз."}, status_code=503)


for router in (auth.router, catalog.router, admin.router, assistant.router):
    app.include_router(router)
app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")


@app.get("/health")
def health():
    from sqlalchemy import text
    from .database import SessionLocal

    try:
        with SessionLocal() as db:
            db.execute(text("SELECT id FROM users LIMIT 1"))
        return {"status": "ok", "version": "1.0.0"}
    except SQLAlchemyError:
        return JSONResponse({"status": "database_unavailable"}, status_code=503)


@app.get("/docs", include_in_schema=False)
def docs():
    return FileResponse(ROOT / "templates" / "docs.html")


@app.get("/", include_in_schema=False)
def index():
    return FileResponse(ROOT / "templates" / "index.html")
