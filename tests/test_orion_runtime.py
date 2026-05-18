"""
Tests for ORION Runtime integration
Phase 1: Edge Decision Layer & Monitoring
"""

import json
import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def orion_client():
    """Fixture to provide test client for ORION router."""
    from api.main import app

    return TestClient(app)


class TestTemporalValidation:
    """Tests for temporal epistemic validation endpoint"""

    def test_validate_temporal_verified_state(self, orion_client):
        """Test temporal validation with high confidence → VERIFIED"""
        payload = {
            "bundesland": "Wien",
            "building_type": "Wohnhaus",
            "calculation_data": {
                "type": "oib_rl_6",
                "bgf_m2": 150.0,
                "u_wert": 0.18,
            },
            "richtlinie": 6,
            "confidence_threshold": 0.95,
        }

        response = orion_client.post("/api/v1/orion-runtime/validate-temporal", json=payload)

        assert response.status_code == 200
        data = response.json()

        assert data["runtime_state"] == "VERIFIED"
        assert data["confidence"] == 0.95
        assert "decision_id" in data
        assert "audit_hash" in data
        assert "consensus" in data

    def test_validate_temporal_transition_state(self, orion_client):
        """Test temporal validation with medium confidence → TRANSITION"""
        payload = {
            "bundesland": "Tirol",
            "building_type": "Büro",
            "calculation_data": {
                "type": "oib_rl_3",
                "wohnungen": 10,
            },
            "richtlinie": 3,
            "confidence_threshold": 0.85,
        }

        response = orion_client.post("/api/v1/orion-runtime/validate-temporal", json=payload)

        assert response.status_code == 200
        data = response.json()

        assert data["runtime_state"] == "TRANSITION"
        assert data["confidence"] == 0.85

    def test_validate_temporal_abstain_state(self, orion_client):
        """Test temporal validation with low confidence → ABSTAIN"""
        payload = {
            "bundesland": "Salzburg",
            "building_type": "Industrie",
            "calculation_data": {
                "type": "oib_rl_7",
                "sustainability_score": 0.3,
            },
            "richtlinie": 7,
            "confidence_threshold": 0.40,
        }

        response = orion_client.post("/api/v1/orion-runtime/validate-temporal", json=payload)

        assert response.status_code == 200
        data = response.json()

        assert data["runtime_state"] == "ABSTAIN"
        assert data["confidence"] == 0.40

    def test_validate_temporal_audit_hash_present(self, orion_client):
        """Test that audit hash is always present and valid SHA256 format"""
        payload = {
            "bundesland": "Wien",
            "building_type": "Wohnhaus",
            "calculation_data": {"type": "test", "value": 123},
            "richtlinie": 6,
            "confidence_threshold": 0.9,
        }

        response = orion_client.post("/api/v1/orion-runtime/validate-temporal", json=payload)

        assert response.status_code == 200
        data = response.json()

        audit_hash = data["audit_hash"]
        assert len(audit_hash) == 64  # SHA256 hex string is 64 chars
        assert all(c in "0123456789abcdef" for c in audit_hash)

    def test_validate_temporal_consensus_metrics(self, orion_client):
        """Test consensus metrics in response"""
        payload = {
            "bundesland": "Vorarlberg",
            "building_type": "Wohnhaus",
            "calculation_data": {"type": "test"},
            "richtlinie": 6,
            "confidence_threshold": 0.95,
        }

        response = orion_client.post("/api/v1/orion-runtime/validate-temporal", json=payload)

        assert response.status_code == 200
        data = response.json()

        consensus = data["consensus"]
        assert consensus["agents_count"] == 8
        assert 0 <= consensus["agreements"] <= 8
        assert 0.0 <= consensus["consensus_level"] <= 1.0
        assert "dominant_state" in consensus
        assert "confidence_score" in consensus


class TestConsensusStatus:
    """Tests for multi-agent consensus status endpoint"""

    def test_consensus_status_default(self, orion_client):
        """Test consensus status with default confidence"""
        response = orion_client.get("/api/v1/orion-runtime/consensus-status")

        assert response.status_code == 200
        data = response.json()

        assert "consensus" in data
        assert "timestamp" in data
        assert "production_readiness" in data
        assert "uptime_sla" in data

    def test_consensus_status_with_confidence(self, orion_client):
        """Test consensus status with custom confidence threshold"""
        response = orion_client.get(
            "/api/v1/orion-runtime/consensus-status?confidence=0.75"
        )

        assert response.status_code == 200
        data = response.json()

        consensus = data["consensus"]
        assert consensus["agents_count"] == 8
        assert consensus["consensus_level"] > 0

    def test_consensus_status_production_readiness(self, orion_client):
        """Test production readiness metric"""
        response = orion_client.get("/api/v1/orion-runtime/consensus-status")

        assert response.status_code == 200
        data = response.json()

        assert data["production_readiness"] >= 96.7
        assert data["uptime_sla"] >= 99.5


class TestAuditChain:
    """Tests for audit chain retrieval endpoint"""

    def test_get_audit_chain_not_found(self, orion_client):
        """Test retrieving non-existent audit chain"""
        response = orion_client.get(
            "/api/v1/orion-runtime/audit-chain/nonexistent-id-12345"
        )

        assert response.status_code == 404

    def test_get_audit_chain_after_validation(self, orion_client):
        """Test retrieving audit chain after validation"""
        # First, create a validation
        payload = {
            "bundesland": "Wien",
            "building_type": "Wohnhaus",
            "calculation_data": {"type": "test"},
            "richtlinie": 6,
            "confidence_threshold": 0.9,
        }

        response1 = orion_client.post("/api/v1/orion-runtime/validate-temporal", json=payload)
        assert response1.status_code == 200

        decision_id = response1.json()["decision_id"]

        # Now retrieve the audit chain
        response2 = orion_client.get(f"/api/v1/orion-runtime/audit-chain/{decision_id}")

        assert response2.status_code == 200
        data = response2.json()

        assert data["decision_id"] == decision_id
        assert "entries_count" in data
        assert data["chain_valid"] is True
        assert "entries" in data
        assert len(data["entries"]) > 0

    def test_audit_chain_sha256_integrity(self, orion_client):
        """Test SHA256 audit chain integrity"""
        payload = {
            "bundesland": "Tirol",
            "building_type": "Büro",
            "calculation_data": {"type": "test_integrity"},
            "richtlinie": 6,
            "confidence_threshold": 0.85,
        }

        response1 = orion_client.post("/api/v1/orion-runtime/validate-temporal", json=payload)
        decision_id = response1.json()["decision_id"]

        response2 = orion_client.get(f"/api/v1/orion-runtime/audit-chain/{decision_id}")
        data = response2.json()

        # Check that entries have hashes
        for entry in data["entries"]:
            assert "current_hash" in entry
            assert len(entry["current_hash"]) == 64  # SHA256
            assert "previous_hash" in entry

        # Check chain validity
        assert data["chain_valid"] is True


class TestRuntimeStatus:
    """Tests for runtime status endpoint"""

    def test_runtime_status_structure(self, orion_client):
        """Test runtime status response structure"""
        response = orion_client.get("/api/v1/orion-runtime/runtime-status")

        assert response.status_code == 200
        data = response.json()

        assert "status" in data
        assert "components_green" in data
        assert "components_total" in data
        assert "production_readiness" in data
        assert "uptime_sla" in data
        assert "audit_chain_valid" in data
        assert "consensus_level" in data
        assert "last_verification" in data
        assert "phase" in data
        assert "next_phase" in data

    def test_runtime_status_green_indicators(self, orion_client):
        """Test all GREEN status indicators"""
        response = orion_client.get("/api/v1/orion-runtime/runtime-status")

        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "operational"
        assert data["components_green"] >= 13  # Phase 1: at least 13/14
        assert data["components_total"] == 14
        assert data["production_readiness"] >= 96.7
        assert data["uptime_sla"] >= 99.5
        assert data["audit_chain_valid"] is True

    def test_runtime_status_phase(self, orion_client):
        """Test phase indicator"""
        response = orion_client.get("/api/v1/orion-runtime/runtime-status")

        assert response.status_code == 200
        data = response.json()

        assert "Edge Decision Layer" in data["phase"]


class TestAbstainSafetyProtocol:
    """Tests for ABSTAIN safety protocol endpoint"""

    def test_abstain_safety_protocol_triggered(self, orion_client):
        """Test ABSTAIN safety protocol trigger"""
        response = orion_client.post(
            "/api/v1/orion-runtime/abstain-safety-protocol?decision_id=test-decision-123&reason=insufficient_data&confidence_threshold=0.75"
        )

        assert response.status_code == 200
        data = response.json()

        assert data["runtime_state"] == "ABSTAIN"
        assert data["action"] == "SAFETY_PROTOCOL_ENGAGED"
        assert data["reason"] == "insufficient_data"
        assert data["logged"] is True

    def test_abstain_safety_protocol_recommendation(self, orion_client):
        """Test ABSTAIN returns safe fallback"""
        response = orion_client.post(
            "/api/v1/orion-runtime/abstain-safety-protocol?decision_id=test-decision-456&reason=conflicting_agents&confidence_threshold=0.60"
        )

        assert response.status_code == 200
        data = response.json()

        assert "recommendation" in data
        assert "Ziviltechniker" in data["recommendation"]


class TestOrionHealth:
    """Tests for ORION health check endpoint"""

    def test_orion_health_check(self, orion_client):
        """Test ORION health check endpoint"""
        response = orion_client.get("/api/v1/orion-runtime/health")

        assert response.status_code == 200
        data = response.json()

        assert "status" in data
        assert "runtime" in data
        assert data["runtime"] == "ORION"
        assert "phase" in data
        assert "components_green" in data
        assert "consensus_level" in data
        assert "timestamp" in data


class TestIntegrationWithCompliance:
    """Integration tests with compliance router"""

    def test_temporal_validation_with_real_bundesland(self, orion_client):
        """Test temporal validation with all 9 Bundesländer"""
        bundeslaender = [
            "Wien",
            "Niederösterreich",
            "Oberösterreich",
            "Salzburg",
            "Tirol",
            "Vorarlberg",
            "Steiermark",
            "Kärnten",
            "Burgenland",
        ]

        for bundesland in bundeslaender:
            payload = {
                "bundesland": bundesland,
                "building_type": "Wohnhaus",
                "calculation_data": {"type": "test", "bl": bundesland},
                "richtlinie": 6,
                "confidence_threshold": 0.85,
            }

            response = orion_client.post(
                "/api/v1/orion-runtime/validate-temporal", json=payload
            )

            assert response.status_code == 200
            data = response.json()
            assert "decision_id" in data
            assert "audit_hash" in data


class TestErrorHandling:
    """Tests for error handling"""

    def test_missing_required_fields(self, orion_client):
        """Test validation with missing required fields"""
        payload = {
            "bundesland": "Wien",
            # missing building_type
            "calculation_data": {},
            "richtlinie": 6,
            "confidence_threshold": 0.85,
        }

        response = orion_client.post("/api/v1/orion-runtime/validate-temporal", json=payload)

        assert response.status_code == 422  # Validation error

    def test_invalid_richtlinie(self, orion_client):
        """Test with invalid OIB-RL number"""
        payload = {
            "bundesland": "Wien",
            "building_type": "Wohnhaus",
            "calculation_data": {},
            "richtlinie": 99,  # Invalid
            "confidence_threshold": 0.85,
        }

        response = orion_client.post("/api/v1/orion-runtime/validate-temporal", json=payload)

        assert response.status_code == 200  # Should still work (graceful handling)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
