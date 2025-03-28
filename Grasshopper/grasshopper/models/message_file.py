from pydantic import BaseModel


class MessageFile(BaseModel):
    message: str
    file_path: str
