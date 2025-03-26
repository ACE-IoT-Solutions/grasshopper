from typing import Literal

from pydantic import BaseModel


class MessageStatus(BaseModel):
    status: Literal["accepted", "success", "error"]
    message: str
