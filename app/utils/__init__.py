"""
Utilities, security authentication, and custom domain exceptions.
"""

from app.utils.exceptions import (
    PharmavigilException,
    DatabaseConnectionError,
    ExpiredBatchDispenseError,
    RecalledBatchOperationError,
    InvalidSeverityScoreError,
    BatchMedicineMismatchError,
    UnauthorizedAccessError
)
from app.utils.auth import (
    authenticate_user,
    hash_password,
    verify_password,
    get_allowed_portals,
    verify_portal_access,
    PORTAL_DOCTOR,
    PORTAL_PHARMACIST,
    PORTAL_ADMIN,
    ROLE_DOCTOR_PATIENT,
    ROLE_PHARMACIST,
    ROLE_SAFETY_OFFICER_ADMIN,
    ALL_ROLES
)

__all__ = [
    "PharmavigilException",
    "DatabaseConnectionError",
    "ExpiredBatchDispenseError",
    "RecalledBatchOperationError",
    "InvalidSeverityScoreError",
    "BatchMedicineMismatchError",
    "UnauthorizedAccessError",
    "authenticate_user",
    "hash_password",
    "verify_password",
    "get_allowed_portals",
    "verify_portal_access",
    "PORTAL_DOCTOR",
    "PORTAL_PHARMACIST",
    "PORTAL_ADMIN",
    "ROLE_DOCTOR_PATIENT",
    "ROLE_PHARMACIST",
    "ROLE_SAFETY_OFFICER_ADMIN",
    "ALL_ROLES"
]
