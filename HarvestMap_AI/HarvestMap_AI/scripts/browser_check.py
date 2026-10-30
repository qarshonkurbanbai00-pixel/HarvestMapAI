"""Real Chromium integration checks against a fresh, migrated, seeded database.
Run: python -m scripts.browser_check
Optional screenshots: HARVEST_SCREENSHOT_DIR=/tmp/previews python -m scripts.browser_check
No external tiles or AI provider required. No real credentials stored.
"""

from pathlib import Path
import os
import secrets
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parents[1]


def main():
    with tempfile.TemporaryDirectory(prefix="harvest-e2e-") as tmp:
        env = os.environ.copy()
        env["DATABASE_URL"] = "sqlite:///" + str(Path(tmp) / "browser.db")
        env["SECRET_KEY"] = secrets.token_urlsafe(48)
        env["AI_API_KEY"] = ""
        env["SECURE_COOKIES"] = "false"
        env["ENVIRONMENT"] = "development"
        password = secrets.token_urlsafe(20)
        admin_password = secrets.token_urlsafe(20)
        env["E2E_ADMIN_PASSWORD"] = admin_password
        for command in [[sys.executable, "-m", "alembic", "upgrade", "head"], [sys.executable, "-m", "scripts.seed"]]:
            subprocess.run(command, cwd=ROOT, env=env, check=True, capture_output=True)
        # Only this test subprocess receives the generated admin password.
        setup = Path(tmp) / "setup_admin.py"
        setup.write_text(
            "import os\nfrom app.database import SessionLocal\nfrom app.models import User\nfrom app.security import password_hash\nwith SessionLocal() as db:\n    db.add(User(email='browser-admin@example.com',name='Сынақ әкімші',role='admin',password_hash=password_hash.hash(os.environ['E2E_ADMIN_PASSWORD'])))\n    db.commit()\n"
        )
        env["PYTHONPATH"] = str(ROOT)
        subprocess.run([sys.executable, str(setup)], cwd=ROOT, env=env, check=True)
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            port = sock.getsockname()[1]
        base = f"http://127.0.0.1:{port}"
        with (Path(tmp) / "server.log").open("w") as log:
            server = subprocess.Popen(
                [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", str(port)],
                cwd=ROOT,
                env=env,
                stdout=log,
                stderr=log,
            )
            try:
                for _ in range(100):
                    try:
                        with urllib.request.urlopen(base + "/health", timeout=1) as response:
                            if response.status == 200:
                                break
                    except Exception:
                        time.sleep(0.1)
                else:
                    raise RuntimeError("Test server failed to start")
                with sync_playwright() as playwright:
                    browser = playwright.chromium.launch(headless=True, args=["--no-sandbox"])
                    context = browser.new_context(
                        viewport={"width": 1440, "height": 1000},
                        locale="kk-KZ",
                        permissions=["geolocation"],
                        geolocation={"latitude": 43.2389, "longitude": 76.8897},
                    )
                    # Network independence: intentionally exercise the documented tile-unavailable path.
                    context.route("**/*.tile.openstreetmap.org/**", lambda route: route.abort())
                    page = context.new_page()
                    errors = []
                    page.on("pageerror", lambda error: errors.append(error.stack))

                    def go(path, title=None):
                        page.goto(base + "/#/" + path)
                        if title:
                            expect(page.locator("main h1")).to_contain_text(title)

                    go("", "Жергілікті өнім")
                    assert page.locator("html").get_attribute("lang") == "kk"
                    expect(page.locator(".card")).to_have_count(8)
                    screenshots = os.environ.get("HARVEST_SCREENSHOT_DIR")
                    if screenshots:
                        Path(screenshots).mkdir(parents=True, exist_ok=True)
                        page.screenshot(path=str(Path(screenshots) / "desktop-home.png"), full_page=True)
                    print("PASS desktop landing, navigation, seeded cards")
                    go("products", "Өнімдер нарығы")
                    expect(page.locator(".card")).to_have_count(12)
                    page.locator("button[data-action=page]").last.click()
                    expect(page.locator(".card")).to_have_count(4)
                    page.get_by_role("searchbox", name="Атауы бойынша іздеу").fill("қызанақ")
                    page.locator("#catalog-filter button[type=submit]").click()
                    expect(page.locator(".card")).to_have_count(3)
                    page.locator(".compare-toggle").nth(0).click()
                    page.locator(".compare-toggle").nth(1).click()
                    page.locator("[data-action=compare-open]").click()
                    expect(page.locator("dialog")).to_be_visible()
                    expect(page.locator("dialog table")).to_be_visible()
                    page.locator("[data-action=close-modal]").first.click()
                    page.locator("[data-action=compare-clear]").click()
                    page.locator(".card h3").first.click()
                    expect(page.locator("#price-history")).to_be_visible()
                    assert page.locator("#price-history").evaluate("canvas=>canvas.width>0")
                    print("PASS pagination, Kazakh search, price comparison, product history")
                    go("map", "Өңіріңізді зерттеңіз")
                    expect(page.locator(".leaflet-marker-icon")).to_have_count(24)
                    page.locator("#map-kind").select_option("product")
                    page.locator("#map-filter button[type=submit]").click()
                    expect(page.locator(".leaflet-marker-icon")).to_have_count(16)
                    page.locator(".map-item").first.click()
                    expect(page.locator(".leaflet-popup")).to_be_visible()
                    page.locator(".leaflet-popup-close-button").click()
                    page.locator("[data-action=nearby]").click()
                    expect(page.locator("#map-status")).not_to_contain_text("жүктелуде")
                    page.locator("#map-bounds").check()
                    page.locator("#map-filter button[type=submit]").click()
                    expect(page.locator(".leaflet-control-attribution")).to_contain_text("OpenStreetMap")
                    print("PASS map layers, marker popup, geolocation, viewport filter, attribution")
                    go("businesses", "Кәсіптер каталогы")
                    expect(page.locator(".card")).to_have_count(8)
                    page.locator(".card h3").first.click()
                    expect(page.locator("#detail-map .leaflet-container, #detail-map.leaflet-container")).to_have_count(1)
                    expect(page.locator(".detail-content h1")).to_be_visible()
                    page.goto(base + "/docs")
                    expect(page.locator(".swagger-ui .info .title")).to_contain_text("HarvestMap AI")
                    expect(page.locator(".opblock")).not_to_have_count(0)
                    print("PASS business profile, embedded map, fully local interactive API documentation")
                    go("dashboard", "Өңірлік шолу")
                    expect(page.locator("canvas")).to_have_count(2)
                    expect(page.locator(".stat-card")).to_have_count(4)
                    go("assistant", "Деректерге негізделген көмекші")
                    page.locator("#chat-form input").fill("Қызанақ бағасы")
                    page.locator("#chat-form button").click()
                    expect(page.locator(".message.bot").last).to_contain_text("650")
                    expect(page.locator(".message.bot").last).to_contain_text("API кілтінсіз")
                    print("PASS dashboard charts and data-backed no-key assistant")
                    go("register", "Тіркелгі жасау")
                    page.locator("#name").fill("Браузер кәсіп иесі")
                    page.locator("#email").fill("browser-owner@example.com")
                    page.locator("#password").fill(password)
                    page.locator("#role").select_option("owner")
                    page.locator("#auth-form button").click()
                    expect(page.locator("main h1")).to_have_text("Жеке кабинет")
                    page.locator("#profile-name").fill("Жаңартылған кәсіп иесі")
                    page.locator("#profile-form button").click()
                    expect(page.locator(".account-card h3")).to_have_text("Жаңартылған кәсіп иесі")
                    page.get_by_role("link", name="Кәсіптерімді басқару").click()
                    expect(page.locator("main h1")).to_have_text("Кәсібіңізді дамытыңыз")
                    page.locator("[data-action=business-form]").click()
                    page.locator("#f-name").fill("Браузер сынақ кәсібі")
                    page.locator("#f-category").select_option("farm")
                    page.locator("#f-description").fill("Браузер тексеруіне арналған толық сипаттама")
                    page.locator("#f-location").select_option(index=1)
                    page.locator("#f-address").fill("Сынақ мекенжайы, 10")
                    page.locator("#business-form button[type=submit]").click()
                    expect(page.locator("dialog")).not_to_be_visible()
                    expect(page.locator("main")).to_contain_text("Браузер сынақ кәсібі")
                    page.locator("[data-action=product-form]").click()
                    page.locator("#f-name").fill("Браузер сынақ өнімі")
                    page.locator("#f-category").select_option("fruit")
                    page.locator("#f-description").fill("Браузер арқылы енгізілген өнім сипаттамасы")
                    page.locator("#f-price").fill("1234")
                    page.locator("#product-form button[type=submit]").click()
                    expect(page.locator("dialog")).not_to_be_visible()
                    expect(page.locator("main")).to_contain_text("Браузер сынақ өнімі")
                    print("PASS registration, cookie authentication, profile update, business/product submission")
                    admin_context = browser.new_context(viewport={"width": 1440, "height": 1000}, locale="kk-KZ")
                    admin_page = admin_context.new_page()
                    admin_page.on("pageerror", lambda error: errors.append(error.stack))
                    admin_page.goto(base + "/#/login")
                    admin_page.locator("#email").fill("browser-admin@example.com")
                    admin_page.locator("#password").fill(admin_password)
                    admin_page.locator("#auth-form button").click()
                    expect(admin_page.locator("main h1")).to_have_text("Жеке кабинет")
                    admin_page.get_by_role("link", name="Әкімші панелі").click()
                    expect(admin_page.locator("main h1")).to_have_text("Сапа мен сенімділік")
                    admin_page.locator("[data-kind=businesses][data-status=approved]").click()
                    expect(admin_page.locator("[data-kind=businesses][data-status=approved]")).to_have_count(0)
                    admin_page.locator("[data-kind=products][data-status=approved]").click()
                    expect(admin_page.locator("[data-kind=products][data-status=approved]")).to_have_count(0)
                    # Location form is wired to the same admin API as the queue.
                    admin_page.locator("[data-action=location-form]").first.click()
                    admin_page.locator("#f-name").fill("Браузер ауылы")
                    admin_page.locator("#f-region").fill("Сынақ облысы")
                    admin_page.locator("#location-form button").click()
                    expect(admin_page.locator("dialog")).not_to_be_visible()
                    expect(admin_page.locator("main")).to_contain_text("Браузер ауылы")
                    print("PASS administrator login, moderation, and location form")
                    go("products?q=Браузер", "Өнімдер нарығы")
                    expect(page.locator(".card")).to_have_count(1)
                    page.locator(".card h3").click()
                    expect(page.locator("main h1")).to_have_text("Браузер сынақ өнімі")
                    go("owner", "Кәсібіңізді дамытыңыз")
                    page.locator("[data-action=product-form][data-id]").click()
                    page.locator("#f-price").fill("1500")
                    page.locator("#product-form button[type=submit]").click()
                    expect(page.locator("dialog")).not_to_be_visible()
                    expect(page.locator("main")).to_contain_text("Тексерілуде")
                    page.locator("[data-action=delete][data-kind=products]").click()
                    page.locator("#delete-form button[type=submit]").click()
                    expect(page.locator("main")).not_to_contain_text("Браузер сынақ өнімі")
                    print("PASS approved public visibility, owner price edit, re-moderation, confirmed deletion")
                    go("account", "Жеке кабинет")
                    page.locator("#current-password").fill(password)
                    new_password = secrets.token_urlsafe(20)
                    page.locator("#new-password").fill(new_password)
                    page.locator("#password-form button").click()
                    expect(page.locator("#toast")).to_contain_text("Құпиясөз жаңартылды")
                    page.locator("[data-action=logout]").click()
                    expect(page.locator("main h1")).to_contain_text("Жергілікті өнім")
                    go("login", "Қайта қош келдіңіз")
                    page.locator("#email").fill("browser-owner@example.com")
                    page.locator("#password").fill(new_password)
                    page.locator("#auth-form button").click()
                    expect(page.locator("main h1")).to_have_text("Жеке кабинет")
                    page.reload()
                    expect(page.locator("main h1")).to_have_text("Жеке кабинет")
                    print("PASS password change, logout, new-password login, session persistence")
                    page.set_viewport_size({"width": 390, "height": 844})
                    go("", "Жергілікті өнім")
                    assert page.evaluate("document.documentElement.scrollWidth<=innerWidth"), "Mobile home horizontal overflow"
                    page.locator(".mobile-toggle").click()
                    expect(page.locator("#navigation")).to_be_visible()
                    page.locator('#navigation a[href="#/map"]').click()
                    expect(page.locator("main h1")).to_have_text("Өңіріңізді зерттеңіз")
                    expect(page.locator(".leaflet-marker-icon")).to_have_count(25)
                    assert page.evaluate("document.documentElement.scrollWidth<=innerWidth"), "Mobile map horizontal overflow"
                    for path, title in [
                        ("products", "Өнімдер нарығы"),
                        ("businesses", "Кәсіптер каталогы"),
                        ("dashboard", "Өңірлік шолу"),
                        ("assistant", "Деректерге негізделген көмекші"),
                        ("account", "Жеке кабинет"),
                    ]:
                        go(path, title)
                        assert page.evaluate("document.documentElement.scrollWidth<=innerWidth"), f"Mobile {path} horizontal overflow"
                    go("", "Жергілікті өнім")
                    if screenshots:
                        page.screenshot(path=str(Path(screenshots) / "mobile-home.png"), full_page=True)
                    page.set_viewport_size({"width": 820, "height": 1180})
                    go("dashboard", "Өңірлік шолу")
                    assert page.evaluate("document.documentElement.scrollWidth<=innerWidth"), "Tablet overflow"
                    print("PASS mobile navigation and six responsive pages; tablet dashboard")
                    assert errors == [], "Browser JavaScript errors: " + repr(errors)
                    print("PASS zero uncaught browser JavaScript errors")
                    browser.close()
            finally:
                server.terminate()
                try:
                    server.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    server.kill()


if __name__ == "__main__":
    main()
