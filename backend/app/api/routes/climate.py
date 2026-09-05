from fastapi import APIRouter,Depends,Query
from fastapi.middleware.cors import CORSMiddleware
from app.services.climate_service import ClimateService
from app.services.interpolation_service import InterpolationService
from app.core.config import settings

router = APIRouter(prefix="/api/climate",tags=["climate"])

async def get_climate_service():
    """Provee una instancia de ClimateService y la limpia al final"""
    service = ClimateService()
    try:
        yield service
    finally:      
        await service.close()

@router.get("/all")
async def get_all_climate(
    climate_service: ClimateService = Depends(get_climate_service)):
    """
    Obtener datos climáticos de todas las ciudades.
    
    Returns:
        ClimateResponse: Datos completos de todas las ciudades
    """
    return await climate_service.get_all_climate_data()

@router.get("/heatmap")
async def get_heatmap_points(
    climate_service: ClimateService = Depends(get_climate_service)):
    """
    Obtener puntos para el mapa de calor (sin interpolación).
    
    Returns:
        List[HeatmapPoint]: Puntos de las ciudades reales
    """
    data = await climate_service.get_all_climate_data()
    return climate_service.generate_heatmap_points(data)

@router.get("/heatmap/interpolated")
async def get_interpolated_heatmap(
    resolution:int = Query(40,ge=20, le=100, description="resolucion de la grilla"),
    climate_service: ClimateService = Depends(get_climate_service)):
        """
        Obtener mapa de calor con interpolación IDW.

        Args:
            resolution: Número de puntos por lado (total = resolution^2)
                        Mayor resolución = más detalle pero más lento

        Returns:
            dict: {
                interpolated: List[HeatmapPoint] - Puntos estimados,
                cities: List[HeatmapPoint] - Ciudades reales,
                total_points: int - Total de puntos
            }
        """
        data = await climate_service.get_all_climate_data()
        interpolation = InterpolationService()
        interpolation.grid_resolution = resolution
        
        return interpolation.generate_heatmap_with_cities(data)

@router.get("/cities")
async def get_cities():
    """
    Obtener lista de ciudades disponibles.
    
    Returns:
        List[dict]: Lista de ciudades con nombre, latitud y longitud
    """
    cities = []
    for city_str in settings.CITIES.split('|'):
        name, coords = city_str.split(':')
        lat, lon = coords.split(',')
        cities.append({
            'name': name,
            'lat': float(lat),
            'lon': float(lon)
        })
    return cities