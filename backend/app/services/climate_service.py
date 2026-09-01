import httpx
import asyncio
from typing import List, Dict, Optional
from datetime import datetime
from app.core.config import settings
from app.models.city import City,Coordinates
from app.models.climate import (
    CityClimate, CurrentWeather, DailyWeather,
    ClimateResponse, HeatmapPoint
)

class ClimateService:
    """Servicio para obtener datos climáticos de Open-Meteo"""

    def __init__(self):
        self.api_url = settings.CLIMATE_API_URL
        self.cities = self._parse_cities(settings.CITIES)
        self.client = httpx.AsyncClient(timeout=30.0)

    def _parse_cities(self, cities_str: str) -> List[City]:
        cities = []
        for city_str in cities_str.split('|'):
            name,coords =city_str.split(':')
            lat,lon = coords.split(',')
            cities.append(City(
                name=name,
                coordinates=Coordinates(lat=float(lat), lon=float(lon))
            ))
        return cities

    async def get_city_climate(self, lat: float, lon: float) -> Dict:
        params = {
            'latitude': lat,
            'longitude': lon,
            'current_weather': 'true',
            'daily': 'temperature_2m_max,temperature_2m_min,precipitation_sum',
            'hourly': 'wind_speed_10m,wind_direction_10m',
            'timezone': 'America/Bogota',
            'forecast_days': 7
        }
        try:
            response = await self.client.get(self.api_url, params=params)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            print(f" Error obteniendo clima: {e}")
            return None

    async def get_all_climate_data(self) -> ClimateResponse:
        results = []
        tasks = []
        for city in self.cities:
            task = self.get_city_climate(
                city.coordinates.lat,
                city.coordinates.lon
            )
            tasks.append(task)
        climate_data_list = await asyncio.gather(*tasks)
        for city, climate_data in zip(self.cities, climate_data_list):
            if climate_data:
                results.append(CityClimate(
                    city=city.name,
                    coordinates=city.coordinates,
                    current=CurrentWeather(
                        temperature=climate_data['current_weather']['temperature'],
                        weather_code=climate_data['current_weather']['weathercode'],
                        wind_speed=climate_data['current_weather']['windspeed'],
                        wind_direction=climate_data['hourly']['wind_direction_10m'][0],            
                        timestamp=climate_data['current_weather']['time']
                    ),
                    daily=DailyWeather(
                        max_temp=climate_data['daily']['temperature_2m_max'],
                        min_temp=climate_data['daily']['temperature_2m_min'],
                        precipitation=climate_data['daily']['precipitation_sum'],
                        dates=climate_data['daily']['time']
                    )
                ))
        return ClimateResponse(
            timestamp=datetime.now().isoformat(),
            cities=results
        )

    def generate_heatmap_points(self, climate_data: ClimateResponse) -> List[HeatmapPoint]:
        points = []
        for city in climate_data.cities:
            points.append(HeatmapPoint(
                lat=city.coordinates.lat,
                lon=city.coordinates.lon,
                temp=city.current.temperature,
                wind_speed=city.current.wind_speed,         
                wind_direction=city.current.wind_direction,     
                precipitation=city.daily.precipitation[0] if city.daily.precipitation else 0,
                city=city.city
            ))
        return points

    async def close(self):
        await self.client.aclose()