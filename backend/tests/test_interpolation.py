import pytest
from math import isclose
from app.services.interpolation_service import InterpolationService
from app.models.climate import HeatmapPoint

def test_haversine_bogota_medellin():
    service = InterpolationService()
    distance = service.haversine_distance(4.61, -74.08, 6.24, -75.57)
    assert isclose(distance, 240, abs_tol=10)

def test_haversine_same_point():
    service = InterpolationService()
    distance = service.haversine_distance(4.61, -74.08, 4.61, -74.08)
    assert isclose(distance , 0)

def test_grid_resolution_10():
    service = InterpolationService()
    service.grid_resolution = 10
    points = service.generate_grid()
    assert len(points) == 100

def test_grid_resolution_40():
    service = InterpolationService()
    service.grid_resolution = 40
    points = service.generate_grid()
    assert len(points) == 1600

def test_filter_ocean_points():
    service = InterpolationService()
    points = [(5.0, -78.0)]  
    filtered = service.filter_land_points(points)
    assert len(filtered) == 0

def test_filter_land_point():
    service = InterpolationService()
    points = [(4.61, -74.08)]  
    filtered = service.filter_land_points(points)
    assert len(filtered) == 1
    assert filtered[0] == (4.61, -74.08)

def test_interpolate_exact_city():
    service = InterpolationService()
    city_data = [
        {'lat': 4.61, 'lon': -74.08, 'value': 18.5}
    ]
    valor = service.interpolate_value(4.61, -74.08, city_data, 500)
    assert valor == 18.5

def test_interpolate_between_cities():
    service = InterpolationService()
    city_data = [
        {'lat': 4.61, 'lon': -74.08, 'value': 18.5},
        {'lat': 6.24, 'lon': -75.57, 'value': 24.2}
    ]
    valor = service.interpolate_value(5.4, -74.8, city_data, 500)
    assert 18.5 < valor < 24.2

def test_generate_heatmap_points():
    service = InterpolationService()
    climate_data = create_test_climate_data()
    points = service.generate_heatmap_points(climate_data)
    
    assert len(points) > len(climate_data.cities)
    
    city_points = [p for p in points if p.city != ""]
    assert len(city_points) == len(climate_data.cities)

def create_test_climate_data():
    from app.models.city import Coordinates
    from app.models.climate import (
        ClimateResponse, CityClimate, CurrentWeather, DailyWeather
    )
    
    coords_bogota = Coordinates(lat=4.61, lon=-74.08)
    coords_medellin = Coordinates(lat=6.24, lon=-75.57)
    
    current_bogota = CurrentWeather(
        temperature=18.5,
        weather_code=2,
        wind_speed=12.3,
        wind_direction=270,
        timestamp="2024-01-15T14:30:00"
    )
    
    daily_bogota = DailyWeather(
        max_temp=[20.0, 21.0, 22.0, 23.0, 24.0, 25.0, 26.0],
        min_temp=[10.0, 11.0, 12.0, 13.0, 14.0, 15.0, 16.0],
        precipitation=[0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0],
        dates=["2024-01-15", "2024-01-16", "2024-01-17", "2024-01-18", 
               "2024-01-19", "2024-01-20", "2024-01-21"]
    )
    
    city_bogota = CityClimate(
        city="Bogotá",
        coordinates=coords_bogota,
        current=current_bogota,
        daily=daily_bogota
    )
    
    current_medellin = CurrentWeather(
        temperature=24.2,
        weather_code=1,
        wind_speed=8.5,
        wind_direction=180,
        timestamp="2024-01-15T14:30:00"
    )
    
    daily_medellin = DailyWeather(
        max_temp=[26.0, 27.0, 28.0, 29.0, 30.0, 31.0, 32.0],
        min_temp=[18.0, 19.0, 20.0, 21.0, 22.0, 23.0, 24.0],
        precipitation=[0.0, 0.0, 0.5, 1.0, 0.0, 0.0, 0.0],
        dates=["2024-01-15", "2024-01-16", "2024-01-17", "2024-01-18",
               "2024-01-19", "2024-01-20", "2024-01-21"]
    )
    
    city_medellin = CityClimate(
        city="Medellín",
        coordinates=coords_medellin,
        current=current_medellin,
        daily=daily_medellin
    )
    
    return ClimateResponse(
        timestamp="2024-01-15T14:30:00",
        cities=[city_bogota, city_medellin]
    )