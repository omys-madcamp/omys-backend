# Backend 기능 범위 (핵심 / 선택)

> 전체 서비스 명세는 [`omys-rebuild-spec.md`](./omys-rebuild-spec.md) 참고. 이 문서는 그중 **백엔드가 담당하는 부분만** 골라 핵심(MVP)/선택으로 나눈 작업 가이드다. 팀원이 "이번 스프린트에 뭘 꼭 해야 하나"를 고를 때 기준으로 쓴다.

## 핵심 기능 (MVP — 반드시 구현)

### 도메인 & 상태
- Room 생성/조회/참가, 상태 전이 `waiting → drawn → navigating → revealed` (허용 안 된 전이는 409)
- 6자리 초대 코드(영문+숫자 혼합, unique) 발급/검증
- Participant: 닉네임, 참가자 토큰 발급(256비트 이상, 서버는 hash만 저장), 방장 여부
- 친구 모드: 후보 제출(본인만 조회 가능), 제출 완료 처리, 전원 완료 + 2명 이상일 때만 방장 추첨 허용
- OMYS 모드: 조건 저장 → 장소 검색 → 필터(이동시간/예산/카테고리/실내외/제외활동/음식/총시간) → 최종 영업 재검증 → 선정
- 재추첨: 방장만, `drawn` 상태에서 출발 전, 최대 1회, 이전 선정지 재선정 금지
- 추첨 동시성 보장: DB row lock 또는 동등 원자적 처리 + unique constraint, `SecureRandom` 사용, 중복 draw 요청은 기존 결과 반환
- 이동/공개: 위치 기반 남은거리/ETA/진행률/방향 힌트만 응답 (공개 전 목적지 이름/주소/좌표/외부ID/전화/URL 절대 미노출), 마지막 100m 경로는 잘라서 응답
- 도착 판정(기본 100m) 후 reveal 가능 여부 반환, `/reveal` 재검증 후 상태를 `revealed`로 전환
- 방장 수동 공개 옵션 (`hideUntilArrival=false`일 때)
- 공유 API: 공개 전/후 응답 분리 (공개 전엔 장소 상세 없음)
- 미스터리 활동: 세션 생성(익명), 분위기별 추첨, 건너뛰기, 시작/타이머 기준시각 저장, 완료(성공/실패/중단) 기록
- 안전 검수된 활동 카탈로그 (위해 가능 활동 전면 배제 — 기존 FastAPI의 폭죽/뜨거운 국물 등 위험 활동 절대 이관 금지)
- 익명 분석 이벤트 수집 API (allowlist 방식, 좌표/토큰/비공개 장소 절대 기록 금지) + 관리자 집계 API

### API 계약
- OpenAPI 스펙 (springdoc-openapi) 우선 확정 후 구현, 엔드포인트는 명세서 §6.2 표 그대로
- 공통 오류 응답 포맷(`code`/`message`/`field_errors`/`trace_id`) 전 엔드포인트 통일
- 권한별 Room 응답 DTO 분리 (엔티티 직접 직렬화 금지 — 명세서 §6.4 공개 정책 표 그대로 구현)

### 보안 (P0, 협상 불가)
- 목적지 비공개 전 정보가 API 응답/로그 어디에도 없음 (통합 테스트로 검증)
- 참가자 토큰 Keychain/Keystore 대응 — 서버는 hash만 저장
- 서버 API 키/관리자 키를 코드/저장소에 하드코딩 금지, `.env`로 관리
- **기존 FastAPI의 `navigation_admin_key` 기본값 + `/reveal` body `admin_key` 우회 경로는 이관 금지** (새로 관리자 인증 방식 설계)
- 입력 검증(길이/enum), CORS는 공개 웹 origin만 허용
- endpoint별 rate limit (join/search/analytics 별도 제한)
- 로그 masking (토큰/좌표/비공개 장소/API 키 미기록)

### 인프라 (MVP 최소)
- PostgreSQL + Flyway 마이그레이션
- Docker 이미지, HTTPS, 기본 CI(테스트/빌드 PR 게이트)
- Places Provider 인터페이스 + Mock/Kakao(또는 Google) 구현체 최소 1개

## 선택 사항 (시간 되면 / 이후 개선)

- Redis (rate limit/캐시/이동 상태) — 단일 인스턴스면 Caffeine으로 충분, 다중 인스턴스 확장 시에만 필요
- Resilience4j (retry/circuit breaker) — 외부 provider 장애 대비, 없어도 MVP 동작엔 지장 없음
- Micrometer/Actuator, OpenTelemetry/Sentry 등 관측 — 프로덕션 운영 품질용, 데모/MVP엔 필수 아님
- 실제 경로/ETA provider 연동 — MVP는 직선거리 추정치로 대체 가능 (UI에 "예상"으로 표기)
- `Idempotency-Key` 헤더 — 있으면 좋지만 없어도 기존 멱등성 로직(중복 draw 반환 등)으로 MVP 커버 가능
- staging 배포 단계, 알림(quota/5xx) — 해커톤 규모에서는 후순위
- 관리자 지표 API의 시간대별(6h/12h/24h/3d) 세분화 — 기본 전체 집계만으로 시작 가능

## 범위 밖 (아예 안 만듦)

- 회원가입/로그인, 친구 목록, 채팅, 결제, 리뷰 작성
- 상시 백그라운드 위치 추적, 완전한 턴바이턴 내비게이션
