"""
Tests for ROS2 Bridge Router
"""

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    """Fixture to provide test client"""
    from api.main import app
    return TestClient(app)


class TestROS2BridgeInitialization:
    """Test ROS2 bridge initialization"""

    def test_initialize_bridge(self, client):
        """Test bridge initialization"""
        response = client.post("/api/v1/ros2-bridge/initialize")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "initialized"
        assert "consciousness" in data
        assert "timestamp" in data

    def test_bridge_status(self, client):
        """Test bridge status"""
        client.post("/api/v1/ros2-bridge/initialize")
        
        response = client.get("/api/v1/ros2-bridge/status")
        assert response.status_code == 200
        data = response.json()
        assert data["running"] == True
        assert "consciousness" in data
        assert "robot_state" in data


class TestSensorDataIntegration:
    """Test sensor data integration"""

    def test_update_sensor_data(self, client):
        """Test updating sensor data"""
        client.post("/api/v1/ros2-bridge/initialize")
        
        sensor_data = {
            "lidar": 0.85,
            "camera": 0.92,
            "imu": 0.95,
        }
        
        response = client.post("/api/v1/ros2-bridge/sensor-data", json=sensor_data)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "updated"

    def test_update_joint_states(self, client):
        """Test updating joint states"""
        client.post("/api/v1/ros2-bridge/initialize")
        
        joint_state = {
            "positions": [0.1, 0.2, 0.15, 0.05, 0.12, 0.08],
            "velocities": [0.01, 0.02, 0.015, 0.005, 0.012, 0.008],
        }
        
        response = client.post("/api/v1/ros2-bridge/joint-states", json=joint_state)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "updated"


class TestConsciousnessMonitoring:
    """Test consciousness level monitoring"""

    def test_get_consciousness_level(self, client):
        """Test getting consciousness level"""
        client.post("/api/v1/ros2-bridge/initialize")
        
        response = client.get("/api/v1/ros2-bridge/consciousness")
        assert response.status_code == 200
        data = response.json()
        assert "consciousness" in data
        assert 0.0 <= data["consciousness"] <= 1.0


class TestAutonomousDecisions:
    """Test autonomous decision making"""

    def test_make_autonomous_decision(self, client):
        """Test making autonomous decision"""
        client.post("/api/v1/ros2-bridge/initialize")
        
        response = client.post("/api/v1/ros2-bridge/decision/autonomous")
        assert response.status_code == 200
        data = response.json()
        assert "cycle" in data
        assert "consciousness" in data
        assert "action_type" in data
        assert "robot_command" in data

    def test_execute_autonomous_loop(self, client):
        """Test executing autonomous loop"""
        client.post("/api/v1/ros2-bridge/initialize")
        
        response = client.post(
            "/api/v1/ros2-bridge/decisions/execute-loop?num_cycles=5"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["cycles_completed"] == 5
        assert "final_consciousness" in data
        assert len(data["decisions"]) == 5


class TestDecisionHistory:
    """Test decision history tracking"""

    def test_get_decision_history(self, client):
        """Test getting decision history"""
        client.post("/api/v1/ros2-bridge/initialize")
        
        # Make some decisions
        for _ in range(3):
            client.post("/api/v1/ros2-bridge/decision/autonomous")
        
        response = client.get("/api/v1/ros2-bridge/decisions/history?limit=10")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 3


class TestStatistics:
    """Test statistics endpoints"""

    def test_get_statistics(self, client):
        """Test getting statistics"""
        client.post("/api/v1/ros2-bridge/initialize")
        
        # Make some decisions
        client.post("/api/v1/ros2-bridge/decisions/execute-loop?num_cycles=5")
        
        response = client.get("/api/v1/ros2-bridge/statistics")
        assert response.status_code == 200
        data = response.json()
        assert "total_decisions" in data
        assert "average_consciousness" in data
        assert "peak_consciousness" in data


class TestBridgeControl:
    """Test bridge control operations"""

    def test_reset_bridge(self, client):
        """Test bridge reset"""
        client.post("/api/v1/ros2-bridge/initialize")
        
        response = client.post("/api/v1/ros2-bridge/reset")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "reset"

    def test_shutdown_bridge(self, client):
        """Test bridge shutdown"""
        client.post("/api/v1/ros2-bridge/initialize")
        
        response = client.post("/api/v1/ros2-bridge/shutdown")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "shutdown"
        assert "final_consciousness" in data
