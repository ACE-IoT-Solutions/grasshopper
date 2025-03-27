from pydantic import BaseModel

class NetworkData(BaseModel):
    nodes: list
    edges: list