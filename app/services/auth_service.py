from typing import Optional
from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from datetime import datetime, timedelta
from bson import ObjectId

from app.core.security import verify_password, get_password_hash, create_access_token, create_refresh_token, verify_token
from app.core.config import settings
from app.models.user import UserCreate, UserInDB, UserLogin, Token
from app.db.database import get_db

security = HTTPBearer()

class AuthService:
    def __init__(self):
        pass
    
    async def create_user(self, user_data: UserCreate, db) -> UserInDB:
        """Create a new user."""
        # Check if user already exists
        existing_user = await db.users.find_one({"email": user_data.email})
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        
        # Hash password
        hashed_password = get_password_hash(user_data.password)
        
        # Create user document
        user_dict = user_data.dict(exclude={"password"})
        user_dict["hashed_password"] = hashed_password
        user_dict["created_at"] = datetime.utcnow()
        user_dict["updated_at"] = datetime.utcnow()
        
        # Insert user
        result = await db.users.insert_one(user_dict)
        user_dict["_id"] = result.inserted_id
        
        return UserInDB(**user_dict)
    
    async def authenticate_user(self, login_data: UserLogin, db) -> Optional[UserInDB]:
        """Authenticate user with email and password."""
        user = await db.users.find_one({"email": login_data.email})
        if not user:
            return None
        
        if not verify_password(login_data.password, user["hashed_password"]):
            return None
        
        # Update last login
        await db.users.update_one(
            {"_id": user["_id"]},
            {"$set": {"last_login": datetime.utcnow()}}
        )
        
        return UserInDB(**user)
    
    async def create_tokens(self, user: UserInDB) -> Token:
        """Create access and refresh tokens for user."""
        access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
        access_token = create_access_token(
            data={"sub": user.email, "user_id": str(user.id)},
            expires_delta=access_token_expires
        )
        
        refresh_token = create_refresh_token(
            data={"sub": user.email, "user_id": str(user.id)}
        )
        
        return Token(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=settings.access_token_expire_minutes * 60
        )
    
    async def get_current_user(self, credentials: HTTPAuthorizationCredentials = Depends(security), db = Depends(get_db)) -> UserInDB:
        """Get current authenticated user from token."""
        token = credentials.credentials
        
        try:
            payload = verify_token(token)
            email: str = payload.get("sub")
            user_id: str = payload.get("user_id")
            
            if email is None or user_id is None:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Could not validate credentials",
                    headers={"WWW-Authenticate": "Bearer"},
                )
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        user = await db.users.find_one({"_id": ObjectId(user_id)})
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        if not user.get("is_active", True):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Inactive user"
            )
        
        return UserInDB(**user)
    
    async def get_current_active_user(self, current_user: UserInDB = Depends(get_current_user)) -> UserInDB:
        """Get current active user."""
        if not current_user.is_active:
            raise HTTPException(status_code=400, detail="Inactive user")
        return current_user
    
    async def get_current_admin_user(self, current_user: UserInDB = Depends(get_current_active_user)) -> UserInDB:
        """Get current admin user."""
        if current_user.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not enough permissions"
            )
        return current_user
    
    async def refresh_token(self, refresh_token: str, db) -> Token:
        """Refresh access token using refresh token."""
        try:
            payload = verify_token(refresh_token)
            email: str = payload.get("sub")
            user_id: str = payload.get("user_id")
            token_type: str = payload.get("type")
            
            if email is None or user_id is None or token_type != "refresh":
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid refresh token"
                )
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token"
            )
        
        user = await db.users.find_one({"_id": ObjectId(user_id)})
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found"
            )
        
        user_obj = UserInDB(**user)
        return await self.create_tokens(user_obj)

# Create service instance
auth_service = AuthService()



# Dependency to get current user
async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db = Depends(get_db)
):
    """Get current authenticated user."""
    try:
        token = credentials.credentials
        payload = verify_token(token)
        email: str = payload.get("sub")
        user_id: str = payload.get("user_id")
        token_type: str = payload.get("type")
        
        if email is None or user_id is None or token_type != "access":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )
    
    user = await db.users.find_one({"_id": ObjectId(user_id)})
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
    
    return UserInDB(**user)

