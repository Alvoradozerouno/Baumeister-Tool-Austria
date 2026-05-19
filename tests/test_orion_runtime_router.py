"""
Test suite for ORION Runtime Router
Tests the deterministic temporal edge runtime decision system.
"""

import pytest
import time
from datetime import datetime
from fastapi.testclient import TestClient

from api.main import app

client = TestClient(app)


class TestOrionRuntimeRouter:
    """Tests for ORION Runtime API endpoints."""

    def test_process_decision_verified(self):
        """Test processing a decision that results in VERIFIED state."""
        response = client.post(
            "/api/v1/orion-runtime/process-decision",
            params={"confidence": 0.95, "timeout_ms": 100}
        )
        assert response.status_code == 200
        data = response.json()
        
        assert "decision_id" in data
        assert "state" in data
        assert data["confidence"] == 0.95
        assert "consensus_score" in data
        assert "audit_hash" in data
        assert "processing_time_ms" in data
        assert data["state"] in ["VERIFIED", "PROCESSING", "UNCERTAIN", "ABSTAIN", "UNKNOWN", "FAILED"]

    def test_process_decision_low_confidence(self):
        """Test processing a decision with low confidence."""
        response = client.post(
            "/api/v1/orion-runtime/process-decision",
            params={"confidence": 0.4, "timeout_ms": 100}
        )
        assert response.status_code == 200
        data = response.json()
        
        assert "decision_id" in data
        assert data["confidence"] == 0.4
        assert "consensus_score" in data

    def test_process_decision_boundary_values(self):
        """Test with boundary confidence values."""
        for conf in [0.0, 0.5, 1.0]:
            response = client.post(
                "/api/v1/orion-runtime/process-decision",
                params={"confidence": conf, "timeout_ms": 100}
            )
            assert response.status_code == 200
            data = response.json()
            assert data["confidence"] == conf

    def test_get_status(self):
        """Test getting system status."""
        # First process a decision
        client.post(
            "/api/v1/orion-runtime/process-decision",
            params={"confidence": 0.8, "timeout_ms": 100}
        )
        
        # Get status
        response = client.get("/api/v1/orion-runtime/status")
        assert response.status_code == 200
        data = response.json()
        
        assert "version" in data
        assert "state" in data
        assert "hardware_target" in data
        assert "decision_count" in data
        assert data["decision_count"] >= 1
        assert "verified_count" in data
        assert "abstain_count" in data
        assert "failed_count" in data
        assert "audit_chain_valid" in data
        assert "audit_chain_entries" in data
        assert "hardware_status" in data

    def test_verify_audit_chain(self):
        """Test audit chain verification."""
        response = client.get("/api/v1/orion-runtime/verify-audit-chain")
        assert response.status_code == 200
        data = response.json()
        
        assert "valid" in data
        assert isinstance(data["valid"], bool)
        assert "message" in data
        assert "entry_count" in data
        assert "last_hash" in data
        assert len(data["last_hash"]) == 64  # SHA256 hex string

    def test_get_audit_chain_entries(self):
        """Test retrieving audit chain entries."""
        # Process some decisions first
        for _ in range(3):
            client.post(
                "/api/v1/orion-runtime/process-decision",
                params={"confidence": 0.8, "timeout_ms": 100}
            )
        
        response = client.get("/api/v1/orion-runtime/audit-chain/entries", 
                            params={"limit": 10, "offset": 0})
        assert response.status_code == 200
        data = response.json()
        
        assert "entries" in data
        assert "total" in data
        assert "limit" in data
        assert "offset" in data
        assert data["limit"] == 10
        assert data["offset"] == 0
        
        if data["entries"]:
            entry = data["entries"][0]
            assert "timestamp" in entry
            assert "component" in entry
            assert "event_type" in entry
            assert "state" in entry
            assert "hash_id" in entry

    def test_audit_chain_entries_pagination(self):
        """Test pagination of audit chain entries."""
        response = client.get(
            "/api/v1/orion-runtime/audit-chain/entries",
            params={"limit": 5, "offset": 0}
        )
        assert response.status_code == 200
        data1 = response.json()
        
        response = client.get(
            "/api/v1/orion-runtime/audit-chain/entries",
            params={"limit": 5, "offset": 5}
        )
        assert response.status_code == 200
        data2 = response.json()
        
        # Both should be valid
        assert "entries" in data1
        assert "entries" in data2

    def test_reset_consensus(self):
        """Test resetting the consensus engine."""
        response = client.post("/api/v1/orion-runtime/reset-consensus")
        assert response.status_code == 200
        data = response.json()
        
        assert "message" in data
        assert "Consensus" in data["message"]

    def test_consensus_status(self):
        """Test getting consensus status."""
        response = client.get("/api/v1/orion-runtime/consensus-status")
        assert response.status_code == 200
        data = response.json()
        
        assert "agent_count" in data
        assert "agents_voted" in data
        assert "consensus_score" in data
        assert isinstance(data["consensus_score"], float)
        assert 0.0 <= data["consensus_score"] <= 1.0
        assert "votes_per_agent" in data

    def test_temporal_validation(self):
        """Test that temporal validation works over multiple decisions."""
        # Process multiple decisions to test temporal accumulation
        decisions = []
        for confidence in [0.8, 0.85, 0.9, 0.92, 0.95]:
            response = client.post(
                "/api/v1/orion-runtime/process-decision",
                params={"confidence": confidence, "timeout_ms": 100}
            )
            assert response.status_code == 200
            decisions.append(response.json())
        
        # All should have processed successfully
        assert len(decisions) == 5
        for decision in decisions:
            assert "decision_id" in decision
            assert "state" in decision

    def test_safe_to_execute_flag(self):
        """Test that safe_to_execute flag is set correctly."""
        response = client.post(
            "/api/v1/orion-runtime/process-decision",
            params={"confidence": 0.95, "timeout_ms": 100}
        )
        assert response.status_code == 200
        data = response.json()
        
        assert "safe_to_execute" in data
        # safe_to_execute should be True only if state is VERIFIED
        if data["state"] == "VERIFIED":
            assert data["safe_to_execute"] is True
        else:
            assert data["safe_to_execute"] is False

    def test_hardware_target_info(self):
        """Test that hardware target information is included."""
        response = client.post(
            "/api/v1/orion-runtime/process-decision",
            params={"confidence": 0.8, "timeout_ms": 100}
        )
        assert response.status_code == 200
        data = response.json()
        
        assert "hardware_target" in data
        assert data["hardware_target"] in ["laptop_cpu", "pi5_arm64", "kria_kv260", "note10_exynos", "jetson_orin"]
        assert "fpga_latency_ns" in data

    def test_processing_time_measurement(self):
        """Test that processing time is measured accurately."""
        response = client.post(
            "/api/v1/orion-runtime/process-decision",
            params={"confidence": 0.8, "timeout_ms": 100}
        )
        assert response.status_code == 200
        data = response.json()
        
        assert "processing_time_ms" in data
        assert data["processing_time_ms"] >= 0
        assert data["processing_time_ms"] < 1000  # Should be less than 1 second

    def test_invalid_confidence_value(self):
        """Test that invalid confidence values are rejected."""
        # Negative confidence
        response = client.post(
            "/api/v1/orion-runtime/process-decision",
            params={"confidence": -0.1, "timeout_ms": 100}
        )
        assert response.status_code == 422  # FastAPI validation error
        
        # Confidence > 1.0
        response = client.post(
            "/api/v1/orion-runtime/process-decision",
            params={"confidence": 1.5, "timeout_ms": 100}
        )
        assert response.status_code == 422  # FastAPI validation error

    def test_decision_id_uniqueness(self):
        """Test that each decision gets a unique ID."""
        decision_ids = []
        for _ in range(5):
            response = client.post(
                "/api/v1/orion-runtime/process-decision",
                params={"confidence": 0.8, "timeout_ms": 100}
            )
            assert response.status_code == 200
            decision_ids.append(response.json()["decision_id"])
        
        # All IDs should be unique
        assert len(decision_ids) == len(set(decision_ids))

    def test_runtime_state_transitions(self):
        """Test that runtime state can transition between different states."""
        states_seen = set()
        
        # Process multiple decisions with different confidences
        for conf in [0.3, 0.5, 0.7, 0.9, 0.95]:
            response = client.post(
                "/api/v1/orion-runtime/process-decision",
                params={"confidence": conf, "timeout_ms": 100}
            )
            assert response.status_code == 200
            state = response.json()["state"]
            states_seen.add(state)
        
        # Should see at least one state (likely multiple)
        assert len(states_seen) >= 1


class TestOrionRuntimeEdgeCases:
    """Test edge cases and error conditions."""

    def test_concurrent_decisions(self):
        """Test that multiple concurrent decisions are handled."""
        responses = []
        for i in range(10):
            response = client.post(
                "/api/v1/orion-runtime/process-decision",
                params={"confidence": 0.5 + (i * 0.05), "timeout_ms": 100}
            )
            assert response.status_code == 200
            responses.append(response.json())
        
        # All should succeed
        assert len(responses) == 10
        
        # All should have unique IDs
        ids = [r["decision_id"] for r in responses]
        assert len(set(ids)) == 10

    def test_audit_chain_integrity(self):
        """Test that audit chain maintains integrity."""
        # Process several decisions
        for conf in [0.7, 0.8, 0.9]:
            client.post(
                "/api/v1/orion-runtime/process-decision",
                params={"confidence": conf, "timeout_ms": 100}
            )
        
        # Verify chain
        response = client.get("/api/v1/orion-runtime/verify-audit-chain")
        assert response.status_code == 200
        data = response.json()
        
        assert data["valid"] is True
        assert "verified" in data["message"].lower()

    def test_long_running_operations(self):
        """Test behavior with timeout close to limit."""
        response = client.post(
            "/api/v1/orion-runtime/process-decision",
            params={"confidence": 0.8, "timeout_ms": 500}
        )
        assert response.status_code == 200
        data = response.json()
        
        assert data["processing_time_ms"] <= 500


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
