"""Pydantic schemas for O*NET enrichment LLM responses."""

from pydantic import BaseModel, Field


class CareerEnrichment(BaseModel):
    match_score: int = Field(ge=0, le=100)
    personalized_description: str
    skill_gaps: list[str]
    education_recommendation: str
    transferable_skills: list[str]
