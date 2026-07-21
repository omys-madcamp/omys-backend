from math import asin, ceil, cos, radians, sin, sqrt


Coordinate = tuple[float, float]


def distance_meters(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    earth = 6_371_000
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
    return 2 * earth * asin(sqrt(a))


def path_length(path: list[Coordinate]) -> float:
    return sum(
        distance_meters(start[0], start[1], end[0], end[1]) for start, end in zip(path, path[1:])
    )


def closest_path_index(path: list[Coordinate], latitude: float, longitude: float) -> int:
    if not path:
        return 0
    return min(
        range(len(path)),
        key=lambda index: distance_meters(
            latitude,
            longitude,
            path[index][0],
            path[index][1],
        ),
    )


def slice_path_ahead(
    path: list[Coordinate],
    max_distance: float,
    reserve_at_end: float = 0,
) -> list[Coordinate]:
    if len(path) < 2 or max_distance <= 0:
        return path[:1]

    visible_distance = min(max_distance, max(0, path_length(path) - reserve_at_end))
    if visible_distance <= 0:
        return path[:1]

    result = [path[0]]
    traversed = 0.0
    for start, end in zip(path, path[1:]):
        segment = distance_meters(start[0], start[1], end[0], end[1])
        if segment <= 0:
            continue
        if traversed + segment <= visible_distance:
            result.append(end)
            traversed += segment
            continue

        fraction = (visible_distance - traversed) / segment
        result.append(
            (
                start[0] + (end[0] - start[0]) * fraction,
                start[1] + (end[1] - start[1]) * fraction,
            )
        )
        break
    return result


SPEED_KMH = {"walk": 4.2, "transit": 18.0, "car": 24.0}


def travel_distance_meters(minutes: int, mode: str) -> int:
    """Return the straight-line distance covered by the ETA model."""
    speed = SPEED_KMH.get(mode, SPEED_KMH["walk"])
    return ceil(speed * 1000 * minutes / 60)


def travel_minutes(distance: float, mode: str) -> int:
    speed = SPEED_KMH.get(mode, SPEED_KMH["walk"])
    return max(1, round((distance / 1000) / speed * 60))


def navigation_hint(from_lat: float, from_lon: float, to_lat: float, to_lon: float) -> str:
    vertical = "북쪽" if to_lat >= from_lat else "남쪽"
    horizontal = "동쪽" if to_lon >= from_lon else "서쪽"
    return f"{vertical} · {horizontal} 방향으로 이동하세요"
