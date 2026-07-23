---
description: 이 저장소 컨벤션에 맞춰 git 커밋을 생성한다 (티켓 번호 필수)
argument-hint: [ticket-number]
---

# /commit

이 프로젝트에서 커밋을 생성할 때 반드시 따라야 하는 절차. `CLAUDE.md`의 "커밋 규칙"에 의해 Claude는 이 절차를 거치지 않고 임의로 `git commit`을 실행해서는 안 된다.

## 1. 티켓 번호 확보

- `$ARGUMENTS`로 티켓 번호가 전달되었으면 그것을 사용한다.
- 전달되지 않았다면, 이번 대화에서 사용자가 이미 명시적으로 준 티켓 번호가 있는지 확인한다.
- 그것도 없다면 **반드시 AskUserQuestion으로 사용자에게 먼저 물어본다.** 이전 대화/이전 작업에서 쓰인 티켓 번호를 임의로 재사용하지 않는다 — 작업마다 티켓이 다를 수 있다.
- 티켓 형식 예시: `SR-N`, `SR-YYYY-NNNN`, `BACKOFFICE-N`. 여러 티켓이 관련되면 `[SR-2026-0080, SR-85]`처럼 콤마로 나열한다.
- 티켓 번호가 정말로 필요 없는 변경(예: 오탈자 수정, 순수 chore)이라고 사용자가 명시적으로 말한 경우에만 티켓 없이 진행한다.

## 2. 현재 상태 파악

다음을 병렬로 실행해 파악한다:
- `git status --short` — 변경/미추적 파일 확인. 특히 다음은 명시적 지시 없이는 절대 건드리지 않는다:
  - `pilot/pilot-src` 서브모듈 (상시 dirty 상태, 무관)
  - 저장소 루트의 이런 미추적 파일들: `2620패치.zip`, `feature-mail*.zip/.bundle`, `jira-reporter-feature-mail.tar.gz`, `optool.bundle` 등 백업/배포용 산출물
- `git diff` — staged + unstaged 변경 내용 검토
- `git log --oneline -15` — 이 브랜치의 최근 커밋 메시지 스타일 확인

## 3. 원격과의 diverge 확인

`git fetch origin <current-branch>` 후 `git log HEAD..origin/<current-branch>`로 원격이 앞서 있는지 확인한다.
- 앞서 있다면 커밋 전에(혹은 커밋 후 push 전에) merge하거나, 필요 시 신중히 재구성한다 (강제 push/force-with-lease는 사용자의 명시적 허락 없이 금지).
- feature/mail 관련 작업은 반드시 `feature/mail` 브랜치에서, 그 외 작업은 `dev`에서 진행한다 — 브랜치를 혼동하지 않는다.

## 4. 커밋 메시지 형식

이 저장소의 관례:

```
[TICKET] type(scope): 한국어로 변경 사항을 간결히 설명

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
```

- `type`: `feat`, `fix`, `refactor`, `chore` 등 일반적인 conventional commit 타입
- `scope`: 변경된 도메인/모듈 (예: `auth`, `theme`, `layout`, `admin`)
- 설명은 한국어, 명사형으로 간결하게 — "왜"보다 "무엇을 바꿨는지" 중심 (이 저장소 기존 로그 스타일을 따름)
- 티켓이 여러 개면 `[SR-2026-0080, SR-85]` 형태로

## 5. 스테이징 & 커밋

- 관련 파일만 이름으로 명시해서 `git add`한다 (`git add -A`/`git add .` 금지 — 시크릿/불필요 파일 혼입 방지)
- 커밋 메시지는 항상 HEREDOC으로 전달한다:

```bash
git commit -m "$(cat <<'EOF'
[TICKET] type(scope): 설명

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

- `--no-verify`, `--no-gpg-sign` 등 훅/서명 우회 플래그는 사용자가 명시적으로 요청하지 않는 한 사용하지 않는다.
- pre-commit 훅이 실패하면 원인을 고치고 다시 add한 뒤 **새 커밋**을 만든다 (이미 실패한 커밋은 존재하지 않으므로 `--amend`가 아니라 새로 커밋).
- 이미 push된 커밋은 사용자의 명시적 확인 없이 `--amend`하지 않는다.

## 6. 커밋 후

- `git status`로 정상적으로 커밋되었는지 확인한다.
- 사용자가 push까지 요청한 경우에만 push한다 (push는 별도의 명시적 요청 필요 — 커밋 자체가 push를 의미하지 않음). push 전에도 다시 한 번 원격 diverge 여부를 확인한다.
- push 후, 이 작업이 `dev`에서 이루어졌고 세션의 작업 브랜치가 `feature/mail`이었다면 관례상 `git checkout feature/mail`로 돌아간다 (다른 지시가 없는 한).
