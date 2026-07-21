from conftest import auth
from app.database import SessionLocal
from app.models import PlaceCandidate, Room
from sqlalchemy import select


def create_room(client, hide_until_arrival=False):
    response = client.post(
        "/api/rooms",
        json={
            "title": "토요일 모험",
            "mode": "friends",
            "host_nickname": "방장",
            "departure": {"label": "서울시청", "latitude": 37.5665, "longitude": 126.9780},
            "redraw_allowed": True,
            "hide_until_arrival": hide_until_arrival,
        },
    )
    assert response.status_code == 201
    room = response.json()
    assert len(room["invite_code"]) == 6
    assert room["invite_code"].isalnum()
    assert any(character.isalpha() for character in room["invite_code"])
    assert any(character.isdigit() for character in room["invite_code"])
    return room


def submit(client, code, token, place):
    response = client.post(
        f"/api/rooms/{code}/candidates", headers=auth(token), json={"place": place}
    )
    assert response.status_code == 201, response.text
    assert (
        client.post(f"/api/rooms/{code}/submission/complete", headers=auth(token)).status_code
        == 200
    )


def test_secret_candidates_locked_draw_and_redraw_rules(client):
    host = create_room(client)
    code = host["invite_code"]
    guest_response = client.post(f"/api/rooms/{code}/join", json={"nickname": "친구"})
    assert guest_response.status_code == 201
    guest = guest_response.json()

    search = client.get(
        f"/api/rooms/{code}/places/search",
        headers=auth(host["participant_token"]),
    )
    assert search.status_code == 200
    open_places = [
        item for item in search.json()["places"] if item["open_now"] or item["is_public_outdoor"]
    ]
    assert len(open_places) >= 2
    submit(client, code, host["participant_token"], open_places[0])
    submit(client, code, guest["participant_token"], open_places[1])

    host_view = client.get(f"/api/rooms/{code}", headers=auth(host["participant_token"])).json()
    guest_view = client.get(f"/api/rooms/{code}", headers=auth(guest["participant_token"])).json()
    assert len(host_view["own_candidates"]) == 1
    assert len(guest_view["own_candidates"]) == 1
    assert host_view["own_candidates"][0]["name"] != guest_view["own_candidates"][0]["name"]

    draw = client.post(f"/api/rooms/{code}/draw", headers=auth(host["participant_token"]))
    assert draw.status_code == 200, draw.text
    assert draw.json()["selection_locked"] is True
    views = [
        client.get(f"/api/rooms/{code}", headers=auth(host["participant_token"])).json(),
        client.get(f"/api/rooms/{code}", headers=auth(guest["participant_token"])).json(),
    ]
    assert sum(view["selected_place"] is not None for view in views) == 1
    selected_name = next(view["selected_place"]["name"] for view in views if view["selected_place"])

    repeated = client.post(f"/api/rooms/{code}/draw", headers=auth(host["participant_token"]))
    assert repeated.status_code == 200
    repeated_views = [
        client.get(f"/api/rooms/{code}", headers=auth(item)).json()
        for item in [host["participant_token"], guest["participant_token"]]
    ]
    assert (
        next(view["selected_place"]["name"] for view in repeated_views if view["selected_place"])
        == selected_name
    )
    assert client.get(f"/api/share/{code}").json()["place"] is None

    redraw = client.post(f"/api/rooms/{code}/redraw", headers=auth(host["participant_token"]))
    assert redraw.status_code == 200, redraw.text
    assert redraw.json()["redraw_count"] == 1
    assert (
        client.post(
            f"/api/rooms/{code}/redraw", headers=auth(host["participant_token"])
        ).status_code
        == 409
    )
    assert (
        client.post(f"/api/rooms/{code}/start", headers=auth(host["participant_token"])).status_code
        == 200
    )
    assert (
        client.post(
            f"/api/rooms/{code}/redraw", headers=auth(host["participant_token"])
        ).status_code
        == 409
    )


def test_closed_place_is_never_selected(client):
    host = create_room(client)
    code = host["invite_code"]
    guest = client.post(f"/api/rooms/{code}/join", json={"nickname": "친구"}).json()
    search = client.get(
        f"/api/rooms/{code}/places/search?q=오늘%20쉬는", headers=auth(host["participant_token"])
    ).json()["places"]
    closed = next(item for item in search if item["external_place_id"] == "mock-closed")
    submit(client, code, host["participant_token"], closed)
    submit(client, code, guest["participant_token"], closed)
    response = client.post(f"/api/rooms/{code}/draw", headers=auth(host["participant_token"]))
    assert response.status_code == 422
    assert "찾지 못했습니다" in response.json()["detail"]


def test_hidden_friend_spot_uses_navigation_and_reveals_submitter(client):
    host = create_room(client, hide_until_arrival=True)
    code = host["invite_code"]
    guest = client.post(f"/api/rooms/{code}/join", json={"nickname": "친구"}).json()
    search = client.get(
        f"/api/rooms/{code}/places/search",
        headers=auth(host["participant_token"]),
    )
    open_places = [
        item for item in search.json()["places"] if item["open_now"] or item["is_public_outdoor"]
    ]
    submit(client, code, host["participant_token"], open_places[0])
    submit(client, code, guest["participant_token"], open_places[1])

    draw = client.post(f"/api/rooms/{code}/draw", headers=auth(host["participant_token"]))
    assert draw.status_code == 200, draw.text
    views = [
        client.get(f"/api/rooms/{code}", headers=auth(token)).json()
        for token in [host["participant_token"], guest["participant_token"]]
    ]
    assert all(view["selected_place"] is None for view in views)
    assert all(view["you_are_guide"] is False for view in views)

    assert (
        client.post(f"/api/rooms/{code}/start", headers=auth(host["participant_token"])).status_code
        == 200
    )
    with SessionLocal() as db:
        room = db.scalar(select(Room).where(Room.invite_code == code))
        place = db.get(PlaceCandidate, room.selected_place_id)
        target = {"latitude": place.latitude, "longitude": place.longitude, "accuracy": 20}

    navigation = client.post(
        f"/api/rooms/{code}/navigation",
        headers=auth(guest["participant_token"]),
        json=target,
    )
    assert navigation.status_code == 200
    assert navigation.json()["reveal_available"] is True

    reveal = client.post(
        f"/api/rooms/{code}/reveal",
        headers=auth(guest["participant_token"]),
        json=target,
    )
    assert reveal.status_code == 200, reveal.text
    assert reveal.json()["selected_place"]["name"]
    assert reveal.json()["selected_by_nickname"] in {"방장", "친구"}
