from pydantic import BaseModel, Field


class APPConfig(BaseModel):
    host: str = Field(default='0.0.0.0')
    port: int = Field(default=8080)
    routers: list[str] = ['cassanova_router']
