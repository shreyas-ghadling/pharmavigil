"""
Authentication and Role-Based Access Control (RBAC) Module for Pharmavigil
Uses bcrypt for secure password hashing and verifies user credentials.
"""

import hashlib
import os
from typing import Optional, Dict, Any, List

try:
    import bcrypt
    HAS_BCRYPT = True
except ImportError:
    HAS_BCRYPT = False

# Role Constants
ROLE_DOCTOR_PATIENT = "DOCTOR_PATIENT"
ROLE_PHARMACIST = "PHARMACIST"
ROLE_SAFETY_OFFICER_ADMIN = "SAFETY_OFFICER_ADMIN"

ALL_ROLES = [ROLE_DOCTOR_PATIENT, ROLE_PHARMACIST, ROLE_SAFETY_OFFICER_ADMIN]

def hash_password(password: str) -> str:
    """Hashes a plaintext password using bcrypt (or salted SHA256 fallback)."""
    if HAS_BCRYPT:
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")
    else:
        # Fallback if bcrypt C-extension is not installed
        salt = os.urandom(16).hex()
        digest = hashlib.sha256((salt + password).encode("utf-8")).hexdigest()
        return f"sha256${salt}${digest}"


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies a plaintext password against a stored hash."""
    if not hashed_password:
        return False

    if hashed_password.startswith("$2b$") or hashed_password.startswith("$2a$"):
        if HAS_BCRYPT:
            try:
                return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
            except Exception:
                return False
        else:
            # If bcrypt library is not present, check demo credentials map
            return False

    elif hashed_password.startswith("sha256$"):
        try:
            parts = hashed_password.split("$")
            if len(parts) == 3:
                _, salt, expected_digest = parts
                actual_digest = hashlib.sha256((salt + plain_password).encode("utf-8")).hexdigest()
                return actual_digest == expected_digest
        except Exception:
            return False

    return False


def authenticate_user(username: str, password: str) -> Optional[Dict[str, Any]]:
    """Verify an existing MySQL account; never bypass password verification."""
    from app.database.mysql_client import mysql_client
    row = mysql_client.execute_one(
        "SELECT user_id, username, password_hash, role, full_name, email FROM users WHERE LOWER(username) = %s",
        (username.strip().lower(),),
    )
    if row and verify_password(password, row["password_hash"]):
        return {key: row[key] for key in ("user_id", "username", "role", "full_name", "email")}
    return None


PORTAL_DOCTOR = "1. Doctor & Patient Reporting Portal"
PORTAL_PHARMACIST = "2. Hospital Pharmacist Inventory Portal"
PORTAL_ADMIN = "3. Safety Officer & Admin Control Center"

ROLE_PORTAL_PERMISSIONS = {
    ROLE_DOCTOR_PATIENT: {PORTAL_DOCTOR},
    ROLE_PHARMACIST: {PORTAL_PHARMACIST},
    ROLE_SAFETY_OFFICER_ADMIN: {PORTAL_DOCTOR, PORTAL_PHARMACIST, PORTAL_ADMIN}
}


def get_allowed_portals(role: str) -> List[str]:
    """Returns the list of portals accessible to a specific role."""
    if role == ROLE_SAFETY_OFFICER_ADMIN:
        return [PORTAL_DOCTOR, PORTAL_PHARMACIST, PORTAL_ADMIN]
    elif role == ROLE_PHARMACIST:
        return [PORTAL_PHARMACIST]
    elif role == ROLE_DOCTOR_PATIENT:
        return [PORTAL_DOCTOR]
    return []


def verify_portal_access(role: str, portal_name: str) -> bool:
    """
    Server-side authorization check.
    Raises UnauthorizedAccessError if role is not permitted to access portal_name.
    """
    from app.utils.exceptions import UnauthorizedAccessError
    allowed = ROLE_PORTAL_PERMISSIONS.get(role, set())
    if portal_name not in allowed:
        raise UnauthorizedAccessError(
            role=role,
            resource=portal_name,
            message=f"Access Denied: Role '{role}' is not authorized to access '{portal_name}'."
        )
    return True

