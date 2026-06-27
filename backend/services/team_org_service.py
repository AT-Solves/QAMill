"""
Team & Organization Management Service
Enables team/organization sign-up, role-based access, and collaboration

Features:
- Organization creation and management
- Team creation within organizations
- Role-based access control (Admin, Lead, Member, Viewer)
- Invite system with email verification
- Team collaboration workspace
- Project sharing between teams
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import secrets


class UserRole(Enum):
    """User roles within organization/team"""
    ADMIN = "admin"  # Full access to org/team
    LEAD = "lead"  # Team lead, can manage team members
    MEMBER = "member"  # Full access to projects
    VIEWER = "viewer"  # Read-only access


class InviteStatus(Enum):
    """Status of team/org invitations"""
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    EXPIRED = "expired"


@dataclass
class Organization:
    """Organization entity"""
    id: str
    name: str
    description: str
    owner_id: str
    logo_url: Optional[str] = None
    website: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    settings: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Team:
    """Team entity within organization"""
    id: str
    org_id: str
    name: str
    description: str
    created_by: str
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    settings: Dict[str, Any] = field(default_factory=dict)


@dataclass
class OrganizationMember:
    """Organization member with role"""
    id: str
    org_id: str
    user_id: str
    role: UserRole
    joined_at: datetime = field(default_factory=datetime.now)
    invited_by: Optional[str] = None


@dataclass
class TeamMember:
    """Team member with role"""
    id: str
    team_id: str
    user_id: str
    role: UserRole
    joined_at: datetime = field(default_factory=datetime.now)
    invited_by: Optional[str] = None


@dataclass
class Invite:
    """Invitation to join organization/team"""
    id: str
    org_id: str
    team_id: Optional[str] = None
    email: str
    role: UserRole = UserRole.MEMBER
    status: InviteStatus = InviteStatus.PENDING
    token: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    expires_at: datetime = None
    created_by: Optional[str] = None


class TeamOrgService:
    """Service for managing teams and organizations"""

    def __init__(self):
        self.organizations: Dict[str, Organization] = {}
        self.teams: Dict[str, Team] = {}
        self.org_members: List[OrganizationMember] = []
        self.team_members: List[TeamMember] = []
        self.invites: List[Invite] = []
        self.id_counter = 0

    # ==================== ORGANIZATION MANAGEMENT ====================

    async def create_organization(
        self,
        name: str,
        description: str,
        owner_id: str,
        logo_url: Optional[str] = None,
        website: Optional[str] = None
    ) -> Organization:
        """Create new organization"""

        self.id_counter += 1
        org_id = f"org_{self.id_counter:04d}"

        org = Organization(
            id=org_id,
            name=name,
            description=description,
            owner_id=owner_id,
            logo_url=logo_url,
            website=website
        )

        self.organizations[org_id] = org

        # Add owner as admin
        await self.add_org_member(org_id, owner_id, UserRole.ADMIN, invited_by=owner_id)

        return org

    async def get_organization(self, org_id: str) -> Optional[Organization]:
        """Get organization by ID"""
        return self.organizations.get(org_id)

    async def list_user_organizations(self, user_id: str) -> List[Organization]:
        """List all organizations user is member of"""

        org_ids = [
            m.org_id for m in self.org_members
            if m.user_id == user_id
        ]

        return [self.organizations[oid] for oid in org_ids if oid in self.organizations]

    async def update_organization(
        self,
        org_id: str,
        **updates
    ) -> Optional[Organization]:
        """Update organization"""

        org = self.organizations.get(org_id)
        if not org:
            return None

        for key, value in updates.items():
            if hasattr(org, key):
                setattr(org, key, value)

        org.updated_at = datetime.now()
        return org

    async def delete_organization(self, org_id: str) -> bool:
        """Delete organization"""

        if org_id in self.organizations:
            del self.organizations[org_id]
            # TODO: Delete associated teams, members, projects
            return True
        return False

    # ==================== TEAM MANAGEMENT ====================

    async def create_team(
        self,
        org_id: str,
        name: str,
        description: str,
        created_by: str
    ) -> Team:
        """Create team within organization"""

        self.id_counter += 1
        team_id = f"team_{self.id_counter:04d}"

        team = Team(
            id=team_id,
            org_id=org_id,
            name=name,
            description=description,
            created_by=created_by
        )

        self.teams[team_id] = team

        # Add creator as lead
        await self.add_team_member(team_id, created_by, UserRole.LEAD, invited_by=created_by)

        return team

    async def get_team(self, team_id: str) -> Optional[Team]:
        """Get team by ID"""
        return self.teams.get(team_id)

    async def list_org_teams(self, org_id: str) -> List[Team]:
        """List all teams in organization"""

        return [
            team for team in self.teams.values()
            if team.org_id == org_id
        ]

    async def list_user_teams(self, user_id: str) -> List[Team]:
        """List all teams user is member of"""

        team_ids = [
            m.team_id for m in self.team_members
            if m.user_id == user_id
        ]

        return [self.teams[tid] for tid in team_ids if tid in self.teams]

    async def update_team(
        self,
        team_id: str,
        **updates
    ) -> Optional[Team]:
        """Update team"""

        team = self.teams.get(team_id)
        if not team:
            return None

        for key, value in updates.items():
            if hasattr(team, key):
                setattr(team, key, value)

        team.updated_at = datetime.now()
        return team

    async def delete_team(self, team_id: str) -> bool:
        """Delete team"""

        if team_id in self.teams:
            del self.teams[team_id]
            return True
        return False

    # ==================== MEMBERSHIP MANAGEMENT ====================

    async def add_org_member(
        self,
        org_id: str,
        user_id: str,
        role: UserRole = UserRole.MEMBER,
        invited_by: Optional[str] = None
    ) -> OrganizationMember:
        """Add member to organization"""

        self.id_counter += 1
        member_id = f"orgmem_{self.id_counter:04d}"

        member = OrganizationMember(
            id=member_id,
            org_id=org_id,
            user_id=user_id,
            role=role,
            invited_by=invited_by
        )

        self.org_members.append(member)
        return member

    async def add_team_member(
        self,
        team_id: str,
        user_id: str,
        role: UserRole = UserRole.MEMBER,
        invited_by: Optional[str] = None
    ) -> TeamMember:
        """Add member to team"""

        self.id_counter += 1
        member_id = f"team_mem_{self.id_counter:04d}"

        member = TeamMember(
            id=member_id,
            team_id=team_id,
            user_id=user_id,
            role=role,
            invited_by=invited_by
        )

        self.team_members.append(member)
        return member

    async def get_org_members(self, org_id: str) -> List[OrganizationMember]:
        """Get all members of organization"""

        return [m for m in self.org_members if m.org_id == org_id]

    async def get_team_members(self, team_id: str) -> List[TeamMember]:
        """Get all members of team"""

        return [m for m in self.team_members if m.team_id == team_id]

    async def update_member_role(
        self,
        member_id: str,
        new_role: UserRole,
        is_org_member: bool = True
    ) -> bool:
        """Update member role"""

        members = self.org_members if is_org_member else self.team_members

        for member in members:
            if member.id == member_id:
                member.role = new_role
                return True

        return False

    async def remove_member(
        self,
        member_id: str,
        is_org_member: bool = True
    ) -> bool:
        """Remove member from organization/team"""

        members = self.org_members if is_org_member else self.team_members

        for i, member in enumerate(members):
            if member.id == member_id:
                members.pop(i)
                return True

        return False

    # ==================== INVITATION SYSTEM ====================

    async def create_invite(
        self,
        org_id: str,
        email: str,
        role: UserRole = UserRole.MEMBER,
        created_by: str = None,
        team_id: Optional[str] = None
    ) -> Invite:
        """Create invitation"""

        self.id_counter += 1
        invite_id = f"inv_{self.id_counter:04d}"
        token = secrets.token_urlsafe(32)

        from datetime import timedelta
        expires_at = datetime.now() + timedelta(days=7)

        invite = Invite(
            id=invite_id,
            org_id=org_id,
            team_id=team_id,
            email=email,
            role=role,
            token=token,
            expires_at=expires_at,
            created_by=created_by
        )

        self.invites.append(invite)
        return invite

    async def get_pending_invites(self, email: str) -> List[Invite]:
        """Get pending invites for email"""

        return [
            inv for inv in self.invites
            if inv.email == email and inv.status == InviteStatus.PENDING
        ]

    async def accept_invite(
        self,
        invite_id: str,
        user_id: str
    ) -> bool:
        """Accept invitation"""

        for invite in self.invites:
            if invite.id == invite_id and invite.status == InviteStatus.PENDING:
                # Check if invite expired
                if datetime.now() > invite.expires_at:
                    invite.status = InviteStatus.EXPIRED
                    return False

                # Add user to org/team
                if invite.team_id:
                    await self.add_team_member(
                        invite.team_id,
                        user_id,
                        invite.role,
                        invited_by=invite.created_by
                    )
                else:
                    await self.add_org_member(
                        invite.org_id,
                        user_id,
                        invite.role,
                        invited_by=invite.created_by
                    )

                invite.status = InviteStatus.ACCEPTED
                return True

        return False

    async def reject_invite(self, invite_id: str) -> bool:
        """Reject invitation"""

        for invite in self.invites:
            if invite.id == invite_id:
                invite.status = InviteStatus.REJECTED
                return True

        return False

    # ==================== ACCESS CONTROL ====================

    async def check_org_access(
        self,
        user_id: str,
        org_id: str,
        required_role: UserRole = UserRole.VIEWER
    ) -> bool:
        """Check if user has access to organization"""

        member = None
        for m in self.org_members:
            if m.user_id == user_id and m.org_id == org_id:
                member = m
                break

        if not member:
            return False

        role_hierarchy = {
            UserRole.VIEWER: 1,
            UserRole.MEMBER: 2,
            UserRole.LEAD: 3,
            UserRole.ADMIN: 4
        }

        return role_hierarchy.get(member.role, 0) >= role_hierarchy.get(required_role, 0)

    async def check_team_access(
        self,
        user_id: str,
        team_id: str,
        required_role: UserRole = UserRole.VIEWER
    ) -> bool:
        """Check if user has access to team"""

        member = None
        for m in self.team_members:
            if m.user_id == user_id and m.team_id == team_id:
                member = m
                break

        if not member:
            return False

        role_hierarchy = {
            UserRole.VIEWER: 1,
            UserRole.MEMBER: 2,
            UserRole.LEAD: 3,
            UserRole.ADMIN: 4
        }

        return role_hierarchy.get(member.role, 0) >= role_hierarchy.get(required_role, 0)

    # ==================== WORKSPACE SHARING ====================

    async def share_project_with_team(
        self,
        project_id: str,
        team_id: str
    ) -> bool:
        """Share project with entire team"""

        team = self.teams.get(team_id)
        if not team:
            return False

        # TODO: Link project to team in database
        return True

    async def share_analysis_with_org(
        self,
        analysis_id: str,
        org_id: str
    ) -> bool:
        """Share analysis with entire organization"""

        org = self.organizations.get(org_id)
        if not org:
            return False

        # TODO: Link analysis to org with access control
        return True

    # ==================== REPORTING ====================

    async def get_org_stats(self, org_id: str) -> Dict[str, Any]:
        """Get organization statistics"""

        org = self.organizations.get(org_id)
        if not org:
            return {}

        members = await self.get_org_members(org_id)
        teams = await self.list_org_teams(org_id)

        return {
            "org_name": org.name,
            "member_count": len(members),
            "team_count": len(teams),
            "admin_count": sum(1 for m in members if m.role == UserRole.ADMIN),
            "lead_count": sum(1 for m in members if m.role == UserRole.LEAD),
            "member_count_role": sum(1 for m in members if m.role == UserRole.MEMBER),
            "viewer_count": sum(1 for m in members if m.role == UserRole.VIEWER)
        }

    async def get_team_stats(self, team_id: str) -> Dict[str, Any]:
        """Get team statistics"""

        team = self.teams.get(team_id)
        if not team:
            return {}

        members = await self.get_team_members(team_id)

        return {
            "team_name": team.name,
            "org_id": team.org_id,
            "member_count": len(members),
            "admin_count": sum(1 for m in members if m.role == UserRole.ADMIN),
            "lead_count": sum(1 for m in members if m.role == UserRole.LEAD),
            "member_count_role": sum(1 for m in members if m.role == UserRole.MEMBER),
            "viewer_count": sum(1 for m in members if m.role == UserRole.VIEWER)
        }
