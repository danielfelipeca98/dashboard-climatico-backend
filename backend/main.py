import asyncio
import json
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.routes import climate
from app.api.websocket.manager import manager
from app.services.climate_service import ClimateService


async def broadcast_climate_data(climate_service: ClimateService):
    """
    Tarea en segundo plano que envía datos climáticos a todos los clientes
    conectados por WebSocket, cada UPDATE_INTERVAL segundos.

    Recibe el ClimateService COMPARTIDO (creado una sola vez en el lifespan)
    en vez de crear el suyo propio — así su caché/TTL interno es el MISMO
    que usan los endpoints REST y el WebSocket, no uno aislado.
    """
    try:
        while True:
            await asyncio.sleep(settings.UPDATE_INTERVAL)

            try:
                data = await climate_service.get_all_climate_data()
                await manager.broadcast(json.dumps({
                    "type": "climate_update",
                    "data": data.model_dump()
                }))
                print(f" Datos broadcast enviados: {data.timestamp}")
            except Exception as e:
                print(f" Error en broadcast: {e}")
    except asyncio.CancelledError:
        # Cancelación normal al apagar la app, no es un error.
        raise


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Maneja el ciclo de vida de la aplicación.

    ClimateService se crea UNA SOLA VEZ aquí y se guarda en app.state —
    es el único punto de la app que habla con Open-Meteo. Los endpoints
    REST, el WebSocket y la tarea de broadcast reciben todos esta MISMA
    instancia (ver get_climate_service en app/api/routes/climate.py y
    websocket_endpoint más abajo), en vez de crear cada uno la suya.
    Antes, cada request HTTP creaba su propio ClimateService con su propio
    caché vacío — el TTL/caché interno nunca protegía nada porque el
    objeto que lo guardaba se destruía al terminar cada request.
    """
    app.state.climate_service = ClimateService()

    broadcast_task = asyncio.create_task(
        broadcast_climate_data(app.state.climate_service)
    )
    print(" Servidor iniciado - Broadcast automático activado")

    yield

    broadcast_task.cancel()
    try:
        await broadcast_task
    except asyncio.CancelledError:
        pass

    await app.state.climate_service.close()
    print(" Servidor cerrado - Broadcast detenido")


app = FastAPI(
    title="Dashboard Climático Colombia API",
    description="API para dashboard climático en tiempo real con interpolación",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(climate.router)


@app.get("/")
async def root():
    """Endpoint raíz para verificar que la API está funcionando"""
    return {
        "message": "Dashboard Climático Colombia API",
        "version": "1.0.0",
        "status": "running",
        "endpoints": [
            "/api/climate/all",
            "/api/climate/heatmap",
            "/api/climate/heatmap/interpolated",
            "/api/climate/cities",
            "/ws"
        ]
    }


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    Endpoint WebSocket para comunicación en tiempo real.

    Usa websocket.app.state.climate_service (la instancia COMPARTIDA) en
    vez de crear su propio ClimateService — antes cada nueva conexión de
    WebSocket disparaba otra llamada aislada a Open-Meteo, con su propio
    caché que nadie más veía.
    """
    await manager.connect(websocket)

    try:
        climate_service: ClimateService = websocket.app.state.climate_service
        data = await climate_service.get_all_climate_data()
        await websocket.send_text(json.dumps({
            "type": "climate_update",
            "data": data.model_dump()
        }))

        while True:
            await websocket.receive_text()

    except Exception as e:
        print(f" Error en WebSocket: {e}")
    finally:
        manager.disconnect(websocket)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=True
    )