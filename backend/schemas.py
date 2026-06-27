"""
Pydantic schemas for request/response validation
Zero magic - explicit validation for all API inputs
"""
from typing import Optional, List, Dict
from pydantic import BaseModel, EmailStr, Field
from datetime import datetime


# ── User Schemas ──
class UserBase(BaseModel):
    email: EmailStr
    name: str


class UserCreate(UserBase):
    password: str = Field(..., min_length=8)


class UserResponse(UserBase):
    id: str
    avatar_url: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


# ── Organization Schemas ──
class OrganizationBase(BaseModel):
    slug: str = Field(..., min_length=3, max_length=50)
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None


class OrganizationCreate(OrganizationBase):
    pass


class OrganizationResponse(OrganizationBase):
    id: str
    avatar_url: Optional[str] = None
    plan: str = "free"
    created_at: datetime

    class Config:
        from_attributes = True


# ── Team Schemas ──
class TeamBase(BaseModel):
    slug: str = Field(..., min_length=3, max_length=50)
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    type: str = "engineering"  # engineering, qa, devops


class TeamCreate(TeamBase):
    pass


class TeamResponse(TeamBase):
    id: str
    org_id: str
    created_at: datetime

    class Config:
        from_attributes = True


# ── Project Schemas ──
class ProjectBase(BaseModel):
    slug: str = Field(..., min_length=3, max_length=50)
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None


class ProjectCreate(ProjectBase):
    languages: List[str] = ["python"]
    frameworks: List[str] = ["pytest"]
    repo_url: Optional[str] = None


class ProjectResponse(ProjectBase):
    id: str
    org_id: str
    team_id: Optional[str] = None
    languages: List[str]
    frameworks: List[str]
    is_public: bool = False
    created_at: datetime

    class Config:
        from_attributes = True


# ── Analysis Schemas ──
class AnalysisBase(BaseModel):
    file_path: str
    language: str  # python, javascript, csharp
    llm_provider: Optional[str] = None
    llm_model: Optional[str] = None


class AnalysisCreate(AnalysisBase):
    pass


class AnalysisResponse(AnalysisBase):
    id: str
    project_id: str
    status: str  # pending, running, completed, failed
    mutation_count: int = 0
    killed_count: int = 0
    survived_count: int = 0
    equivalent_count: int = 0
    mutation_score: float = 0.0
    coverage_score: float = 0.0
    quality_score: float = 0.0
    error_message: Optional[str] = None
    started_at: datetime
    completed_at: Optional[datetime] = None
    duration_seconds: Optional[int] = None
    created_at: datetime

    class Config:
        from_attributes = True


# ── Report Schemas ──
class ReportBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None


class ReportCreate(ReportBase):
    report_type: str = "html"  # html, pdf, json


class ReportResponse(ReportBase):
    id: str
    project_id: str
    analysis_id: Optional[str] = None
    report_type: str
    file_path: Optional[str] = None
    is_public: bool = False
    share_token: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


# ── Error Schemas ──
class ErrorResponse(BaseModel):
    error: str
    status_code: int
    details: Optional[Dict] = None
