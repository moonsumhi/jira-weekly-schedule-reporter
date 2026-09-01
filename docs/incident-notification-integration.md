# 장애 알림 메일 대상자 연동 API

Admin > 환경설정 > 장애 알림 서비스 메일 대상자에 등록된 활성 대상자를 외부 서비스에 제공합니다.

## API 키 설정

운영 환경에서 키를 생성합니다.

```bash
openssl rand -hex 32
```

생성된 키는 Git에 저장하지 않고 백엔드의 `app/secret/.env`와 호출 서비스의 Secret에 각각 등록합니다.

```dotenv
INCIDENT_NOTIFY_API_KEY=생성한_64자리_키
```

환경변수를 변경한 뒤에는 백엔드 컨테이너를 재시작해야 합니다.

## 요청

```http
GET /api/integrations/v1/incident-notification/recipients
X-API-Key: 생성한_64자리_키
```

```bash
curl \
  -H "X-API-Key: ${BACKOFFICE_API_KEY}" \
  https://백오피스주소/api/integrations/v1/incident-notification/recipients
```

## 정상 응답

활성화된 대상자만 환경설정의 정렬 순서대로 반환합니다. 동일한 이메일이 중복 등록된 경우 한 번만 반환합니다.

```json
{
  "recipients": [
    {
      "name": "홍길동",
      "email": "hong@example.com"
    }
  ],
  "count": 1
}
```

대상자가 없으면 `200 OK`와 빈 배열을 반환합니다.

```json
{
  "recipients": [],
  "count": 0
}
```

## 오류 응답

- API 키 누락 또는 불일치: `401 Unauthorized`
- 백엔드 API 키 미설정: `503 Service Unavailable`

운영 Nginx에서 접근 IP를 제한하는 경우 호출 서비스의 고정 IP도 허용 목록에 추가해야 합니다.
