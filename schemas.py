from typing import List, Optional
from pydantic import BaseModel, Field


class TriageRequest(BaseModel):
    # Core facts; clients can send free text and/or structured fields
    message: str = Field(..., description="Caller or witness description of the incident")
    location: Optional[str] = Field(None, description="Approximate location text or coordinates")
    incident_type: Optional[str] = Field(None, description="e.g., cardiac_arrest, fire, accident")
    age: Optional[int] = Field(None, ge=0, le=120)
    conscious: Optional[bool] = None
    breathing: Optional[bool] = None
    bleeding: Optional[bool] = None
    symptoms: Optional[List[str]] = None


class Recommendation(BaseModel):
    priority: str
    actions: List[str]
    resources: List[str]


class TriageResponse(BaseModel):
    severity: str
    confidence: float
    recommendation: Recommendation
    advice: List[str]
