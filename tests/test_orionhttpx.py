"""Tests for OrionHttpx class."""
import time
import pytest
from unittest.mock import Mock, patch, AsyncMock
import jwt
import httpx

from orionpy.network.orionhttpx import OrionHttpx


class TestOrionHttpx:
    """Test the OrionHttpx class."""
    
    @pytest.fixture
    def mock_k8s_config(self):
        """Mock Kubernetes configuration."""
        with patch('orionpy.network.orionhttpx.config.load_incluster_config'):
            yield
    
    @pytest.fixture
    def mock_k8s_clients(self):
        """Mock Kubernetes client APIs."""
        with patch('orionpy.network.orionhttpx.client.CoreV1Api') as core_api, \
             patch('orionpy.network.orionhttpx.client.AuthenticationV1Api') as auth_api:
            yield {'core': core_api, 'auth': auth_api}
    
    @pytest.fixture
    def orion_client(self, mock_k8s_config, mock_k8s_clients):
        """Create an OrionHttpx client with mocked dependencies."""
        # Clear the token cache between tests
        OrionHttpx._token_cache.clear()
        return OrionHttpx()
    
    @pytest.mark.asyncio
    async def test_service_key_generation(self, orion_client):
        """Test service key generation for cache."""
        key = orion_client._get_service_key('default', 'my-service')
        assert key == 'default::my-service'
    
    @pytest.mark.asyncio
    async def test_build_url(self, orion_client):
        """Test URL building."""
        url = orion_client._build_url('default', 'my-service', 8000, '/api/test')
        assert url == 'http://my-service.default.svc.cluster.local:8000/api/test'
        
        url = orion_client._build_url('default', 'my-service', 8000, 'api/test')
        assert url == 'http://my-service.default.svc.cluster.local:8000/api/test'
        
        url = orion_client._build_url('default', 'my-service', 8000)
        assert url == 'http://my-service.default.svc.cluster.local:8000'
    
    @pytest.mark.asyncio
    async def test_create_token(self, orion_client):
        """Test token creation."""
        # Mock the token response
        mock_token_response = Mock()
        mock_token_response.status.token = 'test-token-123'
        
        orion_client._core_api.create_namespaced_service_account_token = Mock(
            return_value=mock_token_response
        )
        
        token = orion_client._create_token('default', 'my-service')
        
        assert token == 'test-token-123'
        orion_client._core_api.create_namespaced_service_account_token.assert_called_once()
        call_args = orion_client._core_api.create_namespaced_service_account_token.call_args
        # Should use the in-cluster service account, not 'default'
        assert call_args[1]['name'] == orion_client._service_account_name
        assert call_args[1]['namespace'] == orion_client._namespace
    
    @pytest.mark.asyncio
    async def test_get_token_caching(self, orion_client):
        """Test token caching and reuse."""
        # Create a valid token with 10 minute expiry
        exp_time = int(time.time()) + 600
        token_payload = {'exp': exp_time, 'aud': 'test'}
        test_token = jwt.encode(token_payload, 'secret', algorithm='HS256')
        
        # Mock the create_token method
        orion_client._create_token = Mock(return_value=test_token)
        
        # First call should create token
        token1 = await orion_client._get_token('default', 'my-service')
        assert token1 == test_token
        assert orion_client._create_token.call_count == 1
        
        # Second call should use cached token
        token2 = await orion_client._get_token('default', 'my-service')
        assert token2 == test_token
        assert orion_client._create_token.call_count == 1  # Still 1, not called again
    
    @pytest.mark.asyncio
    async def test_get_token_refresh(self, orion_client):
        """Test token refresh when expiring soon."""
        # Create a token that expires in 4 minutes (should trigger refresh)
        exp_time_old = int(time.time()) + 240
        token_payload_old = {'exp': exp_time_old, 'aud': 'test'}
        old_token = jwt.encode(token_payload_old, 'secret', algorithm='HS256')
        
        # Create a new token with 10 minute expiry
        exp_time_new = int(time.time()) + 600
        token_payload_new = {'exp': exp_time_new, 'aud': 'test'}
        new_token = jwt.encode(token_payload_new, 'secret', algorithm='HS256')
        
        # Mock the create_token method
        orion_client._create_token = Mock(side_effect=[old_token, new_token])
        
        # First call creates token
        token1 = await orion_client._get_token('default', 'my-service')
        assert token1 == old_token
        
        # Second call should refresh the token since it expires in < 5 minutes
        token2 = await orion_client._get_token('default', 'my-service')
        assert token2 == new_token
        assert orion_client._create_token.call_count == 2
    
    @pytest.mark.asyncio
    async def test_make_request(self, orion_client):
        """Test making HTTP requests."""
        # Create a valid token
        exp_time = int(time.time()) + 600
        token_payload = {'exp': exp_time, 'aud': 'test'}
        test_token = jwt.encode(token_payload, 'secret', algorithm='HS256')
        
        orion_client._create_token = Mock(return_value=test_token)
        
        # Mock httpx AsyncClient
        mock_response = Mock()
        mock_response.status_code = 200
        
        with patch('orionpy.network.orionhttpx.httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.request = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client
            
            response = await orion_client._make_request(
                'GET', 'default', 'my-service', 8000, '/api/test'
            )
            
            assert response.status_code == 200
            mock_client.request.assert_called_once()
            call_args = mock_client.request.call_args
            assert call_args[0][0] == 'GET'
            assert call_args[0][1] == 'http://my-service.default.svc.cluster.local:8000/api/test'
            assert call_args[1]['headers']['X-ORION-SERVICE-AUTH'] == test_token
    
    @pytest.mark.asyncio
    async def test_get_method(self, orion_client):
        """Test GET method."""
        exp_time = int(time.time()) + 600
        token_payload = {'exp': exp_time, 'aud': 'test'}
        test_token = jwt.encode(token_payload, 'secret', algorithm='HS256')
        
        orion_client._create_token = Mock(return_value=test_token)
        mock_response = Mock()
        
        with patch('orionpy.network.orionhttpx.httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.request = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client
            
            await orion_client.get('default', 'my-service', 8000, '/api/test')
            
            assert mock_client.request.call_args[0][0] == 'GET'
    
    @pytest.mark.asyncio
    async def test_post_method(self, orion_client):
        """Test POST method."""
        exp_time = int(time.time()) + 600
        token_payload = {'exp': exp_time, 'aud': 'test'}
        test_token = jwt.encode(token_payload, 'secret', algorithm='HS256')
        
        orion_client._create_token = Mock(return_value=test_token)
        mock_response = Mock()
        
        with patch('orionpy.network.orionhttpx.httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.request = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client
            
            await orion_client.post('default', 'my-service', 8000, '/api/test', json={'key': 'value'})
            
            assert mock_client.request.call_args[0][0] == 'POST'
            assert mock_client.request.call_args[1]['json'] == {'key': 'value'}
    
    @pytest.mark.asyncio
    async def test_put_method(self, orion_client):
        """Test PUT method."""
        exp_time = int(time.time()) + 600
        token_payload = {'exp': exp_time, 'aud': 'test'}
        test_token = jwt.encode(token_payload, 'secret', algorithm='HS256')
        
        orion_client._create_token = Mock(return_value=test_token)
        mock_response = Mock()
        
        with patch('orionpy.network.orionhttpx.httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.request = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client
            
            await orion_client.put('default', 'my-service', 8000, '/api/test')
            
            assert mock_client.request.call_args[0][0] == 'PUT'
    
    @pytest.mark.asyncio
    async def test_delete_method(self, orion_client):
        """Test DELETE method."""
        exp_time = int(time.time()) + 600
        token_payload = {'exp': exp_time, 'aud': 'test'}
        test_token = jwt.encode(token_payload, 'secret', algorithm='HS256')
        
        orion_client._create_token = Mock(return_value=test_token)
        mock_response = Mock()
        
        with patch('orionpy.network.orionhttpx.httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.request = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client
            
            await orion_client.delete('default', 'my-service', 8000, '/api/test')
            
            assert mock_client.request.call_args[0][0] == 'DELETE'
    
    @pytest.mark.asyncio
    async def test_patch_method(self, orion_client):
        """Test PATCH method."""
        exp_time = int(time.time()) + 600
        token_payload = {'exp': exp_time, 'aud': 'test'}
        test_token = jwt.encode(token_payload, 'secret', algorithm='HS256')
        
        orion_client._create_token = Mock(return_value=test_token)
        mock_response = Mock()
        
        with patch('orionpy.network.orionhttpx.httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.request = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client
            
            await orion_client.patch('default', 'my-service', 8000, '/api/test')
            
            assert mock_client.request.call_args[0][0] == 'PATCH'
    
    @pytest.mark.asyncio
    async def test_custom_headers_preserved(self, orion_client):
        """Test that custom headers are preserved when making requests."""
        exp_time = int(time.time()) + 600
        token_payload = {'exp': exp_time, 'aud': 'test'}
        test_token = jwt.encode(token_payload, 'secret', algorithm='HS256')
        
        orion_client._create_token = Mock(return_value=test_token)
        mock_response = Mock()
        
        with patch('orionpy.network.orionhttpx.httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.request = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client
            
            custom_headers = {'X-Custom-Header': 'custom-value'}
            await orion_client.get('default', 'my-service', 8000, '/api/test', headers=custom_headers)
            
            call_headers = mock_client.request.call_args[1]['headers']
            assert call_headers['X-Custom-Header'] == 'custom-value'
            assert call_headers['X-ORION-SERVICE-AUTH'] == test_token
