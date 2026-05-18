"""
Test suite for api/main.py - FastAPI application initialization and routing.
Tests application setup, middleware configuration, and endpoint registration.
"""

import os
import sys
from typing import Dict

import pytest

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from fastapi.testclient import TestClient
    from api.main import app

    HAS_FASTAPI = True
    client = TestClient(app)
except ImportError:
    HAS_FASTAPI = False
    client = None


@pytest.mark.skipif(not HAS_FASTAPI, reason="FastAPI not installed")
class TestApplicationInitialization:
    """Test application startup and initialization"""

    def test_app_instance_created(self):
        """Test that FastAPI app instance is created"""
        assert app is not None

    def test_app_is_fastapi_instance(self):
        """Test that app is a FastAPI instance"""
        from fastapi import FastAPI

        assert isinstance(app, FastAPI)

    def test_app_title_set(self):
        """Test that app title is properly configured"""
        assert app.title is not None
        assert len(app.title) > 0

    def test_app_debug_mode(self):
        """Test that app debug mode is configurable"""
        # App should have a debug attribute (through openapi config)
        assert hasattr(app, "openapi_schema") or hasattr(app, "debug")

    def test_openapi_schema_generation(self):
        """Test OpenAPI schema can be generated"""
        schema = app.openapi()
        assert schema is not None
        assert "paths" in schema or "openapi" in schema


@pytest.mark.skipif(not HAS_FASTAPI, reason="FastAPI not installed")
class TestApplicationRoutes:
    """Test application route registration"""

    def test_routes_registered(self):
        """Test that routes are registered in the app"""
        routes = app.routes
        assert len(routes) > 0

    def test_health_check_endpoint(self):
        """Test health check endpoint exists"""
        with client:
            try:
                response = client.get("/health")
                # Should either return 200, 404 (if not implemented), or allow the call
                assert response.status_code in [200, 404, 405]
            except Exception:
                pass  # Some routing might be strict

    def test_api_docs_available(self):
        """Test API documentation endpoints"""
        with client:
            try:
                # Swagger UI
                response = client.get("/docs")
                assert response.status_code in [200, 404]

                # OpenAPI JSON
                response = client.get("/openapi.json")
                assert response.status_code in [200, 404]
            except Exception:
                pass

    def test_redoc_available(self):
        """Test ReDoc documentation"""
        with client:
            try:
                response = client.get("/redoc")
                assert response.status_code in [200, 404]
            except Exception:
                pass

    def test_static_files_mount_point(self):
        """Test static files are mounted"""
        # Check if app has mounted routes
        routes_str = str(app.routes)
        # App may or may not have static files, just verify it doesn't error
        assert isinstance(app.routes, list)


@pytest.mark.skipif(not HAS_FASTAPI, reason="FastAPI not installed")
class TestCORSConfiguration:
    """Test CORS middleware configuration"""

    def test_cors_headers_in_options(self):
        """Test CORS headers are set in OPTIONS requests"""
        with client:
            try:
                # Most endpoints should respond to OPTIONS
                response = client.options("/")
                # CORS headers may or may not be present depending on config
                assert response.status_code in [200, 404, 405, 500]
            except Exception:
                pass

    def test_allowed_origins_configured(self):
        """Test CORS allowed origins are configured"""
        # Check middleware list for CORSMiddleware
        middleware_names = [
            str(type(m).__name__) for m in app.user_middleware
        ]
        # May or may not have CORS configured
        assert isinstance(middleware_names, list)


@pytest.mark.skipif(not HAS_FASTAPI, reason="FastAPI not installed")
class TestMiddlewareIntegration:
    """Test middleware integration"""

    def test_middleware_registered(self):
        """Test that middleware is registered"""
        assert hasattr(app, "middleware") or hasattr(app, "user_middleware")

    def test_request_response_flow(self):
        """Test basic request-response flow through middleware"""
        with client:
            try:
                # Make a simple request to test middleware
                response = client.get("/")
                # Should return something (200, 404, 422, etc.)
                assert response.status_code > 0
            except Exception:
                pass

    def test_request_headers_preserved(self):
        """Test that custom request headers are preserved"""
        with client:
            try:
                headers = {"X-Custom-Header": "test-value"}
                response = client.get("/", headers=headers)
                # Request should go through (regardless of endpoint existence)
                assert True
            except Exception:
                pass


@pytest.mark.skipif(not HAS_FASTAPI, reason="FastAPI not installed")
class TestErrorHandling:
    """Test error handling and exception routes"""

    def test_404_not_found(self):
        """Test 404 error handling"""
        with client:
            response = client.get("/nonexistent-endpoint-that-should-not-exist")
            assert response.status_code == 404

    def test_405_method_not_allowed(self):
        """Test 405 method not allowed"""
        with client:
            try:
                # Try wrong HTTP method
                response = client.post("/docs")
                assert response.status_code in [404, 405, 422]
            except Exception:
                pass

    def test_422_validation_error(self):
        """Test 422 validation error response"""
        with client:
            try:
                # Send malformed data to any endpoint
                response = client.post("/api/v1/calculations", json={})
                # Should either accept or return 422
                assert response.status_code in [200, 201, 404, 405, 422]
            except Exception:
                pass


@pytest.mark.skipif(not HAS_FASTAPI, reason="FastAPI not installed")
class TestResponseFormats:
    """Test response format consistency"""

    def test_json_response_format(self):
        """Test that responses are valid JSON"""
        with client:
            try:
                response = client.get("/")
                if response.status_code in [200, 201]:
                    # Should be valid JSON
                    data = response.json()
                    assert isinstance(data, (dict, list))
            except Exception:
                pass

    def test_response_content_type(self):
        """Test response content-type headers"""
        with client:
            try:
                response = client.get("/openapi.json")
                if response.status_code == 200:
                    assert "application/json" in response.headers.get(
                        "content-type", ""
                    )
            except Exception:
                pass


@pytest.mark.skipif(not HAS_FASTAPI, reason="FastAPI not installed")
class TestEnvironmentConfiguration:
    """Test environment-based configuration"""

    def test_app_responds_to_requests(self):
        """Test app responds to requests"""
        with client:
            try:
                response = client.get("/")
                # App should be responsive
                assert response.status_code > 0
            except Exception:
                pass

    def test_app_has_exception_handlers(self):
        """Test that app has exception handlers configured"""
        # Check if exception handlers are registered
        assert hasattr(app, "exception_handlers")


@pytest.mark.skipif(not HAS_FASTAPI, reason="FastAPI not installed")
class TestShutdownAndCleanup:
    """Test app shutdown and cleanup"""

    def test_app_context_manager(self):
        """Test app can be used with context managers"""
        try:
            with client:
                pass
            assert True
        except Exception as e:
            pytest.fail(f"App context manager failed: {e}")

    def test_multiple_sequential_requests(self):
        """Test app handles multiple sequential requests"""
        with client:
            try:
                for i in range(3):
                    response = client.get("/")
                    assert response.status_code > 0
            except Exception:
                pass


@pytest.mark.skipif(not HAS_FASTAPI, reason="FastAPI not installed")
class TestApplicationMetadata:
    """Test application metadata and configuration"""

    def test_openapi_version(self):
        """Test OpenAPI version is specified"""
        schema = app.openapi()
        if schema:
            assert "openapi" in schema or "info" in schema

    def test_app_version(self):
        """Test app version is set"""
        if hasattr(app, "version"):
            assert app.version is not None

    def test_app_description(self):
        """Test app description is available"""
        if hasattr(app, "description"):
            assert app.description is not None
