from typing import Union, List
from typing import List
from pydantic import BaseModel


class Section(BaseModel):
    description: str
    value: Union[str, List[str]]


class OfficeDesignRequest(BaseModel):
    interior_style: Section
    layout_preferences: Section
    equipment_and_features: Section
    additional_notes_on_design: Section
    images: Section


class InpaintModification(BaseModel):
    image: str
    prompt: str
