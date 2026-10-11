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

# In-Memory Demo Users (Used for immediate demonstration or when DB user table is not yet seeded)
DEMO_CREDENTIALS = {
    "doctor_smith": {
        "password": "doctor123",
        "role": ROLE_DOCTOR_PATIENT,
        "full_name": "Dr. Sarah Smith, MD",
        "email": "dr.smith@stjudehospital.org"
    },
    "pharmacist_jane": {
        "password": "pharmacist123",
        "role": ROLE_PHARMACIST,
        "full_name": "Jane Doe, PharmD",
        "email": "jane.doe@centralpharmacy.com"
    },
    "admin_officer": {
        "password": "admin123",
        "role": ROLE_SAFETY_OFFICER_ADMIN,
        "full_name": "Chief Safety Officer Miller",
        "email": "compliance@pharmavigil.gov"
    }
}


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
    """
    Authenticates a user against the MySQL users table.
    Falls back gracefully to demo credentials if MySQL is offline or users table is empty.
    """
    cleaned_username = username.strip().lower()

    # 1. Try MySQL Database authentication
    try:
        from app.database.mysql_client import mysql_client
        query = "SELECT user_id, username, password_hash, role, full_name, email FROM users WHERE LOWER(username) = %s"
        user_row = mysql_client.execute_one(query, (cleaned_username,))
        
        if user_row:
            stored_hash = user_row.get("password_hash", "")
            # Check bcrypt / salted hash
            if verify_password(password, stored_hash):
                return {
                    "user_id": user_row["user_id"],
                    "username": user_row["username"],
                    "role": user_row["role"],
                    "full_name": user_row["full_name"],
                    "email": user_row["email"],
                    "source": "mysql"
                }
            # Also allow fallback match against demo accounts if seed used sample placeholder
            if cleaned_username in DEMO_CREDENTIALS and password == DEMO_CREDENTIALS[cleaned_username]["password"]:
                return {
                    "user_id": user_row["user_id"],
                    "username": user_row["username"],
                    "role": user_row["role"],
                    "full_name": user_row["full_name"],
                    "email": user_row["email"],
                    "source": "mysql_demo_sync"
                }
    except Exception:
        # Fallback to local demo credentials for seamless demo/offline presentations
        pass

    # 2. Check in-memory demo credentials
    if cleaned_username in DEMO_CREDENTIALS:
        demo = DEMO_CREDENTIALS[cleaned_username]
        if password == demo["password"]:
            return {
                "user_id": 999,
                "username": cleaned_username,
                "role": demo["role"],
                "full_name": demo["full_name"],
                "email": demo["email"],
                "source": "in_memory_demo"
            }

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

