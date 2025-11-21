"""
Database Schemas for Climate Resilient Agriculture MVP

Each Pydantic model represents a MongoDB collection. The collection name
is the lowercase of the class name (e.g., Farm -> "farm").
"""

from pydantic import BaseModel, Field
from typing import Optional, List


class Farm(BaseModel):
    """Farm profiles provided by users"""
    name: str = Field(..., description="Farm or farmer name")
    country: Optional[str] = Field(None, description="Country")
    region: Optional[str] = Field(None, description="Region/State/Province")
    acreage: Optional[float] = Field(None, ge=0, description="Farm size in acres")
    soil_type: Optional[str] = Field(None, description="Dominant soil type")
    crops: List[str] = Field(default_factory=list, description="Primary crops grown")
    risks: List[str] = Field(default_factory=list, description="Key climate risks e.g., drought, heat, flood, salinity, pests")
    budget: Optional[str] = Field(None, description="Budget level: low, medium, high")


class Practice(BaseModel):
    """Climate-smart practice library"""
    title: str = Field(..., description="Practice name")
    description: str = Field(..., description="What it is and how it helps")
    crops: List[str] = Field(default_factory=list, description="Applicable crops")
    risks: List[str] = Field(default_factory=list, description="Risks this helps address")
    cost_level: str = Field(..., description="low | medium | high")
    benefits: List[str] = Field(default_factory=list, description="Key benefits")
    prerequisites: Optional[str] = Field(None, description="Notable requirements or setup")


# Optional: Structured response model for recommendations
class Recommendation(BaseModel):
    practice_title: str
    match_score: float = Field(..., ge=0, le=1)
    reasons: List[str] = Field(default_factory=list)
    cost_level: str
    risks: List[str] = []
    crops: List[str] = []
