import os
import secrets
from enum import Enum
from fastapi import Request, HTTPException, Security, Depends
from fastapi.security.api_key import APIKeyHeader
from typing import Optional

class Role(str, Enum):
    ADMIN = "admin"
    OPERATOR = "operator"
    VIEWER = "viewer"
    AUDITOR = "auditor"

# Using a standard X-API-Key header
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

def get_role_for_key(api_key: str) -> Optional[Role]:
    env = os.getenv("RECOVERAI_ENV", "production")
    if not api_key and env == "development":
        return Role.ADMIN
        
    if not api_key:
        return None
        
    # Constant-time comparison for keys
    admin_key = os.getenv("RECOVERAI_ADMIN_KEY")
    if admin_key and secrets.compare_digest(api_key, admin_key):
        return Role.ADMIN
        
    operator_key = os.getenv("RECOVERAI_OPERATOR_KEY")
    if operator_key and secrets.compare_digest(api_key, operator_key):
        return Role.OPERATOR
        
    auditor_key = os.getenv("RECOVERAI_AUDITOR_KEY")
    if auditor_key and secrets.compare_digest(api_key, auditor_key):
        return Role.AUDITOR
        
    viewer_key = os.getenv("RECOVERAI_VIEWER_KEY")
    if viewer_key and secrets.compare_digest(api_key, viewer_key):
        return Role.VIEWER
        
    return None

def require_auth(api_key_header: str = Security(api_key_header)) -> Role:
    """Enforce authentication for protected routes."""
    env = os.getenv("RECOVERAI_ENV", "production")
    if not api_key_header and env == "development":
        return Role.ADMIN

    if not api_key_header:
        raise HTTPException(status_code=401, detail="Authentication credentials were not provided.")
        
    role = get_role_for_key(api_key_header)
    if not role:
        raise HTTPException(status_code=401, detail="Invalid API key.")
        
    return role

def require_role(allowed_roles: list[Role]):
    def role_checker(role: Role = Depends(require_auth)):
        if role not in allowed_roles:
            raise HTTPException(status_code=403, detail="You do not have permission to perform this action.")
        return role
    return role_checker

# Convenience dependencies
require_admin = require_role([Role.ADMIN])
require_operator = require_role([Role.ADMIN, Role.OPERATOR])
require_viewer = require_role([Role.ADMIN, Role.OPERATOR, Role.VIEWER, Role.AUDITOR])
require_auditor = require_role([Role.ADMIN, Role.AUDITOR])
