from typing import Generic, TypeVar
from pydantic import BaseModel

Model = TypeVar("Model", bound=BaseModel)


class ResponseModel(BaseModel, Generic[Model]):
    status_code: int
    data: Model


class ListResponseModel(BaseModel, Generic[Model]):
    status_code: int
    data: list[Model]
    records_per_page: int
    total_count: int
