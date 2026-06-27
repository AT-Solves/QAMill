"""
Project Service - Project management and CRUD operations
"""
from typing import List, Optional
from sqlalchemy.orm import Session
from models.database import Project, Analysis
from datetime import datetime


class ProjectService:
    """Service for managing projects"""

    def __init__(self, db: Session):
        self.db = db

    def create_project(
        self,
        name: str,
        description: Optional[str] = None,
        languages: List[str] = None,
        frameworks: List[str] = None,
        org_id: str = "default-org",  # TODO: Get from auth context
        team_id: Optional[str] = None,
    ) -> Project:
        """Create a new project"""
        project = Project(
            org_id=org_id,
            team_id=team_id,
            slug=name.lower().replace(" ", "-"),
            name=name,
            description=description,
            languages=languages or ["python"],
            frameworks=frameworks or ["pytest"],
        )
        self.db.add(project)
        self.db.commit()
        self.db.refresh(project)
        return project

    def get_project(self, project_id: str) -> Optional[Project]:
        """Get project by ID"""
        return self.db.query(Project).filter(
            Project.id == project_id
        ).first()

    def list_projects(
        self,
        org_id: str = "default-org",
        skip: int = 0,
        limit: int = 50,
    ) -> List[Project]:
        """List projects for an organization"""
        return (
            self.db.query(Project)
            .filter(Project.org_id == org_id)
            .order_by(Project.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    def update_project(
        self,
        project_id: str,
        **kwargs
    ) -> Optional[Project]:
        """Update project"""
        project = self.get_project(project_id)
        if not project:
            return None

        for key, value in kwargs.items():
            if hasattr(project, key) and value is not None:
                setattr(project, key, value)

        project.updated_at = datetime.utcnow()
        self.db.add(project)
        self.db.commit()
        self.db.refresh(project)
        return project

    def delete_project(self, project_id: str) -> bool:
        """Delete project"""
        project = self.get_project(project_id)
        if not project:
            return False

        self.db.delete(project)
        self.db.commit()
        return True

    def get_project_dashboard(self, project_id: str) -> dict:
        """Get dashboard data for project"""
        project = self.get_project(project_id)
        if not project:
            return {}

        # Get latest 5 analyses
        analyses = (
            self.db.query(Analysis)
            .filter(Analysis.project_id == project_id)
            .order_by(Analysis.created_at.desc())
            .limit(5)
            .all()
        )

        # Calculate stats
        completed = [a for a in analyses if a.status == "completed"]
        avg_score = (
            sum(a.mutation_score for a in completed) / len(completed)
            if completed
            else 0
        )

        return {
            "project": project,
            "total_analyses": len(analyses),
            "avg_mutation_score": avg_score,
            "recent_analyses": analyses,
            "languages": project.languages,
            "frameworks": project.frameworks,
        }
