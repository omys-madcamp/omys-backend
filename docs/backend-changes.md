# 원본 대비 백엔드 변경 이력

원본: [ssiuuuuuu/omys](https://github.com/ssiuuuuuu/omys) `backend/`를 그대로 가져온 뒤 (`b572150`), 이 레포에서 직접 고친 부분만 기록한다. Kotlin+Spring 재구축은 하지 않고 이 FastAPI 코드베이스를 계속 이어간다.

## 2026-07-21 — Kakao 차량 경로만 쓰던 버그 수정 + 도보 경로에 Tmap 보행자 API 연동

- 이전: `navigation_route()`가 `transport_mode`와 상관없이 무조건 Kakao Mobility의 차량 길찾기 REST API(`apis-navi.kakaomobility.com`)를 호출했음. Kakao는 도보/대중교통 REST API 자체가 없어서, walk 모드 방에서도 이동 화면에 자동차 도로 기준 경로가 나오는 버그가 있었음.
- 1차 수정: `mode != "car"`면 Kakao 호출을 안 하고 직선(origin→destination) 경로로 fallback (ETA 계산은 원래도 mode별 속도로 직선거리 기반이라 정상이었음, 화면에 그리는 폴리라인만 문제였음).
- 2차로 실제 도보 경로가 필요해서 Tmap(SK Open API) 보행자 길찾기를 붙임.
  - `app/services.py`:
    - `_tmap_pedestrian_route` 추가 — `POST https://apis.openapi.sk.com/tmap/routes/pedestrian` 호출, `appKey` 헤더 인증.
    - `_coordinates_from_tmap_pedestrian` — 응답 GeoJSON의 `LineString` feature들에서 `[lon, lat]` 좌표를 `(lat, lon)`으로 변환 (카카오 파서와 동일 좌표 관례 유지).
    - 경로 마무리 로직(`len < 2`면 버리고 origin/destination 보정)은 `_finalize_route`로 공통화해서 Kakao/Tmap 둘 다 재사용.
    - `navigation_route(origin, destination, mode)`: `mode == "car"` → Kakao 차량 경로, `mode == "walk"` → Tmap 보행자 경로, 그 외(transit) 또는 해당 provider 키 없으면 직선 fallback.
  - `app/config.py`에 `tmap_api_key` 설정 추가 (`TMAP_API_KEY` env). 값 없으면 walk도 자동으로 직선 fallback되니 배포 전 반드시 채워야 함.
  - 순수 파싱 로직(`_coordinates_from_tmap_pedestrian`, `_finalize_route`, 기존 카카오 파서)에 대한 유닛 테스트 추가 (`tests/test_navigation_routes.py`) — 실제 네트워크 호출 없이 좌표 변환만 검증. 통합 테스트는 `environment == "test"`일 때 항상 직선 fallback을 타서 외부 호출 없이 통과함.
- 참고: Tmap 앱키는 콘솔(openapi.sk.com)에서 앱에 "경로안내" 상품을 연결해야 동작함 — 연결 직후엔 활성화 시차로 몇 분간 403 `INVALID_API_KEY`가 날 수 있음.

## 아직 손 안 댄 항목

- transit 모드는 아직 직선 fallback만 있음 (실제 대중교통 경로 provider 미연동, 필요해지면 Tmap 대중교통 API 검토)
- rate limit / 검색 캐시 / 내비게이션 경로 캐시가 프로세스 메모리 (다중 인스턴스 시 깨짐, 싱글 인스턴스 MVP는 문제 없음)
- Kakao 검색 결과 중 영업시간 미확인 후보(`UNKNOWN_KAKAO`)에 대한 안내 UX 미비 (iOS UI 영역)

필요해지면 이 문서에 이어서 기록할 것.
