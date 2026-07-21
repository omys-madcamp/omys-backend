# omys-backend

`omys` 앱의 백엔드. 기존 웹 MVP(FastAPI+Python, https://github.com/ssiuuuuuu/omys)를 새 스택으로 재작성하지 않고, 이 FastAPI 코드베이스를 그대로 이어받아 계속 개발한다. iOS 앱만 새로 만든다.

이 레포는 스프린트1에서 집중적으로 작업되고, 스프린트2부터는 전담 인력 없이 iOS 팀이 API만 보고 붙는 구조다. **API 계약을 문서로 정확히 남기는 것이 이 레포에서 제일 중요한 책임이다.**

> 원래 `docs/omys-rebuild-spec.md`, `docs/feature-scope.md`는 Kotlin+Spring 재구축을 전제로 쓴 문서라 스택 관련 서술은 더 이상 유효하지 않다. 도메인 규칙·상태 전이·보안 요구사항(P0)·API 계약 부분은 여전히 기준으로 참고하되, 스택/기술 선택 부분은 이 파일이 우선한다.

전체 서비스 명세는 [`docs/omys-rebuild-spec.md`](docs/omys-rebuild-spec.md), 백엔드가 담당하는 범위를 핵심(MVP)/선택으로 나눈 가이드는 [`docs/feature-scope.md`](docs/feature-scope.md)를 참고한다. 새 기능을 시작하기 전에 먼저 이 두 문서를 확인할 것.

## 이 문서에 대해

이 프로젝트는 Claude Code와 Codex를 함께 쓴다. 두 툴이 서로 다른 지시사항을 보면 어긋나기 쉬우니, 실제 규칙은 전부 이 `AGENTS.md`에만 쓰고 `CLAUDE.md`는 이 파일을 가리키기만 한다. 규칙을 바꿀 땐 반드시 `AGENTS.md`를 수정할 것.

## 팀 워크플로우

- `main`은 항상 배포 가능한 상태로 유지, 직접 push 금지
- 작업 브랜치: `feat/<설명>`, `fix/<설명>`, `chore/<설명>`
- PR 최소 1명 리뷰 후 squash merge
- 커밋 메시지: [Conventional Commits](https://www.conventionalcommits.org/) (`feat:`, `fix:`, `chore:`, `docs:`, `refactor:`)

## 스택

- Python 3.12, FastAPI
- SQLAlchemy + Alembic (마이그레이션)
- PostgreSQL(운영) / SQLite(로컬·테스트)
- FastAPI 자동 OpenAPI 스펙 / Swagger UI (`/docs`, `/openapi.json`)
- pytest

## 로컬 실행

```bash
pip install -r requirements.txt -r requirements-dev.txt
uvicorn app.main:app --reload
```

DB 연결 정보 등 시크릿은 `.env`로 관리하고 커밋하지 않는다 (`app/config.py`의 `Settings` 참고).

## API 계약 관리 (제일 중요한 규칙)

스프린트2부터는 iOS 담당자가 백엔드 코드를 직접 보지 않고 API 계약만 보고 작업한다. **엔드포인트 시그니처나 요청/응답 스키마(`app/schemas.py`)를 바꾸면, 같은 PR 안에서 반드시:**

1. FastAPI가 생성하는 OpenAPI 스펙이 실제로 갱신됐는지 로컬에서 `/openapi.json` 확인
2. 어떤 엔드포인트/스키마가 바뀌었는지 PR 설명에 명시

## 보안 관련 알려진 변경 이력

`docs/backend-changes.md`에 원본 ssiuuuuuu/omys 코드에서 갈라져 나온 보안 수정 사항을 기록한다. 새 기능을 추가하거나 원본 참고 코드를 다시 볼 때 이 문서를 먼저 확인해서 이미 고친 취약점을 되살리지 않도록 한다.
