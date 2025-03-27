from pydantic import BaseModel

class Data(BaseModel):
    data: list[str]