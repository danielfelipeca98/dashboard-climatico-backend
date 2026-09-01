from pydantic import BaseModel, Field

class Coordinates(BaseModel):
    lat: float = Field(..., ge=-90, le=90)
    lon: float = Field(..., ge=-180, le=180)

class City(BaseModel):
    name: str = Field(...,min_length=3,max_length=50, description="nombre de la ciudad")
    coordinates: Coordinates