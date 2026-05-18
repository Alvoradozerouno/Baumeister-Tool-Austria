"""
Tests for Multi-Agent Consensus Router
"""

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    """Fixture to provide test client"""
    from api.main import app
    return TestClient(app)


class TestConsensusEvaluation:
    """Test consensus evaluation"""

    def test_evaluate_consensus_default(self, client):
        """Test consensus evaluation with default metrics"""
        response = client.get("/api/v1/multi-agent-consensus/metrics/default")
        assert response.status_code == 200
        metrics = response.json()
        
        response = client.post(
            "/api/v1/multi-agent-consensus/evaluate",
            json=metrics,
        )
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert "timestamp" in data
        assert "consensus_level" in data
        assert data["consensus_level"] in ["GREEN", "YELLOW", "RED"]
        assert "average_score" in data
        assert "production_readiness" in data
        assert "agents" in data

    def test_evaluate_consensus_custom(self, client):
        """Test consensus evaluation with custom metrics"""
        metrics = {
            "motion_score": 0.80,
            "temporal_average": 0.85,
            "variance": 0.02,
            "optical_flow": 0.82,
            "fps": 30.0,
            "runtime_green": 18,
            "runtime_total": 20,
            "audit_valid": True,
            "confidence": 0.88,
        }
        
        response = client.post(
            "/api/v1/multi-agent-consensus/evaluate",
            json=metrics,
        )
        assert response.status_code == 200
        data = response.json()
        assert "agents" in data
        assert len(data["agents"]) == 8  # 8 agents


class TestAgentAssessments:
    """Test individual agent assessments"""

    def test_all_agents_present(self, client):
        """Test that all agents are evaluated"""
        metrics = {
            "motion_score": 0.75,
            "temporal_average": 0.85,
            "variance": 0.02,
            "optical_flow": 0.80,
            "fps": 30.0,
            "runtime_green": 19,
            "runtime_total": 20,
            "audit_valid": True,
            "confidence": 0.90,
        }
        
        response = client.post(
            "/api/v1/multi-agent-consensus/evaluate",
            json=metrics,
        )
        assert response.status_code == 200
        data = response.json()
        
        agents = data["agents"]
        agent_names = list(agents.keys())
        
        expected_agents = [
            "EIRA",
            "ORION",
            "DDGK",
            "GUARDIAN",
            "NEXUS",
            "EPISTEMIC",
            "AGENT_8",
            "AGENT_17",
        ]
        
        for agent in expected_agents:
            assert agent in agent_names
            assert "score" in agents[agent]
            assert "position" in agents[agent]
            assert "fpga_portable" in agents[agent]


class TestConsensusLevel:
    """Test consensus level determination"""

    def test_consensus_green(self, client):
        """Test GREEN consensus level"""
        metrics = {
            "motion_score": 0.90,
            "temporal_average": 0.95,
            "variance": 0.01,
            "optical_flow": 0.92,
            "fps": 30.0,
            "runtime_green": 20,
            "runtime_total": 20,
            "audit_valid": True,
            "confidence": 0.95,
        }
        
        response = client.post(
            "/api/v1/multi-agent-consensus/evaluate",
            json=metrics,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["consensus_level"] == "GREEN"

    def test_consensus_yellow(self, client):
        """Test YELLOW consensus level"""
        metrics = {
            "motion_score": 0.65,
            "temporal_average": 0.70,
            "variance": 0.05,
            "optical_flow": 0.68,
            "fps": 25.0,
            "runtime_green": 14,
            "runtime_total": 20,
            "audit_valid": True,
            "confidence": 0.75,
        }
        
        response = client.post(
            "/api/v1/multi-agent-consensus/evaluate",
            json=metrics,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["consensus_level"] in ["YELLOW", "GREEN"]


class TestProductionReadiness:
    """Test production readiness scoring"""

    def test_production_readiness_high(self, client):
        """Test high production readiness"""
        metrics = {
            "motion_score": 0.90,
            "temporal_average": 0.95,
            "variance": 0.01,
            "optical_flow": 0.92,
            "fps": 30.0,
            "runtime_green": 20,
            "runtime_total": 20,
            "audit_valid": True,
            "confidence": 0.95,
        }
        
        response = client.post(
            "/api/v1/multi-agent-consensus/evaluate",
            json=metrics,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["production_readiness"] > 80


class TestConsensusHistory:
    """Test consensus history tracking"""

    def test_get_last_consensus(self, client):
        """Test getting last consensus"""
        metrics = {
            "motion_score": 0.75,
            "temporal_average": 0.85,
            "variance": 0.02,
            "optical_flow": 0.80,
            "fps": 30.0,
            "runtime_green": 19,
            "runtime_total": 20,
            "audit_valid": True,
            "confidence": 0.90,
        }
        
        # First evaluation
        client.post("/api/v1/multi-agent-consensus/evaluate", json=metrics)
        
        # Get last
        response = client.get("/api/v1/multi-agent-consensus/last")
        assert response.status_code == 200
        data = response.json()
        assert "consensus_level" in data

    def test_get_consensus_history(self, client):
        """Test getting consensus history"""
        metrics = {
            "motion_score": 0.75,
            "temporal_average": 0.85,
            "variance": 0.02,
            "optical_flow": 0.80,
            "fps": 30.0,
            "runtime_green": 19,
            "runtime_total": 20,
            "audit_valid": True,
            "confidence": 0.90,
        }
        
        # Make multiple evaluations
        for _ in range(3):
            client.post("/api/v1/multi-agent-consensus/evaluate", json=metrics)
        
        response = client.get("/api/v1/multi-agent-consensus/history?limit=10")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)


class TestAgentListing:
    """Test agent listing"""

    def test_list_agents(self, client):
        """Test listing all agents"""
        response = client.get("/api/v1/multi-agent-consensus/agents")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 8
        
        # Check structure
        for agent in data:
            assert "name" in agent
            assert "role" in agent


class TestConsensusSummary:
    """Test consensus summary"""

    def test_get_consensus_summary(self, client):
        """Test getting consensus summary"""
        metrics = {
            "motion_score": 0.75,
            "temporal_average": 0.85,
            "variance": 0.02,
            "optical_flow": 0.80,
            "fps": 30.0,
            "runtime_green": 19,
            "runtime_total": 20,
            "audit_valid": True,
            "confidence": 0.90,
        }
        
        client.post("/api/v1/multi-agent-consensus/evaluate", json=metrics)
        
        response = client.get("/api/v1/multi-agent-consensus/summary")
        assert response.status_code == 200
        data = response.json()
        assert "consensus_level" in data
        assert "average_score" in data
        assert "production_readiness" in data
        assert "agents_total" in data
        assert "agents_approved" in data


class TestMetrics:
    """Test metrics endpoints"""

    def test_get_default_metrics(self, client):
        """Test getting default metrics"""
        response = client.get("/api/v1/multi-agent-consensus/metrics/default")
        assert response.status_code == 200
        data = response.json()
        
        # Verify all fields
        assert "motion_score" in data
        assert "temporal_average" in data
        assert "variance" in data
        assert "optical_flow" in data
        assert "fps" in data


class TestReset:
    """Test reset functionality"""

    def test_reset_consensus(self, client):
        """Test resetting consensus"""
        metrics = {
            "motion_score": 0.75,
            "temporal_average": 0.85,
            "variance": 0.02,
            "optical_flow": 0.80,
            "fps": 30.0,
            "runtime_green": 19,
            "runtime_total": 20,
            "audit_valid": True,
            "confidence": 0.90,
        }
        
        # Evaluate
        client.post("/api/v1/multi-agent-consensus/evaluate", json=metrics)
        
        # Reset
        response = client.post("/api/v1/multi-agent-consensus/reset")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "reset"
