# 원본 대비 백엔드 변경 이력

원본: [ssiuuuuuu/omys](https://github.com/ssiuuuuuu/omys) `backend/`를 그대로 가져온 뒤 (`b572150`), 이 레포에서 직접 고친 부분만 기록한다. Kotlin+Spring 재구축은 하지 않고 이 FastAPI 코드베이스를 계속 이어간다 (스택 결정은 `AGENTS.md` 참고).

## 2026-07-21 — P0 보안 수정

`docs/omys-rebuild-spec.md` §11 "현재 코드에서 그대로 옮기면 안 되는 항목"에서 지적된 것 중 실제로 코드에 남아있던 3가지를 수정.

### 1. 참가자 토큰 평문 저장 → 해시 저장

- 이전: `participants.participant_token` 컬럼에 원문 토큰을 그대로 저장하고, 요청마다 원문끼리 비교 (`app/security.py`, `app/models.py`).
- 이후: 컬럼명 `token_hash`로 변경, `sha256` 해시만 저장. 요청 시 들어온 토큰을 해시해서 비교 (`security.hash_token`).
- 원문 토큰은 방 생성/입장 응답(`participant_token` 필드)에서 여전히 1회만 내려준다 — API 응답 계약은 안 바뀜, DB 저장 방식만 바뀜.
- 마이그레이션: `alembic/versions/c7a4f1e93b6d_hash_participant_token.py` (컬럼 rename + unique constraint/index 재생성).
- **주의**: 기존에 로컬/개발 DB에 생성된 방이 있다면 저장된 값이 해시가 아니라 예전 원문이라 로그인(토큰 조회)이 깨진다. 운영 데이터 없는 시점이라 별도 백필 없이 진행함.

### 2. `/reveal`의 관리자 키 우회 경로 제거

- 이전: `config.py`의 `navigation_admin_key` 기본값이 `"1210"`으로 하드코딩되어 있었고, `/api/rooms/{code}/reveal` 요청 body에 `admin_key`를 보내면 위치 검증도 방장 권한도 없이 바로 공개 처리됨 (`app/main.py`).
- 이후: 이 분기 전체 삭제. `admin_key` 필드도 `RevealRequest` 스키마에서 제거. 정상적인 수동 공개는 기존 `manual_confirm` + `require_host` 경로(방장 전용)로만 가능.
- 관리자 통계 API(`/api/admin/stats`)의 `X-Admin-Key` 인증은 별개 메커니즘이라 그대로 둠 — 이건 하드코딩된 기본값이 없고 env로만 설정됨.
- 영향받은 테스트: `tests/test_omys_flow.py`의 `test_destination_can_be_revealed_with_test_admin_key` 삭제 (기능 자체가 없어졌으므로).

### 3. 위해 가능 활동(dopamine 카테고리) 교체

- 이전: `app/activities.py`의 dopamine 활동 4개가 폭죽 맞기, 뜨거운 국물에 손가락 넣기, 날계란 맞기, 전기파리채로 맞기였음. 같은 파일의 안전성 테스트(`test_activities_flow.py`)와 실제 데이터가 서로 안 맞는 상태였음.
- 이후: 신체 위해 요소 없는 활동 10개로 전면 교체 (색깔 찾기, 목소리 순서 맞히기, 가위바위보 대결, 삼행시, 이어말하기 등).
- 원래 dopamine 항목이 4개뿐이라 `light`/`funny`(각 10개)와 개수가 안 맞았던 것도 겸사겸사 10개로 맞춤 — `test_all_activities_can_reset_without_immediate_repeat` 테스트가 이 불일치 때문에 원래부터 실패하고 있었음 (이번 변경과 무관한 기존 버그, 같이 해결됨).

## 2026-07-21 — 활동 세션 소유권 검증 추가

- 이전: `GET/POST /api/activity-sessions/{id}/...` 전부 세션 UUID만 알면 아무나 조회/skip/start/complete 가능 (`app/main.py`의 `activity_session_by_id`가 `db.get`으로 인증 없이 바로 반환).
- 이후: 참가자 토큰과 같은 패턴 적용.
  - `ActivitySession`에 `session_token_hash` 컬럼 추가 (`alembic/versions/d9b2e6a4f018_add_activity_session_token.py`).
  - `POST /api/activity-sessions` 응답에 원문 `session_token` 필드 추가 (이 호출에서만 값이 들어있고, 이후 응답에서는 항상 `null`).
  - 이후 모든 세션 endpoint(`GET /{id}`, `/draw`, `/skip`, `/start`, `/complete`)는 `X-Session-Token` 헤더 필수 — 없으면 401, id/토큰 조합이 안 맞으면 404 (세션 존재 여부를 노출하지 않기 위해 403 대신 404로 통일).
- **API 계약 변경**: iOS 쪽은 세션 생성 응답의 `session_token`을 저장해뒀다가 이후 모든 활동 세션 요청에 `X-Participant-Token`과 동일한 방식으로 `X-Session-Token` 헤더로 실어 보내야 함.
- 영향받은 테스트: `tests/test_activities_flow.py` 전체 헤더 추가, `test_activity_session_requires_matching_token` 신규 추가.

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

## 2026-07-21 — 미스터리 활동 기능 전체 제거

- 제품 결정으로 "미스터리 활동"(방과 무관한 분위기별 랜덤 활동 추천) 기능을 스코프에서 뺌. `docs/omys-rebuild-spec.md`/`docs/feature-scope.md`엔 핵심 기능으로 나와있지만, 이 결정이 그 문서들보다 우선함. 바로 위 "활동 세션 소유권 검증" 작업은 이 결정 이전에 들어간 것이라 이력으로만 남는다.
- 제거한 것:
  - `app/activities.py` 파일 삭제 (활동 카탈로그, mood 선택 로직)
  - `app/models.py`의 `ActivitySession` 모델 삭제
  - `app/schemas.py`의 `ActivitySessionCreate`/`ActivityDraw`/`ActivityComplete` 삭제
  - `app/main.py`의 `GET /api/activities`, `POST /api/activity-sessions`, `GET/POST /api/activity-sessions/{id}/...` (draw/skip/start/complete) 엔드포인트 전부 삭제
  - `app/security.py`의 `session_token_header` (활동 세션 전용 인증이라 같이 제거)
  - 분석 이벤트 allowlist(`EVENTS`)에서 `activity_*` 계열 전부 제거, 관리자 통계(`/api/admin/stats`)의 `activity_visitors`/`activity_pageviews` 필드와 집계 로직도 제거
  - `alembic/versions/e3f7c2a9d456_drop_activity_sessions.py` — `activity_sessions` 테이블 drop (기존 배포된 마이그레이션은 안 건드리고 새 마이그레이션으로 처리)
  - `tests/test_activities_flow.py` 삭제, `tests/test_admin_stats.py`에서 활동 관련 assertion 제거
- **API 계약 변경**: iOS 쪽엔 애초에 이 엔드포인트들 아직 안 붙였으니 영향 없음. 혹시 프론트/기획 쪽에 미스터리 활동 화면이 이미 논의됐다면 그쪽에 스코프 제외 공유 필요.

## 아직 손 안 댄 항목

- transit 모드는 아직 직선 fallback만 있음 (실제 대중교통 경로 provider 미연동, 필요해지면 Tmap 대중교통 API 검토)
- rate limit / 검색 캐시 / 내비게이션 경로 캐시가 프로세스 메모리 (다중 인스턴스 시 깨짐, 싱글 인스턴스 MVP는 문제 없음)
- Kakao 검색 결과 중 영업시간 미확인 후보(`UNKNOWN_KAKAO`)에 대한 안내 UX 미비 (iOS UI 영역) — Google Places로 최종 검증하는 방안 검토했으나 영업시간 필드가 Enterprise SKU라 비용 부담 큼, TourAPI(무료, 관광/쇼핑 카테고리 한정) 절충안 검토 중
- `admin_api_key` 기본값(`"change-me-before-production"`)이 여전히 하드코딩 — prod 환경에서 기본값 그대로면 막는 안전장치 없음

필요해지면 이 문서에 이어서 기록할 것.
