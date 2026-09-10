from typing import Any, Literal
from pydantic import BaseModel, Field


class ExportFormField(BaseModel):
    label: str
    type: str = 'text'
    paired_image: str | None = Field(default=None, alias='pairedImage')


class ExportFormSection(BaseModel):
    title: str
    multiple: bool = False
    fields: list[ExportFormField] = Field(max_length=100)


class ExportOriginalForm(BaseModel):
    title: str
    sections: list[ExportFormSection] = Field(max_length=100)
    data: dict[str, Any]


class FormDocumentExport(BaseModel):
    markdown: str = Field(min_length=1, max_length=2_000_000)
    format: Literal['hwp', 'docx']
    original_form: ExportOriginalForm | None = None


class FormOriginalFile(BaseModel):
    url: str
    original_name: str
    content_type: str | None = None
    size: int | None = None


class FormEntryCreate(BaseModel):
    template_id: str
    data: dict[str, Any]
    original_file: FormOriginalFile | None = None


class FormEntryPatch(BaseModel):
    data: dict[str, Any]
    version: int
    original_file: FormOriginalFile | None = None


class FormEntryOut(BaseModel):
    id: str
    template_id: str
    data: dict[str, Any]
    original_file: FormOriginalFile | None = None
    version: int
    is_deleted: bool
    created_at: str | None = None
    created_by: str | None = None
    updated_at: str | None = None
    updated_by: str | None = None
