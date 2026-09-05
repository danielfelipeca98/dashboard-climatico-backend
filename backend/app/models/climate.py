from pydantic import BaseModel, Field
from typing import List, Optional
from app.models.city import Coordinates

class CurrentWeather(BaseModel):
    """Modelo del clima actual"""
    temperature: float = Field(..., ge=-10, le=45, description="Temperatura en °C")
    weather_code: int = Field(..., ge=0, le=99, description="Código del clima (0-99)")
    wind_speed: float = Field(..., ge=0, description="Velocidad del viento en km/h")
    wind_direction: float = Field(..., ge=0, le=360, description="Dirección del viento en grados")
    timestamp: str = Field(..., description="Marca de tiempo ISO")

class DailyWeather(BaseModel):
    """Modelo del clima semanal"""
    max_temp: List[float] = Field(..., min_length=7, max_length=7, description="Temperaturas máximas (°C)")
    min_temp: List[float] = Field(..., min_length=7, max_length=7, description="Temperaturas mínimas (°C)")
    precipitation: List[float] = Field(..., min_length=7, max_length=7, description="Precipitación (mm)")
    dates: List[str] = Field(..., min_length=7, max_length=7, description="Fechas en formato ISO")

class CityClimate(BaseModel):
    """Clima completo de una ciudad"""
    city: str = Field(..., min_length=3, description="Nombre de la ciudad")
    coordinates: Coordinates
    current: CurrentWeather
    daily: DailyWeather

class ClimateResponse(BaseModel):
    """Respuesta con el clima de todas las ciudades"""
    timestamp: str = Field(..., description="Marca de tiempo de generación de ESTA respuesta (siempre 'ahora')")
    cities: List[CityClimate] = Field(..., description="Lista de ciudades con su clima")
    is_stale: bool = Field(
        default=False,
        description="True si los datos vienen del caché de fallback (Open-Meteo no respondió) en vez de ser frescos"
    )
    data_updated_at: Optional[str] = Field(
        default=None,
        description="Marca de tiempo ISO de cuándo se obtuvo por última vez un dato REAL de Open-Meteo "
                    "(distinto de 'timestamp' cuando is_stale=True)"
    )

class HeatmapPoint(BaseModel):
    """Punto para el mapa de calor (interpolado o real)"""
    lat: float = Field(..., ge=-90, le=90, description="Latitud del punto")
    lon: float = Field(..., ge=-180, le=180, description="Longitud del punto")
    temp: float = Field(..., ge=-10, le=45, description="Temperatura en °C")
    wind_speed: float = Field(..., ge=0, description="Velocidad del viento en km/h")
    wind_direction: float = Field(..., ge=0, le=360, description="Dirección del viento en grados")
    precipitation: float = Field(..., ge=0, description="Precipitación en mm")
    city: str = Field(default="", description="Nombre de la ciudad (vacío si es interpolado)")