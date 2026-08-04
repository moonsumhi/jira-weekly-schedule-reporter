"""업로드된 첨부파일(SR 등)을 파일시스템 경로 기준으로 HTML 미리보기 변환.

document_files 컬렉션에 등록된 파일이 아닌, /app/uploads 아래 임의 위치에
저장된 첨부파일(SR 접수/댓글 등)을 대상으로 하므로 file_id가 아니라
/app/uploads 기준 상대경로(path)로 대상을 지정한다.
"""
import logging
import shutil
import subprocess
import tempfile
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import HTMLResponse

from app.utils.html_preview import HWP_BASE_CSS, make_self_contained

logger = logging.getLogger(__name__)
router = APIRouter()

UPLOADS_ROOT = Path("/app/uploads").resolve()


def _resolve_safe_path(rel_path: str) -> Path:
    candidate_raw = Path(rel_path)
    if candidate_raw.is_absolute() or ".." in candidate_raw.parts:
        raise HTTPException(status_code=400, detail="잘못된 경로입니다.")
    candidate = (UPLOADS_ROOT / candidate_raw).resolve()
    if not candidate.is_relative_to(UPLOADS_ROOT) or not candidate.is_file():
        raise HTTPException(status_code=404, detail="파일을 찾을 수 없습니다.")
    return candidate


@router.get("/hwp-preview", response_class=HTMLResponse)
async def hwp_preview(path: str = Query(...)):
    file_path = _resolve_safe_path(path)
    if file_path.suffix.lower() != ".hwp":
        raise HTTPException(status_code=400, detail="HWP 파일이 아닙니다.")

    out_dir = tempfile.mkdtemp()
    try:
        subprocess.run(
            ["hwp5html", "--output", out_dir, str(file_path)],
            capture_output=True, text=True, timeout=60,
        )
        out_path = Path(out_dir)
        for fname in ("index.xhtml", "body.xhtml", "index.html"):
            out_file = out_path / fname
            if out_file.exists():
                html = out_file.read_text(encoding="utf-8", errors="ignore")
                return HTMLResponse(content=make_self_contained(html, out_path))
        raise RuntimeError("hwp5html 결과물을 찾을 수 없습니다.")
    except Exception as e:
        logger.warning("hwp5html 변환 실패: %s", e)
        return HTMLResponse(content="<html><body><p>미리보기를 생성할 수 없습니다.</p></body></html>")
    finally:
        shutil.rmtree(out_dir, ignore_errors=True)


@router.get("/docx-preview", response_class=HTMLResponse)
async def docx_preview(path: str = Query(...)):
    file_path = _resolve_safe_path(path)
    if file_path.suffix.lower() != ".docx":
        raise HTTPException(status_code=400, detail="DOCX 파일이 아닙니다.")

    import mammoth
    try:
        with open(file_path, "rb") as fp:
            result = mammoth.convert_to_html(fp)
    except Exception as e:
        logger.warning("mammoth 변환 실패: %s", e)
        raise HTTPException(status_code=422, detail="문서를 변환할 수 없습니다.")

    html = f"<html><head><meta charset='utf-8'>{HWP_BASE_CSS}</head><body>{result.value}</body></html>"
    return HTMLResponse(content=html)
