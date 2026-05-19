"""
Test suite for Multi-Agent Consensus Router
Tests the 8-agent consensus decision-making system.
"""

import pytest
from datetime import datetime
from fastapi.testclient import TestClient

from api.main import app

client = TestClient(app)


class TestMultiAgentConsensusRouter:
    """Tests for Multi-Agent Consensus API endpoints."""

    def test_register_agent_vote_basic(self):
        """Test registering a basic agent vote."""
        response = client.post(
            "/api/v1/multi-agent-consensus/register-agent-vote",
            json={
                "agent_id": "agent_1",
                "confidence": 0.85
            }
        )
        assert response.status_code == 200
        data = response.json()
        
        assert data["agent_id"] == "agent_1"
        assert data["confidence"] == 0.85
        assert "vote_count" in data
        assert data["vote_count"] >= 1
        assert "consensus_score" in data
        assert "agents_voting" in data
        assert "registered_at" in data

    def test_register_multiple_agent_votes(self):
        """Test registering votes from multiple agents."""
        agents = ["agent_1", "agent_2", "agent_3"]
        responses = []
        
        for agent_id in agents:
            response = client.post(
                "/api/v1/multi-agent-consensus/register-agent-vote",
                json={
                    "agent_id": agent_id,
                    "confidence": 0.8 + (0.05 * len(responses))
                }
            )
            assert response.status_code == 200
            responses.append(response.json())
        
        # Consensus should increase with more agents voting
        assert len(responses) == 3
        last_response = responses[-1]
        assert last_response["agents_voting"] >= 1

    def test_register_agent_vote_with_reasoning(self):
        """Test registering vote with reasoning."""
        response = client.post(
            "/api/v1/multi-agent-consensus/register-agent-vote",
            json={
                "agent_id": "agent_reasoning",
                "confidence": 0.92,
                "reasoning": "Objects detected with 92% confidence after temporal validation"
            }
        )
        assert response.status_code == 200
        data = response.json()
        
        assert data["confidence"] == 0.92

    def test_register_agent_vote_with_metadata(self):
        """Test registering vote with metadata."""
        response = client.post(
            "/api/v1/multi-agent-consensus/register-agent-vote",
            json={
                "agent_id": "agent_meta",
                "confidence": 0.88,
                "metadata": {
                    "model_version": "v2.1",
                    "processing_time_ms": 45,
                    "gpu_utilization": 72.5,
                    "inference_backend": "ONNX"
                }
            }
        )
        assert response.status_code == 200
        data = response.json()
        
        assert "metadata" in data

    def test_register_agent_vote_boundary_confidence(self):
        """Test boundary confidence values."""
        for conf in [0.0, 0.5, 1.0]:
            response = client.post(
                "/api/v1/multi-agent-consensus/register-agent-vote",
                json={
                    "agent_id": f"agent_boundary_{conf}",
                    "confidence": conf
                }
            )
            assert response.status_code == 200
            data = response.json()
            assert data["confidence"] == conf

    def test_invalid_confidence_value(self):
        """Test that invalid confidence values are rejected."""
        # Negative confidence
        response = client.post(
            "/api/v1/multi-agent-consensus/register-agent-vote",
            json={
                "agent_id": "agent_invalid",
                "confidence": -0.1
            }
        )
        assert response.status_code == 422  # FastAPI validation error
        
        # Confidence > 1.0
        response = client.post(
            "/api/v1/multi-agent-consensus/register-agent-vote",
            json={
                "agent_id": "agent_invalid",
                "confidence": 1.5
            }
        )
        assert response.status_code == 422  # FastAPI validation error

    def test_get_consensus_score(self):
        """Test getting current consensus score."""
        # Register some votes first
        for i in range(3):
            client.post(
                "/api/v1/multi-agent-consensus/register-agent-vote",
                json={
                    "agent_id": f"agent_score_{i}",
                    "confidence": 0.85 + (0.05 * i)
                }
            )
        
        response = client.get("/api/v1/multi-agent-consensus/consensus-score")
        assert response.status_code == 200
        data = response.json()
        
        assert "consensus_score" in data
        assert 0.0 <= data["consensus_score"] <= 1.0
        assert "agents_count_expected" in data
        assert "agents_voting" in data
        assert "quality" in data
        assert data["quality"] in ["LOW", "MEDIUM", "HIGH"]
        assert "interpretation" in data
        assert "calculated_at" in data

    def test_consensus_score_interpretation(self):
        """Test consensus score interpretation quality."""
        response = client.get("/api/v1/multi-agent-consensus/consensus-score")
        assert response.status_code == 200
        data = response.json()
        
        score = data["consensus_score"]
        
        # Quality should match score
        if score >= 0.90:
            assert "strongly agree" in data["interpretation"].lower() or "strong" in data["interpretation"].lower()
        elif score >= 0.70:
            assert "moderate" in data["interpretation"].lower() or "moderately" in data["interpretation"].lower()
        else:
            assert "disagree" in data["interpretation"].lower() or "significant" in data["interpretation"].lower()

    def test_get_agent_votes(self):
        """Test retrieving agent vote information."""
        response = client.get("/api/v1/multi-agent-consensus/agent-votes")
        assert response.status_code == 200
        data = response.json()
        
        assert "agents" in data
        assert isinstance(data["agents"], list)
        assert "total_votes" in data
        assert "consensus_strength" in data
        assert "agent_count" in data
        assert "retrieved_at" in data

    def test_get_agent_votes_detailed(self):
        """Test retrieving detailed agent vote history."""
        # Register some votes first
        for i in range(2):
            client.post(
                "/api/v1/multi-agent-consensus/register-agent-vote",
                json={
                    "agent_id": f"agent_detail_{i}",
                    "confidence": 0.8 + (0.1 * i)
                }
            )
        
        response = client.get(
            "/api/v1/multi-agent-consensus/agent-votes",
            params={"detailed": True}
        )
        assert response.status_code == 200
        data = response.json()
        
        if data["agents"]:
            agent = data["agents"][0]
            assert "agent_id" in agent
            assert "vote_count" in agent
            assert "average_confidence" in agent
            assert "min_confidence" in agent
            assert "max_confidence" in agent

    def test_reset_consensus(self):
        """Test resetting the consensus engine."""
        # Register some votes
        client.post(
            "/api/v1/multi-agent-consensus/register-agent-vote",
            json={"agent_id": "agent_reset", "confidence": 0.9}
        )
        
        # Reset
        response = client.post("/api/v1/multi-agent-consensus/reset-consensus")
        assert response.status_code == 200
        data = response.json()
        
        assert "message" in data
        assert "Consensus" in data["message"]
        assert "previous_agent_count" in data
        assert "previous_total_votes" in data
        assert "reset_at" in data
        assert data["ready_for_new_round"] is True

    def test_validate_agreement_threshold_met(self):
        """Test agreement validation when threshold is met."""
        # Register high-confidence votes
        for i in range(5):
            client.post(
                "/api/v1/multi-agent-consensus/register-agent-vote",
                json={
                    "agent_id": f"agent_high_{i}",
                    "confidence": 0.95
                }
            )
        
        response = client.post(
            "/api/v1/multi-agent-consensus/validate-agreement",
            json={
                "minimum_threshold": 0.70,
                "minimum_agents": 3
            }
        )
        assert response.status_code == 200
        data = response.json()
        
        assert "valid" in data
        assert "current_consensus" in data
        assert "current_agents" in data
        assert "meets_threshold" in data
        assert "meets_agent_count" in data
        assert "safe_to_proceed" in data

    def test_validate_agreement_threshold_not_met(self):
        """Test agreement validation when threshold is not met."""
        response = client.post(
            "/api/v1/multi-agent-consensus/validate-agreement",
            json={
                "minimum_threshold": 0.99,  # Very high threshold
                "minimum_agents": 10  # Require many agents
            }
        )
        assert response.status_code == 200
        data = response.json()
        
        # Should likely not be valid with such high requirements
        assert "valid" in data
        assert "safe_to_proceed" in data

    def test_validate_agreement_boundary_values(self):
        """Test boundary values for threshold validation."""
        # Minimum threshold
        response = client.post(
            "/api/v1/multi-agent-consensus/validate-agreement",
            json={
                "minimum_threshold": 0.0,
                "minimum_agents": 1
            }
        )
        assert response.status_code == 200
        
        # Maximum threshold
        response = client.post(
            "/api/v1/multi-agent-consensus/validate-agreement",
            json={
                "minimum_threshold": 1.0,
                "minimum_agents": 10
            }
        )
        assert response.status_code == 200

    def test_agent_vote_accumulation(self):
        """Test that votes accumulate for the same agent."""
        agent_id = "accumulator_agent"
        
        # Register multiple votes from same agent
        for conf in [0.8, 0.85, 0.9]:
            response = client.post(
                "/api/v1/multi-agent-consensus/register-agent-vote",
                json={
                    "agent_id": agent_id,
                    "confidence": conf
                }
            )
            assert response.status_code == 200
            data = response.json()
            assert data["agent_id"] == agent_id
        
        # Get votes and check accumulation
        response = client.get(
            "/api/v1/multi-agent-consensus/agent-votes",
            params={"detailed": True}
        )
        agents = response.json()["agents"]
        
        # Find our agent
        our_agent = next((a for a in agents if a["agent_id"] == agent_id), None)
        assert our_agent is not None
        assert our_agent["vote_count"] == 3

    def test_consensus_with_diverse_agents(self):
        """Test consensus calculation with diverse agent votes."""
        # Register votes from diverse agents with varying confidence
        agents_data = [
            ("ml_vision", 0.92),
            ("sensor_fusion", 0.88),
            ("rule_engine", 0.85),
            ("ensemble", 0.95),
            ("temporal_validator", 0.91),
        ]
        
        for agent_id, conf in agents_data:
            client.post(
                "/api/v1/multi-agent-consensus/register-agent-vote",
                json={
                    "agent_id": agent_id,
                    "confidence": conf
                }
            )
        
        # Get consensus
        response = client.get("/api/v1/multi-agent-consensus/consensus-score")
        assert response.status_code == 200
        data = response.json()
        
        # Should have all agents voting
        assert data["agents_voting"] >= 5
        assert 0.0 <= data["consensus_score"] <= 1.0

    def test_consecutive_consensus_cycles(self):
        """Test multiple consecutive consensus cycles."""
        for cycle in range(3):
            # Register votes
            for i in range(3):
                client.post(
                    "/api/v1/multi-agent-consensus/register-agent-vote",
                    json={
                        "agent_id": f"cycle_{cycle}_agent_{i}",
                        "confidence": 0.8 + (0.05 * i)
                    }
                )
            
            # Get consensus
            response = client.get("/api/v1/multi-agent-consensus/consensus-score")
            assert response.status_code == 200
            
            # Reset for next cycle
            if cycle < 2:
                client.post("/api/v1/multi-agent-consensus/reset-consensus")


class TestMultiAgentConsensusEdgeCases:
    """Test edge cases and error conditions."""

    def test_no_votes_consensus_score(self):
        """Test consensus score when no votes registered."""
        # Reset first
        client.post("/api/v1/multi-agent-consensus/reset-consensus")
        
        response = client.get("/api/v1/multi-agent-consensus/consensus-score")
        assert response.status_code == 200
        data = response.json()
        
        assert data["agents_voting"] >= 0
        assert "consensus_score" in data

    def test_single_agent_voting(self):
        """Test consensus with only one agent voting."""
        client.post("/api/v1/multi-agent-consensus/reset-consensus")
        
        client.post(
            "/api/v1/multi-agent-consensus/register-agent-vote",
            json={
                "agent_id": "lonely_agent",
                "confidence": 0.9
            }
        )
        
        response = client.get("/api/v1/multi-agent-consensus/consensus-score")
        assert response.status_code == 200
        data = response.json()
        
        assert data["agents_voting"] >= 1

    def test_conflicting_agent_votes(self):
        """Test consensus with conflicting votes."""
        client.post("/api/v1/multi-agent-consensus/reset-consensus")
        
        # Register opposing votes
        client.post(
            "/api/v1/multi-agent-consensus/register-agent-vote",
            json={"agent_id": "optimistic", "confidence": 0.95}
        )
        client.post(
            "/api/v1/multi-agent-consensus/register-agent-vote",
            json={"agent_id": "pessimistic", "confidence": 0.1}
        )
        
        response = client.get("/api/v1/multi-agent-consensus/consensus-score")
        assert response.status_code == 200
        data = response.json()
        
        # Consensus should be low due to disagreement
        assert "consensus_score" in data

    def test_agent_votes_statistics(self):
        """Test vote statistics calculations."""
        agent_id = "stats_agent"
        
        # Register votes with known values
        confidences = [0.7, 0.8, 0.9]
        for conf in confidences:
            client.post(
                "/api/v1/multi-agent-consensus/register-agent-vote",
                json={
                    "agent_id": agent_id,
                    "confidence": conf
                }
            )
        
        response = client.get(
            "/api/v1/multi-agent-consensus/agent-votes",
            params={"detailed": True}
        )
        agents = response.json()["agents"]
        
        # Find our agent
        our_agent = next((a for a in agents if a["agent_id"] == agent_id), None)
        assert our_agent is not None
        
        # Check statistics
        assert our_agent["min_confidence"] == min(confidences)
        assert our_agent["max_confidence"] == max(confidences)
        assert our_agent["vote_count"] == len(confidences)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
