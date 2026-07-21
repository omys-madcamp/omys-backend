# 원본 대비 백엔드 변경 이력

원본: [ssiuuuuuu/omys](https://github.com/ssiuuuuuu/omys) `backend/`를 그대로 가져온 뒤 (`b572150`), 이 레포에서 직접 고친 부분만 기록한다. Kotlin+Spring 재구축은 하지 않고 이 FastAPI 코드베이스를 계속 이어간다.

## 2026-07-21 — 미스터리 활동 기능 전체 제거

- 제품 결정으로 "미스터리 활동"(방과 무관한 분위기별 랜덤 활동 추천) 기능을 스코프에서 뺌. `docs/omys-rebuild-spec.md`/`docs/feature-scope.md`엔 핵심 기능으로 나와있지만, 이 결정이 그 문서들보다 우선함.
- 제거한 것:
  - `app/activities.py` 파일 삭제 (활동 카탈로그, mood 선택 로직)
  - `app/models.py`의 `ActivitySession` 모델 삭제
  - `app/schemas.py`의 `ActivitySessionCreate`/`ActivityDraw`/`ActivityComplete` 삭제
  - `app/main.py`의 `GET /api/activities`, `POST /api/activity-sessions`, `GET/POST /api/activity-sessions/{id}/...` (draw/skip/start/complete) 엔드포인트 전부 삭제
  - 분석 이벤트 allowlist(`EVENTS`)에서 `activity_*` 계열 전부 제거, 관리자 통계(`/api/admin/stats`)의 `activity_visitors`/`activity_pageviews` 필드와 집계 로직도 제거
  - `alembic/versions/e3f7c2a9d456_drop_activity_sessions.py` — `activity_sessions` 테이블 drop (기존 배포된 마이그레이션은 안 건드리고 새 마이그레이션으로 처리)
  - `tests/test_activities_flow.py` 삭제, `tests/test_admin_stats.py`에서 활동 관련 assertion 제거
- **API 계약 변경**: iOS 쪽엔 애초에 이 엔드포인트들 아직 안 붙였으니 영향 없음. 혹시 프론트/기획 쪽에 미스터리 활동 화면이 이미 논의됐다면 그쪽에 스코프 제외 공유 필요.

필요해지면 이 문서에 이어서 기록할 것.
