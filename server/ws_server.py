"""WebSocket + HTTP server for phone subtitle display.

- WebSocket (ws_port): broadcasts translation results to connected phones
- HTTP (http_port): serves phone/index.html so the user just opens a URL
"""

import asyncio
import json
import os
import websockets
from websockets.asyncio.server import serve


class BroadcastServer:
    """Manages WebSocket connections and broadcasts messages."""

    def __init__(self, ws_port: int = 8765, http_port: int = 8080):
        self.ws_port = ws_port
        self.http_port = http_port
        self.clients: set = set()

    async def _ws_handler(self, websocket):
        """Handle a new WebSocket connection."""
        self.clients.add(websocket)
        client_info = websocket.remote_address
        print(f"Phone connected: {client_info}")
        try:
            async for message in websocket:
                pass
        except websockets.ConnectionClosed:
            pass
        finally:
            self.clients.discard(websocket)
            print(f"Phone disconnected: {client_info}")

    async def broadcast(self, message: dict):
        """Send a JSON message to all connected phone clients concurrently."""
        if not self.clients:
            return
        data = json.dumps(message, ensure_ascii=False)

        async def _send(ws):
            try:
                await ws.send(data)
            except websockets.ConnectionClosed:
                self.clients.discard(ws)

        await asyncio.gather(*[_send(ws) for ws in list(self.clients)])

    async def start_ws(self):
        """Start the WebSocket server."""
        async with serve(self._ws_handler, "0.0.0.0", self.ws_port):
            print(f"WebSocket server running on ws://0.0.0.0:{self.ws_port}")
            await asyncio.Future()  # run forever

    async def start_http(self):
        """Start a minimal HTTP server to serve the phone UI."""
        phone_html_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), "phone", "index.html"
        )

        async def http_handler(reader, writer):
            try:
                request_line = await reader.readline()
                parts = request_line.decode().split()
                path = parts[1] if len(parts) > 1 else "/"

                if path == "/" or path == "/index.html":
                    with open(phone_html_path, "r") as f:
                        content = f.read()
                    content = content.replace(
                        "__WS_PORT__", str(self.ws_port)
                    )
                    response = (
                        f"HTTP/1.1 200 OK\r\n"
                        f"Content-Type: text/html; charset=utf-8\r\n"
                        f"Content-Length: {len(content.encode())}\r\n"
                        f"Connection: close\r\n"
                        f"\r\n"
                        f"{content}"
                    )
                else:
                    response = "HTTP/1.1 404 Not Found\r\nConnection: close\r\n\r\n"
                writer.write(response.encode())
                await writer.drain()
            except Exception:
                pass
            finally:
                writer.close()

        server = await asyncio.start_server(http_handler, "0.0.0.0", self.http_port)
        print(f"HTTP server running on http://0.0.0.0:{self.http_port}")
        async with server:
            await server.serve_forever()
