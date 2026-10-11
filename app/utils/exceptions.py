"""
Custom Domain Exceptions for Pharmavigil
Encapsulates domain-specific business errors and database exceptions.
"""


class PharmavigilException(Exception):
    """Base exception for all Pharmavigil domain errors."""
    pass


class DatabaseConnectionError(PharmavigilException):
    """Raised when establishing a connection to MySQL or MongoDB fails."""
    def __init__(self, message: str = "Failed to connect to the database engine.", original_exception: Exception = None):
        super().__init__(message)
        self.original_exception = original_exception


class ExpiredBatchDispenseError(PharmavigilException):
    """Raised when an operation attempts to dispense or distribute an expired medicine batch."""
    def __init__(self, batch_number: str, expiry_date: str = None, message: str = None):
        default_msg = f"Cannot dispense or distribute expired batch '{batch_number}' (Expiry Date: {expiry_date})."
        super().__init__(message or default_msg)
        self.batch_number = batch_number
        self.expiry_date = expiry_date


class RecalledBatchOperationError(PharmavigilException):
    """Raised when an operation is attempted on a batch that has been recalled or placed under investigation."""
    def __init__(self, batch_number: str, recall_status: str = "RECALLED", message: str = None):
        default_msg = f"Operation rejected: Batch '{batch_number}' is marked as '{recall_status}'."
        super().__init__(message or default_msg)
        self.batch_number = batch_number
        self.recall_status = recall_status


class InvalidSeverityScoreError(PharmavigilException):
    """Raised when an adverse reaction severity score falls outside the valid [1, 5] range."""
    def __init__(self, score: int, message: str = None):
        default_msg = f"Invalid severity score: {score}. Severity score must be an integer between 1 and 5 (inclusive)."
        super().__init__(message or default_msg)
        self.score = score


class BatchMedicineMismatchError(PharmavigilException):
    """Raised when a batch does not belong to the selected medicine formulation."""
    def __init__(self, batch_number: str, medicine_id: int, expected_medicine_id: int = None, message: str = None):
        default_msg = f"Batch mismatch: Batch '{batch_number}' does not belong to medicine ID {medicine_id}."
        super().__init__(message or default_msg)
        self.batch_number = batch_number
        self.medicine_id = medicine_id
        self.expected_medicine_id = expected_medicine_id


class UnauthorizedAccessError(PharmavigilException):
    """Raised when a user attempts to access a portal or resource without proper role authorization."""
    def __init__(self, role: str, resource: str, message: str = None):
        default_msg = f"Unauthorized access: Role '{role}' does not have permission to access '{resource}'."
        super().__init__(message or default_msg)
        self.role = role
        self.resource = resource


