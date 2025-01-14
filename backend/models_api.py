from typing import Optional

from pydantic import BaseModel


class ResponseModel(BaseModel):
    """Standard response model for API endpoints"""

    status: str
    message: str
    data: Optional[dict] = None


class ErrorResponseModel(BaseModel):
    """Error response model for API endpoints"""

    status: str
    message: str
