from __future__ import annotations

import logging
import os
import subprocess
import tempfile
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

SUPPORTED_EXTENSIONS = {"hwp", "txt", "md"}


async def _download(url: str, auth: tuple) -> bytes:
    async with httpx.AsyncClient(timeout=60.0, auth=auth, follow_redirects=True) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        return resp.content


def _extract_hwp(data: bytes) -> Optional[str]:
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".hwp", delete=False) as f:
            f.write(data)
            tmp_path = f.name

        result = subprocess.run(
            ["hwp5txt", tmp_path],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode == 0:
            return result.stdout.strip()
        logger.warning("[Attachment] hwp5txt failed: %s", result.stderr[:200])
        return None
    except FileNotFoundError:
        logger.warning("[Attachment] hwp5txt not found — pyhwp 미설치")
        return None
    except Exception as e:
        logger.warning("[Attachment] HWP 추출 실패: %s", e)
        return None
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)


async def extract_text_from_attachment(attachment: dict, auth: tuple) -> Optional[str]:
    """Jira attachment 객체에서 텍스트를 추출해 반환."""
    filename: str = attachment.get("filename", "")
    content_url: str = attachment.get("content", "")
    if not content_url or not filename:
        return None

    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in SUPPORTED_EXTENSIONS:
        logger.info("[Attachment] 지원하지 않는 형식 건너뜀: %s", filename)
        return None

    try:
        data = await _download(content_url, auth)
    except Exception as e:
        logger.warning("[Attachment] 다운로드 실패 (%s): %s", filename, e)
        return None

    if ext == "hwp":
        text = _extract_hwp(data)
    else:
        text = data.decode("utf-8", errors="replace")

    if not text:
        return None

    return f"[첨부파일: {filename}]\n{text}"
