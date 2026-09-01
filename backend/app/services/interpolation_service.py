from math import radians, sin, cos, sqrt, atan2
from typing import List,Tuple,Dict
from app.models.climate import HeatmapPoint
from app.services.climate_service import ClimateResponse

class InterpolationService:
    """Servicio para la interpolacion en el mapa"""

    def __init__(self):
        self.lat_min = -4.0
        self.lat_max = 12.5
        self.lon_min = -79.0
        self.lon_max = -67.0
        self.grid_resolution = 40
        self.power = 2
        self.max_distance = 500

    def haversine_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:     
        R = 6371

        lat1_rad = radians(lat1)
        lon1_rad = radians(lon1)
        lat2_rad = radians(lat2)
        lon2_rad = radians(lon2)

        dlat = lat2_rad - lat1_rad
        dlon = lon2_rad - lon1_rad

        a = sin(dlat/2)**2 + cos(lat1_rad) * cos(lat2_rad) * sin(dlon/2)**2        
        
        c = 2 * atan2(sqrt(a), sqrt(1-a))

        distancia = R * c
        return distancia

    def generate_grid(self) -> List[Tuple[float,float]]:
        """Genera una grilla de puntos que cubren Colombia"""

        lat_step = (self.lat_max-self.lat_min)/self.grid_resolution
        lon_step = (self.lon_max-self.lon_min)/self.grid_resolution

        points = []

        for i in range(self.grid_resolution):     
            lat = self.lat_min + i * lat_step + lat_step/2
            for j in range(self.grid_resolution):  
                lon = self.lon_min + j * lon_step + lon_step/2
                points.append((lat,lon))
        return points

    def filter_land_points(self, points):
        """
        Filtrar puntos en el mar.
        Mantiene solo los puntos que están en tierra firme.
        """
        
        
        zonas_mar = [
            {'lat_min': -4.0, 'lat_max': 8.0, 'lon_min': -79.0, 'lon_max': -77.5},
            {'lat_min': 10.0, 'lat_max': 12.5, 'lon_min': -76.0, 'lon_max': -71.0},
            {'lat_min': -4.0, 'lat_max': 6.0, 'lon_min': -68.0, 'lon_max': -67.0},
        ]
        
        puntos_tierra = []
        
        for lat, lon in points:
            es_mar = False  
            for zona in zonas_mar:
                if (zona['lat_min'] <= lat <= zona['lat_max'] and 
                    zona['lon_min'] <= lon <= zona['lon_max']):
                    es_mar = True  
                    break  
            
            if not es_mar:
                puntos_tierra.append((lat, lon))
        
        return puntos_tierra

    def interpolate_value(self, lat: float, lon: float, city_data: List[Dict], max_distance: float) -> float:
        """
        Interpolar un valor usando IDW (Inverse Distance Weighting)
        
        Args:
            lat: Latitud del punto
            lon: Longitud del punto
            city_data: Lista de diccionarios con lat, lon, value
            max_distance: Distancia máxima de influencia (km)
        
        Returns:
            Valor interpolado (temperatura o precipitación)
        """
        
        numerador = 0.0
        denominador = 0.0
        
        for ciudad in city_data:
            lat_ciudad = ciudad['lat']
            lon_ciudad = ciudad['lon']
            valor_ciudad = ciudad['value']
            
            distancia = self.haversine_distance(lat, lon, lat_ciudad, lon_ciudad)
            
            if distancia < 0.1:
                return valor_ciudad            
            if distancia > max_distance:
                continue

            peso = 1 / (distancia ** self.power)
            
            numerador += peso * valor_ciudad
            denominador += peso
        
        if denominador == 0:
            return sum(c['value'] for c in city_data) / len(city_data)
        
        return numerador / denominador

    def generate_heatmap_points(self, climate_data: ClimateResponse) -> List[HeatmapPoint]:
        """
        Generar todos los puntos del mapa de calor (interpolados + ciudades reales)
        
        Args:
            climate_data: Datos climáticos de todas las ciudades (ClimateResponse)
        
        Returns:
            Lista de HeatmapPoint con todos los puntos para el mapa
        """
        
        city_data_temp = []
        city_data_precip = []
        city_data_wind_speed = []
        city_data_wind_direction = []
        
        for city in climate_data.cities:
            city_data_temp.append({
                'lat': city.coordinates.lat,
                'lon': city.coordinates.lon,
                'value': city.current.temperature
            })

            city_data_precip.append({
                'lat': city.coordinates.lat,
                'lon': city.coordinates.lon,
                'value': city.daily.precipitation[0] if city.daily.precipitation else 0
            })

            city_data_wind_speed.append({
                'lat': city.coordinates.lat,
                'lon': city.coordinates.lon,
                'value': city.current.wind_speed
            })

            city_data_wind_direction.append({
                'lat': city.coordinates.lat,
                'lon': city.coordinates.lon,
                'value': city.current.wind_direction
            })
        
        grid_points = self.generate_grid()        
        land_points = self.filter_land_points(grid_points)
        
        heatmap_points = []
        
        for lat, lon in land_points:
            temp = self.interpolate_value(lat, lon, city_data_temp, self.max_distance)            
            precip = self.interpolate_value(lat, lon, city_data_precip, self.max_distance)
            wind_speed = self.interpolate_value(lat, lon, city_data_wind_speed, self.max_distance) 
            wind_direction = self.interpolate_value(lat, lon, city_data_wind_direction, self.max_distance) 

            wind_direction = wind_direction % 360
            
            if -5 < temp < 45: 
                heatmap_points.append(HeatmapPoint(
                    lat=lat,
                    lon=lon,
                    temp=round(temp, 1),
                    wind_speed=round(wind_speed, 1), 
                    wind_direction=round(wind_direction, 1),
                    precipitation=round(precip, 1),
                    city=""  
                ))
        
        for city in climate_data.cities:
            heatmap_points.append(HeatmapPoint(
                lat=city.coordinates.lat,
                lon=city.coordinates.lon,
                temp=city.current.temperature,
                wind_speed=city.current.wind_speed,  
                wind_direction=city.current.wind_direction,
                precipitation=city.daily.precipitation[0] if city.daily.precipitation else 0,
                city=city.city 
            ))
        
        return heatmap_points

    def generate_heatmap_with_cities(self, climate_data: ClimateResponse) -> dict:
        """
        Generar puntos del mapa de calor separando interpolados de ciudades reales
        
        Args:
            climate_data: Datos climáticos de todas las ciudades (ClimateResponse)
        
        Returns:
            Diccionario con:
            - interpolated: Lista de HeatmapPoint (puntos estimados)
            - cities: Lista de HeatmapPoint (ciudades reales)
            - total_points: Número total de puntos
        """
        
        heatmap_points = self.generate_heatmap_points(climate_data)
        
        interpolated_points = []
        city_points = []
        
        for point in heatmap_points:
            if point.city == "":
                interpolated_points.append(point)
            else:
                city_points.append(point)
        
        return {
            'interpolated': interpolated_points,
            'cities': city_points,
            'total_points': len(heatmap_points)
        }

            
