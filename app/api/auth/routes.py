from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer
from app.models.user import UserCreate, UserLogin, Token, User
from app.services.auth_service import auth_service
from app.db.database import get_db

router = APIRouter()
security = HTTPBearer()

@router.post("/register", response_model=User, status_code=status.HTTP_201_CREATED)
async def register(user_data: UserCreate, db = Depends(get_db)):
    """Register a new user."""
    try:
        user = await auth_service.create_user(user_data, db)
        return User(**user.dict())
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create user"
        )

@router.post("/login", response_model=Token)
async def login(login_data: UserLogin, db = Depends(get_db)):
    """Login user and return tokens."""
    user = await auth_service.authenticate_user(login_data, db)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    
    tokens = await auth_service.create_tokens(user)
    return tokens

@router.post("/refresh", response_model=Token)
async def refresh_token(refresh_token: str, db = Depends(get_db)):
    """Refresh access token."""
    try:
        tokens = await auth_service.refresh_token(refresh_token, db)
        return tokens
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )

@router.get("/me", response_model=User)
async def get_current_user_info(current_user = Depends(auth_service.get_current_active_user)):
    """Get current user information."""
    return User(**current_user.dict())

@router.post("/logout")
async def logout():
    """Logout user (client should discard tokens)."""
    return {"message": "Successfully logged out"}

