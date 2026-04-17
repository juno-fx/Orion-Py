"""
OrionHttpx - Async HTTP client for Kubernetes service-to-service
communication with automatic token management.
"""

import asyncio
import time
from typing import Any, Dict

import httpx
import jwt
from kubernetes import client, config


class OrionHttpx:
    """
    Async HTTP client for Kubernetes service-to-service communication.

    Automatically manages service account tokens with caching and refresh logic.
    Thread-safe and async-safe for use in FastAPI endpoints.
    """

    # Class-level token cache shared across all instances
    _token_cache: Dict[str, Dict[str, Any]] = {}
    _cache_lock = asyncio.Lock()

    def __init__(self):
        """Initialize OrionHttpx client with in-cluster config."""
        config.load_incluster_config()
        self._core_api = client.CoreV1Api()
        self._auth_api = client.AuthenticationV1Api()

        # Read namespace from the mounted service account
        ns_path = "/var/run/secrets/kubernetes.io/serviceaccount/namespace"
        with open(ns_path, "r", encoding="utf-8") as f:
            self._namespace = f.read().strip()

        # Read and decode the service account token to get the SA name
        token_path = "/var/run/secrets/kubernetes.io/serviceaccount/token"
        with open(token_path, "r", encoding="utf-8") as f:
            token = f.read()
        decoded = jwt.decode(token, options={"verify_signature": False})
        # SA name is in 'sub' field as system:serviceaccount:namespace:name
        sub = decoded.get("sub", "")
        parts = sub.split(":")
        self._service_account_name = parts[3] if len(parts) >= 4 else "default"

    @staticmethod
    def _get_service_key(namespace: str, service: str) -> str:
        """Generate cache key for a service."""
        return f"{namespace}::{service}"

    async def _get_token(self, namespace: str, service: str) -> str:
        """
        Get or refresh the service account token for the given service.

        Args:
            namespace: Kubernetes namespace
            service: Service name

        Returns:
            Valid JWT token
        """
        service_key = self._get_service_key(namespace, service)

        async with self._cache_lock:
            # Check if we have a cached token
            if service_key in self._token_cache:
                cached = self._token_cache[service_key]
                token = cached["token"]
                exp = cached["exp"]

                # Check if token has more than 5 minutes remaining
                time_remaining = exp - time.time()
                if time_remaining > 300:  # 5 minutes in seconds
                    return token

            # Need to refresh token - run in thread pool since k8s client is sync
            token = await asyncio.to_thread(self._create_token, namespace, service)

            # Decode to get expiry time
            decoded = jwt.decode(token, options={"verify_signature": False})
            exp = decoded["exp"]

            # Cache the token
            self._token_cache[service_key] = {"token": token, "exp": exp}

            return token

    def _create_token(self, namespace: str, service: str) -> str:
        """
        Create a new service account token using Kubernetes TokenRequest API.

        Args:
            namespace: Kubernetes namespace
            service: Service name

        Returns:
            JWT token string
        """
        audience = f'{namespace}::Service::"{service}"'

        token_request = client.AuthenticationV1TokenRequest(
            spec=client.V1TokenRequestSpec(
                audiences=[audience],
                expiration_seconds=600,  # 10 minutes
            )
        )

        # Request token for the current service account in the current namespace
        response = self._core_api.create_namespaced_service_account_token(
            name=self._service_account_name, namespace=self._namespace, body=token_request
        )

        return response.status.token

    @staticmethod
    def _build_url(namespace: str, service: str, port: int, path: str = "") -> str:
        """
        Build the service URL.

        Args:
            namespace: Kubernetes namespace
            service: Service name
            port: Service port
            path: URL path (should start with / if provided)

        Returns:
            Full service URL
        """
        base_url = f"http://{service}.{namespace}.svc.cluster.local:{port}"
        if path and not path.startswith("/"):
            path = "/" + path
        return base_url + path

    async def _make_request(  # pylint: disable=too-many-arguments,too-many-positional-arguments
        self, method: str, namespace: str, service: str, port: int, path: str = "", **kwargs
    ) -> httpx.Response:
        """
        Make an HTTP request to a Kubernetes service.

        Args:
            method: HTTP method (GET, POST, etc.)
            namespace: Kubernetes namespace
            service: Service name
            port: Service port
            path: URL path
            **kwargs: Additional arguments to pass to httpx

        Returns:
            Response object from httpx library
        """
        token = await self._get_token(namespace, service)
        url = self._build_url(namespace, service, port, path)

        # Inject the authentication header
        headers = kwargs.get("headers", {})
        headers["X-ORION-SERVICE-AUTH"] = token
        kwargs["headers"] = headers

        # Set a default timeout if not provided
        timeout = kwargs.pop("timeout", 30)

        async with httpx.AsyncClient(timeout=timeout) as http_client:
            return await http_client.request(method, url, **kwargs)

    async def get(
        self, namespace: str, service: str, port: int, path: str = "", **kwargs
    ) -> httpx.Response:
        """Make a GET request."""
        return await self._make_request("GET", namespace, service, port, path, **kwargs)

    async def post(
        self, namespace: str, service: str, port: int, path: str = "", **kwargs
    ) -> httpx.Response:
        """Make a POST request."""
        return await self._make_request("POST", namespace, service, port, path, **kwargs)

    async def put(
        self, namespace: str, service: str, port: int, path: str = "", **kwargs
    ) -> httpx.Response:
        """Make a PUT request."""
        return await self._make_request("PUT", namespace, service, port, path, **kwargs)

    async def delete(
        self, namespace: str, service: str, port: int, path: str = "", **kwargs
    ) -> httpx.Response:
        """Make a DELETE request."""
        return await self._make_request("DELETE", namespace, service, port, path, **kwargs)

    async def patch(
        self, namespace: str, service: str, port: int, path: str = "", **kwargs
    ) -> httpx.Response:
        """Make a PATCH request."""
        return await self._make_request("PATCH", namespace, service, port, path, **kwargs)
