import uuid

from app.auth.security import create_access_token, hash_password
from app.models import AdminUser, BracketRound, Match, Participant, Team


def _seed_admin(client, username="admin", password="testpassword123"):
    db = client.SessionLocal()
    try:
        db.add(AdminUser(username=username, password_hash=hash_password(password)))
        db.commit()
    finally:
        db.close()


def _create_tournament(client, name="Admin Test Cup"):
    resp = client.post("/tournaments", json={"name": name})
    assert resp.status_code == 200
    return resp.json()


def _add_participants(client, manage_token, n):
    for i in range(n):
        resp = client.post(f"/tournaments/{manage_token}/participants", json={"display_name": f"Player{i}"})
        assert resp.status_code == 200


def _pending_playable_matches(state):
    matches = []
    for round_ in state["rounds"]:
        for m in round_["matches"]:
            if m["team_b"] is not None and m["winner_team_id"] is None:
                matches.append(m)
    return matches


def _auth_headers(token):
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# Login
# ---------------------------------------------------------------------------


def test_login_success(client):
    _seed_admin(client, "admin", "correct-password-1")
    resp = client.post("/admin/login", json={"username": "admin", "password": "correct-password-1"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["token_type"] == "bearer"
    assert len(body["access_token"]) > 10


def test_login_wrong_password(client):
    _seed_admin(client, "admin", "correct-password-1")
    resp = client.post("/admin/login", json={"username": "admin", "password": "wrong-password"})
    assert resp.status_code == 401


def test_login_unknown_username(client):
    resp = client.post("/admin/login", json={"username": "nobody", "password": "whatever123"})
    assert resp.status_code == 401


def test_login_inactive_admin_rejected(client):
    db = client.SessionLocal()
    try:
        db.add(AdminUser(username="disabled", password_hash=hash_password("somepassword1"), is_active=False))
        db.commit()
    finally:
        db.close()
    resp = client.post("/admin/login", json={"username": "disabled", "password": "somepassword1"})
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Protected endpoint auth guards
# ---------------------------------------------------------------------------


def test_list_tournaments_without_token_rejected(client):
    resp = client.get("/admin/tournaments")
    assert resp.status_code == 401


def test_list_tournaments_with_garbage_token_rejected(client):
    resp = client.get("/admin/tournaments", headers=_auth_headers("not-a-real-jwt"))
    assert resp.status_code == 401


def test_me_returns_username(client):
    _seed_admin(client, "admin", "correct-password-1")
    token = create_access_token("admin")
    resp = client.get("/admin/me", headers=_auth_headers(token))
    assert resp.status_code == 200
    assert resp.json()["username"] == "admin"


# ---------------------------------------------------------------------------
# List all tournaments
# ---------------------------------------------------------------------------


def test_list_all_tournaments_returns_everything(client):
    _seed_admin(client)
    token = create_access_token("admin")
    created = [_create_tournament(client, f"Cup {i}") for i in range(3)]

    resp = client.get("/admin/tournaments", headers=_auth_headers(token))
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 3
    names = {t["name"] for t in body}
    assert names == {c["name"] for c in created}
    # manage_token must be present so the admin can jump into the normal manage page
    assert all(t["manage_token"] for t in body)


# ---------------------------------------------------------------------------
# Delete cascade correctness
# ---------------------------------------------------------------------------


def test_delete_tournament_removes_everything(client):
    _seed_admin(client)
    token = create_access_token("admin")

    created = _create_tournament(client, "To Be Deleted")
    manage_token = created["manage_token"]
    tournament_id = uuid.UUID(created["id"])
    _add_participants(client, manage_token, 8)
    state = client.post(f"/tournaments/{manage_token}/start").json()

    # Play enough matches to generate bye/waiting/excluded cross-references
    # (teams, matches, and bracket_rounds all populated with FK references
    # back into participants) before deleting, so the cascade delete is
    # actually exercised against a non-trivial dependency graph.
    safety = 0
    while state["status"] != "COMPLETE" and safety < 20:
        safety += 1
        pending = _pending_playable_matches(state)
        if not pending:
            break
        match = pending[0]
        resp = client.post(
            f"/tournaments/{manage_token}/matches/{match['id']}/report",
            json={"winner_team_id": match["team_a"]["id"]},
        )
        state = resp.json()

    db = client.SessionLocal()
    try:
        round_ids = [r.id for r in db.query(BracketRound.id).filter(BracketRound.tournament_id == tournament_id)]
        assert len(round_ids) > 0
        assert db.query(Team).filter(Team.bracket_round_id.in_(round_ids)).count() > 0
        assert db.query(Match).filter(Match.bracket_round_id.in_(round_ids)).count() > 0
    finally:
        db.close()

    resp = client.delete(f"/admin/tournaments/{tournament_id}", headers=_auth_headers(token))
    assert resp.status_code == 204

    db = client.SessionLocal()
    try:
        assert db.query(Participant).filter(Participant.tournament_id == tournament_id).count() == 0
        assert db.query(BracketRound).filter(BracketRound.tournament_id == tournament_id).count() == 0
        assert db.query(Team).filter(Team.bracket_round_id.in_(round_ids)).count() == 0
        assert db.query(Match).filter(Match.bracket_round_id.in_(round_ids)).count() == 0
    finally:
        db.close()

    # No longer listed, and the old manage_token is dead.
    list_resp = client.get("/admin/tournaments", headers=_auth_headers(token))
    assert all(t["id"] != str(tournament_id) for t in list_resp.json())

    manage_resp = client.get(f"/tournaments/{manage_token}/manage")
    assert manage_resp.status_code == 404


def test_delete_unknown_tournament_404s(client):
    _seed_admin(client)
    token = create_access_token("admin")
    resp = client.delete(
        "/admin/tournaments/00000000-0000-0000-0000-000000000000", headers=_auth_headers(token)
    )
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Admin user creation
# ---------------------------------------------------------------------------


def test_authenticated_admin_can_create_another_admin(client):
    _seed_admin(client, "first", "firstpassword1")
    token = create_access_token("first")

    resp = client.post(
        "/admin/users", json={"username": "second", "password": "secondpassword1"}, headers=_auth_headers(token)
    )
    assert resp.status_code == 201
    assert resp.json()["username"] == "second"

    login_resp = client.post("/admin/login", json={"username": "second", "password": "secondpassword1"})
    assert login_resp.status_code == 200


def test_create_admin_duplicate_username_conflict(client):
    _seed_admin(client, "first", "firstpassword1")
    token = create_access_token("first")
    resp = client.post(
        "/admin/users", json={"username": "first", "password": "anotherpassword1"}, headers=_auth_headers(token)
    )
    assert resp.status_code == 409


def test_create_admin_requires_auth(client):
    resp = client.post("/admin/users", json={"username": "sneaky", "password": "sneakypassword1"})
    assert resp.status_code == 401
