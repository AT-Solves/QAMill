"""
auth_manager.py
OAuth 2.0 PKCE authentication for QAMill.

Providers:
  Social / Professional : Google, Microsoft, LinkedIn
  Developer platforms   : GitHub, Atlassian (Jira/Confluence), Slack
  LLM providers         : Claude, GPT-4o, Grok, Ollama

OAuth tokens → ~/.qamill/auth.json (local only, never transmitted).
When Google / Microsoft are connected, reports are sent via their
native APIs (Gmail / Graph) — no App Password required.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional
from urllib.parse import urlencode

import httpx

# ── Storage path ─────────────────────────────────────────────────────────────

STORE_PATH    = Path.home() / ".qamill" / "auth.json"
CALLBACK_BASE = "http://localhost:8765"

# ── OAuth provider registry ───────────────────────────────────────────────────

OAUTH_PROVIDERS: dict[str, dict] = {
    # ── Social / Professional ────────────────────────────────────────────
    "google": {
        "label":       "Google",
        "group":       "social",
        "color":       "#EA4335",
        "bg":          "#fff",
        "text":        "#3c4043",
        "auth_url":    "https://accounts.google.com/o/oauth2/v2/auth",
        "token_url":   "https://oauth2.googleapis.com/token",
        "info_url":    "https://www.googleapis.com/oauth2/v3/userinfo",
        "scope":       "openid email profile https://www.googleapis.com/auth/gmail.send",
        "pkce":        True,
        "can_email":   True,     # can send via Gmail API
        "access_type": "offline",
        "extra_params": {"prompt": "consent"},   # force consent screen so gmail.send is always explicitly granted
        "env_id":      "QAMILL_GOOGLE_CLIENT_ID",
        "env_secret":  "QAMILL_GOOGLE_CLIENT_SECRET",
    },
    "microsoft": {
        "label":       "Microsoft",
        "group":       "social",
        "color":       "#00A4EF",
        "bg":          "#2f2f2f",
        "text":        "#fff",
        "auth_url":    "https://login.microsoftonline.com/common/oauth2/v2.0/authorize",
        "token_url":   "https://login.microsoftonline.com/common/oauth2/v2.0/token",
        "info_url":    "https://graph.microsoft.com/v1.0/me",
        "scope":       "openid email profile User.Read Mail.Send offline_access",
        "pkce":        True,
        "can_email":   True,     # can send via Graph API
        "extra_params": {"prompt": "select_account"},
        "env_id":      "QAMILL_MICROSOFT_CLIENT_ID",
        "env_secret":  "QAMILL_MICROSOFT_CLIENT_SECRET",
    },
    "linkedin": {
        "label":       "LinkedIn",
        "group":       "social",
        "color":       "#fff",
        "bg":          "#0A66C2",
        "text":        "#fff",
        "auth_url":    "https://www.linkedin.com/oauth/v2/authorization",
        "token_url":   "https://www.linkedin.com/oauth/v2/accessToken",
        "info_url":    "https://api.linkedin.com/v2/me",
        "scope":       "r_liteprofile r_emailaddress",
        "pkce":        False,
        "can_email":   False,
        "env_id":      "QAMILL_LINKEDIN_CLIENT_ID",
        "env_secret":  "QAMILL_LINKEDIN_CLIENT_SECRET",
    },
    # ── Developer platforms ──────────────────────────────────────────────
    "github": {
        "label":       "GitHub",
        "group":       "dev",
        "color":       "#fff",
        "bg":          "#24292e",
        "text":        "#fff",
        "auth_url":    "https://github.com/login/oauth/authorize",
        "token_url":   "https://github.com/login/oauth/access_token",
        "info_url":    "https://api.github.com/user",
        "scope":       "read:user user:email",
        "pkce":        False,   # GitHub does not support PKCE
        "can_email":   False,
        "env_id":      "QAMILL_GITHUB_CLIENT_ID",
        "env_secret":  "QAMILL_GITHUB_CLIENT_SECRET",
    },
    "atlassian": {
        "label":       "Atlassian",
        "group":       "dev",
        "color":       "#fff",
        "bg":          "#0052CC",
        "text":        "#fff",
        "auth_url":    "https://auth.atlassian.com/authorize",
        "token_url":   "https://auth.atlassian.com/oauth/token",
        "info_url":    "https://api.atlassian.com/me",
        "scope":       "read:me offline_access",
        "pkce":        True,
        "can_email":   False,
        "extra_params": {"audience": "api.atlassian.com", "prompt": "consent"},
        "env_id":      "QAMILL_ATLASSIAN_CLIENT_ID",
        "env_secret":  "QAMILL_ATLASSIAN_CLIENT_SECRET",
    },
    "slack": {
        "label":       "Slack",
        "group":       "dev",
        "color":       "#fff",
        "bg":          "#4A154B",
        "text":        "#fff",
        "auth_url":    "https://slack.com/oauth/v2/authorize",
        "token_url":   "https://slack.com/api/oauth.v2.access",
        "info_url":    "https://slack.com/api/users.identity",
        "scope":       "identity.basic identity.email identity.avatar",
        "pkce":        False,
        "can_email":   False,
        "env_id":      "QAMILL_SLACK_CLIENT_ID",
        "env_secret":  "QAMILL_SLACK_CLIENT_SECRET",
    },
}

# ── LLM provider registry ─────────────────────────────────────────────────────

LLM_PROVIDERS: dict[str, dict] = {
    "claude": {
        "label":       "Claude",
        "sublabel":    "Anthropic",
        "color":       "#D4A574",
        "bg":          "#2d1f0e",
        "validate_url": "https://api.anthropic.com/v1/messages",
        "validate_method": "POST",
        "validate_body": {"model": "claude-haiku-4-5", "max_tokens": 1,
                          "messages": [{"role": "user", "content": "hi"}]},
        "ok_codes":    {200, 400},   # 400 = bad request but auth succeeded
        "auth_header": lambda k: {"x-api-key": k, "anthropic-version": "2023-06-01",
                                   "content-type": "application/json"},
        "key_env":     "ANTHROPIC_API_KEY",
        "key_placeholder": "sk-ant-api03-...",
    },
    "gpt": {
        "label":       "GPT-4o",
        "sublabel":    "OpenAI",
        "color":       "#10A37F",
        "bg":          "#0a2a20",
        "validate_url": "https://api.openai.com/v1/models",
        "validate_method": "GET",
        "validate_body": None,
        "ok_codes":    {200},
        "auth_header": lambda k: {"Authorization": f"Bearer {k}"},
        "key_env":     "OPENAI_API_KEY",
        "key_placeholder": "sk-proj-...",
    },
    "grok": {
        "label":       "Grok",
        "sublabel":    "xAI",
        "color":       "#1DA1F2",
        "bg":          "#0a1a2a",
        "validate_url": "https://api.x.ai/v1/models",
        "validate_method": "GET",
        "validate_body": None,
        "ok_codes":    {200},
        "auth_header": lambda k: {"Authorization": f"Bearer {k}"},
        "key_env":     "XAI_API_KEY",
        "key_placeholder": "xai-...",
    },
    "ollama": {
        "label":       "Ollama",
        "sublabel":    "Local",
        "color":       "#9B59B6",
        "bg":          "#1a0a2a",
        "validate_url": "http://localhost:11434/api/tags",
        "validate_method": "GET",
        "validate_body": None,
        "ok_codes":    {200},
        "auth_header": lambda k: {},
        "key_env":     "",
        "key_placeholder": "No key needed",
    },
}


# ── File security helper ──────────────────────────────────────────────────────

def _secure_file(path: Path) -> None:
    """
    Restrict path to the current user only.
    Unix  : chmod 600 (owner read/write, no group/other).
    Windows: icacls — remove inherited ACEs, grant current user Full Control only.
    Both paths are best-effort; failures are silently ignored so a permissions
    error never prevents the token from being written.
    """
    if sys.platform == "win32":
        try:
            username = os.environ.get("USERNAME", "")
            if username:
                subprocess.run(
                    ["icacls", str(path),
                     "/inheritance:r",          # remove inherited permissions
                     "/grant:r", f"{username}:(F)"],  # current user: Full Control
                    capture_output=True, check=False,
                )
        except Exception:
            pass
    else:
        try:
            path.chmod(0o600)
        except Exception:
            pass


# ── Auth manager ──────────────────────────────────────────────────────────────

class AuthManager:
    """PKCE OAuth + LLM key manager. Single instance per process."""

    def __init__(self) -> None:
        STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
        # In-memory pending states: {state: {provider, code_verifier, expires}}
        self._pending: dict[str, dict] = {}

    # ── Store helpers ────────────────────────────────────────────────────

    def _load(self) -> dict:
        try:
            return json.loads(STORE_PATH.read_text(encoding="utf-8"))
        except Exception:
            return {}

    def _save(self, data: dict) -> None:
        STORE_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")
        _secure_file(STORE_PATH)

    def _store_get(self, *path: str, default=None):
        node = self._load()
        for k in path:
            if not isinstance(node, dict) or k not in node:
                return default
            node = node[k]
        return node

    def _store_set(self, *path: str, value) -> None:
        data = self._load()
        node = data
        for k in path[:-1]:
            node = node.setdefault(k, {})
        node[path[-1]] = value
        self._save(data)

    def _store_del(self, *path: str) -> None:
        data = self._load()
        node = data
        for k in path[:-1]:
            if not isinstance(node, dict) or k not in node:
                return
            node = node[k]
        if isinstance(node, dict):
            node.pop(path[-1], None)
        self._save(data)

    # ── PKCE ────────────────────────────────────────────────────────────

    @staticmethod
    def _pkce() -> tuple[str, str]:
        verifier  = base64.urlsafe_b64encode(secrets.token_bytes(40)).rstrip(b"=").decode()
        challenge = base64.urlsafe_b64encode(
            hashlib.sha256(verifier.encode()).digest()
        ).rstrip(b"=").decode()
        return verifier, challenge

    # ── OAuth flow ───────────────────────────────────────────────────────

    # ── OAuth client credential storage ──────────────────────────────────

    def store_oauth_client(self, provider: str, client_id: str, client_secret: str) -> None:
        """Store OAuth app credentials (client_id + secret) locally."""
        self._store_set("oauth_config", provider, value={
            "client_id":     client_id.strip(),
            "client_secret": client_secret.strip(),
        })

    def _get_client_id(self, provider: str) -> str:
        """Return client_id: env var first, then stored config."""
        cfg     = OAUTH_PROVIDERS.get(provider, {})
        env_val = os.getenv(cfg.get("env_id", ""), "")
        return env_val or self._store_get("oauth_config", provider, "client_id") or ""

    def _get_client_secret(self, provider: str) -> str:
        cfg     = OAUTH_PROVIDERS.get(provider, {})
        env_val = os.getenv(cfg.get("env_secret", ""), "")
        return env_val or self._store_get("oauth_config", provider, "client_secret") or ""

    def provider_configured(self, provider: str) -> bool:
        return bool(self._get_client_id(provider))

    def get_authorization_url(self, provider: str) -> str:
        cfg = OAUTH_PROVIDERS.get(provider)
        if not cfg:
            raise KeyError(f"Unknown provider: {provider}")
        client_id = self._get_client_id(provider)
        if not client_id:
            raise ValueError(
                f"OAuth is not configured for {cfg['label']}. "
                f"Click Setup in the QAMill login panel to enter your Client ID and Secret."
            )
        state = secrets.token_urlsafe(20)
        params: dict[str, str] = {
            "client_id":     client_id,
            "redirect_uri":  f"{CALLBACK_BASE}/auth/callback/{provider}",
            "response_type": "code",
            "scope":         cfg["scope"],
            "state":         state,
        }
        if cfg.get("access_type"):
            params["access_type"] = cfg["access_type"]
        params.update(cfg.get("extra_params", {}))

        entry: dict = {"provider": provider, "code_verifier": None,
                       "expires": time.time() + 600}
        if cfg.get("pkce"):
            verifier, challenge = self._pkce()
            entry["code_verifier"] = verifier
            params["code_challenge"]        = challenge
            params["code_challenge_method"] = "S256"

        self._pending[state] = entry
        return cfg["auth_url"] + "?" + urlencode(params)

    async def handle_callback(self, provider: str, code: str, state: str) -> dict:
        pending = self._pending.pop(state, None)
        if not pending or pending["provider"] != provider:
            raise ValueError("Invalid or expired OAuth state — please try again")
        if time.time() > pending["expires"]:
            raise ValueError("OAuth session expired — please try again")

        cfg           = OAUTH_PROVIDERS[provider]
        client_id     = self._get_client_id(provider)
        client_secret = self._get_client_secret(provider)

        body: dict = {
            "grant_type":   "authorization_code",
            "code":         code,
            "redirect_uri": f"{CALLBACK_BASE}/auth/callback/{provider}",
            "client_id":    client_id,
            "client_secret": client_secret,
        }
        if pending["code_verifier"]:
            body["code_verifier"] = pending["code_verifier"]

        extra_headers: dict = {}
        if provider == "github":
            extra_headers["Accept"] = "application/json"
        # Slack uses form body, not JSON
        post_kw = {"data": body, "headers": extra_headers}

        async with httpx.AsyncClient(timeout=20) as c:
            r = await c.post(cfg["token_url"], **post_kw)
            r.raise_for_status()
            tokens = r.json()

        access_token  = tokens.get("access_token", "")
        refresh_token = tokens.get("refresh_token", "")
        expires_in    = int(tokens.get("expires_in", 3600))

        profile = await self._fetch_profile(provider, access_token, tokens)
        entry = {
            "provider":      provider,
            "access_token":  access_token,
            "refresh_token": refresh_token,
            "expires_at":    int(time.time()) + expires_in,
            "email":         profile.get("email", ""),
            "name":          profile.get("name", ""),
            "picture":       profile.get("picture", ""),
            "workspace":     profile.get("workspace", ""),
            "connected_at":  int(time.time()),
        }
        self._store_set("oauth", provider, value=entry)

        # ── Auto-create / link a QAMill user account from this OAuth identity ──
        if profile.get("email"):
            self._upsert_oauth_user(provider, profile)
            self._set_session(profile["email"])

        return entry

    async def _fetch_profile(self, provider: str, token: str, raw_tokens: dict) -> dict:
        cfg = OAUTH_PROVIDERS[provider]

        if provider == "slack":
            # Slack identity uses bot token from authed_user
            user_token = raw_tokens.get("authed_user", {}).get("access_token", token)
            async with httpx.AsyncClient(timeout=10) as c:
                r = await c.get(cfg["info_url"],
                                headers={"Authorization": f"Bearer {user_token}"})
                r.raise_for_status()
                d = r.json()
            workspace = raw_tokens.get("team", {}).get("name", "")
            user_info = d.get("user", {})
            return {
                "name":      user_info.get("name", ""),
                "email":     user_info.get("email", ""),
                "picture":   user_info.get("image_72", ""),
                "workspace": workspace,
            }

        headers = {"Authorization": f"Bearer {token}"}
        if provider == "github":
            headers["Accept"] = "application/vnd.github.v3+json"

        async with httpx.AsyncClient(timeout=10) as c:
            r = await c.get(cfg["info_url"], headers=headers)
            r.raise_for_status()
            d = r.json()

        if provider == "github":
            email = d.get("email", "")
            if not email:
                async with httpx.AsyncClient(timeout=10) as c2:
                    re = await c2.get("https://api.github.com/user/emails",
                                      headers=headers)
                    if re.status_code == 200:
                        primary = next((e for e in re.json() if e.get("primary")), None)
                        if primary:
                            email = primary.get("email", "")
            return {"email": email, "name": d.get("name") or d.get("login", ""),
                    "picture": d.get("avatar_url", "")}

        if provider == "microsoft":
            return {"email": d.get("mail") or d.get("userPrincipalName", ""),
                    "name": d.get("displayName", ""), "picture": ""}

        if provider == "linkedin":
            first = d.get("localizedFirstName", "")
            last  = d.get("localizedLastName", "")
            # Fetch primary email separately
            async with httpx.AsyncClient(timeout=10) as c3:
                re3 = await c3.get(
                    "https://api.linkedin.com/v2/emailAddress?q=members&projection=(elements*(handle~))",
                    headers=headers)
                email = ""
                if re3.status_code == 200:
                    elems = re3.json().get("elements", [])
                    if elems:
                        email = elems[0].get("handle~", {}).get("emailAddress", "")
            return {"email": email, "name": f"{first} {last}".strip(), "picture": ""}

        if provider == "atlassian":
            return {"email": d.get("email", ""), "name": d.get("displayName", d.get("name", "")),
                    "picture": d.get("picture", d.get("avatarUrls", {}).get("48x48", ""))}

        # Google
        return {"email": d.get("email", ""), "name": d.get("name", ""),
                "picture": d.get("picture", "")}

    # ── Status queries ───────────────────────────────────────────────────

    def get_connected_providers(self) -> list[dict]:
        data = self._load()
        result = []
        for p, entry in data.get("oauth", {}).items():
            cfg = OAUTH_PROVIDERS.get(p, {})
            result.append({
                "provider":    p,
                "label":       cfg.get("label", p),
                "group":       cfg.get("group", "social"),
                "email":       entry.get("email", ""),
                "name":        entry.get("name", ""),
                "picture":     entry.get("picture", ""),
                "workspace":   entry.get("workspace", ""),
                "can_email":   cfg.get("can_email", False),
                "expires_at":  entry.get("expires_at", 0),
                "connected_at": entry.get("connected_at", 0),
            })
        return result

    def get_primary_identity(self) -> Optional[dict]:
        """Best identity for pre-filling sender: first email-capable, else first connected."""
        connected = self.get_connected_providers()
        for c in connected:
            if c.get("can_email"):
                return c
        return connected[0] if connected else None

    def get_oauth_entry(self, provider: str) -> Optional[dict]:
        return self._store_get("oauth", provider)

    def logout(self, provider: str) -> None:
        self._store_del("oauth", provider)

    def logout_all(self) -> None:
        data = self._load()
        data.pop("oauth", None)
        self._save(data)

    # ── User accounts (sign up / sign in / sign out / session) ────────────
    #
    # Storage layout in ~/.qamill/auth.json:
    #   "users":   { "<email>": {email, name, picture, auth_type,
    #                            pw_hash, pw_salt, providers[], created_at} }
    #   "session": { "email": "<email>", "token": "<hmac>", "issued_at": int }
    #
    # Passwords: scrypt (stdlib hashlib) with a per-user random salt — no deps.
    # Session token: HMAC-SHA256 over email+issued_at with a machine-local secret,
    # so a copied token can't be forged without the secret.

    _SESSION_TTL = 60 * 60 * 24 * 30   # 30 days

    def _machine_secret(self) -> bytes:
        """Stable per-install secret for signing session tokens."""
        sec = self._store_get("_session_secret")
        if not sec:
            sec = secrets.token_hex(32)
            self._store_set("_session_secret", value=sec)
        return sec.encode()

    @staticmethod
    def _hash_pw(password: str, salt: str) -> str:
        return hashlib.scrypt(
            password.encode(), salt=salt.encode(),
            n=16384, r=8, p=1, dklen=32,
        ).hex()

    def _make_token(self, email: str, issued_at: int) -> str:
        msg = f"{email}:{issued_at}".encode()
        return hmac.new(self._machine_secret(), msg, hashlib.sha256).hexdigest()

    def _set_session(self, email: str) -> str:
        issued = int(time.time())
        token  = self._make_token(email, issued)
        self._store_set("session", value={"email": email, "token": token, "issued_at": issued})
        return token

    def _norm_email(self, email: str) -> str:
        return (email or "").strip().lower()

    # ── Sign up (email + password) ───────────────────────────────────────
    def sign_up(self, email: str, password: str, name: str = "") -> dict:
        email = self._norm_email(email)
        if not email or "@" not in email:
            raise ValueError("Enter a valid email address.")
        if len(password) < 8:
            raise ValueError("Password must be at least 8 characters.")
        users = self._load().get("users", {})
        existing = users.get(email)
        if existing and existing.get("pw_hash"):
            raise ValueError("An account with this email already exists. Sign in instead.")

        salt = secrets.token_hex(16)
        user = {
            "email":      email,
            "name":       name.strip() or email.split("@")[0],
            "picture":    "",
            "auth_type":  "email",
            "pw_hash":    self._hash_pw(password, salt),
            "pw_salt":    salt,
            "providers":  existing.get("providers", []) if existing else [],
            "created_at": int(time.time()),
        }
        self._store_set("users", email, value=user)
        self._set_session(email)
        return self._public_user(user)

    # ── Sign in (email + password) ───────────────────────────────────────
    def sign_in(self, email: str, password: str) -> dict:
        email = self._norm_email(email)
        user  = self._load().get("users", {}).get(email)
        if not user or not user.get("pw_hash"):
            raise ValueError("No account found with this email. Sign up first.")
        expected = user["pw_hash"]
        actual   = self._hash_pw(password, user.get("pw_salt", ""))
        if not hmac.compare_digest(expected, actual):
            raise ValueError("Incorrect password.")
        self._set_session(email)
        return self._public_user(user)

    # ── OAuth → user account ─────────────────────────────────────────────
    def _upsert_oauth_user(self, provider: str, profile: dict) -> None:
        email = self._norm_email(profile.get("email", ""))
        if not email:
            return
        users = self._load().get("users", {})
        user  = users.get(email, {
            "email": email, "auth_type": "oauth", "providers": [],
            "created_at": int(time.time()), "pw_hash": "", "pw_salt": "",
        })
        user["name"]    = user.get("name") or profile.get("name", "")
        user["picture"] = profile.get("picture", "") or user.get("picture", "")
        provs = set(user.get("providers", []))
        provs.add(provider)
        user["providers"] = sorted(provs)
        self._store_set("users", email, value=user)

    # ── Session / current user ───────────────────────────────────────────
    def get_current_user(self) -> Optional[dict]:
        sess = self._store_get("session")
        if not sess:
            return None
        email, token, issued = sess.get("email"), sess.get("token"), sess.get("issued_at", 0)
        if not email or not token:
            return None
        # Expiry
        if int(time.time()) - int(issued) > self._SESSION_TTL:
            self.sign_out()
            return None
        # Integrity — token must match (defends against a tampered store)
        if not hmac.compare_digest(token, self._make_token(email, int(issued))):
            self.sign_out()
            return None
        user = self._load().get("users", {}).get(email)
        return self._public_user(user) if user else None

    def sign_out(self) -> None:
        """Clear session. Does NOT delete the account or OAuth tokens by default."""
        data = self._load()
        data.pop("session", None)
        self._save(data)

    def sign_out_full(self) -> None:
        """Sign out AND disconnect all OAuth tokens (used by 'Sign out everywhere')."""
        data = self._load()
        data.pop("session", None)
        data.pop("oauth", None)
        self._save(data)

    def _public_user(self, user: Optional[dict]) -> Optional[dict]:
        """Strip secrets before returning a user to any caller."""
        if not user:
            return None
        return {
            "email":     user.get("email", ""),
            "name":      user.get("name", ""),
            "picture":   user.get("picture", ""),
            "auth_type": user.get("auth_type", "email"),
            "providers": user.get("providers", []),
            "can_email": bool([p for p in user.get("providers", []) if p in ("google", "microsoft")]),
        }

    # ── LLM keys ────────────────────────────────────────────────────────

    async def validate_and_store_llm_key(self, provider: str, api_key: str) -> dict:
        cfg = LLM_PROVIDERS.get(provider)
        if not cfg:
            raise ValueError(f"Unknown LLM provider: {provider}")

        if provider == "ollama":
            api_key = ""  # no key needed

        try:
            headers = cfg["auth_header"](api_key)
            async with httpx.AsyncClient(timeout=12) as c:
                if cfg["validate_method"] == "POST":
                    r = await c.post(cfg["validate_url"], headers=headers,
                                     json=cfg["validate_body"])
                else:
                    r = await c.get(cfg["validate_url"], headers=headers)

            if r.status_code not in cfg["ok_codes"]:
                if r.status_code in (401, 403):
                    raise ValueError(
                        f"Invalid API key — {cfg['label']} rejected it. "
                        "Check the key and try again."
                    )
                if r.status_code == 429:
                    pass  # rate-limited but key is valid
                elif r.status_code >= 500:
                    raise ValueError(
                        f"{cfg['label']} API error ({r.status_code}). Try again later."
                    )
        except httpx.ConnectError:
            if provider == "ollama":
                raise ValueError(
                    "Ollama is not running at localhost:11434. "
                    "Start it with `ollama serve`."
                )
            raise ValueError(
                f"Cannot reach {cfg['label']} — check your internet connection."
            )
        except httpx.TimeoutException:
            raise ValueError(f"{cfg['label']} API timed out. Try again.")

        # Persist
        self._store_set("llm", provider, value={
            "api_key":      api_key,
            "label":        cfg["label"],
            "validated_at": int(time.time()),
        })
        # Inject into process environment so the existing adapters pick it up
        if cfg["key_env"]:
            os.environ[cfg["key_env"]] = api_key
        return {"provider": provider, "label": cfg["label"], "valid": True}

    def get_llm_key(self, provider: str) -> Optional[str]:
        stored = self._store_get("llm", provider)
        if stored:
            return stored.get("api_key") or None
        env_key = LLM_PROVIDERS.get(provider, {}).get("key_env", "")
        return os.getenv(env_key) or None

    def get_connected_llm_providers(self) -> list[dict]:
        data    = self._load()
        stored  = data.get("llm", {})
        result  = []
        seen    = set()
        for p, entry in stored.items():
            cfg = LLM_PROVIDERS.get(p, {})
            key = entry.get("api_key", "")
            result.append({
                "provider":     p,
                "label":        cfg.get("label", p),
                "sublabel":     cfg.get("sublabel", ""),
                "key_snippet":  (key[:8] + "..." + key[-4:]) if len(key) > 12 else key[:4] + "...",
                "validated_at": entry.get("validated_at", 0),
                "from_env":     False,
                "color":        cfg.get("color", "#8b949e"),
                "bg":           cfg.get("bg", "#161b22"),
            })
            seen.add(p)
        # Also surface keys that live only in env vars
        for p, cfg in LLM_PROVIDERS.items():
            if p in seen:
                continue
            env_val = os.getenv(cfg.get("key_env", ""), "")
            if env_val or p == "ollama":
                is_ollama = p == "ollama"
                result.append({
                    "provider":     p,
                    "label":        cfg["label"],
                    "sublabel":     cfg["sublabel"],
                    "key_snippet":  "via env var" if env_val else ("local" if is_ollama else ""),
                    "validated_at": 0,
                    "from_env":     True,
                    "color":        cfg["color"],
                    "bg":           cfg["bg"],
                })
                seen.add(p)
        return result

    def disconnect_llm(self, provider: str) -> None:
        self._store_del("llm", provider)
        env_key = LLM_PROVIDERS.get(provider, {}).get("key_env", "")
        if env_key and env_key in os.environ:
            del os.environ[env_key]

    def load_all_llm_keys_to_env(self) -> None:
        """Called on startup: push stored keys into process env for adapters."""
        data = self._load()
        for p, entry in data.get("llm", {}).items():
            cfg = LLM_PROVIDERS.get(p, {})
            if cfg.get("key_env") and entry.get("api_key"):
                os.environ[cfg["key_env"]] = entry["api_key"]

    # ── OAuth email sending ──────────────────────────────────────────────

    async def send_email_via_oauth(self, provider: str, to: str, subject: str,
                                    text_body: str, html_body: str,
                                    attachment_html: str, att_filename: str) -> None:
        """Send email using OAuth — no App Password required."""
        entry = self.get_oauth_entry(provider)
        if not entry:
            raise ValueError(f"Not connected to {provider}. "
                             "Connect your account in QAMill → Log in.")
        token = entry["access_token"]
        if provider == "google":
            await self._gmail_send(token, to, subject, text_body,
                                   html_body, attachment_html, att_filename)
        elif provider == "microsoft":
            await self._graph_send(token, to, subject, text_body,
                                   html_body, attachment_html, att_filename)
        else:
            raise ValueError(f"{provider} does not support direct email sending.")

    async def _gmail_send(self, token: str, to: str, subject: str,
                           text: str, html: str, att: str, att_name: str) -> None:
        from email.mime.multipart import MIMEMultipart
        from email.mime.text     import MIMEText
        from email.mime.base     import MIMEBase
        from email               import encoders as _enc
        import base64 as _b64

        msg = MIMEMultipart("mixed")
        msg["To"]      = to
        msg["Subject"] = subject
        alt = MIMEMultipart("alternative")
        alt.attach(MIMEText(text, "plain", "utf-8"))
        alt.attach(MIMEText(html, "html",  "utf-8"))
        msg.attach(alt)
        if att:
            part = MIMEBase("application", "octet-stream")
            part.set_payload(att.encode("utf-8"))
            _enc.encode_base64(part)
            part.add_header("Content-Disposition", f'attachment; filename="{att_name}"')
            msg.attach(part)

        raw = _b64.urlsafe_b64encode(msg.as_bytes()).decode()
        async with httpx.AsyncClient(timeout=30) as c:
            r = await c.post(
                "https://gmail.googleapis.com/gmail/v1/users/me/messages/send",
                headers={"Authorization": f"Bearer {token}",
                         "Content-Type": "application/json"},
                json={"raw": raw},
            )
            if r.status_code == 401:
                raise ValueError(
                    "Gmail token expired. Open QAMill → Log in → Social → "
                    "Google → Disconnect, then Connect again to refresh."
                )
            if r.status_code == 403:
                # Most common cause: gmail.send scope was never granted (cached consent)
                raise ValueError(
                    "Gmail send permission not granted for this account. "
                    "Open QAMill → Log in → Social → Google → Disconnect, "
                    "then Connect again and approve 'Send email on your behalf' on the consent screen."
                )
            r.raise_for_status()

    async def _graph_send(self, token: str, to: str, subject: str,
                           text: str, html: str, att: str, att_name: str) -> None:
        import base64 as _b64
        payload: dict = {
            "message": {
                "subject": subject,
                "body": {"contentType": "HTML", "content": html or text},
                "toRecipients": [{"emailAddress": {"address": to}}],
                "attachments": [],
            },
            "saveToSentItems": "true",
        }
        if att:
            payload["message"]["attachments"].append({
                "@odata.type": "#microsoft.graph.fileAttachment",
                "name":        att_name,
                "contentType": "text/html",
                "contentBytes": _b64.b64encode(att.encode()).decode(),
            })
        async with httpx.AsyncClient(timeout=30) as c:
            r = await c.post(
                "https://graph.microsoft.com/v1.0/me/sendMail",
                headers={"Authorization": f"Bearer {token}",
                         "Content-Type": "application/json"},
                json=payload,
            )
            if r.status_code == 401:
                raise ValueError("Microsoft token expired — please reconnect your account.")
            r.raise_for_status()


# ── Module-level singleton (imported by main.py) ──────────────────────────────
auth = AuthManager()
auth.load_all_llm_keys_to_env()   # push stored keys into env on import
