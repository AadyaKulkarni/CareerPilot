from pydantic import BaseModel, EmailStr, Field
from typing import Any

class RegisterIn(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    password: str = Field(min_length=6, max_length=128)
class LoginIn(BaseModel):
    email: EmailStr
    password: str
class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict
class ProfileIn(BaseModel):
    career_goal: str = "Software Developer"
    degree: str = ""
    branch: str = ""
    college: str = ""
    cgpa: float | None = None
    graduation_year: int | None = None
    skills: list[dict[str, Any]] = []
    experiences: list[dict[str, Any]] = []
    projects: list[dict[str, Any]] = []
    certifications: list[dict[str, Any]] = []
    achievements: list[str] = []
    interests: list[str] = []
class ResumeIn(BaseModel):
    name: str = "My Resume"
    template: str = "ATS Classic"
    content: dict[str, Any]
class EnhanceIn(BaseModel):
    section: str
    text: str
class JobMatchIn(BaseModel):
    job_description: str
class LLMIn(BaseModel):
    provider: str
    model: str = ""
    api_key: str = ""
class TaskUpdate(BaseModel):
    completed: bool


class TextAnalyzeIn(BaseModel):
    text: str = Field(min_length=40, max_length=30000)
    target_role: str = ""
class CodingSyncIn(BaseModel):
    leetcode: str = ""
    codeforces: str = ""
    github: str = ""
class CodingManualIn(BaseModel):
    easy: int = Field(0, ge=0, le=5000)
    medium: int = Field(0, ge=0, le=5000)
    hard: int = Field(0, ge=0, le=5000)
    rating: int | None = Field(None, ge=0, le=4500)
    contests: int = Field(0, ge=0, le=1000)
class InterviewStartIn(BaseModel):
    role: str = ""
    difficulty: str = Field("medium", pattern="^(easy|medium|hard)$")
    num_questions: int = Field(6, ge=3, le=10)
    use_llm: bool = True
class InterviewAnswerIn(BaseModel):
    question_index: int = Field(ge=0, le=20)
    answer: str = Field(min_length=1, max_length=4000)
class RoadmapIn(BaseModel):
    hours_per_week: int = Field(10, ge=2, le=60)
    target_role: str = ""
