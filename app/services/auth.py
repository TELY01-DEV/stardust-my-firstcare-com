import requests
from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional, Dict, Any
from config import settings
from loguru import logger

# HTTP Bearer token scheme
http_bearer = HTTPBearer()

class AuthService:
    def __init__(self):
        self.base_url = settings.jwt_auth_base_url
        self.login_endpoint = settings.jwt_login_endpoint
        self.refresh_endpoint = settings.jwt_refresh_endpoint
        self.me_endpoint = settings.jwt_me_endpoint
    
    def verify_token_with_stardust(self, token: str) -> Dict[str, Any]:
        """Verify JWT token with Stardust-V1"""
        try:
            response = requests.get(
                f"{self.base_url}{self.me_endpoint}",
                headers={"Authorization": f"Bearer {token}"},
                timeout=10
            )
            
            if response.status_code == 200:
                user_info = response.json()
                logger.info(f"Token verified successfully for user: {user_info.get('username', 'unknown')}")
                return user_info
            else:
                logger.warning(f"Token verification failed: {response.status_code} - {response.text}")
                raise HTTPException(status_code=401, detail="Invalid or expired token")
                
        except requests.RequestException as e:
            logger.error(f"Stardust-V1 connection error: {e}")
            raise HTTPException(status_code=503, detail="Authentication service unavailable")
    
    def login(self, username: str, password: str) -> Dict[str, Any]:
        """Login with Stardust-V1"""
        try:
            response = requests.post(
                f"{self.base_url}{self.login_endpoint}",
                json={"username": username, "password": password},
                timeout=10
            )
            
            if response.status_code == 200:
                tokens = response.json()
                logger.info(f"Login successful for user: {username}")
                return tokens
            else:
                logger.warning(f"Login failed for user {username}: {response.status_code}")
                raise HTTPException(status_code=401, detail="Invalid credentials")
                
        except requests.RequestException as e:
            logger.error(f"Stardust-V1 login error: {e}")
            raise HTTPException(status_code=503, detail="Authentication service unavailable")
    
    def refresh_token(self, refresh_token: str) -> Dict[str, Any]:
        """Refresh JWT token with Stardust-V1"""
        try:
            response = requests.post(
                f"{self.base_url}{self.refresh_endpoint}",
                json={"refresh_token": refresh_token},
                timeout=10
            )
            
            if response.status_code == 200:
                tokens = response.json()
                logger.info("Token refreshed successfully")
                return tokens
            else:
                logger.warning(f"Token refresh failed: {response.status_code}")
                raise HTTPException(status_code=401, detail="Invalid refresh token")
                
        except requests.RequestException as e:
            logger.error(f"Stardust-V1 refresh error: {e}")
            raise HTTPException(status_code=503, detail="Authentication service unavailable")
    
    async def get_current_user(self, credentials: HTTPAuthorizationCredentials = Depends(http_bearer)) -> Dict[str, Any]:
        """Get current user from JWT token"""
        if not settings.enable_jwt_auth:
            # Return mock user for development
            return {"username": "dev_user", "role": "admin"}
        
        return self.verify_token_with_stardust(credentials.credentials)
    
    async def get_current_user_optional(self, credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False))) -> Optional[Dict[str, Any]]:
        """Get current user from JWT token (optional - returns None if no token)"""
        if not settings.enable_jwt_auth:
            # Return mock user for development
            return {"username": "dev_user", "role": "admin"}
        
        if not credentials:
            return None
        
        try:
            return self.verify_token_with_stardust(credentials.credentials)
        except HTTPException:
            return None
    
    def has_role(self, user: Dict[str, Any], required_roles: list) -> bool:
        """Check if user has any of the required roles"""
        if not user:
            return False
        
        user_role = user.get("role", "").lower()
        required_roles_lower = [role.lower() for role in required_roles]
        
        return user_role in required_roles_lower

# Global auth service instance
auth_service = AuthService()

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(http_bearer)) -> Dict[str, Any]:
    """Get current user from JWT token"""
    if not settings.enable_jwt_auth:
        # Return mock user for development
        return {"username": "dev_user", "role": "admin"}
    
    return auth_service.verify_token_with_stardust(credentials.credentials)

def require_auth():
    """Require authentication - returns a dependency that checks settings at runtime"""
    async def auth_dependency(credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False))) -> Dict[str, Any]:
        if not settings.enable_jwt_auth:
            # Return mock user for development
            logger.debug("JWT authentication disabled - returning mock user")
            return {"username": "dev_user", "role": "admin"}
        
        # Authentication is enabled - require valid token
        if not credentials:
            logger.warning("Authentication required but no credentials provided")
            raise HTTPException(
                status_code=401, 
                detail="Authorization header required. Please provide a valid Bearer token."
            )
        
        logger.debug(f"Verifying token for authentication")
        return auth_service.verify_token_with_stardust(credentials.credentials)
    
    return auth_dependency 