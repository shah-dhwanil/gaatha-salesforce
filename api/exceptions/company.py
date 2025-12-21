from .app import AppException, ErrorTypes


class CompanyNotFoundException(AppException):
    def __init__(
        self, field: str, message: str = "Company doesn't exist with given details"
    ):
        super().__init__(
            ErrorTypes.ResourceNotFound,
            message=message,
            resource="company",
            field=field,
        )


class CompanyAlreadyExistsException(AppException):
    def __init__(
        self, field: str, message: str = "Company already exists with given details"
    ):
        super().__init__(
            ErrorTypes.ResourceAlreadyExists,
            message=message,
            resource="company",
            field=field,
        )
