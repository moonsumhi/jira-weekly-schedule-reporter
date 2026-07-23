# Form Template 아키텍처

## 배경

작업계획서/결과서는 초기에 `ServiceWorkPlanPage.vue`, `NonServiceWorkPlanPage.vue`, `ServiceWorkResultPage.vue` 같은 독립 Vue 페이지로 개발되었다.
이후 Pilot AI가 NCDC-598~623 태스크를 수행하면서 **폼 템플릿 방식으로 재설계**했다.

---

## 일반적인 방식 (기존 독립 페이지)

폼 구조가 코드에 하드코딩되어 있다.

```
ServiceWorkPlanPage.vue
  ├─ <q-input label="작업명" />
  ├─ <q-input label="작업 일시" />
  ├─ <q-input label="작업자" />
  └─ ... (Vue 코드에 필드가 직접 정의됨)
```

폼 구조를 바꾸려면 → **코드 수정 → 빌드 → 배포** 필요.

---

## 폼 템플릿 방식 (현재)

폼 구조 자체를 **MongoDB에 JSON으로 저장**한다.

### form_templates 컬렉션 (폼 정의)

```json
{
  "title": "작업계획서(서비스)",
  "menu": "Job",
  "sort_order": 1,
  "sections": [
    {
      "title": "기본 정보",
      "fields": [
        { "label": "작업명",    "type": "text",     "required": true },
        { "label": "작업 일시", "type": "text",     "required": true },
        { "label": "작업자",   "type": "text",     "required": true }
      ]
    },
    {
      "title": "세부 작업 절차",
      "multiple": true,
      "fields": [
        { "label": "작업 내용",  "type": "textarea" },
        { "label": "작업 이미지", "type": "image" }
      ]
    }
  ]
}
```

`multiple: true`인 섹션은 사용자가 행을 여러 개 추가할 수 있다.

### form_entries 컬렉션 (제출된 데이터)

```json
{
  "template_id": "xxx",
  "data": {
    "작업명": "DB 서버 점검",
    "작업자": "홍길동",
    "세부 작업 절차": [
      { "작업 내용": "백업 확인", "작업 이미지": "..." },
      { "작업 내용": "패치 적용", "작업 이미지": "..." }
    ]
  }
}
```

### FormTemplatePage.vue

`/job/forms/:id` 하나의 페이지가 template_id를 URL에서 받아 DB의 섹션/필드 정의를 읽고 **동적으로 UI를 렌더링**한다.
폼 구조를 바꾸려면 → **DB 값만 수정**, 코드·배포 불필요.

---

## 사이드바 메뉴 연동 방식

1. 앱 시작 시 `seed_job_form_templates()`가 `form_templates` 컬렉션에 3개 템플릿을 삽입한다 (없을 때만).
2. 프론트엔드 로그인 시 `menuStore.loadTemplates()`가 `GET /form-templates`를 호출해 템플릿 목록을 가져온다.
3. `menu: "Job"`인 템플릿들이 `templateItems`에 담기고, 각 링크는 `/job/forms/{template_id}` 형태가 된다.
4. 사이드바의 작업관리 하위 메뉴로 표시된다.

```
작업관리
  ├─ 작업계획서(서비스)    → /job/forms/{id1}
  ├─ 작업계획서(서비스 외) → /job/forms/{id2}
  └─ 작업결과서           → /job/forms/{id3}
```

---

## Pilot이 이 방식을 선택한 이유

**PDF/HWP Import 기능** 때문이다. 기존에 HWP로 작성하던 작업계획서를 업로드하면 텍스트를 파싱해 폼을 자동으로 채워준다. 이때 "어떤 텍스트가 어떤 필드에 해당하는지" 매핑 정보가 `sections[].fields[].label`에서 오기 때문에, 필드 구조가 DB에 있어야 파싱 로직이 작동한다.

---

## 지원하는 필드 타입

| type | 설명 |
|------|------|
| `text` | 단행 입력 |
| `textarea` | 여러 줄 입력 |
| `select` | 드롭다운 (`options` 배열 필요) |
| `checkbox` | 체크박스 |
| `image` | 이미지 업로드 |

복잡한 조건부 UI 로직(필드 간 연동 등)은 이 방식으로 구현하기 어렵다는 한계가 있다.
