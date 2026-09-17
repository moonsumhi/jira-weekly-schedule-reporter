from datetime import date

from pydantic import BaseModel, Field, field_validator


class AssetNoteContent(BaseModel):
    content: str = Field(min_length=1, max_length=5000)
    occurred_on: date

    @field_validator('content', mode='before')
    @classmethod
    def trim_content(cls, value):
        return value.strip() if isinstance(value, str) else value


class AssetNoteCreate(AssetNoteContent):
    client_id: str = Field(pattern=r'^[a-f0-9]{32}$')


class AssetNotePatch(AssetNoteContent):
    version: int = Field(ge=1)


class AssetNoteDelete(BaseModel):
    version: int = Field(ge=1)
