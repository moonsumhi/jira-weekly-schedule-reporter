from pydantic import BaseModel, Field, field_validator
from bson import ObjectId


class AssetSelection(BaseModel):
    asset_ids: list[str] = Field(default_factory=list, max_length=100)

    @field_validator('asset_ids')
    @classmethod
    def valid_assets(cls, values):
        if any(not ObjectId.is_valid(value) for value in values):
            raise ValueError('잘못된 자산 ID입니다.')
        values = [str(ObjectId(value)) for value in values]
        if len(values) != len(set(values)):
            raise ValueError('중복된 서버가 있습니다.')
        return values


class LinkedAsset(BaseModel):
    id: str
    name: str = ''
    ip: str = ''
    asset_name: str = ''
    is_deleted: bool = False
