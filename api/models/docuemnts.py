from typing import Any, Optional
from uuid import UUID
from pydantic import BaseModel, Field

class Document(BaseModel):
    """Model for a document."""
    class UploadFile(BaseModel):
        id: UUID = Field(..., description="Document ID")
        name: str = Field(..., min_length=1, max_length=255, description="Document name")
        mime_type: str = Field(..., min_length=1, max_length=255, description="Document mime type")
        extra_info: dict[str, Any] = Field(..., description="Document extra information")
        url:str = Field(..., description="Document URL")
    files:list[UploadFile] = Field(default_factory=list, description="Document files")


class DocumentInDB(Document):
    """Model for a document in the database."""
    class UploadFile(BaseModel):
        id: UUID = Field(..., description="Document ID")
        name: str = Field(..., min_length=1, max_length=255, description="Document name")
        mime_type: str = Field(..., min_length=1, max_length=255, description="Document mime type")
        extra_info: dict[str, Any] = Field(..., description="Document extra information")
    files:list[UploadFile] = Field(default_factory=list, description="Document files")


class DocumentCreate(Document):
    """Model for creating a document."""
    class UploadFile(BaseModel):
        name: str = Field(..., min_length=1, max_length=255, description="Document name")
        mime_type: str = Field(..., min_length=1, max_length=255, description="Document mime type")
        size: int = Field(..., description="Document size")
        extra_info: dict[str, Any] = Field(..., description="Document extra information")
    files:list[UploadFile] = Field(..., description="Document files")

class DocumentCreateResponse(Document):
    """Model for creating a document response."""
    class UploadFile(BaseModel):
        id: UUID = Field(..., description="Document ID")
        name: str = Field(..., min_length=1, max_length=255, description="Document name")
        upload_url: str = Field(..., description="Document URL")
    files:list[UploadFile] = Field(..., description="Document files")
