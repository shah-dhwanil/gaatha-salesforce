from .app import AppException, ErrorTypes


class AreaNotFoundException(AppException):
    def __init__(self, field: str, message: str = "Area doesn't exists with given details"):
        super().__init__(ErrorTypes.ResourceNotFound, message=message, resource="area", field=field)


class AreaAlreadyExistsException(AppException):
    def __init__(self, field: str, message: str = "Area already exists with given details"):
        super().__init__(ErrorTypes.ResourceAlreadyExists, message=message, resource="area", field=field)
