from sqlalchemy import select
from app.models import PriceHistory, Product, Business


def test_search_unicode_filter_and_pagination(client, sample):
    r = client.get(
        "/api/products",
        params={"q": "қызанақ", "category": "vegetables", "location_id": sample["location"].id, "sort": "price_asc", "size": 1},
    )
    assert r.status_code == 200 and r.json()["total"] == 1
    assert r.json()["items"][0]["is_demo"]
    assert client.get("/api/products?page=2&size=1").json()["items"] == []
    assert client.get("/api/products?min_price=700").json()["total"] == 0
    assert client.get("/api/products?max_price=700&unit=кг").json()["total"] == 1
    assert client.get("/api/businesses?q=сынақ").json()["total"] == 1
    assert client.get("/api/businesses?q=%25").json()["total"] == 0


def test_business_crud_moderation(client, sample, business_body):
    owner = sample["headers"]["owner"]
    admin = sample["headers"]["admin"]
    r = client.post("/api/businesses", json=business_body, headers=owner)
    assert r.status_code == 201 and r.json()["status"] == "pending"
    id = r.json()["id"]
    assert client.get(f"/api/businesses/{id}").status_code == 404
    assert client.get("/api/owner/catalog", headers=owner).json()["businesses"][-1]["id"] == id
    assert client.patch(f"/api/admin/businesses/{id}/status", headers=admin, json={"status": "approved"}).status_code == 200
    assert client.get(f"/api/businesses/{id}").status_code == 200
    business_body["name"] = "Жаңартылған кәсіп"
    assert client.put(f"/api/businesses/{id}", headers=owner, json=business_body).json()["status"] == "pending"
    assert client.get(f"/api/businesses/{id}").status_code == 404
    assert client.delete(f"/api/businesses/{id}", headers=owner).status_code == 200
    assert client.delete(f"/api/businesses/{id}", headers=owner).status_code == 404


def test_product_crud_and_price_history(client, db, sample, product_body):
    owner = sample["headers"]["owner"]
    admin = sample["headers"]["admin"]
    r = client.post("/api/products", headers=owner, json=product_body)
    assert r.status_code == 201
    id = r.json()["id"]
    assert client.get(f"/api/products/{id}").status_code == 404
    client.patch(f"/api/admin/products/{id}/status", headers=admin, json={"status": "approved"})
    assert len(client.get(f"/api/products/{id}").json()["history"]) == 1
    product_body["price"] = 500
    assert client.put(f"/api/products/{id}", headers=owner, json=product_body).status_code == 200
    assert len(db.scalars(select(PriceHistory).where(PriceHistory.product_id == id)).all()) == 2
    client.put(f"/api/products/{id}", headers=owner, json=product_body)
    assert len(db.scalars(select(PriceHistory).where(PriceHistory.product_id == id)).all()) == 2
    assert client.delete(f"/api/products/{id}", headers=owner).status_code == 200
    assert db.scalars(select(PriceHistory).where(PriceHistory.product_id == id)).all() == []


def test_permissions_idor(client, sample, business_body, product_body):
    assert client.post("/api/businesses", json=business_body).status_code == 401
    assert client.post("/api/businesses", headers=sample["headers"]["user"], json=business_body).status_code == 403
    assert (
        client.put("/api/businesses/" + str(sample["business"].id), headers=sample["other_headers"], json=business_body).status_code == 403
    )
    assert client.post("/api/products", headers=sample["other_headers"], json=product_body).status_code == 403
    assert client.delete("/api/products/" + str(sample["product"].id), headers=sample["other_headers"]).status_code == 403
    assert client.get("/api/admin/queue", headers=sample["headers"]["owner"]).status_code == 403
    assert client.get("/api/owner/catalog", headers=sample["headers"]["user"]).status_code == 403


def test_validation(client, sample, business_body, product_body):
    h = sample["headers"]["owner"]
    business_body["latitude"] = 91
    assert client.post("/api/businesses", headers=h, json=business_body).status_code == 422
    business_body["latitude"] = 43
    business_body["website"] = "javascript:alert(1)"
    assert client.post("/api/businesses", headers=h, json=business_body).status_code == 422
    product_body["price"] = -1
    assert client.post("/api/products", headers=h, json=product_body).status_code == 422
    product_body["price"] = 400
    product_body["season_end"] = 13
    assert client.post("/api/products", headers=h, json=product_body).status_code == 422
    assert client.get("/api/products?size=101").status_code == 422
    assert client.get("/api/products?sort=DROP").status_code == 422


def test_parent_visibility_and_delete_cascade(client, db, sample):
    b = sample["business"]
    p = sample["product"]
    b.status = "rejected"
    db.commit()
    assert client.get("/api/products").json()["total"] == 0
    assert client.get(f"/api/products/{p.id}").status_code == 404
    assert client.get("/api/map?kind=product").json()["features"] == []
    assert client.delete(f"/api/businesses/{b.id}", headers=sample["headers"]["owner"]).status_code == 200
    assert db.get(Product, p.id) is None
    assert db.scalars(select(PriceHistory)).all() == []


def test_location_crud_protects_referenced_location(client, sample):
    admin = sample["headers"]["admin"]
    body = {"name": "Жаңа ауыл", "region": "Жаңа облыс", "latitude": 42, "longitude": 70}
    assert client.post("/api/locations", headers=sample["headers"]["owner"], json=body).status_code == 403
    r = client.post("/api/locations", headers=admin, json=body)
    assert r.status_code == 201
    id = r.json()["id"]
    body["name"] = "Өзгерген ауыл"
    assert client.put(f"/api/locations/{id}", headers=admin, json=body).status_code == 200
    assert client.delete(f"/api/locations/{sample['location'].id}", headers=admin).status_code == 409
    assert client.delete(f"/api/locations/{id}", headers=admin).status_code == 200


def test_admin_role_and_deactivate_invalidates_session(client, sample):
    admin = sample["headers"]["admin"]
    u = sample["users"]["user"]
    assert client.patch("/api/admin/users/" + str(sample["users"]["admin"].id), headers=admin, json={"role": "user"}).status_code == 409
    assert client.patch(f"/api/admin/users/{u.id}", headers=admin, json={"role": "owner", "is_active": False}).status_code == 200
    assert client.get("/api/auth/me", headers=sample["headers"]["user"]).status_code == 401
    assert client.get("/api/admin/users", headers=admin).status_code == 200


def test_moderation_queue(client, sample, business_body):
    r = client.post("/api/businesses", headers=sample["headers"]["owner"], json=business_body)
    q = client.get("/api/admin/queue", headers=sample["headers"]["admin"]).json()
    assert q["businesses"][0]["id"] == r.json()["id"]
    assert client.patch("/api/admin/invalid/1/status", headers=sample["headers"]["admin"], json={"status": "approved"}).status_code == 404
