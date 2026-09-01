def test_register_and_login(client):
    register_response = client.post(
        "/users/register",
        json={"email": "user@example.com", "password": "supersecret1", "full_name": "User"},
    )
    assert register_response.status_code == 201
    body = register_response.json()
    assert body["email"] == "user@example.com"
    assert "hashed_password" not in body

    login_response = client.post(
        "/users/login", json={"email": "user@example.com", "password": "supersecret1"}
    )
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]

    me_response = client.get("/users/me", headers={"Authorization": f"Bearer {token}"})
    assert me_response.status_code == 200
    assert me_response.json()["email"] == "user@example.com"


def test_register_duplicate_email(client):
    payload = {"email": "dup@example.com", "password": "supersecret1"}
    assert client.post("/users/register", json=payload).status_code == 201
    response = client.post("/users/register", json=payload)
    assert response.status_code == 409


def test_login_wrong_password(client):
    client.post("/users/register", json={"email": "a@example.com", "password": "supersecret1"})
    response = client.post(
        "/users/login", json={"email": "a@example.com", "password": "wrongpassword"}
    )
    assert response.status_code == 401


def test_me_without_token_is_rejected(client):
    response = client.get("/users/me")
    assert response.status_code in (401, 403)


def test_me_with_garbage_token_is_rejected(client):
    response = client.get("/users/me", headers={"Authorization": "Bearer not-a-real-token"})
    assert response.status_code == 401
