from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    """Configuración de la aplicación desde variables de entorno"""
    PORT: int = 8000
    HOST: str = "0.0.0.0"
    
    CLIMATE_API_URL: str = "https://api.open-meteo.com/v1/forecast"
    
    CITIES: str = "Bogotá:4.61,-74.08|Medellín:6.24,-75.57|Cali:3.45,-76.52|Barranquilla:10.96,-74.80|Bucaramanga:7.12,-73.12" 
    
    UPDATE_INTERVAL: int = 300
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()