"""Pydantic schemas for O*NET enrichment LLM responses."""

from pydantic import BaseModel, Field


class CareerEnrichment(BaseModel):
    match_score: int = Field(ge=0, le=100)
    personalized_description: str = Field(max_length=2000)
    skill_gaps: list[str] = Field(max_length=8)
    education_recommendation: str = Field(max_length=1000)
    transferable_skills: list[str] = Field(max_length=12)
