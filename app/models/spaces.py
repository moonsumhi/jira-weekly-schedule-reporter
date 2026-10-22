"""Organization/space input contracts. Login accounts remain independent of people."""
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator
from pydantic.alias_generators import to_camel

Name = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)
]
Identifier = Annotated[str, StringConstraints(pattern=r"^[a-zA-Z0-9_-]{1,64}$")]


class Input(BaseModel):
    model_config = ConfigDict(
        extra="forbid", populate_by_name=True, alias_generator=to_camel
    )


class TeamInput(Input):
    name: Name
    color: str = Field(default="#1976d2", pattern=r"^#[0-9a-fA-F]{6}$")
    manager_ids: list[Identifier] = Field(default_factory=list, max_length=100)


class BuildingInput(Input):
    name: Name
    location: str = Field(default="", max_length=300)
    description: str = Field(default="", max_length=1000)


class FloorInput(Input):
    name: Name
    building_id: Identifier


class RoomInput(BuildingInput):
    floor_id: Identifier
    team_ids: list[Identifier] = Field(default_factory=list, max_length=100)
    manager_ids: list[Identifier] = Field(default_factory=list, max_length=100)
    viewer_ids: list[Identifier] = Field(default_factory=list, max_length=200)
    visibility: Literal["all", "members"] = "all"


class PersonInput(Input):
    name: Name
    team_id: Identifier
    title: str = Field(default="", max_length=100)
    extension: Annotated[str, StringConstraints(strip_whitespace=True, max_length=30)] = ""
    room_id: Identifier | None = None
    user_id: Identifier | None = None
    active: bool = True


class PlanObject(Input):
    id: Identifier
    kind: Literal["wall", "door", "desk", "cabinet", "text", "zone"]
    name: str = Field(default="", max_length=100)
    x: float = Field(ge=-20000, le=20000, allow_inf_nan=False)
    y: float = Field(ge=-20000, le=20000, allow_inf_nan=False)
    width: float = Field(gt=0, le=20000, allow_inf_nan=False)
    height: float = Field(gt=0, le=20000, allow_inf_nan=False)
    rotation: float = Field(default=0, ge=-360, le=360, allow_inf_nan=False)
    font_size: int = Field(default=18, ge=8, le=120)
    bold: bool = False
    seat_id: Identifier | None = None
    team_id: Identifier | None = None

    @model_validator(mode="after")
    def desk_seat(self):
        if (self.kind == "desk") != bool(self.seat_id):
            raise ValueError("책상에만 좌석 식별자가 반드시 필요합니다.")
        return self


class SeatInput(Input):
    id: Identifier
    number: Name
    team_id: Identifier | None = None


class PlanInput(Input):
    version: int = Field(ge=0)
    width: int = Field(default=1600, ge=200, le=20000)
    height: int = Field(default=1000, ge=200, le=20000)
    objects: list[PlanObject] = Field(default_factory=list, max_length=1500)
    seats: list[SeatInput] = Field(default_factory=list, max_length=1000)

    @model_validator(mode="after")
    def unique_references(self):
        ids = [o.id for o in self.objects]
        seats = [s.id for s in self.seats]
        desk_seats = [o.seat_id for o in self.objects if o.kind == "desk"]
        numbers = [s.number.casefold() for s in self.seats]
        if (
            len(ids) != len(set(ids))
            or len(seats) != len(set(seats))
            or len(numbers) != len(set(numbers))
        ):
            raise ValueError("객체 식별자와 사무실 내 좌석번호는 중복될 수 없습니다.")
        if len(desk_seats) != len(set(desk_seats)) or set(desk_seats) != set(seats):
            raise ValueError("책상과 좌석은 일대일로 연결되어야 합니다.")
        return self


class VersionInput(Input):
    version: int = Field(ge=0)


class CloneInput(VersionInput):
    target_room_id: Identifier
    source: Literal["draft", "published"] = "published"


class AssignmentInput(Input):
    person_id: Identifier
    revision: int = Field(ge=0)
    team_id: Identifier | None = None
