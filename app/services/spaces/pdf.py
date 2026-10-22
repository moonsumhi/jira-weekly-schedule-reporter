"""Offline, vector PDF export with embedded Korean text and live seat assignments."""

import math
import re
from datetime import datetime
from threading import Lock
from zoneinfo import ZoneInfo

import pymupdf as pdf

# MuPDF must not be used concurrently by worker threads in the same process.
_render_lock = Lock()
_ink = (0.15, 0.20, 0.25)
_muted = (0.35, 0.42, 0.49)
_line = (0.84, 0.88, 0.92)


def _color(value):
    value = value or "#78909c"
    return tuple(int(value[i : i + 2], 16) / 255 for i in (1, 3, 5))


def _clean(value):
    return " ".join(str(value or "").split())


class Report:
    def __init__(self, state, room, plan, published_at):
        self.doc = pdf.open()
        self.font = pdf.Font("korea")
        self.room, self.plan = room, plan
        self.teams = {t["id"]: t for t in state["teams"]}
        self.people = {p["id"]: p for p in state["people"]}
        self.assignments = {a["seat_id"]: a["person_id"] for a in state["assignments"]}
        self.seats = {s["id"]: s for s in plan["seats"]}
        floor = next(f for f in state["floors"] if f["id"] == room["floor_id"])
        building = next(
            b for b in state["buildings"] if b["id"] == floor["building_id"]
        )
        self.location = " / ".join([building["name"], floor["name"], room["name"]])
        self.printed_at = datetime.now(ZoneInfo("Asia/Seoul")).strftime(
            "%Y-%m-%d %H:%M"
        )
        self.published_at = published_at
        self.occupied = sum(bool(self.person(s)) for s in self.seats)

    def person(self, seat_id):
        return self.people.get(self.assignments.get(seat_id))

    def text(self, page, point, text, size=10, color=_ink, width=None, rotation=0):
        text = _clean(text)
        if width is not None and text:
            size = min(size, width / max(self.font.text_length(text, fontsize=1), 0.01))
        point = pdf.Point(point)
        page.insert_text(
            point,
            text,
            fontsize=size,
            fontname="spacefont",
            color=color,
            morph=(point, pdf.Matrix(-rotation)) if rotation else None,
        )

    def wrap(self, text, width, size=9):
        lines, current = [], ""
        for char in _clean(text):
            if current and self.font.text_length(current + char, fontsize=size) > width:
                lines.append(current)
                current = ""
            current += char
        return [*lines, current] if current else [""]

    def heading(self, page, title):
        page.insert_font(fontname="spacefont", fontbuffer=self.font.buffer)
        y = 48
        for line in self.wrap(title, page.rect.width - 72, 20):
            self.text(page, (36, y), line, 20)
            y += 26
        for line in self.wrap(self.location, page.rect.width - 72, 10):
            self.text(page, (36, y), line, 10, _muted)
            y += 14
        self.text(
            page,
            (36, y + 8),
            f"전체 {len(self.seats)}석   ·   배정 {self.occupied}석   ·   미배정 {len(self.seats) - self.occupied}석",
            11,
        )
        return y + 28

    def map_page(self):
        objects = self.plan["objects"]
        points = []
        for obj in objects:
            angle = math.radians(obj["rotation"])
            for x, y in [
                (0, 0),
                (obj["width"], 0),
                (0, obj["height"]),
                (obj["width"], obj["height"]),
            ]:
                points.append(
                    (
                        obj["x"] + x * math.cos(angle) - y * math.sin(angle),
                        obj["y"] + x * math.sin(angle) + y * math.cos(angle),
                    )
                )
        if points:
            left, top = min(x for x, _ in points), min(y for _, y in points)
            right, bottom = max(x for x, _ in points), max(y for _, y in points)
            width, height = max(600, right - left + 80), max(400, bottom - top + 80)
            left, top = (left + right - width) / 2, (top + bottom - height) / 2
        else:
            left, top, width, height = 0, 0, self.plan["width"], self.plan["height"]
        page_width, page_height = pdf.paper_size("a3-l" if width >= height else "a3")
        page = self.doc.new_page(width=page_width, height=page_height)
        y = self.heading(page, f"{self.room['name']} 좌석 배치도")
        used = {s["team_id"] for s in self.seats.values()} | {
            o["team_id"] for o in objects if o["kind"] == "zone"
        }
        x, first_y = 36, y
        for team_id in sorted(
            used, key=lambda ident: self.teams.get(ident, {}).get("name", "")
        ):
            team = self.teams.get(team_id, {})
            name = team.get("name", "팀 미지정")
            label_width = min(190, self.font.text_length(name, fontsize=9))
            if x + label_width + 24 > page.rect.width - 36:
                x, y = 36, y + 18
            if y > first_y + 36:
                self.text(
                    page,
                    (36, y),
                    "전체 팀은 뒤쪽 좌석별 현황에서 확인하세요.",
                    9,
                    _muted,
                )
                break
            page.draw_rect(
                pdf.Rect(x, y - 7, x + 7, y), color=None, fill=_color(team.get("color"))
            )
            self.text(page, (x + 12, y), name, 9, width=label_width)
            x += label_width + 30
        area = pdf.Rect(36, y + 18, page.rect.width - 36, page.rect.height - 48)
        page.draw_rect(area, color=_line, width=0.5)
        scale = min(area.width / width, area.height / height)
        origin = pdf.Point(
            area.x0 + (area.width - width * scale) / 2 - left * scale,
            area.y0 + (area.height - height * scale) / 2 - top * scale,
        )
        for obj in sorted(objects, key=lambda o: o["kind"] != "zone"):
            self.object(page, obj, origin, scale)
        if not objects:
            self.text(
                page,
                (area.x0 + 20, area.y0 + 30),
                "등록된 배치도 객체가 없습니다.",
                12,
                _muted,
            )

    def object(self, page, obj, origin, scale):
        angle = math.radians(obj["rotation"])

        def point(x, y):
            return pdf.Point(
                origin.x
                + (obj["x"] + x * math.cos(angle) - y * math.sin(angle)) * scale,
                origin.y
                + (obj["y"] + x * math.sin(angle) + y * math.cos(angle)) * scale,
            )

        def rectangle(x, y, w, h, color=None, fill=None, opacity=1, dashed=False):
            shape = page.new_shape()
            shape.draw_polyline(
                [
                    point(x, y),
                    point(x + w, y),
                    point(x + w, y + h),
                    point(x, y + h),
                    point(x, y),
                ]
            )
            shape.finish(
                color=color,
                fill=fill,
                width=max(0.35, 2 * scale),
                fill_opacity=opacity,
                dashes=f"[{8 * scale} {6 * scale}] 0" if dashed else None,
            )
            shape.commit()

        def label(text, x, y, size=14, width=None, center=False, color=_ink):
            text = _clean(text)
            if width is not None and text:
                size = min(
                    size,
                    max(1, width) / max(self.font.text_length(text, fontsize=1), 0.01),
                )
            if center:
                x -= self.font.text_length(text, fontsize=size) / 2
            self.text(
                page, point(x, y), text, size * scale, color, rotation=obj["rotation"]
            )

        w, h, kind = obj["width"], obj["height"], obj["kind"]
        if kind == "wall":
            rectangle(0, 0, w, h, fill=(0.27, 0.35, 0.39))
        elif kind == "door":
            shape = page.new_shape()
            shape.draw_polyline([point(0, h), point(0, 0), point(w, 0)])
            shape.finish(color=_muted, width=max(0.4, 3 * scale), closePath=False)
            shape.draw_bezier(
                point(0, h), point(w * 0.552285, h), point(w, h * 0.552285), point(w, 0)
            )
            shape.finish(
                color=_muted,
                width=max(0.4, 2 * scale),
                dashes=f"[{5 * scale} {4 * scale}] 0",
                closePath=False,
            )
            shape.commit()
        elif kind == "desk":
            seat = self.seats[obj["seat_id"]]
            person = self.person(seat["id"]) or {}
            extension = str(person.get("extension") or "").strip()
            color = _color(self.teams.get(seat["team_id"], {}).get("color"))
            rectangle(0, 0, w, h, color, color, 0.13)
            rectangle(w * 0.3, h - 6, w * 0.4, 13, fill=color)
            size = min(14, max(8, (h - 12) / 2.8))
            if extension:
                label(person.get("name", "미배정"), w / 2, h * 0.45, size, w - 10, True, (0, 0, 0))
                label(extension, w / 2, h * 0.68, size * 0.82, w - 10, True, (0, 0, 0))
            else:
                label(person.get("name", "미배정"), w / 2, h * 0.55, size, w - 10, True, (0, 0, 0))
        elif kind == "cabinet":
            rectangle(0, 0, w, h, _muted, (0.89, 0.91, 0.93))
            page.draw_line(
                point(w / 2, 0), point(w / 2, h), color=_muted, width=max(0.35, scale)
            )
            label(obj["name"] or "캐비닛", w / 2, h / 2 + 4, 12, w - 8, True, _muted)
        elif kind == "zone":
            team = self.teams.get(obj["team_id"], {})
            color = _color(team.get("color"))
            rectangle(0, 0, w, h, color, color, 0.07, True)
            label(
                obj["name"] or team.get("name", "팀 구역"),
                10,
                min(22, h - 2),
                14,
                w - 20,
                color=color,
            )
        else:
            label(obj["name"] or "텍스트", 4, min(h - 2, 22), 18, w - 8)

    def seat_pages(self):
        if not self.seats:
            return
        columns = [
            ("좌석번호", 75),
            ("사용 팀", 130),
            ("배정 인원", 130),
            ("직책", 95),
            ("내선번호", 93),
        ]
        page, y = None, 0
        for seat in sorted(
            self.seats.values(),
            key=lambda s: tuple(
                int(p) if p.isdigit() else p.casefold()
                for p in re.split(r"(\d+)", s["number"])
            ),
        ):
            team = self.teams.get(seat["team_id"], {})
            person = self.person(seat["id"]) or {}
            values = [
                seat["number"],
                team.get("name", "팀 미지정"),
                person.get("name", "미배정"),
                person.get("title") or "—",
                person.get("extension") or "—",
            ]
            lines = [
                self.wrap(value, width - (24 if i == 1 else 16))
                for i, (value, (_, width)) in enumerate(zip(values, columns))
            ]
            height = max(28, max(len(cell) for cell in lines) * 13 + 16)
            if page is None or y + height > page.rect.height - 48:
                page = self.doc.new_page(width=595, height=842)
                y = self.heading(page, f"{self.room['name']} 좌석 배정 현황") + 6
                page.draw_rect(
                    pdf.Rect(36, y, 559, y + 28), color=None, fill=(0.94, 0.96, 0.98)
                )
                x = 36
                for title, width in columns:
                    self.text(page, (x + 8, y + 18), title, 9, _muted)
                    x += width
                y += 28
            x = 36
            for i, (cell, (_, width)) in enumerate(zip(lines, columns)):
                inset = 8
                if i == 1:
                    page.draw_rect(
                        pdf.Rect(x + 8, y + 13, x + 14, y + 19),
                        color=None,
                        fill=_color(team.get("color")),
                    )
                    inset = 20
                for n, line in enumerate(cell):
                    self.text(
                        page,
                        (x + inset, y + 19 + n * 13),
                        line,
                        9,
                        _muted if not person else _ink,
                    )
                x += width
            y += height
            page.draw_line((36, y), (559, y), color=_line, width=0.5)

    def render(self):
        try:
            self.map_page()
            self.seat_pages()
            for i, page in enumerate(self.doc):
                if self.published_at:
                    published = (
                        datetime.fromisoformat(self.published_at)
                        .astimezone(ZoneInfo("Asia/Seoul"))
                        .strftime("%Y-%m-%d %H:%M")
                    )
                    self.text(
                        page,
                        (36, page.rect.height - 34),
                        f"배치도 게시 {published} (KST)",
                        7,
                        _muted,
                    )
                self.text(
                    page,
                    (36, page.rect.height - 22),
                    f"게시 배치도 · 출력 {self.printed_at} (KST) · 전체 팀",
                    8,
                    _muted,
                )
                self.text(
                    page,
                    (page.rect.width - 90, page.rect.height - 22),
                    f"{i + 1} / {len(self.doc)}",
                    8,
                    _muted,
                )
            self.doc.set_metadata(
                {
                    "title": f"{self.room['name']} 좌석 배치도",
                    "author": "OPTOOL",
                    "subject": self.location,
                }
            )
            self.doc.subset_fonts()
            return self.doc.tobytes(garbage=4, deflate=True)
        finally:
            self.doc.close()


def render_plan_pdf(state, room, plan, published_at):
    with _render_lock:
        return Report(state, room, plan, published_at).render()
