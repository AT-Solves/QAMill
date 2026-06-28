# QAMill Enterprise Refactor Plan
## Complete App Architecture, Design & UX Overhaul

**Status:** Planning Phase  
**Scope:** Complete rewrite for enterprise-grade production  
**Timeline:** 4-6 weeks  
**Target:** World-class SaaS QA Governance Platform

---

## Executive Summary

QAMill has evolved organically with features added on top of the original architecture. This creates technical debt and poor UX. We need a **complete architectural redesign** to deliver an **elite, scalable, enterprise-ready** platform.

### Current State Issues
- ❌ Monolithic backend without proper layering
- ❌ Hardcoded values throughout codebase
- ❌ Poor separation of concerns
- ❌ No team/org model
- ❌ Inconsistent API design
- ❌ UI/UX not professional
- ❌ No configuration management
- ❌ Weak error handling
- ❌ No proper logging/observability

### Target State (This Refactor)
- ✅ Clean layered architecture
- ✅ Configuration-driven (0 hardcoded values)
- ✅ Enterprise auth (OAuth + SAML)
- ✅ Team/Org/Account models
- ✅ RESTful API with OpenAPI spec
- ✅ Elite UI/UX (inspired by Linear, GitHub, Figma)
- ✅ Real-time dashboards
- ✅ Comprehensive logging
- ✅ Production-ready deployment

---

## Architecture Redesign

### Current (❌ Problematic)
```
main.py (3000+ lines)
├─ Routes mixed with logic
├─ Hardcoded values
├─ Weak separation
└─ Poor scalability
```

### Target (✅ Enterprise)
```
QAMill API (FastAPI)
├── Core Layer
│   ├─ config/          # Environment-driven, no hardcodes
│   ├─ models/          # SQLAlchemy models
│   ├─ schemas/         # Pydantic schemas (validation)
│   └─ constants/       # Enums, not strings
├── Domain Layer
│   ├─ auth/            # Auth service (OAuth, SAML, JWT)
│   ├─ accounts/        # Account/Team/Org management
│   ├─ projects/        # Project management
│   ├─ analysis/        # Mutation testing logic
│   ├─ reports/         # Report generation
│   └─ ai/              # LLM integration
├── API Layer
│   ├─ v1/auth/         # Auth endpoints
│   ├─ v1/accounts/     # Account management
│   ├─ v1/projects/     # Project operations
│   ├─ v1/analysis/     # Analysis endpoints
│   └─ v1/reports/      # Report endpoints
├── Infrastructure
│   ├─ database/        # SQLAlchemy setup
│   ├─ cache/           # Redis integration
│   ├─ storage/         # File storage (S3/local)
│   ├─ logging/         # Structured logging
│   └─ monitoring/      # Observability
└── main.py             # App initialization only
```

---

## Database Model (Team/Org/Account)

### User Model
```python
class User:
    id: UUID
    email: str (unique)
    password_hash: str
    name: str
    avatar_url: str
    status: enum (active, inactive, suspended)
    
    # Multi-tenancy
    default_org_id: UUID (fk)
    
    # Timestamps
    created_at: datetime
    updated_at: datetime
    last_login: datetime
```

### Organization Model
```python
class Organization:
    id: UUID
    slug: str (unique, for URLs)
    name: str
    description: str
    avatar_url: str
    website: str
    
    # Billing
    plan: enum (free, starter, pro, enterprise)
    billing_email: str
    
    # Settings
    settings: JSON (SSO config, etc)
    
    # Timestamps
    created_at: datetime
    updated_at: datetime
```

### Team Model
```python
class Team:
    id: UUID
    org_id: UUID (fk)
    slug: str (unique within org)
    name: str
    description: str
    
    # Team type
    type: enum (engineering, qa, devops)
    
    # Avatar
    avatar_url: str
    
    # Timestamps
    created_at: datetime
    updated_at: datetime
```

### Project Model
```python
class Project:
    id: UUID
    org_id: UUID (fk)
    team_id: UUID (fk)
    slug: str (unique within org)
    name: str
    description: str
    
    # Technology stack
    languages: list[str] (python, javascript, csharp)
    frameworks: list[str] (pytest, jest, xunit)
    
    # Repository
    repo_url: str
    repo_type: enum (github, gitlab, bitbucket)
    
    # Settings
    settings: JSON (mutation operators, etc)
    
    # Access control
    is_public: bool
    
    # Timestamps
    created_at: datetime
    updated_at: datetime
```

### Analysis Model
```python
class Analysis:
    id: UUID
    project_id: UUID (fk)
    file_path: str
    language: enum (python, javascript, csharp)
    
    # Results
    mutation_count: int
    killed_count: int
    survived_count: int
    equivalent_count: int
    
    # Metrics
    mutation_score: float (0.0-100.0)
    coverage_score: float
    quality_score: float
    
    # Status
    status: enum (pending, running, completed, failed)
    error_message: str (if failed)
    
    # Timeline
    started_at: datetime
    completed_at: datetime
    duration_seconds: int
    
    # Metadata
    llm_provider: str
    llm_model: str
    
    # Timestamps
    created_at: datetime
    updated_at: datetime
```

### Access Control
```python
class OrganizationMember:
    id: UUID
    org_id: UUID (fk)
    user_id: UUID (fk)
    role: enum (owner, admin, member, viewer)
    
class TeamMember:
    id: UUID
    team_id: UUID (fk)
    user_id: UUID (fk)
    role: enum (lead, member, viewer)
```

---

## API Design (RESTful v1)

### Auth Endpoints
```
POST   /api/v1/auth/register          # Create account
POST   /api/v1/auth/login             # Email/password login
POST   /api/v1/auth/oauth/:provider   # OAuth callback
POST   /api/v1/auth/saml/callback     # SAML callback
POST   /api/v1/auth/logout            # Logout
GET    /api/v1/auth/me                # Current user
POST   /api/v1/auth/refresh           # Refresh JWT
```

### Account Endpoints
```
GET    /api/v1/accounts/me            # User profile
PUT    /api/v1/accounts/me            # Update profile
GET    /api/v1/accounts/settings      # User settings
PUT    /api/v1/accounts/settings      # Update settings
POST   /api/v1/accounts/password      # Change password
```

### Organization Endpoints
```
GET    /api/v1/orgs                   # List user's orgs
POST   /api/v1/orgs                   # Create org
GET    /api/v1/orgs/:org_id           # Get org
PUT    /api/v1/orgs/:org_id           # Update org
DELETE /api/v1/orgs/:org_id           # Delete org

# Members
GET    /api/v1/orgs/:org_id/members   # List members
POST   /api/v1/orgs/:org_id/members   # Invite member
PUT    /api/v1/orgs/:org_id/members/:user_id # Update role
DELETE /api/v1/orgs/:org_id/members/:user_id # Remove member
```

### Team Endpoints
```
GET    /api/v1/orgs/:org_id/teams                # List teams
POST   /api/v1/orgs/:org_id/teams                # Create team
GET    /api/v1/orgs/:org_id/teams/:team_id       # Get team
PUT    /api/v1/orgs/:org_id/teams/:team_id       # Update team
DELETE /api/v1/orgs/:org_id/teams/:team_id       # Delete team
```

### Project Endpoints
```
GET    /api/v1/orgs/:org_id/projects                          # List projects
POST   /api/v1/orgs/:org_id/projects                          # Create project
GET    /api/v1/orgs/:org_id/projects/:project_id              # Get project
PUT    /api/v1/orgs/:org_id/projects/:project_id              # Update project
DELETE /api/v1/orgs/:org_id/projects/:project_id              # Delete project

# Analysis
POST   /api/v1/orgs/:org_id/projects/:project_id/analyze      # Start analysis
GET    /api/v1/orgs/:org_id/projects/:project_id/analyses     # List analyses
GET    /api/v1/orgs/:org_id/projects/:project_id/analyses/:id # Get analysis
GET    /api/v1/orgs/:org_id/projects/:project_id/analyses/:id/report # Download report
```

---

## Configuration Management

### Structure (0 Hardcoded Values!)
```
config/
├── __init__.py
├── settings.py          # Pydantic BaseSettings
├── constants.py         # Enums (not strings)
├── database.py          # DB config
├── cache.py             # Redis config
└── storage.py           # S3/local config

# Environment files
.env.example            # Template with all vars
.env.local              # Local overrides (gitignored)
.env.production          # Production config
```

### Example: settings.py
```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8765
    api_debug: bool = False
    
    # Database
    database_url: str
    database_pool_size: int = 10
    
    # Redis
    redis_url: str
    redis_cache_ttl: int = 3600
    
    # Auth
    jwt_secret: str
    jwt_expiry_hours: int = 24
    oauth_providers: dict = Field(default_factory=dict)
    
    # LLM
    llm_providers: dict = Field(default_factory=dict)
    
    # Storage
    storage_type: str = "local"  # local, s3
    storage_path: str = "/tmp/qamill"
    
    class Config:
        env_file = ".env"
        case_sensitive = False

settings = Settings()
```

---

## UI/UX Redesign

### Design Philosophy
- **Modern:** Clean, minimal, professional
- **Responsive:** Works on all devices
- **Accessible:** WCAG 2.1 AA compliant
- **Fast:** Optimized performance
- **Delightful:** Smooth animations, clear feedback

### Inspired By
- **Linear:** Clean UI, task management
- **GitHub:** Workflow, collaboration
- **Figma:** Real-time collaboration
- **Stripe:** Professional, trustworthy

### Key Components

#### Navigation
```
Header
├── Logo
├── Search bar
├── Org switcher
└── User menu
    ├── Account settings
    ├── Team settings
    ├── Billing
    └── Logout

Sidebar (contextual)
├── Projects
│   ├── [Project 1]
│   ├── [Project 2]
│   └── + New project
├── Analytics
├── Reports
├── Team
└── Settings
```

#### Dashboard (Home)
```
Quick Stats
├── Active projects
├── Analyses this week
├── Avg mutation score
└── Total test coverage

Recent Activity
├── Latest analyses
├── Team activity
└── Shared reports

Quick Actions
├── New project
├── Run analysis
└── View reports
```

#### Project View
```
Tabs
├── Overview (dashboard)
├── Analyses (history)
├── Reports (generated)
├── Settings
└── Team

Overview Dashboard
├── Mutation score trend (chart)
├── Test coverage trend (chart)
├── Recent analyses (table)
└── Top weak areas (tree)
```

#### Analysis Page
```
Header
├── File name
├── Language badge
├── Analysis status
└── Timestamp

Results Tabs
├── Summary (key metrics)
├── Mutations (detailed list with filters)
├── Coverage (code-level view)
├── Report (PDF/HTML download)
└── AI Insights (generated tests)

Summary
├── Mutation score (big number)
├── Kill/survive breakdown (donut chart)
├── Equivalent mutants (count)
└── Top 5 survived mutations (list)
```

#### Right-Click Context Menus
```
File/Project
├── Run analysis
├── View latest report
├── Share project
├── Settings
└── Delete

Mutation Result
├── View code change
├── Generate test (AI)
├── Mark equivalent
├── Add to backlog
└── Copy details

Team/Member
├── Change role
├── Remove from team
├── Send message
└── View profile
```

---

## Frontend Architecture

### Tech Stack
```
Vue 3 + TypeScript + Vite
├── UI Components (Tailwind CSS)
├── State Management (Pinia)
├── API Client (axios + tanstack query)
├── Charts (Chart.js/D3)
└── Forms (VeeValidate)

Structure
src/
├── components/
│   ├── common/
│   ├── auth/
│   ├── projects/
│   ├── analysis/
│   └── reports/
├── stores/
│   ├── auth.ts
│   ├── org.ts
│   ├── project.ts
│   └── analysis.ts
├── views/
│   ├── auth/
│   ├── dashboard/
│   ├── projects/
│   ├── analysis/
│   └── reports/
├── composables/
├── utils/
└── types/
```

---

## Backend Services Architecture

### Service Layer Pattern
```
Service (business logic) → Repository (data) → Database
       ↓ (dependency injection)

Example:
ProjectService
├── create_project(data, user_id, org_id)
├── get_project(project_id, user_id)
├── update_project(project_id, data, user_id)
└── delete_project(project_id, user_id)

ProjectRepository
├── create(data)
├── get_by_id(id)
├── update(id, data)
└── delete(id)
```

### Key Services
1. **AuthService** - JWT, OAuth, SAML
2. **AccountService** - User profiles, settings
3. **OrganizationService** - Org CRUD, members
4. **TeamService** - Team CRUD, members
5. **ProjectService** - Project CRUD, settings
6. **AnalysisService** - Run analysis, track results
7. **ReportService** - Generate reports
8. **LLMService** - Multi-provider LLM calls
9. **StorageService** - File management
10. **NotificationService** - Email, webhooks

---

## Phase Rollout (4-6 weeks)

### Phase 1: Foundation (Week 1)
- [ ] Database design & migrations
- [ ] Configuration management
- [ ] Auth service (JWT + OAuth)
- [ ] Basic CRUD services
- [ ] API structure

### Phase 2: Organizational Features (Week 2)
- [ ] Organization CRUD
- [ ] Team CRUD
- [ ] Access control (RBAC)
- [ ] Member management
- [ ] Invitation system

### Phase 3: Core Features (Week 3)
- [ ] Project CRUD
- [ ] Analysis service refactor
- [ ] Report generation
- [ ] Integration with existing mutation engines

### Phase 4: Frontend Redesign (Week 2-4, parallel)
- [ ] New component library
- [ ] Auth pages redesign
- [ ] Dashboard redesign
- [ ] Project pages redesign
- [ ] Analysis pages redesign

### Phase 5: Advanced Features (Week 5)
- [ ] Real-time dashboards (WebSocket)
- [ ] AI-powered test generation
- [ ] Export/sharing features
- [ ] Team collaboration

### Phase 6: Deployment & Optimization (Week 6)
- [ ] Docker/Kubernetes setup
- [ ] Load testing
- [ ] Security hardening
- [ ] Performance optimization
- [ ] Production deployment

---

## MCP Server Integration

### Recommended MCP Servers
1. **GitHub MCP** - Push code, create PRs
2. **Linear MCP** - Create/update issues
3. **Slack MCP** - Notifications, messages
4. **Email MCP** - Transactional emails
5. **S3 MCP** - File storage

### Implementation
```python
from mcp import MCPClient

# Initialize in config
github = MCPClient(provider="github")
linear = MCPClient(provider="linear")
slack = MCPClient(provider="slack")

# Use in services
async def on_analysis_complete(analysis):
    # Create Linear issue
    linear.create_issue(
        title=f"Test gaps in {analysis.file}",
        description=analysis.summary
    )
    
    # Notify on Slack
    slack.send_message(
        channel="#qa-team",
        text=f"Analysis complete: {analysis.mutation_score}%"
    )
```

---

## Testing Strategy

### Unit Tests
- Services, models, validators
- Configuration
- Auth logic

### Integration Tests
- API endpoints
- Database operations
- LLM integrations

### E2E Tests
- Complete user workflows
- Authentication flows
- Analysis pipeline

### Performance Tests
- Load testing
- Database query optimization
- Frontend performance

---

## DevOps & Deployment

### Docker
```dockerfile
# Multi-stage build
FROM python:3.11 AS builder
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

FROM python:3.11
WORKDIR /app
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY . .
CMD ["python", "main.py"]
```

### Docker Compose
```yaml
version: '3.8'
services:
  api:
    build: .
    ports:
      - "8765:8765"
    environment:
      - DATABASE_URL=postgresql://...
      - REDIS_URL=redis://...
    depends_on:
      - postgres
      - redis
  
  postgres:
    image: postgres:15
    environment:
      - POSTGRES_PASSWORD=...
  
  redis:
    image: redis:7
```

### Kubernetes
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: qamill-api
spec:
  replicas: 3
  selector:
    matchLabels:
      app: qamill-api
  template:
    metadata:
      labels:
        app: qamill-api
    spec:
      containers:
      - name: qamill-api
        image: qamill:1.3.0
        ports:
        - containerPort: 8765
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: qamill-secrets
              key: database-url
```

---

## Success Metrics

### Code Quality
- ✅ 0% hardcoded values
- ✅ 100% configuration-driven
- ✅ >80% test coverage
- ✅ Type-safe (mypy, strict mode)

### Performance
- ✅ API response <200ms (p95)
- ✅ Database query <50ms
- ✅ Frontend load <2s
- ✅ 99.9% uptime

### User Experience
- ✅ Mobile responsive
- ✅ Accessibility WCAG AA
- ✅ Zero console errors
- ✅ 90+ Lighthouse score

### Enterprise Features
- ✅ OAuth/SAML support
- ✅ RBAC fully functional
- ✅ Team collaboration works
- ✅ Audit logging complete

---

## Next Steps

1. **Approval & Planning** (This Week)
   - Review this plan
   - Approve architecture
   - Lock in design specs

2. **Setup & Foundation** (Week 1)
   - Database schema
   - Project structure
   - Development environment

3. **Implementation** (Weeks 2-5)
   - Phase-by-phase rollout
   - Parallel frontend/backend work
   - Continuous testing

4. **Deployment** (Week 6)
   - Staging environment
   - Production setup
   - Go-live

---

**This refactor will transform QAMill from a feature-rich prototype into an enterprise-grade SaaS platform.** 🚀

Ready to proceed?
