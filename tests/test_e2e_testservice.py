"""E2E tests for testservice endpoint."""
import json
import pytest
from orionpy.network.orionhttpx import OrionHttpx


class TestTestServiceE2E:
    """End-to-end tests for testservice."""
    
    @pytest.fixture
    def orion_client(self):
        """Create OrionHttpx client for e2e tests."""
        return OrionHttpx()
    
    @pytest.mark.asyncio
    async def test_hello_endpoint_authenticated(self, orion_client):
        """Test authenticated request to hello endpoint returns 200."""
        response = await orion_client.get(
            namespace='default',
            service='testservice',
            port=3000,
            path='/testservice/v1/hello'
        )
        
        assert response.status_code == 200
        assert response.text == 'hello'
    
    @pytest.mark.asyncio
    async def test_hello_endpoint_unauthenticated(self, orion_client):
        """Test unauthenticated request to hello endpoint returns 401."""
        import httpx
        
        # Make request without authentication header
        url = 'http://testservice.default.svc.cluster.local:3000/testservice/v1/hello'
        async with httpx.AsyncClient() as client:
            response = await client.get(url)
        
        assert response.status_code == 401
    
    @pytest.mark.asyncio
    async def test_echo_endpoint_authenticated(self, orion_client):
        """Test authenticated POST request to echo endpoint returns request body."""
        test_data = {"message": "hello world", "value": 42}
        
        response = await orion_client.post(
            namespace='default',
            service='testservice',
            port=3000,
            path='/testservice/v1/echo',
            json=test_data
        )
        
        assert response.status_code == 200
        assert response.json() == test_data
    
    @pytest.mark.asyncio
    async def test_echo_endpoint_unauthenticated(self, orion_client):
        """Test unauthenticated POST request to echo endpoint returns 401."""
        import httpx
        
        test_data = {"message": "hello world", "value": 42}
        url = 'http://testservice.default.svc.cluster.local:3000/testservice/v1/echo'
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=test_data)
        
        assert response.status_code == 401
