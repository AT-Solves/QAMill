# OAuth Setup Guide - GitHub & Google

**Status:** Phase 5 Implementation Complete  
**Features:** GitHub OAuth, Google OAuth, Automatic user creation  
**Tested:** Backend routes & Frontend components ready

---

## Quick Start

### Environment Variables

Add to `.env` file:

```env
# GitHub OAuth
OAUTH_GITHUB_CLIENT_ID=your_github_client_id
OAUTH_GITHUB_CLIENT_SECRET=your_github_client_secret
OAUTH_GITHUB_REDIRECT_URI=http://localhost:5173/auth/github/callback

# Google OAuth
OAUTH_GOOGLE_CLIENT_ID=your_google_client_id
OAUTH_GOOGLE_CLIENT_SECRET=your_google_client_secret
OAUTH_GOOGLE_REDIRECT_URI=http://localhost:5173/auth/google/callback
```

---

## GitHub OAuth Setup

### 1. Create GitHub Application

1. Go to https://github.com/settings/developers
2. Click "New OAuth App"
3. Fill in the form:
   - **Application name:** QAMill
   - **Homepage URL:** http://localhost:5173
   - **Authorization callback URL:** http://localhost:5173/auth/github/callback
4. Click "Register application"

### 2. Get Credentials

1. Copy **Client ID** → `OAUTH_GITHUB_CLIENT_ID`
2. Click "Generate a new client secret" → `OAUTH_GITHUB_CLIENT_SECRET`

### 3. Update .env

```env
OAUTH_GITHUB_CLIENT_ID=abc123...
OAUTH_GITHUB_CLIENT_SECRET=xyz789...
```

### 4. Test

```bash
curl http://localhost:8765/api/v1/oauth/github/login
# Returns: {"redirect_url": "https://github.com/login/oauth/authorize?..."}
```

---

## Google OAuth Setup

### 1. Create Google Application

1. Go to https://console.cloud.google.com/
2. Create new project: "QAMill"
3. Go to "OAuth Consent Screen"
   - Set to "External"
   - Fill required fields
4. Go to "Credentials"
5. Create "OAuth 2.0 Client ID"
   - Type: Web application
   - Name: QAMill
   - Authorized JavaScript origins:
     - http://localhost:5173
   - Authorized redirect URIs:
     - http://localhost:5173/auth/google/callback

### 2. Get Credentials

1. Copy **Client ID** → `OAUTH_GOOGLE_CLIENT_ID`
2. Copy **Client Secret** → `OAUTH_GOOGLE_CLIENT_SECRET`

### 3. Update .env

```env
OAUTH_GOOGLE_CLIENT_ID=abc123...
OAUTH_GOOGLE_CLIENT_SECRET=xyz789...
```

### 4. Test

```bash
curl http://localhost:8765/api/v1/oauth/google/login
# Returns: {"redirect_url": "https://accounts.google.com/o/oauth2/v2/auth?..."}
```

---

## API Endpoints

### OAuth Flow

1. **Get Login URL**
   ```
   GET /api/v1/oauth/github/login
   GET /api/v1/oauth/google/login
   
   Returns: {"redirect_url": "https://..."}
   ```

2. **Handle Callback**
   ```
   POST /api/v1/oauth/github/callback?code=AUTH_CODE
   POST /api/v1/oauth/google/callback?code=AUTH_CODE
   
   Returns: {
     "access_token": "eyJ...",
     "refresh_token": "eyJ...",
     "token_type": "bearer",
     "expires_in": 1800
   }
   ```

3. **Check Status**
   ```
   GET /api/v1/oauth/status
   
   Returns: {
     "github_configured": true,
     "google_configured": true
   }
   ```

---

## Frontend Components

### OAuthButtons Component

Used on Login/Signup pages:

```vue
<OAuthButtons />
```

Features:
- GitHub login button
- Google login button
- Shows configuration status
- Handles OAuth redirects

### OAuthCallback View

Handles OAuth provider callbacks:

```
http://localhost:5173/auth/github/callback?code=AUTH_CODE
http://localhost:5173/auth/google/callback?code=AUTH_CODE
```

Features:
- Exchanges code for tokens
- Creates user if needed
- Stores auth tokens
- Redirects to dashboard

---

## User Creation Flow

1. User clicks "GitHub" or "Google" button
2. Redirects to provider's login page
3. User authorizes QAMill
4. Provider redirects to callback with authorization code
5. Backend exchanges code for access token
6. Backend fetches user profile from provider
7. Backend creates user or updates existing user
8. Backend generates JWT tokens
9. Frontend stores tokens & redirects to dashboard

---

## Security Features

✅ **Authorization Code Flow**
- Code is exchanged server-side
- Never exposed to client

✅ **Token Validation**
- Tokens verified before use
- Expired tokens refresh automatically

✅ **User Creation**
- Automatic account creation
- Email is primary identifier
- Avatar synced from provider

✅ **Password Protection**
- OAuth users get placeholder password
- Cannot login with password
- Security tokens never leak

---

## Troubleshooting

### "Authorization failed" Error

**Check:**
1. OAuth credentials in `.env` correct?
2. Redirect URI matches GitHub/Google settings?
3. Browser allowing third-party cookies?

### User created but profile empty

**Check:**
1. Provider API request succeeding?
2. Email permission requested?
3. Frontend callback handler working?

### Token exchange fails

**Check:**
1. Authorization code valid?
2. Code not expired (usually 10 seconds)?
3. CORS allowing callback?

---

## Testing Without Providers

If OAuth not configured:
1. Login page shows message
2. Can still use email/password
3. OAuth buttons disabled gracefully

---

## Production Setup

For production:

1. **Change redirect URIs**
   ```env
   OAUTH_GITHUB_REDIRECT_URI=https://yourdomain.com/auth/github/callback
   OAUTH_GOOGLE_REDIRECT_URI=https://yourdomain.com/auth/google/callback
   ```

2. **Update GitHub & Google settings**
   - Change Authorization callback URLs
   - Use HTTPS

3. **Enable HTTPS**
   ```env
   OAUTH_GITHUB_REDIRECT_URI=https://yourdomain.com/...
   OAUTH_GOOGLE_REDIRECT_URI=https://yourdomain.com/...
   ```

4. **Secure Secrets**
   - Store in environment variables
   - Never commit to git
   - Rotate regularly

---

## Features Included

- ✅ GitHub OAuth login
- ✅ Google OAuth login
- ✅ Automatic user creation
- ✅ Profile syncing
- ✅ Avatar loading
- ✅ JWT token generation
- ✅ Error handling
- ✅ Loading states
- ✅ Configuration checking

---

## Next: Phase 6

Real-time dashboards with WebSocket:
- Live analysis updates
- Real-time test results
- Activity feeds
- Notifications

---

**Ready to test OAuth?** Set up GitHub/Google apps and add credentials to `.env`! 🚀
