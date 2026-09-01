import asyncio
import json
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.routes import climate
from app.api.websocket.manager import manager
from app.services.climate_service import ClimateService


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manejar el ciclo de vida de la aplicación..."""
    broadcast_task = asyncio.create_task(broadcast_climate_data())  
    print(" Servidor iniciado - Broadcast automático activado")   
    yield                                                 
    broadcast_task.cancel()                                
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
    """Endpoint WebSocket para comunicación en tiempo real"""
    await manager.connect(websocket)
    
    try:
        climate_service = ClimateService()
        try:
            data = await climate_service.get_all_climate_data()
            await websocket.send_text(json.dumps({
                "type": "climate_update",
                "data": data.dict()
            }))
        finally:
            await climate_service.close()
        
        while True:
            await websocket.receive_text()
            
    except Exception as e:
        print(f" Error en WebSocket: {e}")
    finally:
        manager.disconnect(websocket)


async def broadcast_climate_data():
    """Tarea en segundo plano que envía datos climáticos a todos los clientes"""
    climate_service = ClimateService()
    
    try:
        while True:
            await asyncio.sleep(settings.UPDATE_INTERVAL)
            
            try:
                data = await climate_service.get_all_climate_data()
                await manager.broadcast(json.dumps({
                    "type": "climate_update",
                    "data": data.dict()
                }))
                print(f" Datos broadcast enviados: {data.timestamp}")
            except Exception as e:
                print(f" Error en broadcast: {e}")
                
    finally:
        await climate_service.close()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=True
    )