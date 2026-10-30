from datetime import datetime, timedelta, timezone
from app.models import PriceHistory


def test_actual_price_trends_and_assistant(client, db, sample):
    p = sample["product"]
    # Put the comparison point before the fixture's current point.
    db.add(PriceHistory(product_id=p.id, price=1000, recorded_at=datetime.now(timezone.utc) - timedelta(days=30)))
    db.commit()
    r = client.get("/api/statistics/trends", params={"product_id": p.id})
    assert r.status_code == 200
    trend = r.json()["items"][0]
    assert trend["first_price"] == 1000
    assert trend["latest_price"] == 650
    assert trend["change_percent"] == -35
    assert trend["is_demo"] is True
    answer = client.post("/api/assistant", json={"message": "Қызанақ баға тренді"}).json()
    assert "-35%" in answer["answer"] and "Демо баға тарихы" in answer["answer"]
    assert "price_trends" in answer["functions_used"]


def test_documentation_is_local_and_csp_compatible(client):
    page = client.get("/docs")
    assert page.status_code == 200
    assert "/static/js/docs.js" in page.text
    assert "<script>" not in page.text
    assert "cdn.jsdelivr.net" not in page.text
    for asset in ["vendor/swagger-ui-bundle.js", "vendor/swagger-ui.css", "js/docs.js"]:
        assert client.get("/static/" + asset).status_code == 200


def test_precision_validation(client, sample, product_body):
    product_body["price"] = 0.001
    assert client.post("/api/products", headers=sample["headers"]["owner"], json=product_body).status_code == 422
