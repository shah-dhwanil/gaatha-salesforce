from api.exceptions.app import AppException, ErrorTypes

class UserAlreadyExistsException(AppException):
    """Exception raised when a user already exists."""
    def __init__(self, field: str, message: str):
        super().__init__(ErrorTypes.ResourceAlreadyExists, message, field=field)

class UserNotFoundException(AppException):
    """Exception raised when a user is not found."""
    def __init__(self, field: str, message: str="User not found"):
        super().__init__(ErrorTypes.ResourceNotFound, message, field=field)

class UserException(AppException):
    """Exception raised when a user operation fails."""
    def __init__(self, message: str):
        super().__init__(ErrorTypes.InvalidOperation, message)

class UserValidationException(AppException):
    """Exception raised when user validation fails."""
    def __init__(self, message: str, field: str = None, value=None):
        super().__init__(
            ErrorTypes.ValidationError,
            message,
            field=field,
            value=value,
        )

class UserOperationException(AppException):
    """Exception raised when a user operation fails."""
    def __init__(self, message: str, operation: str = None):
        super().__init__(
            ErrorTypes.InvalidOperation,
            message,
            operation=operation,
        )