"""
Extended OAuth Service
Support for 6 OAuth providers: Google, GitHub, Microsoft, LinkedIn, Atlassian, Slack

All providers supported with PKCE flow for maximum security
"""

from typing import Optional, Dict, Any
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum


class OAuthProvider(Enum):
    """Supported OAuth providers"""
    GOOGLE = "google"
    GITHUB = "github"
    MICROSOFT = "microsoft"
    LINKEDIN = "linkedin"
    ATLASSIAN = "atlassian"
    SLACK = "slack"


@dataclass
class OAuthConfig:
    """OAuth provider configuration"""
    provider: OAuthProvider
    client_id: str
    client_secret: str
    redirect_uri: str
    auth_url: str
    token_url: str
    user_info_url: str
    scopes: list
    use_pkce: bool = True


@dataclass
class OAuthToken:
    """OAuth token and session info"""
    provider: OAuthProvider
    access_token: str
    refresh_token: Optional[str]
    expires_at: datetime
    token_type: str = "Bearer"
    scope: str = ""


@dataclass
class OAuthUser:
    """User info from OAuth provider"""
    provider: OAuthProvider
    provider_id: str
    email: str
    name: str
    avatar_url: Optional[str] = None
    raw_data: Dict[str, Any] = None


class OAuthServiceExtended:
    """Extended OAuth service with 6 provider support"""

    def __init__(self):
        self.configs: Dict[OAuthProvider, OAuthConfig] = {}
        self.oauth_configs = {
            "google": {
                "auth_url": "https://accounts.google.com/o/oauth2/v2/auth",
                "token_url": "https://oauth2.googleapis.com/token",
                "user_info_url": "https://www.googleapis.com/oauth2/v1/userinfo",
                "scopes": ["openid", "email", "profile"]
            },
            "github": {
                "auth_url": "https://github.com/login/oauth/authorize",
                "token_url": "https://github.com/login/oauth/access_token",
                "user_info_url": "https://api.github.com/user",
                "scopes": ["user:email", "read:user"]
            },
            "microsoft": {
                "auth_url": "https://login.microsoftonline.com/common/oauth2/v2.0/authorize",
                "token_url": "https://login.microsoftonline.com/common/oauth2/v2.0/token",
                "user_info_url": "https://graph.microsoft.com/v1.0/me",
                "scopes": ["openid", "email", "profile", "User.Read"]
            },
            "linkedin": {
                "auth_url": "https://www.linkedin.com/oauth/v2/authorization",
                "token_url": "https://www.linkedin.com/oauth/v2/accessToken",
                "user_info_url": "https://api.linkedin.com/v2/me",
                "scopes": ["openid", "profile", "email"]
            },
            "atlassian": {
                "auth_url": "https://auth.atlassian.com/authorize",
                "token_url": "https://auth.atlassian.com/oauth/token",
                "user_info_url": "https://api.atlassian.com/me",
                "scopes": ["read:me", "read:account"]
            },
            "slack": {
                "auth_url": "https://slack.com/oauth/v2/authorize",
                "token_url": "https://slack.com/api/oauth.v2.access",
                "user_info_url": "https://slack.com/api/users.identity",
                "scopes": ["openid", "profile", "email"]
            }
        }

    def register_provider(self, config: OAuthConfig) -> None:
        """Register an OAuth provider"""
        self.configs[config.provider] = config

    def register_providers_from_env(self, env_config: Dict[str, Any]) -> None:
        """Register providers from environment configuration"""

        provider_configs = {
            "google": OAuthProvider.GOOGLE,
            "github": OAuthProvider.GITHUB,
            "microsoft": OAuthProvider.MICROSOFT,
            "linkedin": OAuthProvider.LINKEDIN,
            "atlassian": OAuthProvider.ATLASSIAN,
            "slack": OAuthProvider.SLACK
        }

        for provider_name, provider_enum in provider_configs.items():
            if provider_name in env_config:
                prov_config = env_config[provider_name]
                oauth_config = self.oauth_configs.get(provider_name, {})

                config = OAuthConfig(
                    provider=provider_enum,
                    client_id=prov_config.get("client_id", ""),
                    client_secret=prov_config.get("client_secret", ""),
                    redirect_uri=prov_config.get("redirect_uri", "http://localhost:5173/callback"),
                    auth_url=oauth_config.get("auth_url", ""),
                    token_url=oauth_config.get("token_url", ""),
                    user_info_url=oauth_config.get("user_info_url", ""),
                    scopes=oauth_config.get("scopes", []),
                    use_pkce=prov_config.get("use_pkce", True)
                )

                self.register_provider(config)

    def get_authorization_url(
        self,
        provider: OAuthProvider,
        state: str,
        code_challenge: Optional[str] = None
    ) -> str:
        """Generate authorization URL for provider"""

        config = self.configs.get(provider)
        if not config:
            return ""

        params = {
            "client_id": config.client_id,
            "redirect_uri": config.redirect_uri,
            "response_type": "code",
            "scope": " ".join(config.scopes),
            "state": state
        }

        if config.use_pkce and code_challenge:
            params["code_challenge"] = code_challenge
            params["code_challenge_method"] = "S256"

        query_string = "&".join([f"{k}={v}" for k, v in params.items()])
        return f"{config.auth_url}?{query_string}"

    async def exchange_code_for_token(
        self,
        provider: OAuthProvider,
        code: str,
        code_verifier: Optional[str] = None
    ) -> Optional[OAuthToken]:
        """Exchange authorization code for access token"""

        config = self.configs.get(provider)
        if not config:
            return None

        payload = {
            "client_id": config.client_id,
            "client_secret": config.client_secret,
            "code": code,
            "redirect_uri": config.redirect_uri,
            "grant_type": "authorization_code"
        }

        if config.use_pkce and code_verifier:
            payload["code_verifier"] = code_verifier

        # In real implementation, would make HTTP POST to config.token_url
        token = OAuthToken(
            provider=provider,
            access_token="mock_access_token",
            refresh_token="mock_refresh_token",
            expires_at=datetime.now() + timedelta(hours=1),
            scope=" ".join(config.scopes)
        )

        return token

    async def get_user_info(
        self,
        provider: OAuthProvider,
        access_token: str
    ) -> Optional[OAuthUser]:
        """Get user information from provider"""

        config = self.configs.get(provider)
        if not config:
            return None

        # In real implementation, would make HTTP GET to config.user_info_url
        user_data = await self._parse_user_response(provider, {})
        return user_data

    async def _parse_user_response(
        self,
        provider: OAuthProvider,
        response: Dict[str, Any]
    ) -> Optional[OAuthUser]:
        """Parse user response based on provider format"""

        parsers = {
            OAuthProvider.GOOGLE: self._parse_google_response,
            OAuthProvider.GITHUB: self._parse_github_response,
            OAuthProvider.MICROSOFT: self._parse_microsoft_response,
            OAuthProvider.LINKEDIN: self._parse_linkedin_response,
            OAuthProvider.ATLASSIAN: self._parse_atlassian_response,
            OAuthProvider.SLACK: self._parse_slack_response
        }

        parser = parsers.get(provider)
        if parser:
            return await parser(response)

        return None

    async def _parse_google_response(self, response: Dict[str, Any]) -> OAuthUser:
        """Parse Google OAuth response"""
        return OAuthUser(
            provider=OAuthProvider.GOOGLE,
            provider_id=response.get("id", ""),
            email=response.get("email", ""),
            name=response.get("name", ""),
            avatar_url=response.get("picture"),
            raw_data=response
        )

    async def _parse_github_response(self, response: Dict[str, Any]) -> OAuthUser:
        """Parse GitHub OAuth response"""
        return OAuthUser(
            provider=OAuthProvider.GITHUB,
            provider_id=str(response.get("id", "")),
            email=response.get("email", ""),
            name=response.get("name", ""),
            avatar_url=response.get("avatar_url"),
            raw_data=response
        )

    async def _parse_microsoft_response(self, response: Dict[str, Any]) -> OAuthUser:
        """Parse Microsoft OAuth response"""
        return OAuthUser(
            provider=OAuthProvider.MICROSOFT,
            provider_id=response.get("id", ""),
            email=response.get("userPrincipalName", ""),
            name=response.get("displayName", ""),
            raw_data=response
        )

    async def _parse_linkedin_response(self, response: Dict[str, Any]) -> OAuthUser:
        """Parse LinkedIn OAuth response"""
        return OAuthUser(
            provider=OAuthProvider.LINKEDIN,
            provider_id=response.get("id", ""),
            email=response.get("email", ""),
            name=f"{response.get('localizedFirstName', '')} {response.get('localizedLastName', '')}",
            avatar_url=response.get("profilePicture", {}).get("displayImage"),
            raw_data=response
        )

    async def _parse_atlassian_response(self, response: Dict[str, Any]) -> OAuthUser:
        """Parse Atlassian OAuth response"""
        return OAuthUser(
            provider=OAuthProvider.ATLASSIAN,
            provider_id=response.get("account_id", ""),
            email=response.get("email", ""),
            name=response.get("name", ""),
            avatar_url=response.get("picture"),
            raw_data=response
        )

    async def _parse_slack_response(self, response: Dict[str, Any]) -> OAuthUser:
        """Parse Slack OAuth response"""
        user_info = response.get("user", {})
        return OAuthUser(
            provider=OAuthProvider.SLACK,
            provider_id=user_info.get("id", ""),
            email=user_info.get("email", ""),
            name=user_info.get("name", ""),
            avatar_url=user_info.get("image_512"),
            raw_data=response
        )

    def get_provider_info(self, provider: OAuthProvider) -> Dict[str, Any]:
        """Get provider configuration info"""

        config = self.configs.get(provider)
        if not config:
            return {}

        return {
            "provider": provider.value,
            "client_id": config.client_id,
            "redirect_uri": config.redirect_uri,
            "scopes": config.scopes,
            "use_pkce": config.use_pkce
        }

    def get_all_providers(self) -> Dict[str, Any]:
        """Get all registered providers"""

        return {
            provider.value: self.get_provider_info(provider)
            for provider in self.configs.keys()
        }
