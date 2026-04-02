from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.core.config import SECRET_KEY, ALGORITHM
from app.database import get_db
from app.models.user import User

# Define the scheme. auto_error=False allows us to handle missing tokens (e.g. check cookies)
security_scheme = HTTPBearer(auto_error=False)

def get_current_user(
    request: Request,
    token: HTTPAuthorizationCredentials = Depends(security_scheme),
    db: Session = Depends(get_db)
):
    # 1. Check Authorization Header (via HTTPBearer)
    token_str = None
    if token:
        token_str = token.credentials
    
    # 2. Fallback to Cookie
    if not token_str:
        token_str = request.cookies.get("access_token")

    if not token_str:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    try:
        payload = jwt.decode(token_str, SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get("sub")
        if email is None:
            raise HTTPException(status_code=401, detail="Invalid token")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

    user = db.query(User).filter(User.email == email).first()

    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled",
        )

    return user


def require_role(role: str):
    def checker(user: User = Depends(get_current_user)):
        if user.role.lower() != role.lower():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied",
            )
        return user

    return checker


def allow_roles(roles: list[str]):
    def checker(user: User = Depends(get_current_user)):
        # Case-insensitive check
        user_role = user.role.lower()
        allowed = [r.lower() for r in roles]
        
        if user_role not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied",
            )
        return user

    return checker
