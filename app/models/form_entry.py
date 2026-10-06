from typing import Any, Literal
from pydantic import BaseModel, Field
from app.models.asset_link import AssetSelection as WorkAssetSelection, LinkedAsset as LinkedWorkAsset


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
    format: Literal['hwp', 'docx', 'md-zip']
    markdown_filename: str = Field(default='document.md', max_length=255)
    original_form: ExportOriginalForm | None = None


class FormOriginalFile(BaseModel):
    url: str
    original_name: str
    content_type: str | None = None
    size: int | None = None


class FormEntryCreate(WorkAssetSelection):
    template_id: str
    data: dict[str, Any]
    original_file: FormOriginalFile | None = None


class FormEntryPatch(WorkAssetSelection):
    data: dict[str, Any]
    version: int
    original_file: FormOriginalFile | None = None


class FormEntryRevisionOut(BaseModel):
    version: int
    action: Literal['CREATE', 'UPDATE']
    changed_at: str | None = None
    changed_by: str | None = None
    changed_sections: list[str] = Field(default_factory=list)
    has_diff: bool = False


class FormEntryFieldChangeOut(BaseModel):
    path: str
    before: Any = None
    after: Any = None
    before_present: bool = True
    after_present: bool = True


class FormEntryRevisionDetailOut(BaseModel):
    version: int
    changed_at: str | None = None
    changed_by: str | None = None
    changed_sections: list[str] = Field(default_factory=list)
    changes: list[FormEntryFieldChangeOut] = Field(default_factory=list)
    changes_truncated: bool = False


class FormEntryOut(BaseModel):
    id: str
    template_id: str
    data: dict[str, Any]
    linked_assets: list[LinkedWorkAsset] = Field(default_factory=list)
    original_file: FormOriginalFile | None = None
    version: int
    is_deleted: bool
    created_at: str | None = None
    created_by: str | None = None
    updated_at: str | None = None
    updated_by: str | None = None
    revision_history: list[FormEntryRevisionOut] = Field(default_factory=list)
