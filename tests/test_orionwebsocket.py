"""Tests for OrionWebSocket class."""

import time
import pytest
from unittest.mock import Mock, patch, AsyncMock
import jwt

from orionpy.network.orionwebsocket import OrionWebSocket


class TestOrionWebSocket:
    """Test the OrionWebSocket class."""

    @pytest.fixture
    def mock_k8s_config(self):
        """Mock Kubernetes configuration."""
        with patch("orionpy.network.orionhttpx.config.load_incluster_config"):
            yield

    @pytest.fixture
    def mock_k8s_clients(self):
        """Mock Kubernetes client APIs."""
        with patch("orionpy.network.orionhttpx.client.CoreV1Api"), \
             patch("orionpy.network.orionhttpx.client.AuthenticationV1Api"):
            yield

    @pytest.fixture
    def orion_ws(self, mock_k8s_config, mock_k8s_clients):
        """Create an OrionWebSocket client with mocked dependencies."""
        OrionWebSocket._token_cache.clear()
        return OrionWebSocket()

    @pytest.mark.asyncio
    async def test_connect_builds_correct_url(self, orion_ws):
        """Ensure WebSocket URL is built correctly."""
        exp_time = int(time.time()) + 600
        token = jwt.encode({"exp": exp_time, "aud": "test"}, "secret", algorithm="HS256")

        orion_ws._create_token = Mock(return_value=token)

        with patch("orionpy.network.orionwebsocket.websockets.connect", new_callable=AsyncMock) as mock_connect:
            await orion_ws.connect(
                namespace="default",
                service="kuiper",
                port=8000,
                path="/kuiper/.stream",
            )

            mock_connect.assert_awaited_once()
            url = mock_connect.call_args[0][0]
            assert url == "ws://kuiper.default.svc.cluster.local:8000/kuiper/.stream"

    @pytest.mark.asyncio
    async def test_connect_injects_auth_header(self, orion_ws):
        """Ensure auth header is passed during WebSocket handshake."""
        exp_time = int(time.time()) + 600
        token = jwt.encode({"exp": exp_time, "aud": "test"}, "secret", algorithm="HS256")

        orion_ws._create_token = Mock(return_value=token)

        with patch("orionpy.network.orionwebsocket.websockets.connect", new_callable=AsyncMock) as mock_connect:
            await orion_ws.connect(
                namespace="default",
                service="kuiper",
                port=8000,
                path="/kuiper/.stream",
            )

            # Updated key to match current implementation
            headers = mock_connect.call_args.kwargs["additional_headers"]
            assert headers["X-ORION-SERVICE-AUTH"] == token

    @pytest.mark.asyncio
    async def test_connect_sets_ping_options(self, orion_ws):
        """Ensure ping settings are passed through."""
        exp_time = int(time.time()) + 600
        token = jwt.encode({"exp": exp_time, "aud": "test"}, "secret", algorithm="HS256")

        orion_ws._create_token = Mock(return_value=token)

        with patch("orionpy.network.orionwebsocket.websockets.connect", new_callable=AsyncMock) as mock_connect:
            await orion_ws.connect(
                namespace="default",
                service="kuiper",
                port=8000,
                path="/kuiper/.stream",
            )

            assert mock_connect.call_args.kwargs["ping_interval"] == 20
            assert mock_connect.call_args.kwargs["ping_timeout"] == 20

    @pytest.mark.asyncio
    async def test_token_is_cached_between_connections(self, orion_ws):
        """Ensure token is reused from cache for multiple connections."""
        exp_time = int(time.time()) + 600
        token = jwt.encode({"exp": exp_time, "aud": "test"}, "secret", algorithm="HS256")

        orion_ws._create_token = Mock(return_value=token)

        with patch("orionpy.network.orionwebsocket.websockets.connect", new_callable=AsyncMock):
            await orion_ws.connect("default", "kuiper", 8000, "/kuiper/.stream")
            await orion_ws.connect("default", "kuiper", 8000, "/kuiper/.stream")

        # The token should only be generated once
        assert orion_ws._create_token.call_count == 1
