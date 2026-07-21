from app.services import (
    _coordinates_from_kakao_directions,
    _coordinates_from_tmap_pedestrian,
    _finalize_route,
)


def test_tmap_pedestrian_parses_linestring_features_as_lat_lon():
    payload = {
        "features": [
            {"geometry": {"type": "Point", "coordinates": [126.978, 37.5665]}},
            {
                "geometry": {
                    "type": "LineString",
                    "coordinates": [
                        [126.978, 37.5665],
                        [126.979, 37.5670],
                        [126.979, 37.5670],
                        [126.980, 37.5675],
                    ],
                }
            },
        ]
    }
    route = _coordinates_from_tmap_pedestrian(payload)
    assert route == [
        (37.5665, 126.978),
        (37.5670, 126.979),
        (37.5675, 126.980),
    ]


def test_tmap_pedestrian_ignores_missing_features():
    assert _coordinates_from_tmap_pedestrian({}) == []
    assert _coordinates_from_tmap_pedestrian({"features": []}) == []


def test_kakao_directions_still_parses_vertexes_as_lat_lon():
    payload = {
        "routes": [
            {
                "sections": [
                    {
                        "roads": [
                            {"vertexes": [126.978, 37.5665, 126.979, 37.5670]},
                        ]
                    }
                ]
            }
        ]
    }
    assert _coordinates_from_kakao_directions(payload) == [
        (37.5665, 126.978),
        (37.5670, 126.979),
    ]


def test_finalize_route_prepends_and_appends_missing_endpoints():
    origin = (37.5, 127.0)
    destination = (37.6, 127.1)
    route = _finalize_route([(37.52, 127.02), (37.55, 127.05)], origin, destination)
    assert route == [origin, (37.52, 127.02), (37.55, 127.05), destination]


def test_finalize_route_rejects_route_with_fewer_than_two_points():
    assert _finalize_route([], (37.5, 127.0), (37.6, 127.1)) is None
    assert _finalize_route([(37.5, 127.0)], (37.5, 127.0), (37.6, 127.1)) is None
