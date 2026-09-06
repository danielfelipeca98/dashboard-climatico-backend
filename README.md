#  Dashboard Climático Colombia

![Python](https://img.shields.io/badge/Python-3.11-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.104-green)
![React](https://img.shields.io/badge/React-Leaflet-61DAFB)
![Docker](https://img.shields.io/badge/Docker-ready-brightgreen)
![Render](https://img.shields.io/badge/Render-deployed-brightgreen)

Dashboard interactivo del clima en tiempo real para Colombia: mapa de calor continuo estilo satelital, interpolación geográfica sobre el territorio real del país, y actualización en vivo por WebSockets.

---

##  Características

- **Mapa de calor continuo** (temperatura y precipitación) renderizado en canvas, sin cuadrícula ni bordes visibles entre puntos — cada zona muestra su color real, con transición suave hacia sus vecinas.
- **Interpolación IDW (Inverse Distance Weighting)** sobre una grilla de hasta 100×100 puntos, recortada exactamente al límite geográfico real de Colombia (no un rectángulo ni una aproximación dibujada a mano).
- **41 ciudades colombianas** con datos de temperatura, viento (velocidad y dirección) y precipitación.
- **Actualización en tiempo real vía WebSocket**, con broadcast automático cada `UPDATE_INTERVAL`.
- **Doble proveedor de clima**: Open-Meteo como fuente principal, con failover automático a WeatherAPI.com si el primero no responde.
- **Diseñado para fallar con gracia**: ante un corte del proveedor de clima, el sistema sigue respondiendo con el último dato bueno conocido en vez de caerse o devolver un error.

---

##  Resiliencia y manejo de errores

Esta es la parte del proyecto que más iteración tuvo, así que vale la pena documentarla en detalle — cada mecanismo existe porque resolvió un problema real observado en producción, no como buena práctica genérica.

### Capas de protección, en el orden en que actúan

1. **TTL de éxito** — mientras el último dato bueno tenga menos de `UPDATE_INTERVAL` segundos, se sirve directo desde memoria. Ningún request nuevo llama al proveedor de clima si ya hay un dato suficientemente fresco, sin importar cuántos usuarios, pestañas o bots golpeen el endpoint al mismo tiempo.
2. **Cooldown de fallo** — si el proveedor está caído, el TTL de arriba no ayuda (nunca hay un dato "reciente"). Este segundo chequeo evita reintentar más de una vez cada 30 segundos, para no generar una tormenta de peticiones contra una API que ya está bloqueando.
3. **Failover a un segundo proveedor** — si Open-Meteo no responde tras sus reintentos rápidos, el sistema prueba automáticamente con WeatherAPI.com (autenticado por API key propia, no por IP) antes de resignarse a servir datos viejos.
4. **Caché de último dato bueno (hasta 45 min)** — si ningún proveedor responde, se sigue sirviendo el último dato válido, marcado explícitamente como `is_stale: true` en la respuesta, en vez de dejar el dashboard vacío.
5. **Persistencia a disco** — el último dato bueno se guarda en un archivo local, para sobrevivir a un reinicio del proceso (no a un redeploy completo — el filesystem de Render es efímero entre despliegues).
6. **Instancia única compartida (`app.state`)** — el servicio que habla con los proveedores de clima vive una sola vez por proceso, compartido entre todos los endpoints REST, el WebSocket y la tarea de broadcast. Antes, cada request creaba su propia instancia con su propio caché aislado, lo que anulaba por completo el punto 1.

### Por qué existe el segundo proveedor

Open-Meteo aplica límites **por IP**, no por cuenta. En plataformas de hosting con IP de salida compartida entre múltiples clientes (como el free/starter tier de Render), es posible recibir un bloqueo — incluyendo el límite diario — sin que la propia aplicación haya generado un volumen anormal de tráfico, simplemente por compartir esa IP con otros proyectos. WeatherAPI.com se autentica por API key en vez de por IP, así que actúa como un respaldo genuinamente independiente ante ese escenario.

### Límites de las APIs externas (free tier)

| Proveedor | Límite | Autenticación |
|---|---|---|
| **Open-Meteo** | 600/min · 5.000/hora · 10.000/día | Por IP (sin key) |
| **WeatherAPI.com** | 100.000/mes · 3 días de forecast | Por API key |

**Configuración actual (41 ciudades, `UPDATE_INTERVAL=1200s`):**
- 1 petición batch cada 20 minutos ≈ 72 peticiones/día a Open-Meteo — muy por debajo de sus límites.
- Si cae al respaldo, son 41 peticiones individuales (WeatherAPI no ofrece batch gratuito) cada 20 min ≈ 2.950/día — dentro del límite mensual para uso normal.

---

##  Mapa de calor: cómo se logra el efecto continuo

El heatmap **no** usa una librería de densidad tipo `leaflet.heat`: esas herramientas están pensadas para "¿dónde se concentran más eventos?", y acumulan intensidad por superposición — con una grilla ya densa como la nuestra, eso satura el color y la opacidad en casi todo el mapa, perdiendo el detalle real.

En su lugar, una capa de canvas propia pinta el **color real de cada punto interpolado** con un radio de difuminado que se recalcula según el zoom actual (para que siempre se mezcle solo con sus vecinos inmediatos, nunca con decenas de celdas lejanas). El resultado: transición suave, sin cuadrícula visible, y colores que sí representan el dato real en cada zona.

La grilla de interpolación se recorta contra el límite geográfico real de Colombia (fuente pública basada en Natural Earth), no contra un rectángulo ni una forma aproximada — así no aparecen puntos en el mar, en Venezuela, Ecuador, Panamá o Brasil.

---

##  Tecnologías

### Backend
- **FastAPI** + **Uvicorn**
- **httpx** (cliente HTTP asíncrono hacia los proveedores de clima)
- **Pydantic v2** (validación de modelos)
- **Shapely** (geometría del polígono de Colombia)
- **WebSockets** (actualizaciones en tiempo real)

### Frontend
- **React** + **react-leaflet**
- Capa de canvas propia para el heatmap (sin dependencias de terceros para el renderizado)

### DevOps
- **Docker**
- **Render** (despliegue del backend)

---

##  Estructura del proyecto

```
dashboard-climatico-colombia/
├─ backend/
│  ├── app/
│  │  ├── api/
│  │  │  ├── routes/
│  │  │  │  └── climate.py          # Endpoints REST
│  │  │  └── websocket/
│  │  │     └── manager.py          # Gestor de conexiones WebSocket
│  │  ├── core/
│  │  │  └── config.py              # Variables de entorno
│  │  ├── models/
│  │  │  ├── city.py
│  │  │  └── climate.py             # Modelos Pydantic (respuesta, clima, heatmap)
│  │  └── services/
│  │     ├── climate_service.py     # Fetch batch + caché + failover
│  │     └── interpolation_service.py  # Grilla + polígono de Colombia + IDW
│  ├── .env
│  ├── Dockerfile
│  ├── requirements.txt
│  └── main.py                      # Punto de entrada, lifespan, WebSocket
└─ frontend/
   └── src/components/
      └── ClimateMap.jsx            # Mapa + capa de heatmap en canvas
```

---

##  Variables de entorno

```env
# Proveedor principal
CLIMATE_API_URL=https://api.open-meteo.com/v1/forecast
CITIES=Bogotá:4.61,-74.08|Medellín:6.24,-75.57|...

# Cada cuánto se refresca el dato (segundos)
UPDATE_INTERVAL=1200

# Proveedor de respaldo (opcional — si se deja vacío, el failover
# queda deshabilitado y el sistema se comporta como solo-Open-Meteo)
WEATHERAPI_KEY=
WEATHERAPI_URL=https://api.weatherapi.com/v1/forecast.json
```

> `WEATHERAPI_KEY` nunca debe hardcodearse en el código ni versionarse — se configura como variable de entorno en Render (o en `.env` local, que debe estar en `.gitignore`).

---

##  Endpoints de la API

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/` | Información general de la API |
| GET | `/api/climate/all` | Datos completos de todas las ciudades |
| GET | `/api/climate/heatmap` | Puntos del mapa de calor (solo ciudades reales, sin interpolación) |
| GET | `/api/climate/heatmap/interpolated?resolution=` | Puntos interpolados (IDW) + ciudades reales |
| GET | `/api/climate/cities` | Lista de ciudades configuradas (nombre, lat, lon) |
| WS | `/ws` | Suscripción a actualizaciones en tiempo real |

##  Ejemplo de respuesta

### GET `/api/climate/all`

```json
{
  "timestamp": "2026-09-06T14:30:00",
  "is_stale": false,
  "data_updated_at": "2026-09-06T14:28:12",
  "cities": [
    {
      "city": "Bogotá",
      "coordinates": { "lat": 4.61, "lon": -74.08 },
      "current": {
        "temperature": 18.5,
        "weather_code": 2,
        "wind_speed": 12.3,
        "wind_direction": 270,
        "timestamp": "2026-09-06T14:30"
      },
      "daily": {
        "max_temp": [19.2],
        "min_temp": [11.8],
        "precipitation": [2.4],
        "dates": ["2026-09-06"]
      }
    }
  ]
}
```

- `is_stale: true` indica que el dato viene del caché de respaldo (ningún proveedor respondió en el último intento), no de una lectura fresca.
- `data_updated_at` es la marca de tiempo del último dato REAL obtenido de un proveedor — distinta de `timestamp` (que siempre es "ahora") cuando `is_stale` es `true`.

---

##  WebSocket

```javascript
const ws = new WebSocket('wss://tu-backend.onrender.com/ws');

ws.onmessage = (event) => {
    const { type, data } = JSON.parse(event.data);
    if (type === 'climate_update') {
        console.log('Nuevos datos climáticos:', data);
    }
};
```

---

##  Docker

```bash
docker build -t dashboard-climatico-backend .
docker run -p 8000:8000 --env-file .env dashboard-climatico-backend
```

---

##  Limitaciones conocidas

- El caché/TTL vive en memoria del proceso: si el servicio corre con más de un worker o más de una instancia, cada una mantiene su propio contador — para escalar horizontalmente haría falta un caché compartido (ej. Redis).
- El plan free de WeatherAPI.com da 3 días de pronóstico (Open-Meteo da 7); el modelo de datos acepta ambos casos, pero el detalle a más de un día solo está disponible cuando responde Open-Meteo.
- El polígono de Colombia usado para recortar la grilla es de resolución moderada (dataset público tipo Natural Earth): geográficamente correcto, pero no milimétricamente preciso justo en la línea de costa.