import httpx
import asyncio
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from app.core.config import settings
from app.models.city import City, Coordinates
from app.models.climate import (
    CityClimate, CurrentWeather, DailyWeather,
    ClimateResponse, HeatmapPoint
)

class ClimateService:
    """Servicio para obtener datos climáticos de Open-Meteo con UNA SOLA PETICIÓN BATCH"""

    # Cuánto tiempo se sigue sirviendo el último batch bueno como fallback
    # mientras Open-Meteo está caído (429/503/lo que sea). Pasado esto, se
    # prefiere devolver una respuesta vacía y explícita antes que un dato
    # demasiado viejo para un dashboard climático "en vivo".
    CACHE_MAX_AGE = timedelta(minutes=45)

    def __init__(self):
        self.api_url = settings.CLIMATE_API_URL
        self.cities = self._parse_cities(settings.CITIES)
        self.client = httpx.AsyncClient(timeout=60.0)
        self._last_good_batch: Optional[List[Dict]] = None
        self._last_good_at: Optional[datetime] = None
        self._last_call_was_stale: bool = False

    @property
    def last_updated_at(self) -> Optional[datetime]:
        """Cuándo se obtuvo por última vez un dato REAL (no de caché) de Open-Meteo."""
        return self._last_good_at

    @property
    def is_serving_stale_data(self) -> bool:
        """True si la última llamada a get_batch_climate_data devolvió caché, no datos frescos."""
        return self._last_call_was_stale

    def _parse_cities(self, cities_str: str) -> List[City]:
        cities = []
        if not cities_str:
            return cities

        for index, raw in enumerate(cities_str.split('|')):
            city_str = raw.strip()
            if not city_str:
                continue

            if ':' not in city_str:
                print(f"⚠️ [CITIES #{index}] Formato incorrecto (falta ':'): '{city_str}'")
                continue

            name, coords = city_str.rsplit(':', 1)
            name = name.strip()
            coords = coords.strip()

            if not name:
                print(f"⚠️ [CITIES #{index}] Nombre vacío en: '{city_str}'")
                continue

            if ',' not in coords:
                print(f"⚠️ [CITIES #{index}] Coordenadas incorrectas: '{coords}'")
                continue

            lat_str, lon_str = coords.split(',', 1)
            try:
                lat = float(lat_str.strip())
                lon = float(lon_str.strip())
            except ValueError:
                print(f"⚠️ [CITIES #{index}] Lat/lon no numéricos: '{coords}'")
                continue

            cities.append(City(
                name=name,
                coordinates=Coordinates(lat=lat, lon=lon)
            ))

        if not cities:
            print("⚠️ ADVERTENCIA: no se pudo parsear ninguna ciudad desde CITIES.")
        else:
            print(f"✅ {len(cities)} ciudades cargadas correctamente")

        return cities

    async def get_batch_climate_data(self, retries: int = 2) -> Optional[List[Dict]]:
        """
        Obtiene datos de TODAS las ciudades en UNA SOLA petición.

        Si Open-Meteo falla (429/503) después de los reintentos RÁPIDOS de
        esta función, en vez de devolver None (que vacía todo el dashboard),
        se sirve el último batch que sí funcionó — marcado como stale vía
        last_updated_at / is_serving_stale_data — así el usuario sigue
        viendo un mapa, aunque un poco viejo, en vez de una pantalla vacía.

        Los reintentos de ESTA función son deliberadamente cortos (segundos,
        no los 5-15 minutos que puede durar un 503 de Open-Meteo): corren
        dentro de una petición HTTP en vivo del propio frontend. La
        recuperación ante un apagón largo viene de que este método se
        vuelve a llamar en el siguiente ciclo (UPDATE_INTERVAL) — si para
        entonces la API ya volvió, el caché se refresca solo; si no, se
        sigue sirviendo el fallback hasta CACHE_MAX_AGE.
        """
        if not self.cities:
            print("❌ No hay ciudades configuradas")
            return None

        lats = ','.join(str(city.coordinates.lat) for city in self.cities)
        lons = ','.join(str(city.coordinates.lon) for city in self.cities)

        params = {
            'latitude': lats,
            'longitude': lons,
            'current_weather': 'true',
            'daily': 'temperature_2m_max,temperature_2m_min,precipitation_sum',
            'hourly': 'wind_speed_10m,wind_direction_10m',
            'timezone': 'America/Bogota',
            'forecast_days': 7
        }

        for attempt in range(retries):
            try:
                print(f"📡 Solicitando datos para {len(self.cities)} ciudades...")
                response = await self.client.get(self.api_url, params=params)
                response.raise_for_status()
                data = response.json()

                if not isinstance(data, list):
                    print(f"❌ La respuesta no es una lista, es {type(data)}")
                    break  # error de formato, no de disponibilidad: reintentar no ayuda

                print(f"✅ Datos recibidos: {len(data)} resultados")
                self._last_good_batch = data
                self._last_good_at = datetime.now()
                self._last_call_was_stale = False
                return data

            except httpx.HTTPStatusError as e:
                if e.response.status_code == 429:
                    wait_time = 3 * (attempt + 1)
                    print(f"⚠️ 429 en petición batch. Reintentando en {wait_time}s...")
                    await asyncio.sleep(wait_time)
                    continue
                elif e.response.status_code == 503:
                    wait_time = 5 * (attempt + 1)
                    print(f"⚠️ 503 en petición batch. Reintentando en {wait_time}s...")
                    await asyncio.sleep(wait_time)
                    continue
                print(f"❌ Error HTTP en petición batch: {e}")
                break
            except httpx.HTTPError as e:
                print(f"❌ Error en petición batch: {e}")
                break

        # Se agotaron los reintentos rápidos, o hubo un error no
        # recuperable reintentando: caemos al último dato bueno, si existe
        # y no es demasiado viejo para seguir siendo útil.
        if self._last_good_batch is not None and self._last_good_at is not None:
            age = datetime.now() - self._last_good_at
            minutes = int(age.total_seconds() // 60)
            if age <= self.CACHE_MAX_AGE:
                print(f"♻️ Open-Meteo no responde. Sirviendo caché de hace {minutes} min como fallback.")
                self._last_call_was_stale = True
                return self._last_good_batch
            else:
                max_minutes = int(self.CACHE_MAX_AGE.total_seconds() // 60)
                print(f"❌ Open-Meteo no responde y el caché tiene {minutes} min "
                      f"(> {max_minutes} min máx). Se descarta por ser demasiado viejo.")

        print(f"❌ Falló después de {retries} intentos y no hay caché útil disponible")
        return None

    def _extract_city_data(self, city: City, city_data: Dict) -> Optional[CityClimate]:
        """Extrae los datos de una ciudad desde su respuesta individual."""
        try:
            current = city_data['current_weather']
            daily = city_data['daily']
            hourly = city_data.get('hourly', {})
            
            wind_dirs = hourly.get('wind_direction_10m', [0.0]) if hourly else [0.0]

            return CityClimate(
                city=city.name,
                coordinates=city.coordinates,
                current=CurrentWeather(
                    temperature=current['temperature'],
                    weather_code=current['weathercode'],
                    wind_speed=current['windspeed'],
                    wind_direction=wind_dirs[0] if wind_dirs else 0.0,
                    timestamp=current['time']
                ),
                daily=DailyWeather(
                    max_temp=daily['temperature_2m_max'],
                    min_temp=daily['temperature_2m_min'],
                    precipitation=daily['precipitation_sum'],
                    dates=daily['time']
                )
            )
        except (KeyError, IndexError, TypeError) as e:
            print(f"⚠️ Error parseando datos de {city.name}: {e}")
            return None

    async def get_all_climate_data(self) -> ClimateResponse:
        """Obtiene datos de todas las ciudades en UNA sola petición batch."""
        batch_data = await self.get_batch_climate_data()

        if not batch_data:
            print("❌ No se pudieron obtener datos de Open-Meteo")
            return ClimateResponse(
                timestamp=datetime.now().isoformat(),
                cities=[],
                is_stale=False,
                data_updated_at=None
            )

        if len(batch_data) != len(self.cities):
            print(f"⚠️ Número de resultados ({len(batch_data)}) no coincide con ciudades ({len(self.cities)})")

        results = []
        for i, city in enumerate(self.cities):
            if i < len(batch_data):
                city_climate = self._extract_city_data(city, batch_data[i])
                if city_climate:
                    results.append(city_climate)
            else:
                print(f"⚠️ No hay datos para {city.name}")

        print(f"✅ {len(results)} ciudades procesadas correctamente")
        return ClimateResponse(
            timestamp=datetime.now().isoformat(),
            cities=results,
            is_stale=self.is_serving_stale_data,
            data_updated_at=self.last_updated_at.isoformat() if self.last_updated_at else None
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