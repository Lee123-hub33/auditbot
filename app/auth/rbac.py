# app/auth/rbac.py
from fastapi import HTTPException, Depends
from app.auth.jwt import get_current_user
from app.models import UserRole

ROLE_HIERARCHY = {
    UserRole.VIEWER: 0,
    UserRole.UPLOADER: 1,
    UserRole.REVIEWER: 2,
    UserRole.ADMIN: 3,
}


def require_role(minimum_role: UserRole):
    """
    Dependency factory. Use as:
        @router.get("/...", dependencies=[Depends(require_role(UserRole.REVIEWER))])
    """

    async def checker(current_user: dict = Depends(get_current_user)):
        user_role_str = current_user.get("role", UserRole.VIEWER.value)
        try:
            user_role = UserRole(user_role_str)
        except ValueError:
            raise HTTPException(status_code=403, detail="Invalid role in token")

        if ROLE_HIERARCHY[user_role] < ROLE_HIERARCHY[minimum_role]:
            raise HTTPException(
                status_code=403,
                detail=f"Access denied. Required role: {minimum_role.value}",
            )
        return current_user

    return checker


# Shorthand dependencies for common patterns
require_viewer = require_role(UserRole.VIEWER)
require_uploader = require_role(UserRole.UPLOADER)
require_reviewer = require_role(UserRole.REVIEWER)
require_admin = require_role(UserRole.ADMIN)
