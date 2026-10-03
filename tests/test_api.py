"""
API tests derived from the flows in test_api.sh.

ASSUMPTIONS to verify on the first run (adjust the TESTS to match your real
responses; don't loosen assertions just to make them pass):
  - POST /auth/login returns JSON containing "access_token"
  - Created posts come back as JSON with an "id" field
  - GET /posts returns a JSON list
  - Non-owners get 403 on update/delete
"""


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200


def test_register_login_and_me(client, make_user):
    headers = make_user("alice")
    r = client.get("/users/me", headers=headers)
    assert r.status_code == 200
    assert r.json()["username"] == "alice"


def test_login_with_wrong_password_is_rejected(client, make_user):
    make_user("alice")
    r = client.post("/auth/login", json={"username": "alice", "password": "wrong"})
    assert r.status_code in (400, 401)


def test_protected_route_requires_token(client):
    r = client.get("/users/me")
    assert r.status_code in (401, 403)


def test_create_and_list_posts(client, make_user):
    headers = make_user("alice")
    r = client.post(
        "/posts", headers=headers, data={"title": "Hello", "content": "First post"}
    )
    assert r.status_code in (200, 201), r.text

    r = client.get("/posts")
    assert r.status_code == 200
    posts = r.json()
    assert len(posts) == 1
    assert posts[0]["title"] == "Hello"


def test_list_posts_respects_limit(client, make_user):
    headers = make_user("alice")
    for i in range(3):
        client.post(
            "/posts", headers=headers, data={"title": f"Post {i}", "content": "x"}
        )
    r = client.get("/posts", params={"skip": 0, "limit": 2})
    assert r.status_code == 200
    assert len(r.json()) == 2


def test_owner_can_delete_own_post(client, make_user):
    headers = make_user("alice")
    post = client.post(
        "/posts", headers=headers, data={"title": "Mine", "content": "x"}
    ).json()

    r = client.delete(f"/posts/{post['id']}", headers=headers)
    assert r.status_code in (200, 204)

    assert client.get(f"/posts/{post['id']}").status_code == 404


def test_non_owner_cannot_delete_post(client, make_user):
    alice = make_user("alice")
    bob = make_user("bob")
    post = client.post(
        "/posts", headers=alice, data={"title": "Alice's", "content": "x"}
    ).json()

    r = client.delete(f"/posts/{post['id']}", headers=bob)
    assert r.status_code == 403

    # and the post must still exist
    assert client.get(f"/posts/{post['id']}").status_code == 200
