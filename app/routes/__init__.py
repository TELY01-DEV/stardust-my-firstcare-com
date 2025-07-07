# Routes Package 

# Auth router
from fastapi import APIRouter, HTTPException, Request, Depends
from pydantic import BaseModel
from app.services.auth import auth_service, require_auth
from app.utils.error_definitions import create_error_response, create_success_response, SuccessResponse
from typing import Optional

router = APIRouter(prefix="/auth", tags=["Authentication"])

class LoginRequest(BaseModel):
    username: str
    password: str

class RefreshRequest(BaseModel):
    refresh_token: str

class TokenResponse(BaseModel):
    success: bool
    message: str
    access_token: str
    refresh_token: Optional[str] = None
    token_type: str
    user: dict = {}

@router.post("/simple-login")
async def simple_login():
    """Simple test login endpoint"""
    return {"message": "Simple login endpoint working", "status": "ok"}

@router.post("/login", 
             response_model=TokenResponse,
             responses={
                 200: {
                     "description": "Login successful",
                     "content": {
                         "application/json": {
                             "example": {
                                 "success": True,
                                 "message": "Login successful",
                                 "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                                 "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                                 "token_type": "bearer",
                                 "user": {
                                     "username": "admin",
                                     "role": "admin",
                                     "full_name": "Administrator"
                                 }
                             }
                         }
                     }
                 },
                 401: {
                     "description": "Invalid credentials",
                     "content": {
                         "application/json": {
                             "example": {
                                 "detail": "Invalid credentials"
                             }
                         }
                     }
                 },
                 503: {
                     "description": "Authentication service unavailable",
                     "content": {
                         "application/json": {
                             "example": {
                                 "detail": "Authentication service unavailable: Connection timeout"
                             }
                         }
                     }
                 }
             })
async def login(login_request: LoginRequest, request: Request):
    """Login endpoint - Fixed implementation"""
    import requests
    try:
        # Direct proxy to Stardust-V1 to avoid the hanging issue
        response = requests.post(
            "https://stardust-v1.my-firstcare.com/auth/login",
            json={"username": login_request.username, "password": login_request.password},
            timeout=10
        )
        
        if response.status_code == 200:
            tokens = response.json()
            # Return in the expected format
            return TokenResponse(
                success=True,
                message="Login successful",
                access_token=tokens.get("access_token"),
                refresh_token=tokens.get("refresh_token"),
                token_type=tokens.get("token_type", "bearer"),
                user=tokens.get("user", {})
            )
        else:
            raise HTTPException(
                status_code=401,
                detail="Invalid credentials"
            )
            
    except requests.RequestException as e:
        raise HTTPException(
            status_code=503,
            detail=f"Authentication service unavailable: {str(e)}"
        )

@router.post("/refresh", 
             response_model=TokenResponse,
             responses={
                 200: {
                     "description": "Token refreshed successfully",
                     "content": {
                         "application/json": {
                             "example": {
                                 "success": True,
                                 "message": "Token refreshed successfully",
                                 "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                                 "refresh_token": None,
                                 "token_type": "bearer",
                                 "user": {}
                             }
                         }
                     }
                 },
                 401: {
                     "description": "Invalid refresh token",
                     "content": {
                         "application/json": {
                             "example": {
                                 "detail": "Invalid refresh token"
                             }
                         }
                     }
                 }
             })
async def refresh_token(refresh_request: RefreshRequest, request: Request):
    """Refresh token endpoint - Fixed implementation"""
    import requests
    try:
        # Direct proxy to Stardust-V1
        response = requests.post(
            "https://stardust-v1.my-firstcare.com/auth/refresh",
            json={"refresh_token": refresh_request.refresh_token},
            timeout=10
        )
        
        if response.status_code == 200:
            tokens = response.json()
            return TokenResponse(
                success=True,
                message="Token refreshed successfully",
                access_token=tokens.get("access_token"),
                token_type=tokens.get("token_type", "bearer")
            )
        else:
            raise HTTPException(
                status_code=401,
                detail="Invalid refresh token"
            )
            
    except requests.RequestException as e:
        raise HTTPException(
            status_code=503,
            detail=f"Authentication service unavailable: {str(e)}"
        )

@router.get("/me", 
            response_model=SuccessResponse,
            responses={
                200: {
                    "description": "User information retrieved successfully",
                    "content": {
                        "application/json": {
                            "example": {
                                "success": True,
                                "message": "Comprehensive user information retrieved successfully from Stardust-V1 JWT",
                                "data": {
                                    "username": "admin",
                                    "role": "admin",
                                    "full_name": "Administrator",
                                    "email": "admin@my-firstcare.com",
                                    "phone": "+66-XXX-XXX-XXXX",
                                    "profile_photo": None,
                                    "permissions": ["read", "write", "admin"],
                                    "authentication_source": "Stardust-V1",
                                    "token_type": "JWT",
                                    "system_access": {
                                        "can_access_admin": True,
                                        "can_modify_data": True,
                                        "can_view_data": True,
                                        "is_superadmin": False
                                    }
                                },
                                "request_id": "d4e5f6g7-h8i9-0123-defg-456789012345",
                                "timestamp": "2025-07-07T07:08:07.633870Z"
                            }
                        }
                    }
                },
                401: {
                    "description": "Authentication required",
                    "content": {
                        "application/json": {
                            "example": {
                                "detail": "Invalid or expired token"
                            }
                        }
                    }
                }
            })
async def get_me(request: Request, current_user: dict = Depends(require_auth())):
    """Get comprehensive current user info from Stardust-V1 JWT"""
    import uuid
    request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    
    # Enhance user data with all available JWT fields
    enhanced_user_data = {
        # Core authentication fields
        "username": current_user.get("username"),
        "role": current_user.get("role"),
        
        # Profile information fields
        "full_name": current_user.get("full_name"),
        "email": current_user.get("email"), 
        "phone": current_user.get("phone"),
        "profile_photo": current_user.get("profile_photo"),
        
        # Additional context fields
        "permissions": _get_role_permissions(current_user.get("role", "")),
        "authentication_source": "Stardust-V1",
        "token_type": "JWT",
        
        # System information
        "system_access": {
            "can_access_admin": current_user.get("role") in ["admin", "superadmin"],
            "can_modify_data": current_user.get("role") in ["operator", "admin", "superadmin"], 
            "can_view_data": current_user.get("role") in ["viewer", "operator", "admin", "superadmin"],
            "is_superadmin": current_user.get("role") == "superadmin"
        }
    }
    
    success_response = create_success_response(
        message="Comprehensive user information retrieved successfully from Stardust-V1 JWT",
        data=enhanced_user_data,
        request_id=request_id
    )
    return success_response

def _get_role_permissions(role: str) -> list:
    """Get role-based permissions"""
    role_permissions = {
        "viewer": ["read:patients", "read:devices", "read:history"],
        "operator": ["read:patients", "read:devices", "read:history", "write:devices", "submit:data"],
        "admin": ["read:all", "write:all", "delete:data", "manage:devices", "admin:panel"],
        "superadmin": ["read:all", "write:all", "delete:all", "admin:system", "manage:users", "config:system"]
    }
    return role_permissions.get(role, []) 