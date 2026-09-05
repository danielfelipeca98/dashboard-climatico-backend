#  Dashboard Climático Colombia

![Python](https://img.shields.io/badge/Python-3.11-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.104-green)
![Docker](https://img.shields.io/badge/Docker--brightgreen)
![Render](https://img.shields.io/badge/Render--brightgreen)
![Tests](https://img.shields.io/badge/Tests-33%20passing-brightgreen)

Dashboard interactivo que muestra el clima en tiempo real para Colombia utilizando mapas de calor, interpolación de datos y WebSockets.

---

##  Características

-  Mapa de calor interactivo con temperatura y precipitación
-  Visualización de vientos con dirección e intensidad
-  Actualización en tiempo real cada 5 minutos
-  Interpolación IDW para cubrir todo el territorio
-  Datos de 10 ciudades principales de Colombia
-  WebSockets para comunicación en vivo

---

##  Resiliencia y Manejo de Errores

El sistema está diseñado para ser **robusto y tolerante a fallos**:

- **Caché en memoria**: Si Open-Meteo falla (429/503), el sistema sirve los últimos datos válidos durante 45 minutos.
- **Reintentos inteligentes**: Reintentos con backoff para errores 429 y 503.
- **Una sola petición batch**: 41 ciudades en 1 petición (no 41 peticiones individuales).
- **Actualización cada 20 minutos**: Respetando los límites de Open-Meteo (10,000 peticiones/día).

### Límites de Open-Meteo (Free Tier)

| Límite | Valor |
|--------|-------|
| Peticiones por día | 10,000 |
| Peticiones por hora | 5,000 |
| Peticiones por minuto | 600 |

**Configuración actual:**
- 1 petición cada 20 minutos = 72 peticiones/día
- Muy por debajo de los límites → sin riesgo de bloqueo

##  Tecnologías

### Backend
- **FastAPI** 0.104.1 
- **Uvicorn** 0.24.0 
- **WebSockets** 12.0 
- **httpx** 0.25.2 
- **Pydantic** 2.5.0 
- **Geopy** 2.4.1 

### DevOps
- **Docker** 
- **Render** 
- **Git** 

### Pruebas
- **Pytest** 7.4.3 
- **pytest-asyncio** 0.21.1 

---

##  Estructura del Proyecto
```
dashboard-climatico-colombia/
├─ backend/
   ├── app/
   │   ├── api/
   │   │   ├── routes/
   │   │   │   └── climate.py
   │   │   └── websocket/
   │   │       └── manager.py
   │   ├── core/
   │   │   └── config.py
   │   ├── models/
   │   │   ├── city.py
   │   │   └── climate.py
   │   └── services/
   │       ├── climate_service.py
   │       └── interpolation_service.py
   ├── tests/
   │   ├── test_models.py
   │   ├── test_interpolation.py
   │   └── test_api.py
   ├── .env
   ├── .env.production
   ├── .dockerignore
   ├── Dockerfile
   ├── docker-compose.yml
   ├── requirements.txt
   └── main.py
```

##  Archivos Clave

| Archivo | Descripción | Ubicación |
|---------|-------------|-----------|
| `main.py` | Punto de entrada de FastAPI | `backend/` |
| `climate_service.py` | Consulta a Open-Meteo | `backend/app/services/` |
| `interpolation_service.py` | Interpolación IDW | `backend/app/services/` |
| `manager.py` | Gestor de WebSockets | `backend/app/api/websocket/` |
| `climate.py` | Endpoints REST | `backend/app/api/routes/` |
| `config.py` | Variables de entorno | `backend/app/core/` |

---

##  Endpoints de la API

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/` | Información general de la API |
| GET | `/api/climate/all` | Datos completos de todas las ciudades |
| GET | `/api/climate/heatmap` | Puntos del mapa de calor (sin interpolación) |
| GET | `/api/climate/heatmap/interpolated` | Puntos con interpolación IDW |
| WS | `/ws` | WebSocket para datos en tiempo real |

##  Ejemplo de Respuesta

### GET `/api/climate/all`

```json
{
  "timestamp": "2024-01-15T14:30:00",
  "cities": [
    {
      "city": "Bogotá",
      "coordinates": {"lat": 4.61, "lon": -74.08},
      "current": {
        "temperature": 18.5,
        "weather_code": 2,
        "wind_speed": 12.3,
        "wind_direction": 270,
        "timestamp": "2024-01-15T14:30:00"
      }
    }
  ]
}

---

```markdown
##  WebSocket

Conéctate a `ws://localhost:8000/ws` para recibir actualizaciones en tiempo real.

### Cliente WebSocket (JavaScript)

```javascript
const ws = new WebSocket('ws://localhost:8000/ws');

ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    if (data.type === 'climate_update') {
        console.log('Nuevos datos climáticos:', data.data);
    }
};


---

```markdown
##  Docker

### Construir imagen
```bash
docker build -t dashboard-climatico-backend .











