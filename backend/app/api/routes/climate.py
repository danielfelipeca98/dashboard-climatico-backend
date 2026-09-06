from fastapi import APIRouter, Depends, Query, Request
from app.services.climate_service import ClimateService
from app.services.interpolation_service import InterpolationService

router = APIRouter(prefix="/api/climate", tags=["climate"])


async def get_climate_service(request: Request) -> ClimateService:
    """
    Devuelve la instancia ÚNICA de ClimateService creada en el lifespan de
    la app (main.py) — NO crea una nueva por cada request.

    Esto es lo que hace que el caché/TTL en memoria de ClimateService
    (y por tanto el límite real de llamadas a Open-Meteo) sea compartido
    entre /all, /heatmap, /heatmap/interpolated, el WebSocket y el
    broadcast en segundo plano, en vez de que cada uno tenga su propio
    caché aislado (que era el bug real detrás de "demasiadas consultas").
    """
    return request.app.state.climate_service


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
    resolution: int = Query(40, ge=20, le=100, description="resolucion de la grilla"),
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
async def get_cities(
    climate_service: ClimateService = Depends(get_climate_service)):
    """
    Obtener lista de ciudades disponibles.

    Reutiliza climate_service.cities (ya parseado y validado por
    _parse_cities al arrancar el servicio) en vez de volver a parsear el
    string CITIES a mano aquí: la versión anterior de este endpoint hacía
    `name, coords = city_str.split(':')` sin ninguna protección, es decir,
    el mismo ValueError de "not enough values to unpack" que ya se arregló
    en ClimateService podía volver a pasar aquí si una entrada de CITIES
    estaba mal formada.

    Returns:
        List[dict]: Lista de ciudades con nombre, latitud y longitud
    """
    return [
        {
            'name': city.name,
            'lat': city.coordinates.lat,
            'lon': city.coordinates.lon
        }
        for city in climate_service.cities
    ]