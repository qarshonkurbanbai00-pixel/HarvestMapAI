import pytest
from app.services import in_season, distance_km


def test_geojson_coordinate_order_and_layers(client, sample):
    r = client.get("/api/map")
    assert r.status_code == 200
    geo = r.json()
    assert geo["type"] == "FeatureCollection" and len(geo["features"]) == 2
    point = geo["features"][0]
    assert point["geometry"]["coordinates"] == [sample["business"].longitude, sample["business"].latitude]
    assert len(client.get("/api/map?kind=business").json()["features"]) == 1
    assert len(client.get("/api/map?kind=product&category=vegetables").json()["features"]) == 1
    assert client.get("/api/map?q=Табылмайды").json()["features"] == []


def test_geo_bounds_and_nearby(client, sample):
    assert client.get("/api/map?bbox=76,43,78,44").json()["total"] == 2
    assert client.get("/api/map?bbox=1,1,2,2").json()["total"] == 0
    assert client.get("/api/map?bbox=170,-90,-170,90").json()["total"] == 0
    near = client.get("/api/map?lat=43.24&lon=76.89&radius_km=1").json()
    assert near["total"] == 2 and near["features"][0]["properties"]["distance_km"] == 0
    assert client.get("/api/map?lat=51&lon=71&radius_km=1").json()["total"] == 0
    assert client.get("/api/map?lat=43").status_code == 422
    for box in ["bad", "181,0,182,1", "0,50,1,40", "NaN,0,1,2"]:
        assert client.get("/api/map", params={"bbox": box}).status_code == 422


def test_statistics_grouping_and_demo_label(client, sample):
    s = client.get("/api/statistics").json()
    assert s["businesses"] == 1 and s["products"] == 1 and s["seasonal_products"] == 1
    assert s["demo_products"] == 1 and s["demo_businesses"] == 1
    assert s["price_comparison"][0] == {"name": "Қызанақ", "unit": "кг", "min": 650, "max": 650, "average": 650, "offers": 1}
    assert "Демо" in s["notice"]


@pytest.mark.parametrize(
    "start,end,month,expected",
    [(5, 10, 6, True), (5, 10, 1, False), (11, 3, 12, True), (11, 3, 2, True), (11, 3, 7, False), (1, 12, 12, True)],
)
def test_season_cross_year(start, end, month, expected):
    assert in_season(start, end, month) == expected


def test_haversine():
    assert distance_km(43, 76, 43, 76) == 0
    assert 110 < distance_km(0, 0, 1, 0) < 112


def test_seasonal_api(client, sample):
    assert client.get("/api/products?seasonal=true").json()["total"] == 1


def test_assistant_no_key_fallback_and_sources(client, sample):
    result = client.post("/api/assistant", json={"message": "Қызанақ бағасы"})
    assert result.status_code == 200
    r = result.json()
    assert r["mode"] == "fallback" and "650" in r["answer"] and "Демо" in r["answer"]
    assert any(s["url"].startswith("/#/product/") for s in r["sources"])
    assert r["functions_used"] == ["search_catalog", "statistics"]
    assert client.post("/api/assistant", json={"message": "Болмайтынзаттытабу"}).json()["sources"] == []


def test_assistant_provider_failure_falls_back(client, sample, monkeypatch):
    from app.config import get_settings
    import httpx

    settings = get_settings()
    monkeypatch.setattr(settings, "ai_api_key", "test-only-not-a-real-key")

    async def failure(*args, **kwargs):
        raise httpx.ConnectError("offline")

    monkeypatch.setattr(httpx.AsyncClient, "post", failure)
    r = client.post("/api/assistant", json={"message": "Қызанақ бағасы"}).json()
    assert r["mode"] == "fallback" and "қолжетімсіз" in r["notice"]


def test_assistant_provider_mocked_success(client, sample, monkeypatch):
    from app.config import get_settings
    import httpx

    monkeypatch.setattr(get_settings(), "ai_api_key", "test-only-not-a-real-key")

    async def success(*args, **kwargs):
        assert kwargs["json"]["temperature"] == 0
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": "Демо қызанақ бағасы 650 ₸/кг."}}]},
            request=httpx.Request("POST", "https://example.com"),
        )

    monkeypatch.setattr(httpx.AsyncClient, "post", success)
    r = client.post("/api/assistant", json={"message": "Қызанақ бағасы"}).json()
    assert r["mode"] == "ai" and "650" in r["answer"]


def test_openapi_and_local_assets(client):
    spec = client.get("/openapi.json").json()
    for path in ["/api/products", "/api/businesses", "/api/auth/register", "/api/map", "/api/assistant", "/api/admin/queue"]:
        assert path in spec["paths"]
    for asset in ["css/app.css", "js/app.js", "vendor/leaflet.js", "vendor/leaflet.css", "vendor/chart.umd.js", "favicon.svg"]:
        assert client.get("/static/" + asset).status_code == 200
