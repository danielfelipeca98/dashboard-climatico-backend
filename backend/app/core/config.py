from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    """Configuración de la aplicación desde variables de entorno"""
    PORT: int = 8000
    HOST: str = "0.0.0.0"
    
    CLIMATE_API_URL: str = "https://api.open-meteo.com/v1/forecast"
    
    CITIES: str = "Bogotá:4.61,-74.08|Medellín:6.24,-75.57|Cali:3.45,-76.52|Barranquilla:10.96,-74.80|Bucaramanga:7.12,-73.12|Cartagena:10.40,-75.50|Santa Marta:11.24,-74.20|Pereira:4.81,-75.70|Manizales:5.06,-75.52|Cúcuta:7.90,-72.50|Ibagué:4.44,-75.23|Neiva:2.93,-75.28|Villavicencio:4.15,-73.63|Popayán:2.44,-76.61|Armenia:4.53,-75.68|Sincelejo:9.30,-75.39|Valledupar:10.48,-73.25|Montería:8.75,-75.88|Quibdó:5.69,-76.65|Riohacha:11.54,-72.90|Tunja:5.54,-73.36|Pasto:1.21,-77.28|Florencia:1.61,-75.61|Yopal:5.35,-72.40|Mocoa:1.15,-76.65|Arauca:7.09,-70.76|Puerto Carreño:6.18,-67.49|Mitú:1.25,-70.23|Leticia:-4.21,-69.93|San José del Guaviare:2.56,-72.63|Inírida:3.86,-67.92|Tuluá:4.08,-76.19|Buga:3.90,-76.30|Zipaquirá:5.03,-74.00|Facatativá:4.82,-74.36|Girardot:4.31,-74.80|Melgar:4.20,-74.65|Fusagasugá:4.33,-74.36|Sogamoso:5.72,-72.93|Duitama:5.83,-73.02|Chiquinquirá:5.62,-73.82"
    
    UPDATE_INTERVAL: int = 1200
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()