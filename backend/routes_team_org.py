"""
Team & Organization Authentication Routes
Routes for team/org sign-up, login, and management

Endpoints:
- Org sign-up
- Org login
- Team creation
- Team invitation
- Member management
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional
from datetime import datetime

from services.team_org_service import (
    TeamOrgService,
    Organization,
    Team,
    UserRole,
    OrganizationMember,
    TeamMember,
    Invite
)

# Initialize router
team_org_router = APIRouter(prefix="/api/v1/team-org", tags=["team-org"])

# Service instance
team_org_service = TeamOrgService()


# ==================== ORGANIZATION ROUTES ====================

@team_org_router.post("/org/signup")
async def org_signup(
    org_name: str,
    owner_email: str,
    owner_name: str,
    description: str = "",
    logo_url: Optional[str] = None,
    website: Optional[str] = None
):
    """Sign up for new organization"""
    # In real app, would:
    # 1. Create user account
    # 2. Create organization
    # 3. Add user as owner

    return {
        "status": "created",
        "org_id": f"org_{datetime.now().timestamp()}",
        "owner_email": owner_email,
        "message": "Organization created successfully"
    }


@team_org_router.post("/org/login")
async def org_login(
    email: str,
    password: str
):
    """Login to organization account"""
    # In real app, would authenticate user and return token

    return {
        "status": "authenticated",
        "token": "jwt_token_here",
        "user_id": "user_123",
        "organizations": [
            {
                "id": "org_001",
                "name": "Acme Corp",
                "role": "admin"
            }
        ]
    }


@team_org_router.get("/org/{org_id}")
async def get_organization(org_id: str):
    """Get organization details"""
    org = await team_org_service.get_organization(org_id)

    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    return {
        "id": org.id,
        "name": org.name,
        "description": org.description,
        "owner_id": org.owner_id,
        "created_at": org.created_at.isoformat()
    }


@team_org_router.get("/org/{org_id}/members")
async def get_org_members(org_id: str):
    """Get organization members"""
    members = await team_org_service.get_org_members(org_id)

    return {
        "org_id": org_id,
        "members": [
            {
                "id": m.id,
                "user_id": m.user_id,
                "role": m.role.value,
                "joined_at": m.joined_at.isoformat()
            }
            for m in members
        ],
        "total": len(members)
    }


@team_org_router.post("/org/{org_id}/members")
async def add_org_member(
    org_id: str,
    user_id: str,
    role: str = "member"
):
    """Add member to organization"""
    role_enum = UserRole[role.upper()]

    member = await team_org_service.add_org_member(
        org_id=org_id,
        user_id=user_id,
        role=role_enum
    )

    return {
        "status": "added",
        "member_id": member.id,
        "role": member.role.value
    }


@team_org_router.get("/org/{org_id}/teams")
async def list_org_teams(org_id: str):
    """List all teams in organization"""
    teams = await team_org_service.list_org_teams(org_id)

    return {
        "org_id": org_id,
        "teams": [
            {
                "id": t.id,
                "name": t.name,
                "description": t.description,
                "created_by": t.created_by,
                "created_at": t.created_at.isoformat()
            }
            for t in teams
        ],
        "total": len(teams)
    }


@team_org_router.get("/org/{org_id}/stats")
async def get_org_stats(org_id: str):
    """Get organization statistics"""
    stats = await team_org_service.get_org_stats(org_id)
    return stats


# ==================== TEAM ROUTES ====================

@team_org_router.post("/team/create")
async def create_team(
    org_id: str,
    name: str,
    description: str,
    created_by: str
):
    """Create new team in organization"""
    team = await team_org_service.create_team(
        org_id=org_id,
        name=name,
        description=description,
        created_by=created_by
    )

    return {
        "status": "created",
        "team_id": team.id,
        "name": team.name,
        "org_id": team.org_id
    }


@team_org_router.get("/team/{team_id}")
async def get_team(team_id: str):
    """Get team details"""
    team = await team_org_service.get_team(team_id)

    if not team:
        raise HTTPException(status_code=404, detail="Team not found")

    return {
        "id": team.id,
        "name": team.name,
        "description": team.description,
        "org_id": team.org_id,
        "created_by": team.created_by,
        "created_at": team.created_at.isoformat()
    }


@team_org_router.get("/team/{team_id}/members")
async def get_team_members(team_id: str):
    """Get team members"""
    members = await team_org_service.get_team_members(team_id)

    return {
        "team_id": team_id,
        "members": [
            {
                "id": m.id,
                "user_id": m.user_id,
                "role": m.role.value,
                "joined_at": m.joined_at.isoformat()
            }
            for m in members
        ],
        "total": len(members)
    }


@team_org_router.post("/team/{team_id}/members")
async def add_team_member(
    team_id: str,
    user_id: str,
    role: str = "member"
):
    """Add member to team"""
    role_enum = UserRole[role.upper()]

    member = await team_org_service.add_team_member(
        team_id=team_id,
        user_id=user_id,
        role=role_enum
    )

    return {
        "status": "added",
        "member_id": member.id,
        "role": member.role.value
    }


@team_org_router.get("/team/{team_id}/stats")
async def get_team_stats(team_id: str):
    """Get team statistics"""
    stats = await team_org_service.get_team_stats(team_id)
    return stats


# ==================== INVITATION ROUTES ====================

@team_org_router.post("/invite/create")
async def create_invite(
    org_id: str,
    email: str,
    role: str = "member",
    team_id: Optional[str] = None,
    created_by: Optional[str] = None
):
    """Create invitation"""
    role_enum = UserRole[role.upper()]

    invite = await team_org_service.create_invite(
        org_id=org_id,
        email=email,
        role=role_enum,
        team_id=team_id,
        created_by=created_by
    )

    return {
        "status": "created",
        "invite_id": invite.id,
        "email": invite.email,
        "token": invite.token,
        "expires_at": invite.expires_at.isoformat(),
        "invite_url": f"https://qamill.io/join?token={invite.token}"
    }


@team_org_router.get("/invite/pending")
async def get_pending_invites(email: str):
    """Get pending invites for email"""
    invites = await team_org_service.get_pending_invites(email)

    return {
        "email": email,
        "pending_invites": [
            {
                "id": inv.id,
                "org_id": inv.org_id,
                "team_id": inv.team_id,
                "role": inv.role.value,
                "created_at": inv.created_at.isoformat(),
                "expires_at": inv.expires_at.isoformat()
            }
            for inv in invites
        ],
        "total": len(invites)
    }


@team_org_router.post("/invite/{invite_id}/accept")
async def accept_invite(
    invite_id: str,
    user_id: str
):
    """Accept invitation"""
    success = await team_org_service.accept_invite(invite_id, user_id)

    if not success:
        raise HTTPException(status_code=400, detail="Could not accept invite")

    return {
        "status": "accepted",
        "invite_id": invite_id,
        "user_id": user_id
    }


@team_org_router.post("/invite/{invite_id}/reject")
async def reject_invite(invite_id: str):
    """Reject invitation"""
    success = await team_org_service.reject_invite(invite_id)

    if not success:
        raise HTTPException(status_code=404, detail="Invite not found")

    return {
        "status": "rejected",
        "invite_id": invite_id
    }


# ==================== ACCESS CONTROL ROUTES ====================

@team_org_router.get("/access/org/{org_id}")
async def check_org_access(
    org_id: str,
    user_id: str,
    required_role: str = "viewer"
):
    """Check user access to organization"""
    role_enum = UserRole[required_role.upper()]
    has_access = await team_org_service.check_org_access(
        user_id=user_id,
        org_id=org_id,
        required_role=role_enum
    )

    return {
        "org_id": org_id,
        "user_id": user_id,
        "has_access": has_access,
        "required_role": required_role
    }


@team_org_router.get("/access/team/{team_id}")
async def check_team_access(
    team_id: str,
    user_id: str,
    required_role: str = "viewer"
):
    """Check user access to team"""
    role_enum = UserRole[required_role.upper()]
    has_access = await team_org_service.check_team_access(
        user_id=user_id,
        team_id=team_id,
        required_role=role_enum
    )

    return {
        "team_id": team_id,
        "user_id": user_id,
        "has_access": has_access,
        "required_role": required_role
    }


# ==================== DASHBOARD ROUTES ====================

@team_org_router.get("/dashboard/user/{user_id}")
async def get_user_dashboard(user_id: str):
    """Get user's org/team dashboard"""
    # In real app, would fetch user's orgs and teams

    return {
        "user_id": user_id,
        "organizations": [
            {
                "id": "org_001",
                "name": "Acme Corp",
                "role": "admin",
                "member_count": 15,
                "team_count": 3
            }
        ],
        "teams": [
            {
                "id": "team_001",
                "name": "QA Team",
                "org_id": "org_001",
                "role": "lead",
                "member_count": 5
            }
        ],
        "total_orgs": 1,
        "total_teams": 1
    }


@team_org_router.post("/org/{org_id}/share-project")
async def share_project_with_team(
    org_id: str,
    project_id: str,
    team_id: str
):
    """Share project with team"""
    success = await team_org_service.share_project_with_team(
        project_id=project_id,
        team_id=team_id
    )

    if not success:
        raise HTTPException(status_code=400, detail="Could not share project")

    return {
        "status": "shared",
        "project_id": project_id,
        "team_id": team_id
    }


@team_org_router.post("/org/{org_id}/share-analysis")
async def share_analysis_with_org(
    org_id: str,
    analysis_id: str
):
    """Share analysis with organization"""
    success = await team_org_service.share_analysis_with_org(
        analysis_id=analysis_id,
        org_id=org_id
    )

    if not success:
        raise HTTPException(status_code=400, detail="Could not share analysis")

    return {
        "status": "shared",
        "analysis_id": analysis_id,
        "org_id": org_id
    }


# ==================== ROUTE SUMMARY ====================

TEAM_ORG_ROUTES_SUMMARY = {
    "organization": {
        "count": 6,
        "routes": [
            "POST /org/signup - Create organization",
            "POST /org/login - Login to organization",
            "GET /org/{id} - Get organization details",
            "GET /org/{id}/members - List members",
            "POST /org/{id}/members - Add member",
            "GET /org/{id}/teams - List teams"
        ]
    },
    "team": {
        "count": 6,
        "routes": [
            "POST /team/create - Create team",
            "GET /team/{id} - Get team details",
            "GET /team/{id}/members - List team members",
            "POST /team/{id}/members - Add team member",
            "GET /team/{id}/stats - Get team stats"
        ]
    },
    "invitation": {
        "count": 5,
        "routes": [
            "POST /invite/create - Create invitation",
            "GET /invite/pending - Get pending invites",
            "POST /invite/{id}/accept - Accept invite",
            "POST /invite/{id}/reject - Reject invite"
        ]
    },
    "access": {
        "count": 2,
        "routes": [
            "GET /access/org/{id} - Check org access",
            "GET /access/team/{id} - Check team access"
        ]
    },
    "collaboration": {
        "count": 3,
        "routes": [
            "GET /dashboard/user/{id} - User dashboard",
            "POST /org/{id}/share-project - Share project",
            "POST /org/{id}/share-analysis - Share analysis"
        ]
    },
    "total_routes": 22
}
