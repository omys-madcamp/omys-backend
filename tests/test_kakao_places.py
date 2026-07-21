import httpx
import pytest

from app.geo import travel_distance_meters, travel_minutes
from app.places import (
    CachedPlacesProvider,
    KakaoPlacesProvider,
    estimate_price_level,
    infer_category,
    is_food_place,
    is_outdoor_place,
    place_matches_category,
    query_matches_place,
)
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


def test_infer_category_resolves_known_discovery_query_without_explicit_category():
    assert infer_category("보드게임카페", None) == "게임·실내 놀거리"
    assert infer_category("공원", None) == "관광·산책"
    assert infer_category("보드게임카페", "쇼핑·구경") == "쇼핑·구경"
    assert infer_category("아무 검색어", None) is None


@pytest.mark.asyncio
async def test_cached_provider_filters_starbucks_out_of_free_text_board_game_search():
    class NoisyProvider(KakaoPlacesProvider):
        async def search(self, query, latitude, longitude, category=None):
            return [
                PlaceResult(
                    external_place_id="game",
                    name="홍대 보드게임카페",
                    category="오락,스포츠 > 보드게임카페",
                    address="서울 마포구",
                    latitude=latitude,
                    longitude=longitude,
                ),
                PlaceResult(
                    external_place_id="starbucks",
                    name="스타벅스 홍대점",
                    category="음식점 > 카페 > 커피전문점",
                    address="서울 마포구",
                    latitude=latitude,
                    longitude=longitude,
                ),
            ]

    provider = NoisyProvider("test-key")
    await provider.client.aclose()
    cached = CachedPlacesProvider(provider, ttl=60)

    # No `category` passed — same shape as a client free-text search — must still filter.
    places = await cached.search("보드게임카페", 37.5665, 126.9780)

    assert [place.external_place_id for place in places] == ["game"]


def test_query_matches_place_requires_literal_query_in_name_or_category():
    starbucks = PlaceResult(
        external_place_id="starbucks",
        name="스타벅스 홍대점",
        category="음식점 > 카페 > 커피전문점",
        address="서울 마포구",
        latitude=37.5,
        longitude=126.9,
    )
    board_game_cafe = PlaceResult(
        external_place_id="game",
        name="홍대 보드게임카페",
        category="오락,스포츠 > 보드게임카페",
        address="서울 마포구",
        latitude=37.5,
        longitude=126.9,
    )
    assert query_matches_place("보드게임카페", starbucks) is False
    assert query_matches_place("보드게임카페", board_game_cafe) is True
    assert query_matches_place("", starbucks) is True


def test_is_food_place_matches_provider_category_keywords():
    starbucks = PlaceResult(
        external_place_id="starbucks",
        name="스타벅스 홍대점",
        category="음식점 > 카페 > 커피전문점",
        address="서울 마포구",
        latitude=37.5,
        longitude=126.9,
    )
    board_game_cafe = PlaceResult(
        external_place_id="game",
        name="홍대 보드게임카페",
        category="오락,스포츠 > 보드게임카페",
        address="서울 마포구",
        latitude=37.5,
        longitude=126.9,
    )
    assert is_food_place(starbucks) is True
    assert is_food_place(board_game_cafe) is False


def test_is_outdoor_place_from_flag_or_category_keywords():
    flagged_outdoor = PlaceResult(
        external_place_id="flagged",
        name="이름만으로는 모름",
        category="기타",
        address="서울",
        latitude=37.5,
        longitude=126.9,
        is_public_outdoor=True,
    )
    park_by_name = PlaceResult(
        external_place_id="park",
        name="반포 한강공원",
        category="관광명소 > 공원",
        address="서울 서초구",
        latitude=37.5,
        longitude=126.9,
    )
    indoor_place = PlaceResult(
        external_place_id="climbing",
        name="성수 실내 클라이밍",
        category="스포츠,오락 > 클라이밍",
        address="서울 성동구",
        latitude=37.5,
        longitude=126.9,
    )
    assert is_outdoor_place(flagged_outdoor) is True
    assert is_outdoor_place(park_by_name) is True
    assert is_outdoor_place(indoor_place) is False


def test_estimate_price_level_prefers_provider_value_then_category_fallback():
    priced = PlaceResult(
        external_place_id="priced",
        name="장소",
        category="장소",
        address="서울",
        latitude=37.5,
        longitude=126.9,
        price_level=3,
    )
    free_outdoor = PlaceResult(
        external_place_id="park",
        name="반포 한강공원",
        category="관광명소 > 공원",
        address="서울 서초구",
        latitude=37.5,
        longitude=126.9,
        is_public_outdoor=True,
    )
    pottery_studio = PlaceResult(
        external_place_id="pottery",
        name="연남 도자기 작업실",
        category="체험,공방 > 도자기공방",
        address="서울 마포구",
        latitude=37.5,
        longitude=126.9,
    )
    unknown = PlaceResult(
        external_place_id="unknown",
        name="정체불명 장소",
        category="기타",
        address="서울",
        latitude=37.5,
        longitude=126.9,
    )
    assert estimate_price_level(priced) == 3
    assert estimate_price_level(free_outdoor) == 0
    assert estimate_price_level(pottery_studio) == 3
    assert estimate_price_level(unknown) is None
