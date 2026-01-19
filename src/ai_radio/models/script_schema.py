"""Pydantic models for structured field report scripts."""
from pydantic import BaseModel, Field, model_validator


class ColdOpen(BaseModel):
    """Cold open with complaint, realization, and intro."""

    complaint_line: str = Field(
        ..., description="Whispered complaint about equipment/patrol (~15 words)"
    )
    realization: str = Field(..., description="Shocked realization mic is live")
    intro_sentence_1: str = Field(..., description="First introduction sentence")
    intro_sentence_2: str = Field(..., description="Second introduction sentence")


class InterviewSegment(BaseModel):
    """Single question/answer exchange in interview."""

    question: str = Field(..., description="Presenter question (~25-30 words)")
    answer: str = Field(..., description="Source answer (~40-50 words)")
    interference_after: bool = Field(
        default=False, description="Whether interference follows this segment"
    )


class FieldReportScript(BaseModel):
    """Complete field report structure."""

    cold_open: ColdOpen
    interview_segments: list[InterviewSegment] = Field(
        ..., min_length=4, max_length=6
    )
    signoff: str = Field(..., description="Final signoff line")

    @model_validator(mode="after")
    def validate_segment_count(self):
        """Ensure 4-6 interview segments."""
        if not (4 <= len(self.interview_segments) <= 6):
            raise ValueError(
                f"Must have at least 4 interview segments, got {len(self.interview_segments)}"
            )
        return self
