# Stardust-V1 Centralized JWT Authentication Handbook

## Overview

- `Stardust-V1` acts as the central Auth Server for all applications and services.
- All login, token verification, and refresh operations are routed through Stardust-V1.
- Every frontend, backend, and microservice should use this single source of truth for user authentication.
- **UPDATED (June 18, 2025)**: All API endpoints are now secured with JWT authentication.

---

## API Endpoints

| Endpoint         | Method | Description                              |
|------------------|--------|------------------------------------------|
| `/auth/login`    | POST   | Get `access_token` & `refresh_token` with username & password |
| `/auth/refresh`  | POST   | Get new `access_token` via `refresh_token` |
| `/auth/me`       | GET    | Validate and decode user info from `access_token` |
| `/logout`        | POST   | (Client-side only: just remove token from storage) |

---

## Usage Examples

### 1. Login

test user
user: admin
password: Sim!443355

```python
import requests

res = requests.post(
    "https://stardust-v1.my-firstcare.com/auth/login",
    json={"username": "YOUR_USERNAME", "password": "YOUR_PASSWORD"}
)
tokens = res.json()
# tokens["access_token"], tokens["refresh_token"]
```

### 2. Verify token / Get Current User

```python
headers = {"Authorization": "Bearer <access_token>"}
res = requests.get("https://stardust-v1.my-firstcare.com/auth/me", headers=headers)
user_info = res.json()
```

### 3. Refresh Token

```python
res = requests.post(
    "https://stardust-v1.my-firstcare.com/auth/refresh",
    json={"refresh_token": "<refresh_token>"}
)
tokens = res.json()
```

### 4. Logout

Simply remove access_token and refresh_token from localStorage or cookies on the client.
No server API call is needed for stateless JWT logout.
localStorage.removeItem("access_token");
localStorage.removeItem("refresh_token");
window.location.href = "/login";

.env Example

JWT_AUTH_BASE_URL=https://stardust-v1.my-firstcare.com
Best Practices

All apps/services should use Stardust-V1 as the sole JWT provider.
Do not share or distribute JWT secret keys.
Use short-lived access tokens (15–60 min) and refresh tokens.
Always verify JWT via /auth/me endpoint; do not decode tokens locally.
For logout, simply remove tokens from client storage.
Only implement server-side blocklist if forced logout/revocation is required.
Workflow Summary

User logs in → receives access_token & refresh_token.
Each API call sends Authorization: Bearer <access_token>.
When access_token expires, refresh using refresh_token.
Logout by deleting tokens on client side.

//config//

# JWT centralized verification config
JWT_AUTH_BASE_URL: str = os.getenv("JWT_AUTH_BASE_URL", "https://stardust-v1.my-firstcare.com")
JWT_LOGIN_ENDPOINT: str = "/auth/login"
JWT_REFRESH_ENDPOINT: str = "/auth/refresh"
JWT_ME_ENDPOINT: str = "/auth/me"
ENABLE_JWT_AUTH: bool = os.getenv("ENABLE_JWT_AUTH", "true").lower() == "true"


//Login Request//

import requests

def login(username: str, password: str):
    url = f"{JWT_AUTH_BASE_URL}{JWT_LOGIN_ENDPOINT}"
    res = requests.post(url, json={"username": username, "password": password})
    if res.status_code == 200:
        return res.json()  # contains access_token, refresh_token
    else:
        raise Exception(f"Login failed: {res.text}")

//Refresh Token//

def refresh_token(refresh_token: str):
    url = f"{JWT_AUTH_BASE_URL}{JWT_REFRESH_ENDPOINT}"
    res = requests.post(url, json={"refresh_token": refresh_token})
    if res.status_code == 200:
        return res.json()
    else:
        raise Exception("Refresh failed")


//Get Current User (/auth/me)//

def get_me(access_token: str):
    url = f"{JWT_AUTH_BASE_URL}{JWT_ME_ENDPOINT}"
    headers = {"Authorization": f"Bearer {access_token}"}
    res = requests.get(url, headers=headers)
    if res.status_code == 200:
        return res.json()
    else:
        raise Exception("Token invalid or expired")


///auth/logout//

@router.post("/auth/logout")
def logout(request: Request, token: str = Depends(get_token)):
    db.revoked_tokens.insert_one({"token": token, "exp": decode_exp(token)})
    return {"message": "Logged out"}


//Verify token / Get Current User//

headers = {"Authorization": "Bearer <access_token>"}
res = requests.get("https://stardust-v1.my-firstcare.com/auth/me", headers=headers)
user_info = res.json()


//Refresh Token//

res = requests.post(
    "https://stardust-v1.my-firstcare.com/auth/refresh",
    json={"refresh_token": "<refresh_token>"}
)
tokens = res.json()


//FastAPI Integration Example
jwt_auth.py//

import os, requests
from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

JWT_AUTH_BASE_URL = os.getenv("JWT_AUTH_BASE_URL", "https://stardust-v1.my-firstcare.com")
JWT_ME_ENDPOINT = "/auth/me"
http_bearer = HTTPBearer()

def verify_token_with_stardust(token: str):
    res = requests.get(
        f"{JWT_AUTH_BASE_URL}{JWT_ME_ENDPOINT}",
        headers={"Authorization": f"Bearer {token}"}
    )
    if res.status_code == 200:
        return res.json()
    raise HTTPException(status_code=401, detail="Invalid or expired token")

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(http_bearer)):
    return verify_token_with_stardust(credentials.credentials)


## New Authentication Module (June 18, 2025)

As part of the security upgrade, we've implemented a centralized authentication module for all API endpoints:

### Location
- `/api/auth_middleware.py`

### Features
- JWT authentication with Stardust-V1 integration
- API key authentication as fallback for system services
- Combined JWT/API key authentication option
- Easy-to-use decorators for Flask routes

### Usage Examples

#### Import the Module
```python
from api.auth_middleware import init_jwt_auth, jwt_required, api_key_required, jwt_or_api_key_required
```

#### Initialize with Flask App
```python
app = Flask(__name__)
init_jwt_auth(app)  # Initialize JWT authentication
```

#### Secure Routes with JWT
```python
@app.route('/api/secure-endpoint')
@jwt_required
def secure_endpoint():
    # This endpoint will require a valid JWT token
    return jsonify({"message": "Access granted"})
```

#### Allow Either JWT or API Key
```python
@app.route('/api/monitoring-endpoint')
@jwt_or_api_key_required
def monitoring_endpoint():
    # This endpoint will accept either JWT or API key
    return jsonify({"message": "Monitoring data"})
```

### Implementation Status

| API | Authentication Status |
|-----|----------------------|
| `/api/kati_watch_command_api_v2.py` | JWT secured |
| `/api/api_bp76_fall_detection_rest.py` | JWT secured |
| Prometheus metrics endpoint | API key secured |
| Health check endpoints | Publicly accessible |
| All other API endpoints | JWT secured |

### Authentication Flow

1. Client obtains JWT token from Stardust-V1 via `/auth/login` endpoint
2. Client includes token in all API requests via `Authorization: Bearer <token>` header
3. API validates token with Stardust-V1 via `/auth/me` endpoint
4. If valid, request proceeds; if invalid, 401 Unauthorized response is returned
