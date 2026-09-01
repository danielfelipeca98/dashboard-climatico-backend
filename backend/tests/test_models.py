import pytest
from pydantic import ValidationError
from app.models.city import City, Coordinates
from app.models.climate import CurrentWeather, DailyWeather, CityClimate, ClimateResponse, HeatmapPoint

def test_valid_coordinates():
    data = Coordinates(lat=4.61, lon=-74.08)
    assert data.lat == 4.61
    assert data.lon == -74.08

def test_invalid_lat_gt_90():
    with pytest.raises(ValidationError):
        Coordinates(lat = 200, lon = -74.08)

def test_invalid_lat_lt_neg90():
    with pytest.raises(ValidationError):
        Coordinates(lat=-100, lon=-74.08)

def test_invalid_lon_gt_180():
    with pytest.raises(ValidationError):
        Coordinates(lat=4.61, lon=200)

def test_invalid_lon_lt_neg180():
    with pytest.raises(ValidationError):
        Coordinates(lat=4.61, lon=-200)

##Ciudad

def test_valid_city():
    coords = Coordinates(lat = 4.61,lon = -74.08)
    city = City(name="Bogotá", coordinates= coords)
    assert city.name == "Bogotá"
    assert city.coordinates.lat == 4.61
    assert city.coordinates.lon == -74.08

def test_city_name_too_short():
    coords = Coordinates(lat = 4.61,lon = -74.08)
    with pytest.raises(ValidationError):
        City(name="Bo", coordinates=coords)

def test_city_name_too_long():
    coords = Coordinates(lat = 4.61,lon = -74.08)
    with pytest.raises(ValidationError):
        City(name="Un nombre extremadamente largo que supera los 50 caracteres facilmente porque es muy largo", coordinates=coords)

##Clima
def test_valid_current_weather():
    data = CurrentWeather(temperature=18.5,weather_code=2,wind_speed=12.3,wind_direction=270,timestamp="2024-01-15T14:30:00")
    assert data.temperature == 18.5
    assert data.weather_code == 2
    assert data.wind_speed == 12.3
    assert data.timestamp == "2024-01-15T14:30:00"

def test_current_temp_gt_46():
    with pytest.raises(ValidationError):
        CurrentWeather(temperature=50,
            weather_code=2,
            wind_speed=12.3,
            wind_direction=270,
            timestamp="2024-01-15T14:30:00")
        
def test_current_temp_lt_neg10():
    with pytest.raises(ValidationError):
        CurrentWeather(temperature=-15,
            weather_code=2,
            wind_speed=12.3,
            wind_direction=270,
            timestamp="2024-01-15T14:30:00")
        
def test_weather_code_gt_99():
    with pytest.raises(ValidationError):
        CurrentWeather(temperature=18.5,
            weather_code=100,
            wind_speed=12.3,
            wind_direction=270,
            timestamp="2024-01-15T14:30:00")
        
def test_weather_code_lt_0():
    with pytest.raises(ValidationError):
        CurrentWeather(temperature=18.5,
            weather_code=-1,
            wind_speed=12.3,
            wind_direction=270,
            timestamp="2024-01-15T14:30:00")

def test_valid_daily_weather():
    max_temp = [20.0, 21.0, 22.0, 23.0, 24.0, 25.0, 26.0]
    min_temp = [10.0, 11.0, 12.0, 13.0, 14.0, 15.0, 16.0]
    precipitation = [0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0]
    dates = ["2024-01-15", "2024-01-1", "2024-01-15", "2024-01-11", "2024-01-12", "2024-01-13", "2024-01-14" ]
    daily = DailyWeather(max_temp=max_temp, min_temp=min_temp, precipitation=precipitation, dates=dates)

    assert len(daily.max_temp) == 7
    assert daily.max_temp[0] == 20.

def test_daily_weather_6_items():
    with pytest.raises(ValidationError):
        max_temp = [20.0, 21.0, 22.0, 23.0, 24.0, 25.0]
        min_temp = [10.0, 11.0, 12.0, 13.0, 14.0, 15.0]
        precipitation = [0.0, 0.5, 1.0, 1.5, 2.0, 2.5]
        dates = ["2024-01-15", "2024-01-1", "2024-01-11", "2024-01-12", "2024-01-13", "2024-01-14" ]
        DailyWeather(max_temp=max_temp, min_temp=min_temp, precipitation=precipitation, dates=dates)

def test_daily_weather_8_items():
    with pytest.raises(ValidationError):
        max_temp = [20.0, 21.0, 22.0, 23.0, 24.0, 25.0, 26.0, 26.0]
        min_temp = [10.0, 11.0, 12.0, 13.0, 14.0, 15.0, 16.0, 26.0]
        precipitation = [0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 26.0]
        dates = ["2024-01-15", "2024-01-1", "2024-01-15", "2024-01-11", "2024-01-12", "2024-01-13", "2024-01-14","2024-01-14" ]
        DailyWeather(max_temp=max_temp, min_temp=min_temp, precipitation=precipitation, dates=dates)

def test_valid_heatmap_point():
    data = HeatmapPoint(lat=4.61, lon=-74.08, temp=18.5, precipitation=2.3,wind_speed=12.3, wind_direction=270)
    assert data.lat == 4.61
    assert data.lon == -74.08
    assert data.temp == 18.5
    assert data.city == ""

def test_heatmap_with_city():
    data = HeatmapPoint(
        lat=4.61,
        lon=-74.08,
        temp=18.5,
        precipitation=2.3,
        wind_speed=12.3, 
        wind_direction=270,
        city="Bogotá"
    )
    assert data.city == "Bogotá"

def test_heatmap_invalid_lat():
    with pytest.raises(ValidationError):
        HeatmapPoint(
            lat=200,
            lon=-74.08,
            temp=18.5,
            precipitation=2.3,
            city="Bogotá"
        )
