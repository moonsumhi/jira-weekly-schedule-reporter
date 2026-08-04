"""HWP→HTML 변환 결과를 iframe에 바로 넣을 수 있도록 자체완결형으로 만드는 유틸.

app/routers/documents.py의 hwp 미리보기에서 쓰던 로직을 그대로 옮겨서
app/routers/attachments.py에서도 재사용한다.
"""
from __future__ import annotations

import re
from pathlib import Path

HWP_BASE_CSS = """
<style>
* { box-sizing: border-box; }
body { font-family: 'Malgun Gothic', 'Noto Sans KR', sans-serif; font-size: 10pt;
       line-height: 1.6; padding: 24px; color: #222; }
table { border-collapse: collapse; width: auto; margin: 8px 0; }
td, th { border: 1px solid #888; padding: 4px 8px; vertical-align: top; }
th { background: #e8eaf6; font-weight: bold; }
p { margin: 2px 0; }
img { max-width: 100%; height: auto; }
</style>
"""


def make_self_contained(html: str, base_dir: Path) -> str:
    """CSS 인라인 삽입 + 상대 경로 이미지를 base64 data URL로 치환."""
    import base64 as _b64

    mime_map = {
        'png': 'image/png', 'jpg': 'image/jpeg', 'jpeg': 'image/jpeg',
        'gif': 'image/gif', 'bmp': 'image/bmp', 'svg': 'image/svg+xml',
    }
    base_str = str(base_dir.resolve())

    # 1) <link rel="stylesheet" href="..."> → <style>...</style>
    def inline_css(m: re.Match) -> str:
        href = m.group(1)
        if href.startswith(('http', 'data', '//')):
            return m.group(0)
        css_path = (base_dir / href).resolve()
        if not str(css_path).startswith(base_str) or not css_path.exists():
            return ''
        return f'<style>{css_path.read_text(encoding="utf-8", errors="ignore")}</style>'

    html = re.sub(r'<link[^>]+href="([^"]*)"[^>]*/?\s*>', inline_css, html, flags=re.IGNORECASE)

    # 2) 기본 표 스타일 삽입 (</head> 바로 앞)
    if '</head>' in html:
        html = html.replace('</head>', HWP_BASE_CSS + '</head>', 1)
    else:
        html = HWP_BASE_CSS + html

    # 3) src="상대경로" → src="data:..."
    def replace_src(m: re.Match) -> str:
        src = m.group(1)
        if src.startswith(('http://', 'https://', 'data:', '//')):
            return m.group(0)
        img_path = (base_dir / src).resolve()
        if not str(img_path).startswith(base_str) or not img_path.exists():
            return m.group(0)
        ext = img_path.suffix.lstrip('.').lower()
        mime = mime_map.get(ext, 'application/octet-stream')
        data = _b64.b64encode(img_path.read_bytes()).decode()
        return f'src="data:{mime};base64,{data}"'

    return re.sub(r'src="([^"]*)"', replace_src, html)
