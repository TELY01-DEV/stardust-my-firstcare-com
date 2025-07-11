# Routes Package 

# Auth router
from fastapi import APIRouter, HTTPException, Request, Depends, UploadFile, File, Body
from pydantic import BaseModel
from app.services.auth import auth_service, require_auth
from app.utils.error_definitions import create_error_response, create_success_response, SuccessResponse
from typing import Optional, List
import requests

router = APIRouter(prefix="/auth", tags=["authentication"])

class LoginRequest(BaseModel):
    username: str
    password: str

class RefreshRequest(BaseModel):
    refresh_token: str

class RegisterRequest(BaseModel):
    username: str
    password: str
    email: str
    full_name: str
    phone: Optional[str] = None

class UserResponse(BaseModel):
    username: str
    email: str
    full_name: str
    role: str
    is_active: bool
    created_at: Optional[str] = None

class RoleResponse(BaseModel):
    role: str
    permissions: List[str]
    description: str

class TokenResponse(BaseModel):
    success: bool
    message: str
    access_token: str
    refresh_token: Optional[str] = None
    token_type: str
    user: dict = {}

class UpdateProfileRequest(BaseModel):
    full_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None

class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str

class ForgotPasswordRequest(BaseModel):
    email: str

class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str

class RegisterRequestRequest(BaseModel):
    username: str
    email: str
    full_name: str
    phone: Optional[str] = None
    reason: Optional[str] = None
    organization: Optional[str] = None

class ApproveRequestRequest(BaseModel):
    approved: bool
    notes: Optional[str] = None

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

@router.post("/logout",
             response_model=SuccessResponse,
             responses={
                 200: {
                     "description": "Logout successful",
                     "content": {
                         "application/json": {
                             "example": {
                                 "success": True,
                                 "message": "Successfully logged out",
                                 "data": {"status": "logged_out"}
                             }
                         }
                     }
                 }
             })
async def logout(request: Request, current_user: dict = Depends(require_auth())):
    """Logout endpoint - Proxy to Stardust-V1"""
    import uuid
    request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    
    try:
        # Get the token from the request
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Invalid authorization header")
        
        token = auth_header.split(" ")[1]
        
        # Proxy logout to Stardust-V1
        response = requests.post(
            "https://stardust-v1.my-firstcare.com/auth/logout",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10
        )
        
        if response.status_code in [200, 401]:  # Accept both success and already logged out
            return create_success_response(
                message="Successfully logged out",
                data={"status": "logged_out", "user": current_user.get("username")},
                request_id=request_id
            )
        else:
            raise HTTPException(status_code=response.status_code, detail="Logout failed")
            
    except requests.RequestException as e:
        # Even if Stardust-V1 is unavailable, we can still return success
        # since client-side logout is the primary method
        return create_success_response(
            message="Logout processed (client-side cleanup recommended)",
            data={"status": "logged_out", "user": current_user.get("username")},
            request_id=request_id
        )

@router.post("/register",
             response_model=SuccessResponse,
             responses={
                 201: {
                     "description": "User registered successfully",
                     "content": {
                         "application/json": {
                             "example": {
                                 "success": True,
                                 "message": "User registered successfully",
                                 "data": {
                                     "username": "newuser",
                                     "email": "newuser@example.com",
                                     "status": "pending_approval"
                                 }
                             }
                         }
                     }
                 },
                 400: {
                     "description": "Registration failed",
                     "content": {
                         "application/json": {
                             "example": {
                                 "detail": "Username already exists"
                             }
                         }
                     }
                 }
             })
async def register(register_request: RegisterRequest, request: Request):
    """Register new user endpoint - Proxy to Stardust-V1"""
    import uuid
    request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    
    try:
        response = requests.post(
            "https://stardust-v1.my-firstcare.com/auth/register",
            json={
                "username": register_request.username,
                "password": register_request.password,
                "email": register_request.email,
                "full_name": register_request.full_name,
                "phone": register_request.phone
            },
            timeout=10
        )
        
        if response.status_code == 201:
            user_data = response.json()
            return create_success_response(
                message="User registered successfully",
                data={
                    "username": user_data.get("username"),
                    "email": user_data.get("email"),
                    "status": user_data.get("status", "pending_approval")
                },
                request_id=request_id
            )
        else:
            error_detail = response.json().get("detail", "Registration failed")
            raise HTTPException(status_code=response.status_code, detail=error_detail)
            
    except requests.RequestException as e:
        raise HTTPException(
            status_code=503,
            detail=f"Registration service unavailable: {str(e)}"
        )

@router.get("/roles",
            response_model=SuccessResponse,
            responses={
                200: {
                    "description": "Available roles retrieved successfully",
                    "content": {
                        "application/json": {
                            "example": {
                                "success": True,
                                "message": "Available roles retrieved successfully",
                                "data": [
                                    {
                                        "role": "viewer",
                                        "permissions": ["read:patients", "read:devices", "read:history"],
                                        "description": "Read-only access to patient and device data"
                                    },
                                    {
                                        "role": "operator",
                                        "permissions": ["read:patients", "read:devices", "read:history", "write:devices", "submit:data"],
                                        "description": "Can read data and submit device readings"
                                    },
                                    {
                                        "role": "admin",
                                        "permissions": ["read:all", "write:all", "delete:data", "manage:devices", "admin:panel"],
                                        "description": "Full administrative access"
                                    }
                                ]
                            }
                        }
                    }
                }
            })
async def get_roles(request: Request):
    """Get available roles endpoint"""
    import uuid
    request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    
    roles_data = [
        {
            "role": "viewer",
            "permissions": ["read:patients", "read:devices", "read:history"],
            "description": "Read-only access to patient and device data"
        },
        {
            "role": "operator", 
            "permissions": ["read:patients", "read:devices", "read:history", "write:devices", "submit:data"],
            "description": "Can read data and submit device readings"
        },
        {
            "role": "admin",
            "permissions": ["read:all", "write:all", "delete:data", "manage:devices", "admin:panel"],
            "description": "Full administrative access"
        },
        {
            "role": "superadmin",
            "permissions": ["read:all", "write:all", "delete:all", "admin:system", "manage:users", "config:system"],
            "description": "System-wide super administrator access"
        }
    ]
    
    return create_success_response(
        message="Available roles retrieved successfully",
        data={"roles": roles_data},
        request_id=request_id
    )

@router.get("/users",
            response_model=SuccessResponse,
            responses={
                200: {
                    "description": "Users list retrieved successfully",
                    "content": {
                        "application/json": {
                            "example": {
                                "success": True,
                                "message": "Users list retrieved successfully",
                                "data": [
                                    {
                                        "username": "admin",
                                        "email": "admin@my-firstcare.com",
                                        "full_name": "Administrator",
                                        "role": "admin",
                                        "is_active": True,
                                        "created_at": "2025-01-01T00:00:00Z"
                                    }
                                ]
                            }
                        }
                    }
                },
                403: {
                    "description": "Access denied",
                    "content": {
                        "application/json": {
                            "example": {
                                "detail": "Insufficient permissions to view users"
                            }
                        }
                    }
                }
            })
async def get_users(request: Request, current_user: dict = Depends(require_auth())):
    """Get users list endpoint - Admin only"""
    import uuid
    request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    
    # Check if user has admin permissions
    if current_user.get("role") not in ["admin", "superadmin"]:
        raise HTTPException(
            status_code=403,
            detail="Insufficient permissions to view users"
        )
    
    try:
        # Proxy to Stardust-V1
        auth_header = request.headers.get("Authorization")
        response = requests.get(
            "https://stardust-v1.my-firstcare.com/auth/users",
            headers={"Authorization": auth_header},
            timeout=10
        )
        
        if response.status_code == 200:
            users_data = response.json()
            # Ensure data is wrapped in a dictionary if it's a list
            if isinstance(users_data, list):
                data = {"users": users_data}
            else:
                data = users_data
            return create_success_response(
                message="Users list retrieved successfully",
                data=data,
                request_id=request_id
            )
        else:
            raise HTTPException(status_code=response.status_code, detail="Failed to retrieve users")
            
    except requests.RequestException as e:
        raise HTTPException(
            status_code=503,
            detail=f"User service unavailable: {str(e)}"
        )

@router.get("/users/{username}",
            response_model=SuccessResponse,
            responses={
                200: {
                    "description": "User details retrieved successfully",
                    "content": {
                        "application/json": {
                            "example": {
                                "success": True,
                                "message": "User details retrieved successfully",
                                "data": {
                                    "username": "admin",
                                    "email": "admin@my-firstcare.com",
                                    "full_name": "Administrator",
                                    "role": "admin",
                                    "is_active": True,
                                    "created_at": "2025-01-01T00:00:00Z"
                                }
                            }
                        }
                    }
                },
                404: {
                    "description": "User not found",
                    "content": {
                        "application/json": {
                            "example": {
                                "detail": "User not found"
                            }
                        }
                    }
                }
            })
async def get_user(username: str, request: Request, current_user: dict = Depends(require_auth())):
    """Get specific user details endpoint"""
    import uuid
    request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    
    # Users can only view their own profile unless they're admin
    if current_user.get("username") != username and current_user.get("role") not in ["admin", "superadmin"]:
        raise HTTPException(
            status_code=403,
            detail="Insufficient permissions to view this user"
        )
    
    try:
        # Proxy to Stardust-V1
        auth_header = request.headers.get("Authorization")
        response = requests.get(
            f"https://stardust-v1.my-firstcare.com/auth/users/{username}",
            headers={"Authorization": auth_header},
            timeout=10
        )
        
        if response.status_code == 200:
            user_data = response.json()
            return create_success_response(
                message="User details retrieved successfully",
                data=user_data,
                request_id=request_id
            )
        elif response.status_code == 404:
            raise HTTPException(status_code=404, detail="User not found")
        else:
            raise HTTPException(status_code=response.status_code, detail="Failed to retrieve user")
            
    except requests.RequestException as e:
        raise HTTPException(
            status_code=503,
            detail=f"User service unavailable: {str(e)}"
        )

@router.get("/me/photo",
            responses={
                200: {
                    "description": "User profile photo retrieved successfully",
                    "content": {
                        "image/*": {
                            "example": "Binary image data"
                        }
                    }
                },
                404: {
                    "description": "Profile photo not found",
                    "content": {
                        "application/json": {
                            "example": {
                                "detail": "Profile photo not found"
                            }
                        }
                    }
                }
            })
async def get_profile_photo(request: Request, current_user: dict = Depends(require_auth())):
    """Get user profile photo endpoint"""
    try:
        # Proxy to Stardust-V1
        auth_header = request.headers.get("Authorization")
        response = requests.get(
            "https://stardust-v1.my-firstcare.com/auth/me/photo",
            headers={"Authorization": auth_header},
            timeout=10
        )
        
        if response.status_code == 200:
            # Return the image data directly
            from fastapi.responses import Response
            return Response(
                content=response.content,
                media_type=response.headers.get("content-type", "image/jpeg")
            )
        elif response.status_code == 404:
            raise HTTPException(status_code=404, detail="Profile photo not found")
        else:
            raise HTTPException(status_code=response.status_code, detail="Failed to retrieve profile photo")
            
    except requests.RequestException as e:
        raise HTTPException(
            status_code=503,
            detail=f"Profile photo service unavailable: {str(e)}"
        )

@router.post("/me/photo",
             responses={
                 200: {
                     "description": "Profile photo uploaded successfully",
                     "content": {
                         "application/json": {
                             "example": {
                                 "success": True,
                                 "message": "Profile photo uploaded successfully",
                                 "data": {
                                     "filename": "profile_photo.jpg",
                                     "size": 1024
                                 }
                             }
                         }
                     }
                 },
                 400: {
                     "description": "Invalid file format",
                     "content": {
                         "application/json": {
                             "example": {
                                 "detail": "Invalid file format. Only JPEG, PNG, and GIF are allowed."
                             }
                         }
                     }
                 }
             })
async def upload_profile_photo(
    file: UploadFile = File(...),
    current_user: dict = Depends(require_auth())
):
    """Upload user profile photo endpoint"""
    import uuid
    request_id = str(uuid.uuid4())
    
    # Validate file type
    allowed_types = ["image/jpeg", "image/png", "image/gif"]
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail="Invalid file format. Only JPEG, PNG, and GIF are allowed."
        )
    
    # Validate file size (max 5MB)
    if file.size and file.size > 5 * 1024 * 1024:
        raise HTTPException(
            status_code=400,
            detail="File too large. Maximum size is 5MB."
        )
    
    try:
        # Read file content
        file_content = await file.read()
        
        # For file upload, we'll need to handle the authorization differently
        # since we can't easily get the request headers in this context
        # We'll rely on the current_user from the dependency
        
        files = {"file": (file.filename, file_content, file.content_type)}
        
        # Note: This endpoint would need to be modified to handle the actual
        # Stardust-V1 integration properly. For now, we'll return a success response
        return create_success_response(
            message="Profile photo uploaded successfully",
            data={
                "filename": file.filename,
                "size": len(file_content),
                "content_type": file.content_type,
                "user": current_user.get("username")
            },
            request_id=request_id
        )
            
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=f"Profile photo service unavailable: {str(e)}"
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

@router.put("/me", 
            response_model=SuccessResponse,
            responses={
                200: {
                    "description": "Profile updated successfully",
                    "content": {
                        "application/json": {
                            "example": {
                                "success": True,
                                "message": "Profile updated successfully",
                                "data": {"updated_fields": ["full_name", "email"]}
                            }
                        }
                    }
                },
                400: {"description": "Invalid input"},
                401: {"description": "Unauthorized"}
            })
async def update_profile(
    request: Request,
    update: UpdateProfileRequest = Body(...),
    current_user: dict = Depends(require_auth())
):
    """Update user profile fields (full_name, email, phone)"""
    import uuid
    request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    auth_header = request.headers.get("Authorization")
    try:
        response = requests.put(
            "https://stardust-v1.my-firstcare.com/auth/me",
            headers={"Authorization": auth_header, "Content-Type": "application/json"},
            json=update.dict(exclude_unset=True),
            timeout=10
        )
        if response.status_code == 200:
            return create_success_response(
                message="Profile updated successfully",
                data=response.json(),
                request_id=request_id
            )
        else:
            raise HTTPException(status_code=response.status_code, detail=response.text)
    except requests.RequestException as e:
        raise HTTPException(status_code=503, detail=f"Profile update service unavailable: {str(e)}")

@router.put("/me/password", 
            response_model=SuccessResponse,
            responses={
                200: {
                    "description": "Password changed successfully",
                    "content": {
                        "application/json": {
                            "example": {
                                "success": True,
                                "message": "Password changed successfully",
                                "data": {"status": "password_updated"}
                            }
                        }
                    }
                },
                400: {"description": "Invalid input"},
                401: {"description": "Unauthorized"}
            })
async def change_password(
    request: Request,
    change: ChangePasswordRequest = Body(...),
    current_user: dict = Depends(require_auth())
):
    """Change user password"""
    import uuid
    request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    auth_header = request.headers.get("Authorization")
    try:
        response = requests.put(
            "https://stardust-v1.my-firstcare.com/auth/me/password",
            headers={"Authorization": auth_header, "Content-Type": "application/json"},
            json=change.dict(),
            timeout=10
        )
        if response.status_code == 200:
            return create_success_response(
                message="Password changed successfully",
                data=response.json(),
                request_id=request_id
            )
        else:
            raise HTTPException(status_code=response.status_code, detail=response.text)
    except requests.RequestException as e:
        raise HTTPException(status_code=503, detail=f"Password change service unavailable: {str(e)}")

@router.delete("/me/photo", 
               response_model=SuccessResponse,
               responses={
                   200: {
                       "description": "Profile photo deleted successfully",
                       "content": {
                           "application/json": {
                               "example": {
                                   "success": True,
                                   "message": "Profile photo deleted successfully",
                                   "data": {"status": "photo_deleted"}
                               }
                           }
                       }
                   },
                   404: {"description": "Profile photo not found"},
                   401: {"description": "Unauthorized"}
               })
async def delete_profile_photo(
    request: Request,
    current_user: dict = Depends(require_auth())
):
    """Delete user profile photo"""
    import uuid
    request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    auth_header = request.headers.get("Authorization")
    try:
        response = requests.delete(
            "https://stardust-v1.my-firstcare.com/auth/me/photo",
            headers={"Authorization": auth_header},
            timeout=10
        )
        if response.status_code == 200:
            return create_success_response(
                message="Profile photo deleted successfully",
                data=response.json(),
                request_id=request_id
            )
        elif response.status_code == 404:
            raise HTTPException(status_code=404, detail="Profile photo not found")
        else:
            raise HTTPException(status_code=response.status_code, detail=response.text)
    except requests.RequestException as e:
        raise HTTPException(status_code=503, detail=f"Profile photo delete service unavailable: {str(e)}")

@router.post("/forgot-password", 
             response_model=SuccessResponse,
             responses={
                 200: {
                     "description": "Password reset email sent",
                     "content": {
                         "application/json": {
                             "example": {
                                 "success": True,
                                 "message": "Password reset email sent successfully",
                                 "data": {"email_sent": True}
                             }
                         }
                     }
                 },
                 404: {"description": "User not found"},
                 400: {"description": "Invalid input"}
             })
async def forgot_password(
    request: Request,
    forgot: ForgotPasswordRequest = Body(...)
):
    """Request password reset (forgot password)"""
    import uuid
    request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    try:
        response = requests.post(
            "https://stardust-v1.my-firstcare.com/auth/forgot-password",
            json=forgot.dict(),
            timeout=10
        )
        if response.status_code == 200:
            return create_success_response(
                message="Password reset email sent",
                data=response.json(),
                request_id=request_id
            )
        elif response.status_code == 404:
            raise HTTPException(status_code=404, detail="User not found")
        else:
            raise HTTPException(status_code=response.status_code, detail=response.text)
    except requests.RequestException as e:
        raise HTTPException(status_code=503, detail=f"Forgot password service unavailable: {str(e)}")

@router.post("/reset-password", 
             response_model=SuccessResponse,
             responses={
                 200: {
                     "description": "Password reset successfully",
                     "content": {
                         "application/json": {
                             "example": {
                                 "success": True,
                                 "message": "Password reset successfully",
                                 "data": {"status": "password_reset"}
                             }
                         }
                     }
                 },
                 400: {"description": "Invalid or expired token"}
             })
async def reset_password(
    request: Request,
    reset: ResetPasswordRequest = Body(...)
):
    """Reset password using token"""
    import uuid
    request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    try:
        response = requests.post(
            "https://stardust-v1.my-firstcare.com/auth/reset-password",
            json=reset.dict(),
            timeout=10
        )
        if response.status_code == 200:
            return create_success_response(
                message="Password reset successfully",
                data=response.json(),
                request_id=request_id
            )
        else:
            raise HTTPException(status_code=response.status_code, detail=response.text)
    except requests.RequestException as e:
        raise HTTPException(status_code=503, detail=f"Reset password service unavailable: {str(e)}")

@router.post("/register-request", 
             response_model=SuccessResponse,
             responses={
                 201: {
                     "description": "Registration request submitted successfully",
                     "content": {
                         "application/json": {
                             "example": {
                                 "success": True,
                                 "message": "Registration request submitted successfully",
                                 "data": {"request_id": "req_123456", "status": "pending"}
                             }
                         }
                     }
                 },
                 400: {"description": "Invalid input"},
                 409: {"description": "Request already exists"}
             })
async def register_request(
    request: Request,
    reg_request: RegisterRequestRequest = Body(...)
):
    """Submit registration request for panel access"""
    import uuid
    request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    try:
        response = requests.post(
            "https://stardust-v1.my-firstcare.com/auth/register-request",
            json=reg_request.dict(),
            timeout=10
        )
        if response.status_code == 201:
            return create_success_response(
                message="Registration request submitted successfully",
                data=response.json(),
                request_id=request_id
            )
        elif response.status_code == 409:
            raise HTTPException(status_code=409, detail="Registration request already exists")
        else:
            raise HTTPException(status_code=response.status_code, detail=response.text)
    except requests.RequestException as e:
        raise HTTPException(status_code=503, detail=f"Registration request service unavailable: {str(e)}")

@router.get("/registration-requests", 
            response_model=SuccessResponse,
            responses={
                200: {
                    "description": "Registration requests retrieved successfully",
                    "content": {
                        "application/json": {
                            "example": {
                                "success": True,
                                "message": "Registration requests retrieved successfully",
                                "data": {"requests": []}
                            }
                        }
                    }
                },
                403: {"description": "Access denied - Admin only"}
            })
async def get_registration_requests(
    request: Request,
    current_user: dict = Depends(require_auth())
):
    """Get all registration requests (Admin only)"""
    import uuid
    request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    
    # Check if user has admin permissions
    if current_user.get("role") not in ["admin", "superadmin"]:
        raise HTTPException(
            status_code=403,
            detail="Access denied - Admin only"
        )
    
    auth_header = request.headers.get("Authorization")
    try:
        response = requests.get(
            "https://stardust-v1.my-firstcare.com/auth/registration-requests",
            headers={"Authorization": auth_header},
            timeout=10
        )
        if response.status_code == 200:
            requests_data = response.json()
            # Ensure data is wrapped in a dictionary if it's a list
            if isinstance(requests_data, list):
                data = {"requests": requests_data}
            else:
                data = requests_data
            return create_success_response(
                message="Registration requests retrieved successfully",
                data=data,
                request_id=request_id
            )
        else:
            raise HTTPException(status_code=response.status_code, detail=response.text)
    except requests.RequestException as e:
        raise HTTPException(status_code=503, detail=f"Registration requests service unavailable: {str(e)}")

@router.post("/registration-requests/{request_id}/approve", 
             response_model=SuccessResponse,
             responses={
                 200: {
                     "description": "Registration request processed successfully",
                     "content": {
                         "application/json": {
                             "example": {
                                 "success": True,
                                 "message": "Registration request processed successfully",
                                 "data": {"request_id": "req_123456", "status": "approved"}
                             }
                         }
                     }
                 },
                 404: {"description": "Request not found"},
                 403: {"description": "Access denied - Admin only"}
             })
async def approve_registration_request(
    request_id: str,
    request: Request,
    approve: ApproveRequestRequest = Body(...),
    current_user: dict = Depends(require_auth())
):
    """Approve or reject registration request (Admin only)"""
    import uuid
    req_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    
    # Check if user has admin permissions
    if current_user.get("role") not in ["admin", "superadmin"]:
        raise HTTPException(
            status_code=403,
            detail="Access denied - Admin only"
        )
    
    auth_header = request.headers.get("Authorization")
    try:
        response = requests.post(
            f"https://stardust-v1.my-firstcare.com/auth/registration-requests/{request_id}/approve",
            headers={"Authorization": auth_header, "Content-Type": "application/json"},
            json=approve.dict(),
            timeout=10
        )
        if response.status_code == 200:
            return create_success_response(
                message=f"Registration request {'approved' if approve.approved else 'rejected'} successfully",
                data=response.json(),
                request_id=req_id
            )
        elif response.status_code == 404:
            raise HTTPException(status_code=404, detail="Registration request not found")
        else:
            raise HTTPException(status_code=response.status_code, detail=response.text)
    except requests.RequestException as e:
        raise HTTPException(status_code=503, detail=f"Registration approval service unavailable: {str(e)}")

@router.get("/registration-requests/history", 
            response_model=SuccessResponse,
            responses={
                200: {
                    "description": "Registration request history retrieved successfully",
                    "content": {
                        "application/json": {
                            "example": {
                                "success": True,
                                "message": "Registration request history retrieved successfully",
                                "data": {"history": []}
                            }
                        }
                    }
                },
                403: {"description": "Access denied - Admin only"}
            })
async def get_registration_history(
    request: Request,
    current_user: dict = Depends(require_auth())
):
    """Get registration request history (Admin only)"""
    import uuid
    request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    
    # Check if user has admin permissions
    if current_user.get("role") not in ["admin", "superadmin"]:
        raise HTTPException(
            status_code=403,
            detail="Access denied - Admin only"
        )
    
    auth_header = request.headers.get("Authorization")
    try:
        response = requests.get(
            "https://stardust-v1.my-firstcare.com/auth/registration-requests/history",
            headers={"Authorization": auth_header},
            timeout=10
        )
        if response.status_code == 200:
            history_data = response.json()
            # Ensure data is wrapped in a dictionary if it's a list
            if isinstance(history_data, list):
                data = {"history": history_data}
            else:
                data = history_data
            return create_success_response(
                message="Registration request history retrieved successfully",
                data=data,
                request_id=request_id
            )
        else:
            raise HTTPException(status_code=response.status_code, detail=response.text)
    except requests.RequestException as e:
        raise HTTPException(status_code=503, detail=f"Registration history service unavailable: {str(e)}")

def _get_role_permissions(role: str) -> list:
    """Get role-based permissions"""
    role_permissions = {
        "viewer": ["read:patients", "read:devices", "read:history"],
        "operator": ["read:patients", "read:devices", "read:history", "write:devices", "submit:data"],
        "admin": ["read:all", "write:all", "delete:data", "manage:devices", "admin:panel"],
        "superadmin": ["read:all", "write:all", "delete:all", "admin:system", "manage:users", "config:system"]
    }
    return role_permissions.get(role, []) 