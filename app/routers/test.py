from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from app.core.config import settings
from app.core.security import get_current_user

router = APIRouter()


class AnalyzePdfRequest(BaseModel):
    text: str
    filename: str = ""


class TemplateField(BaseModel):
    label: str
    type: str
    placeholder: str = ""
    required: bool = False
    options: list[str] = []


class TemplateSection(BaseModel):
    title: str
    fields: list[TemplateField]


class AnalyzePdfResponse(BaseModel):
    title: str
    description: str
    sections: list[TemplateSection]
    raw_summary: str


@router.post("/analyze-pdf", response_model=AnalyzePdfResponse)
async def analyze_pdf_content(
    req: AnalyzePdfRequest,
    current_user: dict = Depends(get_current_user),
):
    if not settings.ANTHROPIC_API_KEY:
        raise HTTPException(
            status_code=503,
            detail="ANTHROPIC_API_KEY가 설정되지 않았습니다. 관리자에게 문의하세요.",
        )

    try:
        import anthropic

        client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)

        prompt = f"""다음은 PDF 파일에서 추출한 텍스트입니다. 이 문서의 내용을 분석하여 해당 문서 유형에 맞는 입력 폼 틀(template)을 JSON 형식으로 만들어 주세요.

파일명: {req.filename}

추출된 텍스트:
{req.text[:8000]}

응답은 반드시 아래 JSON 형식으로만 답하세요. 다른 설명 없이 JSON만 출력하세요:
{{
  "title": "폼 제목",
  "description": "폼에 대한 간단한 설명",
  "sections": [
    {{
      "title": "섹션 제목",
      "fields": [
        {{
          "label": "필드 레이블",
          "type": "text|number|date|select|textarea|checkbox",
          "placeholder": "입력 예시 또는 힌트",
          "required": true,
          "options": []
        }}
      ]
    }}
  ],
  "raw_summary": "문서 내용 요약 (2-3문장)"
}}

type 필드는 다음 값만 사용: text, number, date, select, textarea, checkbox
select 타입의 경우 options 배열에 선택지를 포함하세요."""

        message = client.messages.create(
            model="claude-opus-4-6",
            max_tokens=4096,
            messages=[{"role": "user", "content": prompt}],
        )

        import json

        response_text = message.content[0].text.strip()
        if response_text.startswith("```"):
            lines = response_text.split("\n")
            response_text = "\n".join(lines[1:-1])

        parsed = json.loads(response_text)

        return AnalyzePdfResponse(
            title=parsed.get("title", "분석된 폼"),
            description=parsed.get("description", ""),
            sections=[
                TemplateSection(
                    title=s.get("title", ""),
                    fields=[
                        TemplateField(
                            label=f.get("label", ""),
                            type=f.get("type", "text"),
                            placeholder=f.get("placeholder", ""),
                            required=f.get("required", False),
                            options=f.get("options", []),
                        )
                        for f in s.get("fields", [])
                    ],
                )
                for s in parsed.get("sections", [])
            ],
            raw_summary=parsed.get("raw_summary", ""),
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"PDF 분석 중 오류가 발생했습니다: {str(e)}",
        )
