# Routes Package 

# Auth router
from fastapi import APIRouter, HTTPException, Request, Depends
from pydantic import BaseModel
from app.services.auth import auth_service, require_auth
from app.utils.error_definitions import create_error_response, create_success_response

router = APIRouter(prefix="/auth", tags=["Authentication"])

class LoginRequest(BaseModel):
    username: str
    password: str

class RefreshRequest(BaseModel):
    refresh_token: str

@router.post("/simple-login")
async def simple_login():
    """Simple test login endpoint"""
    return {"message": "Simple login endpoint working", "status": "ok"}

@router.post("/login")
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
            return {
                "success": True,
                "message": "Login successful",
                "access_token": tokens.get("access_token"),
                "refresh_token": tokens.get("refresh_token"),
                "token_type": tokens.get("token_type", "bearer"),
                "user": tokens.get("user", {})
            }
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

@router.post("/refresh")
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
            return {
                "success": True,
                "message": "Token refreshed successfully",
                "access_token": tokens.get("access_token"),
                "token_type": tokens.get("token_type", "bearer")
            }
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

@router.get("/me")
async def get_me(request: Request, current_user: dict = Depends(require_auth())):
    """Get current user info"""
    request_id = request.headers.get("X-Request-ID")
    
    success_response = create_success_response(
        message="User information retrieved successfully",
        data=current_user,
        request_id=request_id
    )
    return success_response.dict() 