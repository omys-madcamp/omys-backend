import httpx
import pytest

from app.geo import travel_distance_meters, travel_minutes
from app.places import CachedPlacesProvider, KakaoPlacesProvider, place_matches_category
from app.schemas import PlaceResult
from app.services import opening_is_viable


@pytest.mark.asyncio
async def test_kakao_search_and_verification_use_origin_and_place_id():
    requests: list[httpx.Request] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        assert request.headers["Authorization"] == "KakaoAK test-key"
        return httpx.Response(
            200,
            json={
                "documents": [
                    {
                        "id": "12345",
                        "place_name": "시청 보드게임",
                        "category_name": "문화,예술 > 게임 > 보드게임카페",
                        "category_group_name": "",
                        "phone": "02-000-0000",
                        "address_name": "서울 중구 태평로",
                        "road_address_name": "서울 중구 세종대로",
                        "x": "126.9784",
                        "y": "37.5667",
                        "place_url": "https://place.map.kakao.com/12345",
                        "distance": "42",
                    }
                ]
            },
        )

    provider = KakaoPlacesProvider("test-key")
    await provider.client.aclose()
    provider.client = httpx.AsyncClient(
        transport=httpx.MockTransport(handler),
        headers={"Authorization": "KakaoAK test-key"},
    )

    places = await provider.search("보드게임", 37.5665, 126.9780, "게임·실내 놀거리")
    place = places[0]

    assert place.name == "시청 보드게임"
    assert place.distance_meters == 42
    assert place.external_place_id.startswith("kakao:12345:")
    assert len(place.external_place_id) <= 160
    assert requests[0].url.params["sort"] == "distance"
    assert requests[0].url.params["radius"] == "10000"
    assert requests[0].url.params["page"] == "1"
    assert opening_is_viable(place, 30) is True

    verified = await provider.verify(place.external_place_id)
    assert verified is not None
    assert verified.name == place.name
    assert requests[1].url.params["radius"] == "2000"

    await provider.client.aclose()


@pytest.mark.asyncio
async def test_kakao_condition_search_uses_time_radius_and_checks_later_pages():
    requests: list[httpx.Request] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        page = int(request.url.params["page"])
        return httpx.Response(
            200,
            json={
                "documents": [
                    {
                        "id": str(page),
                        "place_name": f"근처 보드게임 {page}",
                        "category_name": "문화,예술 > 게임 > 보드게임카페",
                        "category_group_name": "",
                        "phone": "",
                        "address_name": "서울 중구",
                        "road_address_name": "",
                        "x": "126.9784",
                        "y": "37.5667",
                        "place_url": f"https://place.map.kakao.com/{page}",
                        "distance": str(page * 100),
                    }
                ],
                "meta": {"is_end": page == 3},
            },
        )

    provider = KakaoPlacesProvider("test-key")
    await provider.client.aclose()
    provider.client = httpx.AsyncClient(
        transport=httpx.MockTransport(handler),
        headers={"Authorization": "KakaoAK test-key"},
    )

    radius = travel_distance_meters(30, "walk")
    places = await provider.search(
        "보드게임",
        37.5665,
        126.9780,
        "게임·실내 놀거리",
        radius=radius,
        page_count=3,
    )

    assert radius == 2100
    assert travel_minutes(radius, "walk") == 30
    assert [place.name for place in places] == [
        "근처 보드게임 1",
        "근처 보드게임 2",
        "근처 보드게임 3",
    ]
    assert [request.url.params["radius"] for request in requests] == ["2100"] * 3
    assert [request.url.params["page"] for request in requests] == ["1", "2", "3"]

    await provider.client.aclose()


def test_category_match_rejects_restaurants_from_game_results():
    board_game = PlaceResult(
        external_place_id="game",
        name="시청 보드게임",
        category="문화,예술 > 게임 > 보드게임카페",
        address="서울 중구",
        latitude=37.5665,
        longitude=126.9780,
    )
    restaurant = PlaceResult(
        external_place_id="food",
        name="게임존 숯불닭갈비",
        category="음식점 > 한식 > 육류,고기",
        address="서울 중구",
        latitude=37.5665,
        longitude=126.9780,
    )

    assert place_matches_category(board_game, "게임·실내 놀거리") is True
    assert place_matches_category(restaurant, "게임·실내 놀거리") is False


@pytest.mark.asyncio
async def test_cached_provider_filters_irrelevant_category_results():
    class MixedProvider(KakaoPlacesProvider):
        async def search(self, query, latitude, longitude, category=None):
            return [
                PlaceResult(
                    external_place_id="game",
                    name="강남 방탈출",
                    category="스포츠,오락 > 방탈출카페",
                    address="서울 강남구",
                    latitude=latitude,
                    longitude=longitude,
                ),
                PlaceResult(
                    external_place_id="food",
                    name="강남 맛집",
                    category="음식점 > 한식",
                    address="서울 강남구",
                    latitude=latitude,
                    longitude=longitude,
                ),
            ]

    provider = MixedProvider("test-key")
    await provider.client.aclose()
    cached = CachedPlacesProvider(provider, ttl=60)

    places = await cached.search("방탈출", 37.5665, 126.9780, "게임·실내 놀거리")

    assert [place.external_place_id for place in places] == ["game"]
