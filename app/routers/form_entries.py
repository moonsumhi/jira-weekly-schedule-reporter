"""Form entry CRUD endpoints — stores submitted data for a form template."""

import asyncio
import base64
import glob as glob_module
import io
import logging
import os
import re
import shutil
import subprocess
import tempfile
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

MAX_IMPORT_FILE_SIZE = 50 * 1024 * 1024  # 50 MB

from bson import ObjectId
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status

from app.db.mongo import MongoClientManager
from app.models.form_entry import FormEntryCreate, FormEntryOut, FormEntryPatch
from app.models.user import UserPublic
from app.routers.auth import get_current_user
from app.utils.mongo import fmt_dt, oid as parse_oid

router = APIRouter()


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _to_out(doc: dict) -> FormEntryOut:
    return FormEntryOut(
        id=str(doc["_id"]),
        template_id=doc.get("template_id", ""),
        data=doc.get("data", {}),
        version=doc.get("version", 1),
        is_deleted=doc.get("is_deleted", False),
        created_at=fmt_dt(doc.get("created_at")),
        created_by=doc.get("created_by"),
        updated_at=fmt_dt(doc.get("updated_at")),
        updated_by=doc.get("updated_by"),
    )


def _extract_pdf_text(content: bytes) -> str:
    import pypdf
    reader = pypdf.PdfReader(io.BytesIO(content))
    pages = []
    for page in reader.pages:
        t = page.extract_text() or ""
        pages.append(t)
    text = "\n".join(pages)
    logger.info("PDF extracted text length: %d", len(text))
    logger.debug("PDF text preview: %s", text[:500])
    return text


def _extract_pdf_images(content: bytes) -> list[str]:
    """PDF에서 이미지를 추출해 base64 data URL 리스트로 반환."""
    import fitz  # PyMuPDF
    doc = fitz.open(stream=content, filetype="pdf")
    images = []
    for page in doc:
        for img in page.get_images():
            xref = img[0]
            base_image = doc.extract_image(xref)
            ext = base_image["ext"]
            img_bytes = base_image["image"]
            if len(img_bytes) < 1_000:  # 아이콘/라인 등 소형 이미지 제외
                continue
            b64 = base64.b64encode(img_bytes).decode()
            images.append(f"data:image/{ext};base64,{b64}")
    logger.info("PDF extracted %d image(s)", len(images))
    return images


def _extract_hwp_images(content: bytes) -> list[str]:
    """HWP BinData에서 이미지를 추출해 base64 data URL 리스트로 반환."""
    SUPPORTED_EXT = {'jpg', 'jpeg', 'png', 'gif', 'bmp', 'tif', 'tiff'}
    with tempfile.NamedTemporaryFile(suffix=".hwp", delete=False) as f:
        f.write(content)
        tmppath = f.name
    outdir = tempfile.mkdtemp()
    images: list[str] = []
    try:
        result = subprocess.run(
            ["hwp5proc", "unpack", tmppath, outdir],
            capture_output=True, timeout=60
        )
        if result.returncode != 0:
            logger.warning("hwp5proc unpack failed: %s", result.stderr.decode(errors="replace")[:200])
            return images
        bindata_dir = os.path.join(outdir, "BinData")
        if not os.path.isdir(bindata_dir):
            logger.info("HWP: BinData directory not found")
            return images
        for imgpath in sorted(glob_module.glob(os.path.join(bindata_dir, "*"))):
            ext = os.path.splitext(imgpath)[1].lower().lstrip('.')
            if ext not in SUPPORTED_EXT:
                continue
            with open(imgpath, 'rb') as imgf:
                img_bytes = imgf.read()
            if len(img_bytes) < 1_000:
                continue
            mime = 'jpeg' if ext in ('jpg', 'jpeg') else ext
            b64 = base64.b64encode(img_bytes).decode()
            images.append(f"data:image/{mime};base64,{b64}")
        logger.info("HWP extracted %d image(s)", len(images))
    except Exception as e:
        logger.warning("HWP image extraction failed: %s", e)
    finally:
        try:
            os.unlink(tmppath)
        except Exception:
            pass
        shutil.rmtree(outdir, ignore_errors=True)
    return images


def _parse_hwp_xml(xml_content: str) -> str:
    """hwp5proc xml XML에서 텍스트 추출.
    구조: TableBody → TableRow → TableCell
    TableRow 경계에 ===ROW_END=== 마커를 삽입해 행 구분.
    """
    import xml.etree.ElementTree as ET
    root = None
    try:
        root = ET.fromstring(xml_content)
    except ET.ParseError as e:
        logger.warning("HWP XML parse error: %s — trying lxml recover", e)
        try:
            from lxml import etree as lxml_etree
            parser = lxml_etree.XMLParser(recover=True, encoding='utf-8')
            lxml_root = lxml_etree.fromstring(xml_content.encode('utf-8'), parser)
            # lxml → stdlib ET 변환
            xml_bytes = lxml_etree.tostring(lxml_root)
            root = ET.fromstring(xml_bytes)
        except Exception as e2:
            logger.warning("lxml recover also failed: %s", e2)
            return ""
    if root is None:
        return ""

    def local_tag(elem) -> str:
        t = elem.tag
        return t.split('}', 1)[1] if '}' in t else t

    def collect_cell_text(elem) -> str:
        """셀 내 텍스트 추출. Paragraph 단위로 줄바꿈 보존."""
        lines = []
        for child in elem:
            if local_tag(child) == 'Paragraph':
                para_text = ' '.join(
                    e.text.strip()
                    for e in child.iter()
                    if local_tag(e) == 'Text' and e.text and e.text.strip()
                )
                if para_text:
                    lines.append(para_text)
        return '\n'.join(lines)

    parts = []

    def walk(elem, row_state=None):
        """row_state: [첫_행_지남] — TableBody 내 행 경계 추적용."""
        tag = local_tag(elem)

        if tag == 'TableBody':
            # TableCell의 col 속성으로 정확한 열 위치 결정
            # 수직 병합(rowspan)으로 XML에 없는 셀은 EMPTY로 채워 열 밀림 방지
            row_elems = [c for c in elem if local_tag(c) == 'TableRow']
            if not row_elems:
                return

            # 전체 열 수 = max(col + colspan) across all cells
            num_cols = 0
            for row_elem in row_elems:
                for cell_elem in row_elem:
                    if local_tag(cell_elem) == 'TableCell':
                        c_idx = int(cell_elem.get('col', 0))
                        cs = int(cell_elem.get('colspan', 1))
                        num_cols = max(num_cols, c_idx + cs)
            if num_cols == 0:
                num_cols = 1

            first = True
            for row_elem in row_elems:
                if not first:
                    parts.append('===ROW_END===')
                first = False

                # col→텍스트 매핑
                col_text: dict[int, str] = {}
                for cell_elem in row_elem:
                    if local_tag(cell_elem) != 'TableCell':
                        continue
                    c_idx = int(cell_elem.get('col', 0))
                    if c_idx not in col_text:
                        col_text[c_idx] = collect_cell_text(cell_elem)

                # 0..num_cols-1 순서로 emit, 누락(rowspan 병합) 위치는 EMPTY
                # 셀 내부 줄바꿈(Paragraph 경계)은 ===NEWLINE===으로 인코딩
                # → \n은 셀 구분자로만 사용되어 _build_rows 파싱이 안전해짐
                for c in range(num_cols):
                    t = col_text.get(c)
                    if t:
                        t = t.replace('\n', '===NEWLINE===')
                    parts.append(t if t else '===EMPTY===')
            parts.append('===TABLE_END===')
            return

        if tag == 'Paragraph':
            has_cell = any(local_tag(e) == 'TableCell' for e in elem.iter() if e is not elem)
            if has_cell:
                for child in elem:
                    walk(child, row_state)
            else:
                t = collect_cell_text(elem)
                if t:
                    parts.append(t)
            return

        for child in elem:
            walk(child, row_state)

    walk(root)
    return '\n'.join(parts)


async def _extract_hwp_text(content: bytes) -> str:
    with tempfile.NamedTemporaryFile(suffix=".hwp", delete=False) as f:
        f.write(content)
        tmppath = f.name

    # xmllint가 HWP 내 특수문자 속성으로 실패하는 경우를 방지:
    # PATH 앞에 stdin→stdout 통과만 하는 가짜 xmllint를 넣어
    # hwp5proc xml이 raw XML을 그대로 출력하게 함
    fake_dir = tempfile.mkdtemp()
    fake_xmllint = os.path.join(fake_dir, 'xmllint')
    with open(fake_xmllint, 'w') as _f:
        _f.write('#!/bin/sh\ncat\n')
    os.chmod(fake_xmllint, 0o755)
    import stat as _stat
    _env = os.environ.copy()
    _env['PATH'] = fake_dir + ':' + _env.get('PATH', '')

    try:
        # hwp5proc xml — 표 셀 내용까지 포함한 XML 추출 (xmllint 우회)
        proc = await asyncio.create_subprocess_exec(
            "hwp5proc", "xml", tmppath,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=_env,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=120)
        if stderr:
            logger.warning("hwp5proc stderr: %s", stderr.decode("utf-8", errors="replace")[:300])
        if stdout:
            xml_content = stdout.decode("utf-8", errors="replace")
            text = _parse_hwp_xml(xml_content)
            if text.strip():
                logger.info("hwp5proc xmldump text length: %d", len(text))
                logger.info("hwp5proc full text: %s", text[:1000])
                return text
        logger.warning("hwp5proc xmldump returned empty, falling back to hwp5txt")

        # fallback: hwp5txt (표 내용 제외)
        proc2 = await asyncio.create_subprocess_exec(
            "hwp5txt", tmppath,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout2, _ = await asyncio.wait_for(proc2.communicate(), timeout=120)
        text2 = stdout2.decode("utf-8", errors="replace")
        logger.info("hwp5txt fallback text length: %d", len(text2))
        return text2
    except Exception as e:
        logger.error("HWP extraction failed: %s", e)
        return ""
    finally:
        try:
            os.unlink(tmppath)
        except OSError:
            pass
        try:
            import shutil
            shutil.rmtree(fake_dir, ignore_errors=True)
        except Exception:
            pass


def _normalize_text(text: str) -> str:
    """HWP/PDF 추출 텍스트 정규화."""
    # 2자 이상 단독 한글 글자 간격 패턴 제거 (예: "작 업 명" → "작업명", "직 책" → "직책")
    # 정상 단어 경계 공백은 유지 (예: "작업 일시", "서비스 명" 유지)
    text = re.sub(
        r'(?<![가-힣])([가-힣] ){1,}[가-힣](?![가-힣])',
        lambda m: m.group(0).replace(' ', ''),
        text,
    )
    # " / " → "/" (예: "성함 / 직책" → "성함/직책")
    text = re.sub(r' / ', '/', text)
    return text


def _flexible_label_pattern(label: str) -> str:
    """라벨 글자 사이 공백 유무에 관계없이 매칭되는 정규식 패턴 생성.

    문서마다 "서비스명"/"서비스 명"처럼 공백 표기가 들쭉날쭉하므로,
    라벨의 공백을 제거한 뒤 각 글자 사이에 \\s*를 끼워 유연하게 매칭한다.
    """
    chars = [c for c in label if not c.isspace()]
    return r'\s*'.join(re.escape(c) for c in chars)


def _extract_form_data(text: str, sections: list) -> tuple[dict, list[dict]]:
    """추출된 텍스트에서 폼 필드 값을 파싱."""
    text = _normalize_text(text)

    all_skipped: list[dict] = []

    all_labels: list[str] = [
        f.get("label", "")
        for s in sections
        for f in s.get("fields", [])
        if f.get("label")
    ]
    all_titles = [s.get("title", "") for s in sections]

    def sec_pattern(title: str) -> str:
        # HWP: "[\n작업 개요\n]" / PDF: "[작업 개요]" 두 형태 모두 매칭
        return r'\[\s*' + re.escape(title) + r'\s*\]'

    def _section_scope_bounds(title: str) -> tuple[int, int] | None:
        """섹션 마커 위치를 찾아 (start, end) 반환. 없으면 None."""
        m = re.search(sec_pattern(title), text, re.DOTALL)
        if not m:
            nk = norm_key(title)
            if nk != title:
                m = re.search(sec_pattern(nk), text, re.DOTALL)
        if not m:
            return None
        start = m.end()
        end = len(text)
        for other in all_titles:
            if other == title:
                continue
            om = re.search(sec_pattern(other), text[start:], re.DOTALL)
            if om and start + om.start() < end:
                end = start + om.start()
        km = re.search(r'\[\s*[가-힣][가-힣\s]*[가-힣]\s*\]', text[start:])
        if km and start + km.start() < end:
            end = start + km.start()
        return start, end

    def get_section_text(title: str) -> str:
        """[title] 마커 기준으로 섹션 텍스트 추출."""
        bounds = _section_scope_bounds(title)
        if bounds:
            return text[bounds[0]:bounds[1]]
        # 마커 없음: 직전 섹션의 scope 시작부터 전체 범위를 제공
        # → ===TABLE_END=== 분리로 최적 표를 선택하므로 넓은 범위여도 안전
        idx = all_titles.index(title) if title in all_titles else -1
        if idx > 0:
            for prev in reversed(all_titles[:idx]):
                pb = _section_scope_bounds(prev)
                if pb:
                    return text[pb[0]:]
        return text  # 직전 섹션도 없으면 전체 텍스트

    def find_value(label: str, scope: str, is_textarea: bool = False) -> str:
        m = re.search(re.escape(label), scope) or re.search(_flexible_label_pattern(label), scope)
        if not m:
            logger.info("Field not found: [%s]", label)
            return ""
        start = m.end()
        window = 2000 if is_textarea else 500
        raw = scope[start:start + window]

        if is_textarea:
            # textarea: ROW_END → 개행, EMPTY 제거 후 TABLE_END 경계에서 중단
            # all_labels 경계는 미적용 (본문이 레이블 단어를 포함할 수 있음)
            raw = re.sub(r'===ROW_END===', '\n', raw)
            raw = re.sub(r'===NEWLINE===', '\n', raw)
            raw = re.sub(r'===EMPTY===', '', raw)
            rest = re.sub(r"^[\s:：]+", "", raw)
            end = len(rest)
            table_end_m = re.search(r'===TABLE_END===', rest)
            if table_end_m and table_end_m.start() < end:
                end = table_end_m.start()
            chunk = rest[:end]
            # 줄바꿈은 보존, 같은 줄 내 연속 공백만 축약
            chunk = re.sub(r'===[A-Z_]+===', '', chunk)
            lines_out = [re.sub(r'[ \t]+', ' ', ln).strip() for ln in chunk.splitlines()]
            value = '\n'.join(ln for ln in lines_out if ln)
            logger.info("Field [%s] → [%s]", label, value[:120] if value else "(empty)")
            return value

        rest = re.sub(r"^[\s:：]+", "", raw)
        end = len(rest)
        # ===ROW_END=== 마커를 값 경계로 처리
        row_end_m = re.search(r'===ROW_END===', rest)
        if row_end_m and row_end_m.start() < end:
            end = row_end_m.start()
        # 짧은 한글 레이블처럼 보이는 줄에서 중단 (인라인 label|value|label|value 구조)
        label_line_m = re.search(r'\n[가-힣][가-힣/\s]{0,14}\n', rest)
        if label_line_m and label_line_m.start() < end:
            end = label_line_m.start()
        for other in all_labels:
            if other == label:
                continue
            om = re.search(re.escape(other), rest)
            if om and om.start() < end:
                end = om.start()
        value = re.sub(r"\s+", " ", rest[:end]).strip()
        # 내부 마커 제거 (열 위치 보존/표 경계용 마커가 값에 노출되지 않도록)
        value = re.sub(r'\s*===[A-Z_]+===\s*', ' ', value).strip()

        # 체크박스 스타일 필드 처리: 값이 □/■ 등 마커뿐이거나 포함된 경우
        # 같은 행 전체(ROW_END까지)에서 채워진(■/●) 마커 뒤 텍스트를 추출
        _FILLED = re.compile(r'^[■●▣◉✔✓]$')
        _ANY_MARKER = re.compile(r'^[■●▣◉✔✓□○◎☐☑]$')
        if _ANY_MARKER.match(value):
            row_end_pos = re.search(r'===ROW_END===', scope[m.end():m.end() + 600])
            row_raw = scope[m.end(): m.end() + (row_end_pos.start() if row_end_pos else 600)]
            row_raw = re.sub(r'===\w+===', '', row_raw)
            lines = [l.strip() for l in row_raw.split('\n') if l.strip()]
            selected = []
            for i, line in enumerate(lines):
                if _FILLED.match(line) and i + 1 < len(lines):
                    selected.append(lines[i + 1])
            if selected:
                value = ', '.join(selected)

        logger.info("Field [%s] → [%s]", label, value[:80] if value else "(empty)")
        return value

    def norm_key(s: str) -> str:
        """공백 제거 (레이블-셀 매칭 비교 전용)"""
        return re.sub(r'\s+', '', s)

    def extract_table_rows(title: str, fields: list, scope: str) -> list[dict]:
        """표 섹션: 행 마커 기반(HWP) 또는 레거시(PDF/fallback) 방식으로 데이터 행 추출."""
        labels = [f.get("label", "") for f in fields]
        # 공백 제거 정규화: HWP 개별 글자 공백 제거 후에도 매칭되도록
        labels_norm = {norm_key(lbl): lbl for lbl in labels}

        # HWP 헤더 셀 → 템플릿 레이블 별칭 (예: "회사명" → "소속")
        CELL_ALIASES: dict[str, str] = {
            "회사명": "소속",
        }

        def cell_matches_label(cell: str) -> str | None:
            """셀이 레이블과 일치하면 원본 레이블 반환, 아니면 None"""
            if cell in labels:
                return cell
            alias = CELL_ALIASES.get(cell) or CELL_ALIASES.get(norm_key(cell))
            if alias and alias in labels:
                return alias
            cn = norm_key(cell)
            if cn in labels_norm:
                return labels_norm[cn]
            # 단어 포함 매칭: 셀 텍스트가 레이블의 일부인 경우 (예: "시작" → "작업 시작 시간")
            # 단, 유일하게 하나의 레이블에만 포함될 때만 매칭
            if len(cn) >= 2:
                sub_matches = [lbl for lbl in labels if cn in norm_key(lbl)]
                if len(sub_matches) == 1:
                    return sub_matches[0]
            return None

        if '===ROW_END===' in scope:
            # HWP row-marker 방식: 헤더 행 감지 후 컬럼 인덱스로 매핑
            # ===TABLE_END=== 마커로 표 경계 분리 → 섹션 스코프에 복수 표가 포함될 때
            # (예: [담당자]~[세부 작업 절차] 사이에 개발 내용 표가 포함되는 경우)
            # 레이블 매칭 수가 가장 높은 표만 사용
            def _build_rows(text_chunk: str) -> list[list[str]]:
                segs = [s.strip() for s in text_chunk.split('===ROW_END===')]
                return [
                    ['' if c == '===EMPTY===' else c.replace('===NEWLINE===', '\n')
                     for c in seg.split('\n') if c.strip()]
                    for seg in segs if seg.strip()
                ]

            if '===TABLE_END===' in scope:
                chunks = scope.split('===TABLE_END===')
                best_rows: list[list[str]] = []
                best_score = -1
                for chunk in chunks:
                    if not chunk.strip():
                        continue
                    chunk_rows = _build_rows(chunk)
                    if not chunk_rows:
                        continue
                    score = max(
                        sum(1 for c in row if cell_matches_label(c) is not None)
                        for row in chunk_rows
                    )
                    if score > best_score:
                        best_score = score
                        best_rows = chunk_rows
                rows_as_cells = best_rows
            else:
                rows_as_cells = _build_rows(scope)

            # 템플릿 레이블을 가장 많이 포함하는 행을 헤더로 선택 (정규화 매칭 포함)
            header_idx, best_match = 0, -1
            for i, cells in enumerate(rows_as_cells):
                cnt = sum(1 for c in cells if cell_matches_label(c) is not None)
                if cnt > best_match:
                    best_match, header_idx = cnt, i

            logger.info("Table [%s] rows_as_cells: %s", title, rows_as_cells[:4])
            if best_match > 0:
                header_cells = rows_as_cells[header_idx]

                # 레이블-값 교대 배치 감지 (예: 작업 개요처럼 같은 행에 레이블|값|레이블|값)
                # 모든 행의 짝수 인덱스 셀에 레이블이 하나 이상 있어야 interleaved로 판정
                # (데이터 행에 레이블이 없으면 top-header 테이블로 간주)
                def is_interleaved(rows):
                    if not rows:
                        return False
                    return all(
                        any(cell_matches_label(row[i]) is not None for i in range(0, len(row), 2) if i < len(row))
                        for row in rows
                    )

                if is_interleaved(rows_as_cells):
                    # 레이블|값 교대 방식: 각 행에서 짝수=레이블, 홀수=값으로 추출
                    kv = {}
                    for row_cells in rows_as_cells:
                        for i in range(0, len(row_cells) - 1, 2):
                            matched_lbl = cell_matches_label(row_cells[i])
                            val = row_cells[i + 1] if i + 1 < len(row_cells) else ''
                            if matched_lbl is not None:
                                kv[matched_lbl] = val
                    result = [{lbl: kv.get(lbl, '') for lbl in labels}]
                    logger.info("Table [%s]: 1 row(s) (interleaved kv)", title)
                    return result

                # 일반 top-header 방식 (정규화 매칭으로 label_to_col 구성)
                label_to_col = {}
                for i, cell in enumerate(header_cells):
                    matched_lbl = cell_matches_label(cell)
                    if matched_lbl is not None:
                        label_to_col[matched_lbl] = i

                # 서브헤더 감지: 헤더 다음 행의 모든 셀이 미매핑 레이블과 매칭되면 서브헤더로 처리
                # (예: "작업 시간" 병합셀 아래 "시작" / "종료" 서브헤더)
                data_from = header_idx + 1
                sub_header_adjusted = False  # 병합셀 보정 여부
                no_pat = re.compile(r'^no\.?$|^번호$|^n$', re.IGNORECASE)
                if data_from < len(rows_as_cells):
                    sub_row = rows_as_cells[data_from]
                    unmatched = set(labels) - set(label_to_col.keys())
                    sub_mapped = [(cell_matches_label(c), idx) for idx, c in enumerate(sub_row)]
                    valid_sub = [(lbl, idx) for lbl, idx in sub_mapped
                                 if lbl is not None and lbl in unmatched]
                    # col-based: 빈 셀(rowspan 병합)도 포함될 수 있으므로
                    # 비어있지 않은 셀이 모두 레이블과 매칭되면 서브헤더로 판정
                    all_match_or_empty = all(
                        cell_matches_label(c) is not None or not c.strip()
                        for c in sub_row
                    )
                    if valid_sub and all_match_or_empty:
                        # 병합 헤더 셀 위치 탐색: No./번호 패턴이 아닌 첫 번째 미매핑 헤더 셀
                        parent_col = None
                        for i, cell in enumerate(header_cells):
                            if cell_matches_label(cell) is None and not no_pat.match(cell.strip()):
                                parent_col = i
                                break
                        if parent_col is not None and len(valid_sub) > 1:
                            # col-based: XML col 속성 기반 인덱스를 직접 사용 (확장 불필요)
                            for lbl, idx in valid_sub:
                                label_to_col[lbl] = idx
                            sub_header_adjusted = True
                        else:
                            for lbl, col in valid_sub:
                                label_to_col[lbl] = col
                        data_from = header_idx + 2  # 서브헤더 행 스킵

                # 복합 헤더 처리: "성함/직책" → 같은 컬럼의 값을 "/" 기준으로 분리
                # split_cols: {col_idx: [lbl1, lbl2, ...]} (순서대로 분리)
                split_cols: dict[int, list[str]] = {}
                for i, cell in enumerate(header_cells):
                    if '/' in cell:
                        parts = [p.strip() for p in cell.split('/')]
                        matched = [m for p in parts for m in [cell_matches_label(p)] if m is not None]
                        unassigned = [lbl for lbl in matched if lbl not in label_to_col]
                        if unassigned:
                            split_cols[i] = unassigned
                            for lbl in unassigned:
                                label_to_col[lbl] = i
                    elif cell_matches_label(cell) is None:
                        # 직접 매칭 안 되는 셀: 셀 텍스트 안에 레이블이 포함된 경우 처리
                        # 예: '테스트 데이터 비고' → '테스트 데이터', '비고' 각각 매핑
                        cell_norm = norm_key(cell)
                        if len(cell_norm) >= 2:
                            contained = [lbl for lbl in labels
                                         if len(norm_key(lbl)) >= 2 and norm_key(lbl) in cell_norm
                                         and lbl not in label_to_col]
                            for lbl in contained:
                                label_to_col[lbl] = i

                # HWP 페이지 분리 반복 헤더 셀 제거용 최대 열 수 계산
                no_in_header = bool(header_cells and no_pat.match(header_cells[0].strip()))
                if sub_header_adjusted:
                    # 서브헤더 확장 후 최대 컬럼 인덱스 + 1
                    max_data_len = (max(label_to_col.values()) + 1) if label_to_col else len(header_cells)
                else:
                    # No.가 헤더에 있으면 정확히 헤더 길이, 없으면 +1(No. 컬럼 여유)
                    max_data_len = len(header_cells) if no_in_header else len(header_cells) + 1

                result = []
                for data_cells in rows_as_cells[data_from:]:
                    # 반복 헤더 셀 제거 (HWP 페이지 분리 시 헤더가 직전 행에 합쳐지는 현상)
                    data_cells = data_cells[:max_data_len]
                    # No.(행번호) 컬럼: 병합셀 보정이 없고, 헤더보다 셀이 많고 첫 셀이 숫자면 오프셋 적용
                    offset = 0
                    if (not sub_header_adjusted
                            and len(data_cells) > len(header_cells)
                            and data_cells and re.match(r'^\d+$', data_cells[0])):
                        offset = 1
                    row_dict = {}
                    for lbl in labels:
                        col = label_to_col.get(lbl)
                        if col is not None:
                            idx = col + offset
                            raw_val = data_cells[idx] if idx < len(data_cells) else ''
                            if col in split_cols and lbl in split_cols[col]:
                                parts = [p.strip() for p in raw_val.split('/')]
                                lbl_idx = split_cols[col].index(lbl)
                                row_dict[lbl] = parts[lbl_idx] if lbl_idx < len(parts) else raw_val
                            else:
                                row_dict[lbl] = raw_val
                        else:
                            row_dict[lbl] = ''
                    result.append(row_dict)
                # 모든 값이 빈 행 제거 (HWP 서식용 빈 행 필터링)
                # any(r.values())만으로는 '\n' 등 공백·줄바꿈 셀이 truthy로 통과되므로 .strip() 적용
                filtered = []
                for _i, _r in enumerate(result):
                    if any(
                        v.strip() if isinstance(v, str) else bool(v)
                        for v in _r.values()
                    ):
                        filtered.append(_r)
                    else:
                        all_skipped.append({
                            "section": title,
                            "row": _i + 1,
                            "reason": "모든 필드가 비어 있음 (서식용 빈 행)",
                        })
                result = filtered
                logger.info("Table [%s]: %d row(s) (row-marker) label_to_col=%s", title, len(result), label_to_col)
                logger.info("Table [%s] rows: %s", title, result[:3])
                return result or [dict.fromkeys(labels, "")]

        # 레거시: 마지막 레이블 이후 줄 단위로 n개씩 묶기
        last_end = 0
        for label in labels:
            m = re.search(re.escape(label), scope)
            if m and m.end() > last_end:
                last_end = m.end()
        if last_end == 0:
            return [dict.fromkeys(labels, "")]
        lines = [
            l.strip()
            for l in scope[last_end:].split('\n')
            if l.strip() and not re.match(r'^\d+$', l) and '===ROW_END===' not in l
        ]
        n = len(labels)
        rows = [
            {labels[j]: lines[i + j] if i + j < len(lines) else "" for j in range(n)}
            for i in range(0, len(lines), n)
        ]
        logger.info("Table [%s]: %d row(s) (legacy)", title, len(rows))
        return rows or [dict.fromkeys(labels, "")]

    def parse_work_period(value: str) -> tuple[str, str]:
        """'작업 일시' 값을 시작/종료 datetime 문자열로 분리.
        예: "2026.04.02. 17:00-17:30"          → ("2026-04-02T17:00", "2026-04-02T17:30")
            "2026.04.02. 17:00 ~ 2026.04.03. 09:00" → ("2026-04-02T17:00", "2026-04-03T09:00")
            "02.05(목) 17:00 ~ 17:30"           → ("YYYY-02-05T17:00", "YYYY-02-05T17:30")
        """
        time_pat = r'(\d{1,2}):(\d{2})'
        full_date_pat = r'(\d{4})[./](\d{1,2})[./](\d{1,2})'
        short_date_pat = r'(\d{1,2})[./](\d{1,2})'  # MM.DD (연도 없음)

        cur_year = str(datetime.now(timezone.utc).year)

        # 시작: 4자리 연도 우선, 없으면 MM.DD 시도
        m_start = re.search(full_date_pat + r'[^:\d]*' + time_pat, value)
        if m_start:
            sy, smo, sd, sh, smi = m_start.groups()
        else:
            m_start = re.search(short_date_pat + r'[^:\d]*' + time_pat, value)
            if not m_start:
                return "", ""
            smo, sd, sh, smi = m_start.groups()
            sy = cur_year

        start_str = f"{sy}-{smo.zfill(2)}-{sd.zfill(2)}T{sh.zfill(2)}:{smi}"

        # 구분자(-/~) 이후 부분에서 종료 파싱
        after = value[m_start.end():]
        after = re.sub(r'^[\s\-~]+', '', after)

        m_end_dt = re.search(full_date_pat + r'[.\s]*' + time_pat, after)
        if m_end_dt:
            ey, emo, ed, eh, emi = m_end_dt.groups()
            end_str = f"{ey}-{emo.zfill(2)}-{ed.zfill(2)}T{eh.zfill(2)}:{emi}"
        else:
            m_end_t = re.search(time_pat, after)
            if m_end_t:
                eh, emi = m_end_t.groups()
                end_str = f"{sy}-{smo.zfill(2)}-{sd.zfill(2)}T{eh.zfill(2)}:{emi}"
            else:
                end_str = ""

        logger.info("parse_work_period [%s] → start=%s end=%s", value[:60], start_str, end_str)
        return start_str, end_str

    _CHECK_MARKS = re.compile(r'[√✓✔vVoOxX●■▣◉]')

    def _parse_checkbox_selection(value: str, options: list[str]) -> str:
        """"[  ] 개인 [ √ ] 공공기관 [  ] 비영리법인" 형태의 인라인 체크박스 목록에서
        체크 표시가 붙은 옵션만 골라낸다. 옵션 라벨 바로 앞 대괄호 안의 표시로 판단."""
        selected = [
            opt for opt in options
            if (m := re.search(r'\[([^\[\]]*)\]\s*' + re.escape(opt), value)) and _CHECK_MARKS.search(m.group(1))
        ]
        return ', '.join(selected)

    def convert_field_value(value: str, field_type: str, options: list[str] | None = None) -> str:
        """date/datetime 필드 값을 HTML input 형식으로 변환, select 필드는 체크된 옵션만 추출"""
        if not value:
            return value
        if field_type == 'select' and options:
            selected = _parse_checkbox_selection(value, options)
            if selected:
                return selected
        if field_type == 'date':
            m = re.search(r'(\d{4})[./\-](\d{2})[./\-](\d{2})', value)
            if m:
                return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
        if field_type == 'datetime':
            m = re.search(r'(\d{4})[./\-](\d{1,2})[./\-](\d{1,2})[^:\d]*(\d{1,2}):(\d{2})', value)
            if m:
                return f"{m.group(1)}-{m.group(2).zfill(2)}-{m.group(3).zfill(2)}T{m.group(4).zfill(2)}:{m.group(5)}"
        if field_type == 'time':
            m = re.search(r'(\d{1,2}):(\d{2})', value)
            if m:
                return f"{m.group(1).zfill(2)}:{m.group(2)}"
        return value

    all_markers = re.findall(r'\[\s*[가-힣][가-힣\s]*[가-힣]\s*\]', text)
    logger.info("HWP section markers found: %s", all_markers)

    result = {}
    for section in sections:
        title = section.get("title", "")
        fields = section.get("fields", [])
        scope = get_section_text(title)
        logger.info("Section [%s] scope len=%d", title, len(scope))
        if section.get("multiple"):
            result[title] = extract_table_rows(title, fields, scope)
        else:
            # find_value 우선 시도
            vals = {
                f.get("label", ""): convert_field_value(
                    find_value(f.get("label", ""), scope, is_textarea=f.get("type") == "textarea"),
                    f.get("type", ""),
                    f.get("options"),
                )
                for f in fields
            }
            # 복합 레이블(예: "회사명/성함/직책") 처리
            # 복합 레이블 처리: "회사명/성함/직책" 또는 "회사명 성함 직책" 형태로
            # 여러 레이블이 한 셀에 합쳐진 경우 데이터를 분리하여 각 필드에 재할당
            field_labels = [f.get('label', '') for f in fields]
            lbl_pat = '|'.join(re.escape(l) for l in field_labels if l)
            # "/" 구분 패턴 우선, 없으면 공백 구분 패턴 탐색
            combo_m = re.search(r'(?:' + lbl_pat + r')(?:/(?:' + lbl_pat + r'))+', scope)
            if not combo_m:
                combo_m = re.search(r'(?:' + lbl_pat + r')(?:\s+(?:' + lbl_pat + r'))+', scope)
            if combo_m:
                raw_combo = combo_m.group(0)
                combo_parts = [p.strip() for p in re.split(r'[/\s]+', raw_combo) if p.strip()]
                # 모든 부분이 실제 필드 레이블과 매칭되는지 검증
                matched_lbls = [
                    next((l for l in field_labels if norm_key(l) == norm_key(p)), None)
                    for p in combo_parts
                ]
                if len(matched_lbls) >= 2 and all(m is not None for m in matched_lbls):
                    after = re.sub(r'===\w+===', '', scope[combo_m.end():combo_m.end()+200])
                    data_lines = [l.strip() for l in after.split('\n') if l.strip()]
                    # 레이블 조합 줄(예: 두 번째 "회사명/성함/직책") 건너뜀
                    field_labels_norm = {norm_key(l) for l in field_labels if l}
                    def _is_label_combo(line: str) -> bool:
                        parts = [p.strip() for p in line.split('/') if p.strip()]
                        return len(parts) >= 2 and all(norm_key(p) in field_labels_norm for p in parts)
                    actual_data_lines = [dl for dl in data_lines if not _is_label_combo(dl)]
                    if actual_data_lines:
                        if '/' in actual_data_lines[0]:
                            # 값이 한 셀에 "/" 구분으로 합쳐진 경우: "홍길동/홍/팀장"
                            data_parts = [p.strip() for p in actual_data_lines[0].split('/')]
                        else:
                            # 값이 각각 다른 셀(다른 줄)에 있는 경우: 줄마다 하나씩
                            data_parts = [l.strip() for l in actual_data_lines[:len(matched_lbls)]]
                        for i, matched in enumerate(matched_lbls):
                            if matched and i < len(data_parts) and data_parts[i]:
                                vals[matched] = data_parts[i]

            # 같은 필드에 여러 값이 있는 경우 모두 수집
            # 패턴 1: 레이블 이후 같은 행에 값 셀이 여러 개 (col 방향)
            # 패턴 2: 레이블이 행마다 반복 등장
            # 패턴 3: 첫 행 레이블 이후 행들이 ===EMPTY=== (병합 셀 rowspan)
            if '===ROW_END===' in scope:
                _lbl_norm_set = {norm_key(l) for l in field_labels if l}

                def _collect_val_cells(cells: list[str]) -> list[str]:
                    """레이블이 아닌 값 셀 수집. 다음 레이블을 만나면 중단."""
                    result = []
                    for c in cells:
                        if not c or c == '===EMPTY===':
                            continue
                        if norm_key(c) in _lbl_norm_set:
                            break  # 다음 필드 레이블에서 중단
                        v = re.sub(r'===\w+===', '', c).strip()
                        if v:
                            result.append(v)
                    return result

                for _f in fields:
                    _lbl = _f.get('label', '')
                    if not _lbl or _f.get('type') == 'textarea':
                        continue
                    _m = re.search(re.escape(_lbl), scope)
                    if not _m:
                        continue
                    _after = scope[_m.end():]
                    _re1 = re.search(r'===ROW_END===', _after)
                    if not _re1:
                        continue
                    # 레이블과 같은 행: 레이블 이후 모든 값 셀 수집
                    _first_cells = [c.strip() for c in _after[:_re1.start()].split('\n')]
                    # "/" 포함 복합 레이블(예: 회사명/성함/직책)만 같은 행 다중 값 수집
                    # 일반 레이블은 첫 번째 값 셀만 사용 (인터리브드 KV 테이블 오염 방지)
                    if '/' in _lbl:
                        _all_vals = _collect_val_cells(_first_cells)
                    else:
                        _fv = next(
                            (re.sub(r'===\w+===', '', c).strip()
                             for c in _first_cells
                             if c and c != '===EMPTY===' and norm_key(c) not in _lbl_norm_set),
                            ''
                        )
                        _all_vals = [_fv] if _fv else []
                    if not _all_vals:
                        continue
                    # 체크박스 패턴(■/□ 등 또는 "[ ] 개인 [√] 공공기관" 인라인 형태)이 포함된 경우
                    # find_value/convert_field_value의 체크박스 처리 결과를 그대로 유지 (재수집으로 덮어쓰지 않음)
                    _CB = re.compile(r'^[■●▣◉✔✓□○◎☐☑]')
                    _BRACKET_CB = re.compile(r'\[[^\[\]]*\]')
                    if any(_CB.match(v) or (_f.get('type') == 'select' and _BRACKET_CB.search(v)) for v in _all_vals):
                        continue
                    # 이후 행: ===EMPTY=== 또는 레이블 반복이면 추가 수집
                    _pos = _m.end() + _re1.end()
                    while _pos < len(scope):
                        _ne = re.search(r'===ROW_END===|===TABLE_END===', scope[_pos:])
                        _row = scope[_pos: _pos + (_ne.start() if _ne else len(scope) - _pos)]
                        _cells = [c.strip() for c in _row.split('\n')]
                        _fc = _cells[0] if _cells else ''
                        if _fc == '===EMPTY===' or norm_key(_fc) == norm_key(_lbl):
                            _extra = _collect_val_cells(_cells[1:] if norm_key(_fc) == norm_key(_lbl) else _cells[1:])
                            _all_vals.extend(_extra)
                        else:
                            break
                        if not _ne or scope[_pos + _ne.start():_pos + _ne.start() + 14] == '===TABLE_END===':
                            break
                        _pos = _pos + _ne.end()
                    if _all_vals:
                        vals[_lbl] = '\n'.join(_all_vals)

            # 작업 일시 → 작업 기간 (시작) / (종료) 자동 분리
            START_LBL, END_LBL, PERIOD_LBL = "작업 기간 (시작)", "작업 기간 (종료)", "작업 일시"
            if START_LBL in vals and END_LBL in vals:
                if not vals[START_LBL] and not vals[END_LBL]:
                    jil_raw = find_value(PERIOD_LBL, scope)
                    if jil_raw:
                        s, e = parse_work_period(jil_raw)
                        fields_map = {f.get("label", ""): f for f in fields}
                        if s:
                            vals[START_LBL] = convert_field_value(s, fields_map.get(START_LBL, {}).get("type", "datetime"))
                        if e:
                            vals[END_LBL] = convert_field_value(e, fields_map.get(END_LBL, {}).get("type", "datetime"))
            if not any(vals.values()) and '===ROW_END===' in scope:
                # 모든 값이 비어있고 테이블 구조면 top-header 방식으로 재시도 (예: 개발 내용)
                rows = extract_table_rows(title, fields, scope)
                if not rows:
                    result[title] = vals
                elif len(rows) == 1:
                    result[title] = rows[0]
                else:
                    # 여러 행은 필드별로 합쳐서 단일 값으로 반환
                    merged = {}
                    for f in fields:
                        lbl = f.get("label", "")
                        col_vals = [r.get(lbl, '') for r in rows if r.get(lbl, '')]
                        merged[lbl] = '\n'.join(col_vals)
                    result[title] = merged
            else:
                result[title] = vals

    logger.info("Parsed sections: %s", list(result.keys()))
    logger.info("Skipped rows: %d", len(all_skipped))
    return result, all_skipped


@router.post("/import")
async def import_entry_from_file(
    file: UploadFile = File(...),
    template_id: str = Form(...),
    current_user: UserPublic = Depends(get_current_user),
) -> dict:
    """Parse a HWP/PDF file and extract form data using Claude AI."""
    tmpl_col = MongoClientManager.get_form_templates_collection()
    try:
        tmpl_oid = ObjectId(template_id)
    except Exception:
        raise HTTPException(status_code=400, detail="잘못된 template_id입니다.")
    tmpl = await tmpl_col.find_one({"_id": tmpl_oid})
    if not tmpl:
        raise HTTPException(status_code=404, detail="템플릿을 찾을 수 없습니다.")

    content = await file.read()
    if len(content) > MAX_IMPORT_FILE_SIZE:
        raise HTTPException(status_code=413, detail="파일 크기가 50MB를 초과합니다.")

    filename = (file.filename or "").lower()

    images: list[str] = []
    if filename.endswith(".pdf"):
        text = _extract_pdf_text(content)
        images = _extract_pdf_images(content)
    elif filename.endswith(".hwp"):
        text = await _extract_hwp_text(content)
        images = _extract_hwp_images(content)
    else:
        raise HTTPException(status_code=415, detail="지원하지 않는 파일 형식입니다. PDF 또는 HWP 파일을 업로드하세요.")

    if not text.strip():
        raise HTTPException(status_code=422, detail="파일에서 텍스트를 추출할 수 없습니다.")

    extracted, skipped = _extract_form_data(text, tmpl.get("sections", []))
    return {"data": extracted, "skipped": skipped, "images": images}


async def _email_to_name_map() -> dict[str, str]:
    """이메일 → 이름 변환 맵 (full_name 없으면 email 그대로)"""
    users_col = MongoClientManager.get_users_collection()
    return {
        doc["email"]: doc.get("full_name") or doc["email"]
        async for doc in users_col.find({}, {"email": 1, "full_name": 1})
    }


def _strip_images(data: Any) -> Any:
    """목록 조회 시 base64 이미지 값을 빈 문자열로 대체해 응답 크기를 줄입니다."""
    if isinstance(data, str):
        return "" if data.startswith("data:image/") else data
    if isinstance(data, list):
        return [_strip_images(v) for v in data]
    if isinstance(data, dict):
        return {k: _strip_images(v) for k, v in data.items()}
    return data


@router.get("", response_model=list[FormEntryOut])
async def list_entries(
    template_id: str = Query(...),
    include_deleted: bool = Query(False),
    current_user: UserPublic = Depends(get_current_user),
):
    col = MongoClientManager.get_form_entries_collection()
    query: dict = {"template_id": template_id}
    if not include_deleted:
        query["is_deleted"] = {"$ne": True}
    docs = [doc async for doc in col.find(query).sort("created_at", -1)]

    name_map = await _email_to_name_map()

    def resolve(val: str | None) -> str | None:
        if val is None:
            return None
        return name_map.get(val, val)

    for doc in docs:
        doc["created_by"] = resolve(doc.get("created_by"))
        doc["updated_by"] = resolve(doc.get("updated_by"))
        doc["data"] = _strip_images(doc.get("data", {}))

    return [_to_out(doc) for doc in docs]


@router.get("/{entry_id}", response_model=FormEntryOut)
async def get_entry(
    entry_id: str,
    current_user: UserPublic = Depends(get_current_user),
):
    col = MongoClientManager.get_form_entries_collection()
    doc = await col.find_one({"_id": parse_oid(entry_id)})
    if not doc:
        raise HTTPException(status_code=404, detail="찾을 수 없습니다.")

    name_map = await _email_to_name_map()
    doc["created_by"] = name_map.get(doc.get("created_by", ""), doc.get("created_by"))
    doc["updated_by"] = name_map.get(doc.get("updated_by", ""), doc.get("updated_by"))
    return _to_out(doc)


@router.post("", response_model=FormEntryOut, status_code=status.HTTP_201_CREATED)
async def create_entry(
    payload: FormEntryCreate,
    current_user: UserPublic = Depends(get_current_user),
):
    col = MongoClientManager.get_form_entries_collection()
    now = _now()
    doc = {
        "template_id": payload.template_id,
        "data": payload.data,
        "version": 1,
        "is_deleted": False,
        "created_at": now,
        "created_by": current_user.full_name or current_user.email,
        "updated_at": now,
        "updated_by": current_user.full_name or current_user.email,
    }
    result = await col.insert_one(doc)
    doc["_id"] = result.inserted_id
    return _to_out(doc)


@router.patch("/{entry_id}", response_model=FormEntryOut)
async def patch_entry(
    entry_id: str,
    payload: FormEntryPatch,
    current_user: UserPublic = Depends(get_current_user),
):
    col = MongoClientManager.get_form_entries_collection()
    entry_oid = parse_oid(entry_id, "잘못된 항목 ID입니다.")

    now = _now()
    result = await col.find_one_and_update(
        {"_id": entry_oid, "version": payload.version, "is_deleted": {"$ne": True}},
        {"$set": {"data": payload.data, "updated_at": now, "updated_by": current_user.full_name or current_user.email},
         "$inc": {"version": 1}},
        return_document=True,
    )
    if result is None:
        doc = await col.find_one({"_id": entry_oid})
        if doc is None:
            raise HTTPException(status_code=404, detail="항목을 찾을 수 없습니다.")
        raise HTTPException(status_code=409, detail="다른 사용자가 먼저 수정하여 버전 충돌이 발생했습니다.")
    return _to_out(result)


@router.delete("/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_entry(
    entry_id: str,
    current_user: UserPublic = Depends(get_current_user),
):
    col = MongoClientManager.get_form_entries_collection()
    entry_oid = parse_oid(entry_id, "잘못된 항목 ID입니다.")

    result = await col.update_one(
        {"_id": entry_oid, "is_deleted": {"$ne": True}},
        {"$set": {"is_deleted": True, "updated_at": _now(), "updated_by": current_user.full_name or current_user.email}},
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="항목을 찾을 수 없습니다.")
