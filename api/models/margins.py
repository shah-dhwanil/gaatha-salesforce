from typing import Literal, Optional
from pydantic import BaseModel, Field

class Margin(BaseModel):
    class MarginData:
        margin_type: Literal["MARKUP","MARKDOWN","FIXED"]
        margin_value: float
    super_stockist:Optional[MarginData] = None
    distributor:Optional[MarginData] = None
    retail:Optional[MarginData] = None