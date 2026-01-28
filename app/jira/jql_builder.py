from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from typing import List


@dataclass(frozen=True)
class JqlBuilder:
    assignees: List[str] = field(default_factory=list)
    field: str = "updated"  # updated | created | due
    start: datetime | None = None
    end: datetime | None = None
    order: str = "ASC"

    def with_field(self, field_name: str) -> "JqlBuilder":
        allowed = {"updated", "created", "due"}
        return JqlBuilder(
            field=field_name if field_name in allowed else "updated",
            start=self.start,
            end=self.end,
            assignees=self.assignees.copy(),
            order=self.order,
        )

    def between(self, start: datetime, end: datetime) -> "JqlBuilder":
        return JqlBuilder(
            field=self.field,
            start=start,
            end=end,
            assignees=self.assignees.copy(),
            order=self.order,
        )

    def with_assignees(self, names: List[str]) -> "JqlBuilder":
        return JqlBuilder(
            field=self.field,
            start=self.start,
            end=self.end,
            assignees=list(names),
            order=self.order,
        )

    def order_by(self, order: str = "ASC") -> "JqlBuilder":
        return JqlBuilder(
            field=self.field,
            start=self.start,
            end=self.end,
            assignees=self.assignees.copy(),
            order=order,
        )

    def build(self) -> str:
        if self.start is None or self.end is None:
            raise ValueError("start/end must be set for JQL")

        def fmt(dt: datetime) -> str:
            if self.field == "due":
                return dt.strftime("%Y-%m-%d")
            return dt.strftime("%Y-%m-%d %H:%M")

        date_clause = (
            f"{self.field} >= '{fmt(self.start)}' AND {self.field} <= '{fmt(self.end)}'"
        )
        assignee_clause = ""
        if self.assignees:
            quoted = ", ".join([f'"{a}"' for a in self.assignees])
            assignee_clause = f" AND assignee in ({quoted})"
        order_clause = f" ORDER BY assignee, {self.field} {self.order}"
        return f"{date_clause}{assignee_clause}{order_clause}"
