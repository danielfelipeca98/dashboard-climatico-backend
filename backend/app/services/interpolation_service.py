from math import radians, sin, cos, sqrt, atan2
from typing import List,Tuple,Dict
from shapely.geometry import Point, Polygon
from app.models.climate import HeatmapPoint
from app.services.climate_service import ClimateResponse

class InterpolationService:
    """Servicio para la interpolacion en el mapa"""

    def __init__(self):
        self.lat_min = -4.0
        self.lat_max = 12.5
        self.lon_min = -79.0
        self.lon_max = -67.0
        self.grid_resolution = 100 
        self.power = 2
        self.max_distance = 500

        colombia_coords = [
            (-71.56, 12.45), (-71.32, 11.85), (-71.98, 11.66), (-72.49, 11.12),
            (-73.38, 9.17), (-72.78, 9.08), (-72.0, 7.02), (-70.12, 6.98),
            (-69.25, 6.08), (-67.45, 6.19), (-67.86, 4.56), (-67.29, 3.4),
            (-67.83, 2.83), (-67.19, 2.39), (-66.87, 1.22), (-67.42, 2.14),
            (-67.91, 1.75), (-69.85, 1.71), (-69.84, 1.07), (-69.12, 0.65),
            (-70.04, 0.59), (-69.38, -1.34), (-69.96, -4.24), (-70.72, -3.78),
            (-70.29, -2.51), (-71.7, -2.15), (-72.88, -2.51), (-73.56, -1.37),
            (-75.29, -0.12), (-77.38, 0.38), (-78.59, 1.24), (-78.81, 1.44),
            (-78.57, 2.43), (-77.74, 2.6), (-77.03, 3.92), (-77.43, 4.03),
            (-77.34, 6.57), (-77.89, 7.23), (-77.22, 7.94), (-77.37, 8.67),
            (-76.76, 7.92), (-76.93, 8.57), (-75.63, 9.45), (-75.27, 10.8),
            (-74.86, 11.13), (-74.39, 10.74), (-74.16, 11.33), (-73.28, 11.3),
            (-71.56, 12.45),
        ]
        self.COLOMBIA_POLYGON = Polygon(colombia_coords)
        if not self.COLOMBIA_POLYGON.is_valid:
            
            self.COLOMBIA_POLYGON = self.COLOMBIA_POLYGON.buffer(0)
    
    def filter_colombia_points(self, points):
        """
        Filtra puntos (lat, lon) que caen dentro del polígono de Colombia.

        OJO: Shapely usa la convención (x, y) = (lon, lat), pero los puntos
        de la grilla vienen como (lat, lon) (ver generate_grid). Si se pasa
        el tuple directo a Point(), los ejes quedan invertidos respecto al
        polígono (que sí está en lon/lat) y CONTAINS() nunca es True para
        ningún punto: el mapa interpolado sale completamente vacío. Por eso
        se invierte aquí el orden antes de construir el Point.
        """
        colombia = self.COLOMBIA_POLYGON
        return [p for p in points if colombia.contains(Point(p[1], p[0]))]

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
        [OBSOLETO] Ya no se usa. Antes filtraba puntos "en el mar" con tres
        rectángulos aproximados a mano, pero eran tan imprecisos que también
        excluían tierra firme real (gran parte de la costa Pacífica de Chocó
        y Nariño caía dentro de esos rectángulos). Con COLOMBIA_POLYGON
        ahora usando el límite geográfico real, filter_colombia_points ya
        excluye correctamente mar y países vecinos por sí solo — este método
        se deja sin uso por si algún otro código todavía lo importa.
        """
        return points

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
        if not city_data:
            return 0.0
        
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
        if not climate_data.cities:
            return []
    
        city_data_temp = []
        city_data_precip = []
        city_data_wind_speed = []
        city_data_wind_direction = []
        
        for city in climate_data.cities:
            print(city.current.temperature)
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
        colombia_points = self.filter_colombia_points(grid_points)
        
        heatmap_points = []
        
        for lat, lon in colombia_points:
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
        if not climate_data.cities:
            return {
                'interpolated': [],
                'cities': [],
                'total_points': 0
            }
        
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