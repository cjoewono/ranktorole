"""
Pydantic schemas for the Recon brainstorm Haiku call.

The model returns a ranked list of three candidates. We keep fields short and
bounded to cap token spend and make downstream validation tight.
"""

from typing import List

from pydantic import BaseModel, Field


class BrainstormCandidate(BaseModel):
    """One Haiku pick. onet_code is validated against XX-XXXX.XX pattern downstream."""

    onet_code: str = Field(..., min_length=10, max_length=10)
    match_score: int = Field(..., ge=0, le=100)
    match_rationale: str = Field(..., max_length=400)
    skill_gaps: List[str] = Field(default_factory=list, max_length=5)
    transferable_skills: List[str] = Field(default_factory=list, max_length=6)


class BrainstormRanking(BaseModel):
    """Haiku full response. Exactly three candidates in ranked order."""

    candidates: List[BrainstormCandidate] = Field(..., min_length=1, max_length=3)
