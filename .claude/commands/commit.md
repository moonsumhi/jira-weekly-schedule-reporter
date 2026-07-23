# commit

스테이징된 변경사항을 티켓 번호가 포함된 커밋 메시지로 커밋하고 origin에 push합니다.

## 사용법

```
/commit TICKET-N 커밋 메시지
/commit SR-2026-0080, SR-85 fix 내용 설명
```

예시:
```
/commit BACKOFFICE-8 가이드 내용 수정
/commit SR-2026-0057, SR-64 SR 상태 흐름 개선
```

## 티켓 번호가 없을 때 (ARGUMENTS가 비어있거나 티켓 번호 없이 호출된 경우)

**반드시 커밋을 중단하고 사용자에게 티켓 번호를 먼저 물어본다.**

```
커밋 전에 티켓 번호를 알려주세요. (예: SR-2026-0080, SR-85)
```

티켓 번호를 받기 전까지 git 명령어를 실행하지 않는다.

## 동작 순서

1. `$ARGUMENTS` 에서 첫 번째 단어(들)를 티켓 번호로 파싱
   - `$ARGUMENTS`가 비어있으면 → **중단하고 티켓 번호 요청**
   - 티켓 번호 형식: `SR-N`, `SR-YYYY-NNNN`, `BACKOFFICE-N`, 복수일 경우 `SR-A, SR-B`
2. `git status`와 `git diff --staged`로 스테이징된 변경사항 확인
3. 스테이징된 파일이 없으면 변경된 파일 목록을 보여주고 중단
4. 아래 형식으로 커밋:

```
[TICKET] type(scope): 메시지

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
```

- type/scope는 변경 내용을 보고 자동 판단 (feat/fix/refactor/chore 등)
- 커밋 후 `git push origin <현재 브랜치>`

## 절대 규칙

- **Bash tool로 `git commit`을 직접 실행하지 않는다** — 반드시 이 스킬을 통해서만 커밋
- 티켓 번호 없이 커밋하지 않는다 (예외 없음)
- 이전 커밋의 티켓 번호를 그대로 재사용하지 않는다 — 작업마다 티켓이 다를 수 있음
