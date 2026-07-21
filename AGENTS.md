# omys-backend

`omys` 앱의 백엔드. 기존 웹 MVP(FastAPI+Python, https://github.com/ssiuuuuuu/omys)의 아이디어와 데이터 모델을 참고하되, 코드는 새 스택으로 처음부터 작성한다.

이 레포는 스프린트1에서 집중적으로 작업되고, 스프린트2부터는 전담 인력 없이 iOS/Android 팀이 API만 보고 붙는 구조다. **API 계약을 문서로 정확히 남기는 것이 이 레포에서 제일 중요한 책임이다.**

## 이 문서에 대해

이 프로젝트는 Claude Code와 Codex를 함께 쓴다. 두 툴이 서로 다른 지시사항을 보면 어긋나기 쉬우니, 실제 규칙은 전부 이 `AGENTS.md`에만 쓰고 `CLAUDE.md`는 이 파일을 가리키기만 한다. 규칙을 바꿀 땐 반드시 `AGENTS.md`를 수정할 것.

## 팀 워크플로우

- `main`은 항상 배포 가능한 상태로 유지, 직접 push 금지
- 작업 브랜치: `feat/<설명>`, `fix/<설명>`, `chore/<설명>`
- PR 최소 1명 리뷰 후 squash merge
- 커밋 메시지: [Conventional Commits](https://www.conventionalcommits.org/) (`feat:`, `fix:`, `chore:`, `docs:`, `refactor:`)

## 스택

- Kotlin + Spring Boot 3.x (Spring Web, Spring Data JPA)
- PostgreSQL, Flyway로 마이그레이션 관리
- springdoc-openapi로 OpenAPI 스펙 / Swagger UI 자동 생성 (`/swagger-ui.html`, `/v3/api-docs`)
- Gradle (Kotlin DSL)

## 로컬 실행

```bash
./gradlew bootRun
```

DB 연결 정보 등 시크릿은 `.env` 또는 `application-local.yml`로 관리하고 커밋하지 않는다.

## API 계약 관리 (제일 중요한 규칙)

스프린트2부터는 iOS/Android 담당자가 백엔드 코드를 직접 보지 않고 API 계약만 보고 작업한다. **컨트롤러 시그니처나 요청/응답 스키마를 바꾸면, 같은 PR 안에서 반드시:**

1. springdoc이 생성하는 OpenAPI 스펙이 실제로 갱신됐는지 로컬에서 `/v3/api-docs` 확인
2. 어떤 엔드포인트/스키마가 바뀌었는지 PR 설명에 명시
