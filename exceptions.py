class AppError(Exception):
    """Base application error."""


class ValidationError(AppError):
    """Validation error for user input."""


class AuthenticationError(AppError):
    """Authentication-related error."""


class FileOperationError(AppError):
    """File operation error."""
