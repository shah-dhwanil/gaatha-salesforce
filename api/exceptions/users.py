from .app import AppException, ErrorTypes


class UserNotFoundException(AppException):
    def __init__(
        self, field: str, message: str = "User doesn't exists with given details"
    ):
        super().__init__(
            ErrorTypes.ResourceNotFound, message=message, resource="user", field=field
        )


class UserAlreadyExistsException(AppException):
    def __init__(
        self, field: str, message: str = "User already exists with given details"
    ):
        super().__init__(
            ErrorTypes.ResourceAlreadyExists,
            message=message,
            resource="user",
            field=field,
        )
