"""
QAMill API v2 - Enterprise-grade FastAPI application
Clean architecture with proper service layering
"""
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from contextlib import asynccontextmanager
import logging

# Configuration
from config.settings import settings

# Database
from database import engine, SessionLocal, Base
from models.database import (
    User,
    Organization,
    Project,
    Analysis,
    Report,
)

# Schemas (validation)
from schemas import (
    ProjectCreate,
    ProjectResponse,
    AnalysisCreate,
    AnalysisResponse,
)

# Services
from services.project_service import ProjectService
from services.analysis_service import AnalysisService
from services.report_service import ReportService
from services.storage_service import StorageService
from services.llm_service import LLMService
from services.auth_service import AuthService

# Routes
from routes_auth import router as auth_router
from routes_oauth import router as oauth_router
from routes_websocket import router as ws_router

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Startup/shutdown
@asynccontextmanager
async def lifespan(app: FastAPI):
    """App startup and shutdown"""
    # Startup
    logger.info(f"Starting {settings.app_name} v{settings.app_version}")
    Base.metadata.create_all(bind=engine)
    yield
    # Shutdown
    logger.info("Shutting down...")


# Create app
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth_router)
app.include_router(oauth_router)
app.include_router(ws_router)


# ── Service Instances ──
storage_service = StorageService()
llm_service = LLMService()


# Dependency: Get DB session
def get_db():
    """Get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ── Health Check ──
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "ok",
        "app": settings.app_name,
        "version": settings.app_version,
    }


# ── Projects API ──
@app.post("/api/v1/projects", response_model=ProjectResponse)
async def create_project(
    data: ProjectCreate,
    db: Session = Depends(get_db),
):
    """Create a new project"""
    service = ProjectService(db)
    project = service.create_project(
        name=data.name,
        description=data.description,
        languages=data.languages,
        frameworks=data.frameworks,
    )
    return project


@app.get("/api/v1/projects/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: str,
    db: Session = Depends(get_db),
):
    """Get project details"""
    service = ProjectService(db)
    project = service.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@app.get("/api/v1/projects")
async def list_projects(
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
):
    """List projects"""
    service = ProjectService(db)
    projects = service.list_projects(skip=skip, limit=limit)
    return {"projects": projects, "count": len(projects)}


# ── Analysis API (Core Capability) ──
@app.post("/api/v1/projects/{project_id}/analyze", response_model=AnalysisResponse)
async def start_analysis(
    project_id: str,
    data: AnalysisCreate,
    db: Session = Depends(get_db),
):
    """Start mutation testing analysis"""
    # Validate project exists
    service = ProjectService(db)
    project = service.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Create analysis
    analysis_service = AnalysisService(db, llm_service=llm_service, storage_service=storage_service)
    analysis = await analysis_service.start_analysis(
        project_id=project_id,
        file_path=data.file_path,
        language=data.language,
        llm_provider=data.llm_provider or settings.llm.default_provider,
        llm_model=data.llm_model
        or settings.llm.models.get(
            data.llm_provider or settings.llm.default_provider,
            "default",
        ),
    )
    return analysis


@app.get("/api/v1/projects/{project_id}/analyses")
async def list_analyses(
    project_id: str,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
):
    """List analyses for a project"""
    analysis_service = AnalysisService(db, llm_service=llm_service, storage_service=storage_service)
    analyses = analysis_service.list_analyses(
        project_id, skip=skip, limit=limit
    )
    return {"analyses": analyses, "count": len(analyses)}


@app.get("/api/v1/projects/{project_id}/analyses/{analysis_id}")
async def get_analysis(
    project_id: str,
    analysis_id: str,
    db: Session = Depends(get_db),
):
    """Get analysis details"""
    analysis_service = AnalysisService(db, llm_service=llm_service, storage_service=storage_service)
    analysis = analysis_service.get_analysis(analysis_id)
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")
    return analysis


@app.get("/api/v1/projects/{project_id}/stats")
async def get_project_stats(
    project_id: str,
    db: Session = Depends(get_db),
):
    """Get project quality governance stats"""
    analysis_service = AnalysisService(db, llm_service=llm_service, storage_service=storage_service)
    stats = analysis_service.get_project_stats(project_id)
    return stats


# ── Reports API ──
@app.get("/api/v1/projects/{project_id}/analyses/{analysis_id}/report")
async def generate_report(
    project_id: str,
    analysis_id: str,
    format: str = "html",
    db: Session = Depends(get_db),
):
    """Generate elite HTML/PDF report"""
    service = ReportService(db, storage_service=storage_service)
    report = await service.generate_report(
        analysis_id=analysis_id,
        format=format,
        project_id=project_id,
    )
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    return report


# ── Error Handlers ──
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Handle HTTP exceptions"""
    return {
        "error": exc.detail,
        "status_code": exc.status_code,
    }


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """Handle general exceptions"""
    import traceback
    error_detail = traceback.format_exc()
    logger.error(f"Unhandled exception: {exc}")
    logger.error(error_detail)
    return {
        "error": "Internal server error",
        "detail": str(exc),
        "traceback": error_detail if settings.api.debug else None,
        "status_code": 500,
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main_new:app",
        host=settings.api.host,
        port=settings.api.port,
        reload=settings.api.reload,
        workers=settings.api.workers,
    )
