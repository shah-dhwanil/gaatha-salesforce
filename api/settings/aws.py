from pydantic import BaseModel, Field

class AWSConfig(BaseModel):
    access_key_id: str = Field(..., description="AWS Access Key ID")
    secret_access_key: str = Field(..., description="AWS Secret Access Key")
    region_name: str = Field(..., description="AWS Region")