from pydantic import BaseModel


class PluginCreate(BaseModel):

    name: str
    description: str

class PluginResponse(BaseModel):

    id: int
    name: str
    description: str
    path: str
    manifest: dict
    enabled: bool

    class Config:
        from_attributes = True

class TaskCreate(BaseModel):

    plugin_id: int
    parameters: dict


class TaskResponse(BaseModel):

    id: int
    plugin_id: int
    parameters: dict
    status: str
    error: str | None

    class Config:
        from_attributes = True