"""
SQLAlchemy database models for QAMill
Team/Org/Account/Project/Analysis structure
"""
from datetime import datetime
from typing import Optional, List
from sqlalchemy import Column, String, Integer, Float, DateTime, Boolean, ForeignKey, JSON, Enum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
import uuid
import enum as python_enum

Base = declarative_base()


class User(Base):
    """User account model"""
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    name = Column(String, nullable=False)
    avatar_url = Column(String, nullable=True)

    # Multi-tenancy
    default_org_id = Column(String, ForeignKey("organizations.id"), nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login = Column(DateTime, nullable=True)

    # Relationships
    organizations = relationship("OrganizationMember", back_populates="user")
    team_memberships = relationship("TeamMember", back_populates="user")


class Organization(Base):
    """Organization model"""
    __tablename__ = "organizations"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    slug = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    avatar_url = Column(String, nullable=True)
    website = Column(String, nullable=True)

    # Plan
    plan = Column(String, default="free")  # free, starter, pro, enterprise
    billing_email = Column(String, nullable=True)

    # Settings
    settings = Column(JSON, default={})

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    members = relationship("OrganizationMember", back_populates="organization")
    teams = relationship("Team", back_populates="organization")
    projects = relationship("Project", back_populates="organization")


class OrganizationMember(Base):
    """Organization membership model"""
    __tablename__ = "organization_members"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    org_id = Column(String, ForeignKey("organizations.id"), nullable=False)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    role = Column(String, default="member")  # owner, admin, member, viewer

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    organization = relationship("Organization", back_populates="members")
    user = relationship("User", back_populates="organizations")


class Team(Base):
    """Team model"""
    __tablename__ = "teams"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    org_id = Column(String, ForeignKey("organizations.id"), nullable=False)
    slug = Column(String, index=True, nullable=False)
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    avatar_url = Column(String, nullable=True)

    # Team type
    type = Column(String, default="engineering")  # engineering, qa, devops

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    organization = relationship("Organization", back_populates="teams")
    members = relationship("TeamMember", back_populates="team")
    projects = relationship("Project", back_populates="team")


class TeamMember(Base):
    """Team membership model"""
    __tablename__ = "team_members"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    team_id = Column(String, ForeignKey("teams.id"), nullable=False)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    role = Column(String, default="member")  # lead, member, viewer

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    team = relationship("Team", back_populates="members")
    user = relationship("User", back_populates="team_memberships")


class Project(Base):
    """Project model"""
    __tablename__ = "projects"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    org_id = Column(String, ForeignKey("organizations.id"), nullable=False)
    team_id = Column(String, ForeignKey("teams.id"), nullable=True)
    slug = Column(String, index=True, nullable=False)
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)

    # Technology stack
    languages = Column(JSON, default=["python"])  # python, javascript, csharp
    frameworks = Column(JSON, default=["pytest"])

    # Repository
    repo_url = Column(String, nullable=True)
    repo_type = Column(String, nullable=True)  # github, gitlab, bitbucket

    # Settings
    settings = Column(JSON, default={})

    # Access
    is_public = Column(Boolean, default=False)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    organization = relationship("Organization", back_populates="projects")
    team = relationship("Team", back_populates="projects")
    analyses = relationship("Analysis", back_populates="project")


class Analysis(Base):
    """Analysis result model"""
    __tablename__ = "analyses"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String, ForeignKey("projects.id"), nullable=False)
    file_path = Column(String, nullable=False)
    language = Column(String, nullable=False)  # python, javascript, csharp

    # Results
    mutation_count = Column(Integer, default=0)
    killed_count = Column(Integer, default=0)
    survived_count = Column(Integer, default=0)
    equivalent_count = Column(Integer, default=0)

    # Metrics (0-100)
    mutation_score = Column(Float, default=0.0)
    coverage_score = Column(Float, default=0.0)
    quality_score = Column(Float, default=0.0)

    # Status
    status = Column(String, default="pending")  # pending, running, completed, failed
    error_message = Column(String, nullable=True)

    # Timeline
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    duration_seconds = Column(Integer, nullable=True)

    # LLM info
    llm_provider = Column(String, nullable=True)
    llm_model = Column(String, nullable=True)

    # Detailed results
    mutations_detail = Column(JSON, default=[])  # Array of mutation objects
    coverage_detail = Column(JSON, default={})   # Code-level coverage

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    project = relationship("Project", back_populates="analyses")


class Report(Base):
    """Report model"""
    __tablename__ = "reports"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String, ForeignKey("projects.id"), nullable=False)
    analysis_id = Column(String, ForeignKey("analyses.id"), nullable=True)

    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    report_type = Column(String)  # html, pdf, json

    # File path for storage
    file_path = Column(String, nullable=True)

    # Sharing
    is_public = Column(Boolean, default=False)
    share_token = Column(String, unique=True, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class AuditLog(Base):
    """Audit log for compliance"""
    __tablename__ = "audit_logs"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    org_id = Column(String, ForeignKey("organizations.id"), nullable=False)
    user_id = Column(String, ForeignKey("users.id"), nullable=True)

    action = Column(String, nullable=False)  # create, update, delete, view
    resource_type = Column(String, nullable=False)  # project, analysis, report
    resource_id = Column(String, nullable=True)

    details = Column(JSON, default={})

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
