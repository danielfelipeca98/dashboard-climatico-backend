from fastapi import WebSocket
class ConnectionManager:
    """Gestor de conexiones WebSocket para comunicación en tiempo real"""
    def __init__(self):
        self.active_connections:set[WebSocket] = set()

    async def connect(self,websocket:WebSocket):
        """
            Acepta y registra una nueva conexión WebSocket.

            Args:
                websocket (WebSocket): Conexión WebSocket del cliente
        """
        await websocket.accept()
        self.active_connections.add(websocket)

    def disconnect(self,websocket:WebSocket):
        """
            Elimina una conexión WebSocket del registro.

            Args:
                websocket (WebSocket): Conexión a eliminar
        """
        self.active_connections.remove(websocket)

    async def broadcast(self,message:str):
        """
            Envía un mensaje a todos los clientes conectados.

            Args:
                message (str): Mensaje a enviar

            Note:
                Si un cliente falla, se elimina automáticamente del registro.
        """
        if not self.active_connections:
            return
        disconnected = []
        for connection in self.active_connections:
           try:
               await connection.send_text(message)
           except Exception:
               disconnected.append(connection)
        for conn in disconnected:
            self.active_connections.remove(conn)

manager = ConnectionManager() 