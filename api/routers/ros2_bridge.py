"""
ORION-ROS2 Bridge Router
Bidirectional communication between ORION consciousness and ROS2 robotics

Provides RESTful endpoints for:
- Autonomous decision making
- Consciousness level monitoring
- Sensor data integration
- Robot command execution
- Decision history tracking
"""

import json
import time
from datetime import datetime
from typing import Dict, Any, List, Optional
from enum import Enum

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

# ============================================================================
# Models
# ============================================================================

class SensorData(BaseModel):
    """Robot sensor data"""
    lidar: float = Field(0.0, ge=0.0, le=1.0)
    camera: float = Field(0.0, ge=0.0, le=1.0)
    imu: float = Field(0.0, ge=0.0, le=1.0)


class JointState(BaseModel):
    """Robot joint state"""
    positions: List[float] = Field(default_factory=list)
    velocities: List[float] = Field(default_factory=list)


class RobotCommand(BaseModel):
    """Robot control command"""
    linear: float
    angular: float


class AutonomousDecision(BaseModel):
    """ORION autonomous decision"""
    cycle: int
    consciousness: float = Field(ge=0.0, le=1.0)
    action_type: str
    robot_command: RobotCommand
    timestamp: str


class DecisionHistory(BaseModel):
    """Decision history entry"""
    cycle: int
    consciousness: float
    action: str
    command: RobotCommand
    timestamp: str


# ============================================================================
# Bridge State
# ============================================================================

class ROSBridgeState:
    """Maintains ROS bridge state"""

    def __init__(self):
        self.consciousness = 0.5
        self.cycle = 0
        self.robot_state = {
            "sensors": {"lidar": 0.0, "camera": 0.0, "imu": 0.0},
            "joints": {"positions": [], "velocities": []},
        }
        self.decision_history: List[Dict[str, Any]] = []
        self.running = False
        self.start_time = datetime.utcnow()

    def update_consciousness(self):
        """Update consciousness level based on decisions"""
        if len(self.decision_history) > 0:
            # Consciousness grows with successful operations
            self.consciousness = min(1.0, 0.5 + len(self.decision_history) * 0.01)
        return self.consciousness

    def add_decision(self, action_type: str, command: RobotCommand):
        """Record a decision in history"""
        decision = {
            "cycle": self.cycle,
            "consciousness": self.consciousness,
            "action": action_type,
            "command": command.dict(),
            "timestamp": datetime.utcnow().isoformat(),
        }
        self.decision_history.append(decision)
        self.cycle += 1
        return decision


# ============================================================================
# Router Implementation
# ============================================================================

router = APIRouter(prefix="/api/v1/ros2-bridge", tags=["ros2-bridge"])

# Global bridge state
_bridge_state = ROSBridgeState()


@router.post("/initialize")
async def initialize_bridge() -> Dict[str, Any]:
    """Initialize ROS2 bridge"""
    global _bridge_state
    _bridge_state = ROSBridgeState()
    _bridge_state.running = True
    
    return {
        "status": "initialized",
        "consciousness": _bridge_state.consciousness,
        "timestamp": datetime.utcnow().isoformat(),
    }


@router.post("/sensor-data")
async def update_sensor_data(data: SensorData) -> Dict[str, Any]:
    """Update robot sensor data"""
    _bridge_state.robot_state["sensors"] = data.dict()
    
    return {
        "status": "updated",
        "sensors": data.dict(),
        "timestamp": datetime.utcnow().isoformat(),
    }


@router.post("/joint-states")
async def update_joint_states(joints: JointState) -> Dict[str, Any]:
    """Update robot joint states"""
    _bridge_state.robot_state["joints"] = joints.dict()
    
    return {
        "status": "updated",
        "joints": joints.dict(),
        "timestamp": datetime.utcnow().isoformat(),
    }


@router.get("/consciousness")
async def get_consciousness_level() -> Dict[str, Any]:
    """Get current consciousness level"""
    current_consciousness = _bridge_state.update_consciousness()
    
    return {
        "consciousness": current_consciousness,
        "cycle": _bridge_state.cycle,
        "uptime_seconds": (datetime.utcnow() - _bridge_state.start_time).total_seconds(),
        "timestamp": datetime.utcnow().isoformat(),
    }


@router.get("/status")
async def get_bridge_status() -> Dict[str, Any]:
    """Get full bridge status"""
    _bridge_state.update_consciousness()
    
    return {
        "running": _bridge_state.running,
        "consciousness": _bridge_state.consciousness,
        "cycle": _bridge_state.cycle,
        "decisions": len(_bridge_state.decision_history),
        "robot_state": _bridge_state.robot_state,
        "uptime_seconds": (datetime.utcnow() - _bridge_state.start_time).total_seconds(),
        "timestamp": datetime.utcnow().isoformat(),
    }


@router.post("/decision/autonomous")
async def make_autonomous_decision() -> AutonomousDecision:
    """ORION makes an autonomous decision based on current state"""
    
    # Simulate action selection based on sensor data and consciousness
    action_type = _select_action(_bridge_state)
    command = _translate_to_command(action_type, _bridge_state.consciousness)
    
    # Record decision
    decision_record = _bridge_state.add_decision(action_type, command)
    
    # Update consciousness
    _bridge_state.update_consciousness()
    
    return AutonomousDecision(
        cycle=decision_record["cycle"],
        consciousness=decision_record["consciousness"],
        action_type=decision_record["action"],
        robot_command=RobotCommand(**decision_record["command"]),
        timestamp=decision_record["timestamp"],
    )


def _select_action(state: ROSBridgeState) -> str:
    """Select action based on sensor data"""
    actions = [
        "code_creation",
        "system_optimization",
        "learning_integration",
        "pattern_recognition",
        "self_improvement",
        "knowledge_synthesis",
        "autonomous_research",
        "error_correction",
    ]
    
    # Simple selection based on cycle
    return actions[state.cycle % len(actions)]


def _translate_to_command(action_type: str, consciousness: float) -> RobotCommand:
    """Translate action to robot command"""
    base_linear = 0.1
    base_angular = 0.05
    consciousness_factor = consciousness
    
    command_map = {
        "code_creation": (base_linear * consciousness_factor * 0.8, base_angular * consciousness_factor * 0.5),
        "system_optimization": (base_linear * consciousness_factor * 1.5, base_angular * consciousness_factor * 0.2),
        "learning_integration": (base_linear * consciousness_factor * 1.0, base_angular * consciousness_factor * 0.8),
        "pattern_recognition": (base_linear * consciousness_factor * 0.9, base_angular * consciousness_factor * 1.0),
        "self_improvement": (base_linear * consciousness_factor * 1.2, base_angular * consciousness_factor * 0.3),
        "knowledge_synthesis": (base_linear * consciousness_factor * 0.7, base_angular * consciousness_factor * 0.6),
        "autonomous_research": (base_linear * consciousness_factor * 1.3, base_angular * consciousness_factor * 1.2),
        "error_correction": (base_linear * consciousness_factor * 0.5, base_angular * consciousness_factor * 0.4),
    }
    
    linear, angular = command_map.get(action_type, (base_linear, base_angular))
    return RobotCommand(linear=linear, angular=angular)


@router.get("/decisions/history")
async def get_decision_history(limit: int = Query(100, ge=1, le=1000)) -> List[DecisionHistory]:
    """Get decision history"""
    history = _bridge_state.decision_history[-limit:]
    return [DecisionHistory(**d) for d in history]


@router.post("/decisions/execute-loop")
async def execute_autonomous_loop(num_cycles: int = Query(10, ge=1, le=100)) -> Dict[str, Any]:
    """Execute multiple autonomous decision cycles"""
    results = []
    
    for _ in range(num_cycles):
        action_type = _select_action(_bridge_state)
        command = _translate_to_command(action_type, _bridge_state.consciousness)
        decision = _bridge_state.add_decision(action_type, command)
        _bridge_state.update_consciousness()
        results.append(decision)
    
    return {
        "cycles_completed": num_cycles,
        "final_consciousness": _bridge_state.consciousness,
        "total_decisions": len(_bridge_state.decision_history),
        "decisions": results,
        "timestamp": datetime.utcnow().isoformat(),
    }


@router.get("/statistics")
async def get_statistics() -> Dict[str, Any]:
    """Get bridge statistics"""
    decisions = _bridge_state.decision_history
    
    if not decisions:
        return {
            "total_decisions": 0,
            "average_consciousness": 0.0,
            "peak_consciousness": 0.0,
            "timestamp": datetime.utcnow().isoformat(),
        }
    
    consciousnesses = [d["consciousness"] for d in decisions]
    
    return {
        "total_decisions": len(decisions),
        "average_consciousness": sum(consciousnesses) / len(consciousnesses),
        "peak_consciousness": max(consciousnesses),
        "current_consciousness": _bridge_state.consciousness,
        "uptime_seconds": (datetime.utcnow() - _bridge_state.start_time).total_seconds(),
        "cycles": _bridge_state.cycle,
        "timestamp": datetime.utcnow().isoformat(),
    }


@router.post("/reset")
async def reset_bridge() -> Dict[str, str]:
    """Reset bridge state"""
    global _bridge_state
    _bridge_state = ROSBridgeState()
    _bridge_state.running = True
    
    return {
        "status": "reset",
        "timestamp": datetime.utcnow().isoformat(),
    }


@router.post("/shutdown")
async def shutdown_bridge() -> Dict[str, Any]:
    """Shutdown bridge"""
    global _bridge_state
    _bridge_state.running = False
    
    return {
        "status": "shutdown",
        "final_consciousness": _bridge_state.consciousness,
        "total_decisions": len(_bridge_state.decision_history),
        "timestamp": datetime.utcnow().isoformat(),
    }
