def _create_tournament(client, name="Test Cup", format="DOUBLE_ELIMINATION"):
    resp = client.post("/tournaments", json={"name": name, "format": format})
    assert resp.status_code == 200
    return resp.json()


def _add_participants(client, manage_token, n):
    for i in range(n):
        resp = client.post(f"/tournaments/{manage_token}/participants", json={"display_name": f"Player{i}"})
        assert resp.status_code == 200


def _pending_playable_matches(state):
    """Any match with two real teams and no winner yet (NORMAL, GRAND_FINAL,
    or GRAND_FINAL_RESET) -- TEAM_BYE matches auto-resolve and never appear here."""
    matches = []
    for round_ in state["rounds"]:
        for m in round_["matches"]:
            if m["team_b"] is not None and m["winner_team_id"] is None:
                matches.append(m)
    return matches


def test_create_add_participants_and_start_requires_min_4(client):
    created = _create_tournament(client)
    manage_token = created["manage_token"]

    _add_participants(client, manage_token, 3)
    resp = client.post(f"/tournaments/{manage_token}/start")
    assert resp.status_code == 400

    _add_participants(client, manage_token, 1)  # now 4 total
    resp = client.post(f"/tournaments/{manage_token}/start")
    assert resp.status_code == 200
    state = resp.json()
    assert state["status"] == "IN_PROGRESS"
    wb_rounds = [r for r in state["rounds"] if r["bracket"] == "WINNERS"]
    assert len(wb_rounds) == 1
    assert len(wb_rounds[0]["matches"]) == 1


def test_cannot_add_participants_after_start(client):
    created = _create_tournament(client)
    manage_token = created["manage_token"]
    _add_participants(client, manage_token, 4)
    client.post(f"/tournaments/{manage_token}/start")

    resp = client.post(f"/tournaments/{manage_token}/participants", json={"display_name": "Late"})
    assert resp.status_code == 400


def test_public_endpoint_hides_manage_token(client):
    created = _create_tournament(client)
    manage_token = created["manage_token"]
    public_slug = created["public_slug"]
    _add_participants(client, manage_token, 4)
    client.post(f"/tournaments/{manage_token}/start")

    resp = client.get(f"/tournaments/public/{public_slug}")
    assert resp.status_code == 200
    assert "manage_token" not in resp.json()


def test_reporting_unknown_or_duplicate_winner_rejected(client):
    created = _create_tournament(client)
    manage_token = created["manage_token"]
    _add_participants(client, manage_token, 4)
    state = client.post(f"/tournaments/{manage_token}/start").json()
    match = _pending_playable_matches(state)[0]

    bad_resp = client.post(
        f"/tournaments/{manage_token}/matches/{match['id']}/report", json={"winner_team_id": match["id"]}
    )
    assert bad_resp.status_code == 400

    good_resp = client.post(
        f"/tournaments/{manage_token}/matches/{match['id']}/report", json={"winner_team_id": match["team_a"]["id"]}
    )
    assert good_resp.status_code == 200

    dup_resp = client.post(
        f"/tournaments/{manage_token}/matches/{match['id']}/report", json={"winner_team_id": match["team_a"]["id"]}
    )
    assert dup_resp.status_code == 400


def test_full_tournament_n8_reaches_completion(client):
    created = _create_tournament(client)
    manage_token = created["manage_token"]
    _add_participants(client, manage_token, 8)
    state = client.post(f"/tournaments/{manage_token}/start").json()

    safety = 0
    while state["status"] != "COMPLETE":
        safety += 1
        assert safety < 100, "tournament did not complete in a reasonable number of iterations"
        pending = _pending_playable_matches(state)
        if not pending:
            raise AssertionError(f"no pending matches but tournament not complete: {state['status']}")
        match = pending[0]
        resp = client.post(
            f"/tournaments/{manage_token}/matches/{match['id']}/report",
            json={"winner_team_id": match["team_a"]["id"]},
        )
        assert resp.status_code == 200
        state = resp.json()

    assert state["overall_champion"] is not None
    assert len(state["overall_champion"]) == 2
    wb_final = next(
        r
        for r in state["rounds"]
        if r["bracket"] == "WINNERS" and r["matches"][0]["kind"] == "TEAM_BYE" and r["matches"][0]["team_b"] is None
    )
    lb_final = next(
        r
        for r in state["rounds"]
        if r["bracket"] == "LOSERS" and r["matches"][0]["kind"] == "TEAM_BYE" and r["matches"][0]["team_b"] is None
    )
    assert wb_final is not None
    assert lb_final is not None
    gf_rounds = [r for r in state["rounds"] if r["bracket"] == "GRAND_FINAL"]
    assert len(gf_rounds) >= 1


def test_full_tournament_n5_handles_odd_seed_and_completes(client):
    created = _create_tournament(client)
    manage_token = created["manage_token"]
    _add_participants(client, manage_token, 5)
    state = client.post(f"/tournaments/{manage_token}/start").json()

    safety = 0
    while state["status"] != "COMPLETE":
        safety += 1
        assert safety < 100
        pending = _pending_playable_matches(state)
        if not pending:
            raise AssertionError(f"no pending matches but tournament not complete: {state['status']}")
        match = pending[0]
        resp = client.post(
            f"/tournaments/{manage_token}/matches/{match['id']}/report",
            json={"winner_team_id": match["team_a"]["id"]},
        )
        assert resp.status_code == 200
        state = resp.json()

    assert state["overall_champion"] is not None
    assert len(state["overall_champion"]) == 2


def test_grand_final_reset_when_lb_champion_wins_first_match(client):
    created = _create_tournament(client)
    manage_token = created["manage_token"]
    _add_participants(client, manage_token, 8)
    state = client.post(f"/tournaments/{manage_token}/start").json()

    safety = 0
    while state["status"] != "COMPLETE":
        safety += 1
        assert safety < 100
        pending = _pending_playable_matches(state)
        if not pending:
            raise AssertionError(f"no pending matches but tournament not complete: {state['status']}")
        match = pending[0]
        round_ = next(r for r in state["rounds"] if any(m["id"] == match["id"] for m in r["matches"]))
        # Force the LB champion (team_b, by construction) to win the first
        # grand-final match so we exercise the bracket-reset path.
        if round_["bracket"] == "GRAND_FINAL" and round_["round_number"] == 1:
            winner_id = match["team_b"]["id"]
        else:
            winner_id = match["team_a"]["id"]
        resp = client.post(
            f"/tournaments/{manage_token}/matches/{match['id']}/report", json={"winner_team_id": winner_id}
        )
        assert resp.status_code == 200
        state = resp.json()

    gf_rounds = sorted(
        [r for r in state["rounds"] if r["bracket"] == "GRAND_FINAL"], key=lambda r: r["round_number"]
    )
    assert len(gf_rounds) == 2
    assert gf_rounds[1]["matches"][0]["kind"] == "GRAND_FINAL_RESET"
    reset_match = gf_rounds[1]["matches"][0]
    reset_players = {
        p["id"]
        for p in (
            reset_match["team_a"]["player_one"],
            reset_match["team_a"]["player_two"],
            reset_match["team_b"]["player_one"],
            reset_match["team_b"]["player_two"],
        )
    }
    gf1_match = gf_rounds[0]["matches"][0]
    original_four = {
        p["id"]
        for p in (
            gf1_match["team_a"]["player_one"],
            gf1_match["team_a"]["player_two"],
            gf1_match["team_b"]["player_one"],
            gf1_match["team_b"]["player_two"],
        )
    }
    assert reset_players == original_four
    assert state["overall_champion"] is not None


def test_single_elimination_has_no_losers_bracket_or_grand_final(client):
    created = _create_tournament(client, format="SINGLE_ELIMINATION")
    manage_token = created["manage_token"]
    assert created["format"] == "SINGLE_ELIMINATION"
    _add_participants(client, manage_token, 8)
    state = client.post(f"/tournaments/{manage_token}/start").json()
    assert state["format"] == "SINGLE_ELIMINATION"

    safety = 0
    while state["status"] != "COMPLETE":
        safety += 1
        assert safety < 100
        pending = _pending_playable_matches(state)
        if not pending:
            raise AssertionError(f"no pending matches but tournament not complete: {state['status']}")
        match = pending[0]
        resp = client.post(
            f"/tournaments/{manage_token}/matches/{match['id']}/report",
            json={"winner_team_id": match["team_a"]["id"]},
        )
        assert resp.status_code == 200
        state = resp.json()

    # No losers bracket or grand final should ever have been created.
    assert not [r for r in state["rounds"] if r["bracket"] == "LOSERS"]
    assert not [r for r in state["rounds"] if r["bracket"] == "GRAND_FINAL"]
    assert state["overall_champion"] is not None
    assert len(state["overall_champion"]) == 2
    # Every non-champion participant should have been eliminated directly by a WB loss.
    champion_ids = {p["id"] for p in state["overall_champion"]}
    for p in state["participants"]:
        if p["id"] not in champion_ids:
            assert p["is_eliminated"], f"{p['display_name']} should be eliminated (no LB to catch WB losers)"


def test_single_elimination_odd_seed_completes(client):
    created = _create_tournament(client, format="SINGLE_ELIMINATION")
    manage_token = created["manage_token"]
    _add_participants(client, manage_token, 5)
    state = client.post(f"/tournaments/{manage_token}/start").json()

    safety = 0
    while state["status"] != "COMPLETE":
        safety += 1
        assert safety < 100
        pending = _pending_playable_matches(state)
        if not pending:
            raise AssertionError(f"no pending matches but tournament not complete: {state['status']}")
        match = pending[0]
        resp = client.post(
            f"/tournaments/{manage_token}/matches/{match['id']}/report",
            json={"winner_team_id": match["team_a"]["id"]},
        )
        assert resp.status_code == 200
        state = resp.json()

    assert not [r for r in state["rounds"] if r["bracket"] == "LOSERS"]
    assert state["overall_champion"] is not None


def test_default_format_is_double_elimination_when_omitted(client):
    resp = client.post("/tournaments", json={"name": "No format specified"})
    assert resp.status_code == 200
    assert resp.json()["format"] == "DOUBLE_ELIMINATION"
