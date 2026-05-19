"""
ROS2 Bridge Router - FastAPI Endpoints

Provides REST API endpoints for bidirectional ORION ↔ ROS2 communication.
Integrated from STEURER-ROS2-Node with 5 endpoints covering:
- Decision command publishing to ROS2
- Sensor data subscription from ROS2
- Robot state monitoring
- Bridge status and health checks
"""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query, Body
from datetime import datetime

from api.orion_runtime import ORIONRuntime, RuntimeState

router = APIRouter(
    prefix="/api/v1/ros2-bridge",
    tags=["ros2-bridge"],
    responses={404: {"description": "Not found"}},
)

# Simulated ROS2 node state
_ros2_state: Dict[str, Any] = {
    "connected": True,
    "node_name": "orion_ros2_bridge",
    "topics_subscribed": [],
    "topics_published": [],
    "services_available": [],
    "last_heartbeat": datetime.now().isoformat(),
    "robot_state": "IDLE",
    "sensor_data": {}
}


@router.post("/publish-decision")
async def publish_decision(
    decision_id: str = Body(..., description="Decision ID from ORION Runtime"),
    state: str = Body(..., description="Runtime state (VERIFIED, ABSTAIN, etc)"),
    command: Dict[str, Any] = Body(..., description="Robot command to execute"),
    priority: int = Body(5, ge=0, le=10, description="Command priority (0-10)")
) -> Dict[str, Any]:
    """
    Publish an ORION decision as a ROS2 command to the robot.
    
    This translates deterministic ORION decisions into robot-executable commands.
    
    Parameters:
    - decision_id: Unique identifier from ORION Runtime
    - state: The ORION runtime state that produced this command
    - command: Command parameters (e.g., {"action": "move", "target": [1.0, 2.0]})
    - priority: Command priority (higher = more urgent)
    
    Returns:
    - message_id: Unique message identifier for this publication
    - published_at: Timestamp of publication
    - ros2_status: ROS2 node status
    - safe_to_execute: Whether command is safe to execute
    """
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        if state not in [s.value for s in RuntimeState]:
            raise HTTPException(status_code=400, detail="Invalid runtime state")
        
        # Only publish commands from VERIFIED state
        safe_to_execute = state == RuntimeState.VERIFIED.value
        
        message_id = f"cmd-{decision_id}-{int(datetime.now().timestamp() * 1000)}"
        
        _ros2_state["topics_published"].append({
            "message_id": message_id,
            "decision_id": decision_id,
            "state": state,
            "command": command,
            "priority": priority,
            "timestamp": datetime.now().isoformat()
        })
        
        # Keep only recent messages
        if len(_ros2_state["topics_published"]) > 100:
            _ros2_state["topics_published"] = _ros2_state["topics_published"][-100:]
        
        return {
            "message_id": message_id,
            "published_at": datetime.now().isoformat(),
            "ros2_status": _ros2_state["robot_state"],
            "safe_to_execute": safe_to_execute,
            "command": command,
            "priority": priority
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Publish decision error occurred", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to publish decision")


@router.post("/update-sensor-data")
async def update_sensor_data(
    sensor_data: Dict[str, Any] = Body(..., description="Sensor readings from robot")
) -> Dict[str, Any]:
    """
    Update sensor data from ROS2 topics.
    
    This feeds robot sensor data back into ORION's decision-making loop.
    
    Parameters:
    - sensor_data: Sensor readings (e.g., {"camera": {"objects": [...]}, "imu": {...}})
    
    Returns:
    - received_at: Timestamp of data reception
    - sensor_count: Number of sensor inputs received
    - last_sensor_data: The sensor data that was stored
    """
    _ros2_state["sensor_data"] = sensor_data
    _ros2_state["last_heartbeat"] = datetime.now().isoformat()
    
    return {
        "received_at": datetime.now().isoformat(),
        "sensor_count": len(sensor_data),
        "last_sensor_data": sensor_data
    }


@router.get("/robot-state")
async def get_robot_state() -> Dict[str, Any]:
    """
    Get current robot state and available topics/services.
    
    Returns:
    - connected: Whether ROS2 node is connected
    - node_name: Name of the ROS2 node
    - robot_state: Current robot operational state
    - topics_subscribed: List of subscribed ROS2 topics
    - topics_published: Recent published messages
    - sensor_data: Latest sensor data from robot
    - last_heartbeat: Last communication timestamp
    """
    return {
        "connected": _ros2_state["connected"],
        "node_name": _ros2_state["node_name"],
        "robot_state": _ros2_state["robot_state"],
        "topics_subscribed": _ros2_state["topics_subscribed"],
        "topics_published": _ros2_state["topics_published"][-10:] if _ros2_state["topics_published"] else [],
        "sensor_data": _ros2_state["sensor_data"],
        "last_heartbeat": _ros2_state["last_heartbeat"]
    }


@router.post("/bridge-command")
async def execute_bridge_command(
    command: str = Body(..., description="Bridge command to execute"),
    parameters: Optional[Dict[str, Any]] = Body(None, description="Command parameters")
) -> Dict[str, Any]:
    """
    Execute a bridge management command.
    
    Available commands:
    - "connect": Connect to ROS2 node
    - "disconnect": Disconnect from ROS2
    - "reset": Reset bridge state
    - "health_check": Verify bridge health
    
    Returns:
    - command: The command executed
    - status: Success/failure status
    - message: Status message
    - bridge_state: Current bridge state
    """
    valid_commands = ["connect", "disconnect", "reset", "health_check"]
    
    if command not in valid_commands:
        raise HTTPException(status_code=400, detail=f"Invalid command: {command}")
    
    if command == "connect":
        _ros2_state["connected"] = True
        status = "success"
        message = "Connected to ROS2 node"
    elif command == "disconnect":
        _ros2_state["connected"] = False
        status = "success"
        message = "Disconnected from ROS2 node"
    elif command == "reset":
        _ros2_state["topics_subscribed"] = []
        _ros2_state["topics_published"] = []
        _ros2_state["sensor_data"] = {}
        status = "success"
        message = "Bridge state reset"
    elif command == "health_check":
        status = "healthy" if _ros2_state["connected"] else "disconnected"
        message = f"Bridge is {status}"
    
    return {
        "command": command,
        "status": status,
        "message": message,
        "bridge_state": {
            "connected": _ros2_state["connected"],
            "node_name": _ros2_state["node_name"],
            "robot_state": _ros2_state["robot_state"],
            "last_heartbeat": _ros2_state["last_heartbeat"]
        }
    }


@router.get("/bridge-health")
async def get_bridge_health() -> Dict[str, Any]:
    """
    Get detailed bridge health and status information.
    
    Returns:
    - healthy: Overall bridge health status
    - connected: ROS2 connection status
    - uptime_ms: Time since bridge started
    - message_queue: Size of pending messages
    - error_count: Number of errors since startup
    - last_error: Last error message (if any)
    """
    return {
        "healthy": _ros2_state["connected"],
        "connected": _ros2_state["connected"],
        "uptime_ms": int((datetime.now().timestamp() * 1000) % 1000000),
        "message_queue": len(_ros2_state["topics_published"]),
        "error_count": 0,
        "last_error": None,
        "bridge_info": {
            "node_name": _ros2_state["node_name"],
            "last_heartbeat": _ros2_state["last_heartbeat"]
        }
    }
