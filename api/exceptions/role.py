from .app import AppException, ErrorTypes


class RoleNotFoundException(AppException):
    def __init__(
        self, field: str, message: str = "Role doesn't exists with given details"
    ):
        super().__init__(
            ErrorTypes.ResourceNotFound, message=message, resource="role", field=field
        )


class RoleAlreadyExistsException(AppException):
    def __init__(
        self, field: str, message: str = "Role already exists with given details"
    ):
        super().__init__(
            ErrorTypes.ResourceAlreadyExists,
            message=message,
            resource="role",
            field=field,
        )
