from app.models import User
from app.security import password_hash


def test_registration_login_profile_logout(client, db, sample):
    result = client.post(
        "/api/auth/register", json={"email": "new@example.com", "name": "Жаңа адам", "password": sample["password"], "role": "user"}
    )
    assert result.status_code == 201
    assert result.json()["user"]["role"] == "user"
    h = {"Authorization": "Bearer " + result.json()["access_token"]}
    assert "HttpOnly" in result.headers["set-cookie"]
    user = db.get(User, result.json()["user"]["id"])
    assert user.password_hash != sample["password"] and password_hash.verify(sample["password"], user.password_hash)
    assert client.get("/api/auth/me", headers=h).json()["email"] == "new@example.com"
    assert client.patch("/api/auth/me", headers=h, json={"name": "Өзгерген есім"}).json()["name"] == "Өзгерген есім"
    assert client.post("/api/auth/logout", headers=h).status_code == 200
    assert client.get("/api/auth/me", headers=h).status_code == 401
    assert client.post("/api/auth/login", json={"email": "new@example.com", "password": sample["password"]}).status_code == 200


def test_no_admin_self_registration(client, sample):
    assert (
        client.post(
            "/api/auth/register", json={"email": "hacker@example.com", "name": "Test", "password": sample["password"], "role": "admin"}
        ).status_code
        == 422
    )


def test_short_password_rejected(client):
    assert client.post("/api/auth/register", json={"email": "test@example.com", "name": "Test", "password": "short"}).status_code == 422


def test_duplicate_email_and_normalization(client, sample):
    assert (
        client.post("/api/auth/register", json={"email": "OWNER@example.com", "name": "Test", "password": sample["password"]}).status_code
        == 409
    )


def test_wrong_login(client, sample):
    assert client.post("/api/auth/login", json={"email": "owner@example.com", "password": "incorrect-example"}).status_code == 401
    assert client.post("/api/auth/login", json={"email": "missing@example.com", "password": "incorrect-example"}).status_code == 401


def test_csrf_cookie_protection(client, sample):
    assert client.post("/api/auth/login", json={"email": "owner@example.com", "password": sample["password"]}).status_code == 200
    assert client.patch("/api/auth/me", json={"name": "Жаңа есім"}).status_code == 403
    assert (
        client.patch("/api/auth/me", json={"name": "Жаңа есім"}, headers={"X-CSRF-Token": client.cookies["harvest_csrf"]}).status_code
        == 200
    )


def test_password_change_invalidates_old_token(client, sample):
    old = sample["headers"]["owner"]
    assert (
        client.post(
            "/api/auth/password", headers=old, json={"current_password": "wrong", "new_password": sample["password"] + "new"}
        ).status_code
        == 400
    )
    r = client.post(
        "/api/auth/password", headers=old, json={"current_password": sample["password"], "new_password": sample["password"] + "new"}
    )
    assert r.status_code == 200
    assert client.get("/api/auth/me", headers=old).status_code == 401
    assert client.get("/api/auth/me", headers={"Authorization": "Bearer " + r.json()["access_token"]}).status_code == 200


def test_security_headers_and_expired_token(client):
    r = client.get("/")
    assert r.status_code == 200 and 'lang="kk"' in r.text
    assert r.headers["x-content-type-options"] == "nosniff"
    assert "script-src 'self'" in r.headers["content-security-policy"]
    assert client.get("/api/auth/me", headers={"Authorization": "Bearer invalid"}).status_code == 401


def test_login_rate_limit(client):
    for i in range(15):
        assert client.post("/api/auth/login", json={"email": "none@example.com", "password": "wrong"}).status_code == 401
    assert client.post("/api/auth/login", json={"email": "none@example.com", "password": "wrong"}).status_code == 429
