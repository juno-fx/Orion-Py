"""
OrionWebSocket - Async Websocket client for Kubernetes service-to-service
communication with automatic token management.
"""

# 3rd
import websockets

# Local
from .orionhttpx import OrionHttpx


class OrionWebSocket(OrionHttpx):
    async def connect(
        self,
        namespace: str,
        service: str,
        port: int,
        path: str,
    ):
        token = await self._get_token(namespace, service)

        url = f"ws://{service}.{namespace}.svc.cluster.local:{port}{path}"

        headers = {"X-ORION-SERVICE-AUTH": token}

        return await websockets.connect(
            url,
            additional_headers=headers,
            ping_interval=20,
            ping_timeout=20,
        )
