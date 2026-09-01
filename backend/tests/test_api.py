import pytest
from httpx import AsyncClient, ASGITransport
from main import app


@pytest.fixture
def client():
    """Cliente HTTP para pruebas."""
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


@pytest.mark.asyncio
async def test_root(client):
    response = await client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert "endpoints" in data


@pytest.mark.asyncio
async def test_cities(client):
    response = await client.get("/api/climate/cities")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 5
    for city in data:
        assert "name" in city
        assert "lat" in city
        assert "lon" in city


@pytest.mark.asyncio
async def test_all_climate(client):
    response = await client.get("/api/climate/all")
    assert response.status_code == 200
    data = response.json()
    assert "timestamp" in data
    assert "cities" in data
    assert len(data["cities"]) >= 1
    city = data["cities"][0]
    assert "city" in city
    assert "coordinates" in city
    assert "current" in city
    assert "daily" in city


@pytest.mark.asyncio
async def test_heatmap(client):
    response = await client.get("/api/climate/heatmap")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 5
    point = data[0]
    assert "lat" in point
    assert "lon" in point
    assert "temp" in point
    assert "precipitation" in point
    assert "city" in point


@pytest.mark.asyncio
async def test_heatmap_interpolated(client):
    response = await client.get("/api/climate/heatmap/interpolated?resolution=20")
    assert response.status_code == 200
    data = response.json()
    assert "interpolated" in data
    assert "cities" in data
    assert "total_points" in data
    assert data["total_points"] > 0
    assert len(data["interpolated"]) > 0
    assert len(data["cities"]) > 0
    for city in data["cities"]:
        assert city["city"] != ""
    for point in data["interpolated"]:
        assert point["city"] == ""