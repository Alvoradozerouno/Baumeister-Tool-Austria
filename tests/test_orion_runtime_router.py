"""
Tests for ORION Runtime Router
"""

import pytest
from fastapi.testclient import TestClient
from pathlib import Path


@pytest.fixture
def client():
    """Fixture to provide test client"""
    from api.main import app
    return TestClient(app)


class TestORIONRuntimeInitialization:
    """Test ORION runtime initialization"""

    def test_initialize_runtime(self, client):
        """Test runtime initialization"""
        response = client.post("/api/v1/orion-runtime/initialize")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "initialized"
        assert "timestamp" in data
        assert "genesis_hash" in data

    def test_health_check(self, client):
        """Test health check endpoint"""
        response = client.post("/api/v1/orion-runtime/initialize")
        assert response.status_code == 200
        
        response = client.get("/api/v1/orion-runtime/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "uptime_seconds" in data
        assert "components" in data


class TestAuditChain:
    """Test audit chain functionality"""

    def test_verify_audit_chain(self, client):
        """Test audit chain verification"""
        client.post("/api/v1/orion-runtime/initialize")
        
        response = client.get("/api/v1/orion-runtime/audit-chain/verify")
        assert response.status_code == 200
        data = response.json()
        assert data["valid"] == True
        assert data["entries"] >= 1

    def test_get_audit_entries(self, client):
        """Test retrieving audit entries"""
        client.post("/api/v1/orion-runtime/initialize")
        
        response = client.get("/api/v1/orion-runtime/audit-chain/entries?limit=50")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_add_audit_entry(self, client):
        """Test adding audit entry"""
        client.post("/api/v1/orion-runtime/initialize")
        
        response = client.post(
            "/api/v1/orion-runtime/audit-chain/add",
            params={
                "component": "test_component",
                "status": "GREEN",
                "message": "Test entry",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "hash" in data


class TestComponentStatus:
    """Test component status endpoints"""

    def test_get_components_status(self, client):
        """Test getting component status"""
        client.post("/api/v1/orion-runtime/initialize")
        
        response = client.get("/api/v1/orion-runtime/components/status")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)

    def test_get_runtime_state(self, client):
        """Test getting runtime state"""
        client.post("/api/v1/orion-runtime/initialize")
        
        response = client.get("/api/v1/orion-runtime/runtime-state")
        assert response.status_code == 200
        data = response.json()
        assert "state" in data
        assert "entries" in data


class TestValidation:
    """Test validation endpoints"""

    def test_validate_fpga_targets(self, client):
        """Test FPGA targets validation"""
        client.post("/api/v1/orion-runtime/initialize")
        
        response = client.post("/api/v1/orion-runtime/validate/fpga-targets")
        assert response.status_code == 200
        data = response.json()
        assert "total_expected" in data
        assert "found" in data

    def test_validate_formal_proofs(self, client):
        """Test formal proofs validation"""
        client.post("/api/v1/orion-runtime/initialize")
        
        response = client.post("/api/v1/orion-runtime/validate/formal-proofs")
        assert response.status_code == 200
        data = response.json()
        assert "total_expected" in data
        assert "found" in data


class TestReporting:
    """Test reporting endpoints"""

    def test_get_runtime_report(self, client):
        """Test getting runtime report"""
        client.post("/api/v1/orion-runtime/initialize")
        
        response = client.get("/api/v1/orion-runtime/report")
        assert response.status_code == 200
        data = response.json()
        assert "timestamp" in data
        assert "audit_chain" in data
        assert "components" in data
        assert "consensus" in data
        assert "production_readiness" in data

    def test_reset_runtime(self, client):
        """Test runtime reset"""
        client.post("/api/v1/orion-runtime/initialize")
        
        response = client.post("/api/v1/orion-runtime/reset")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "reset"
