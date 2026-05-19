"""
ORION Runtime Router - FastAPI Endpoints

Provides REST API endpoints for the deterministic temporal edge runtime decision system.
Integrated from STEURER-ROS2-Node with 6 endpoints covering:
- Decision processing
- System status monitoring
- Audit chain verification
- Consensus management
"""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query
from datetime import datetime

from api.orion_runtime import ORIONRuntime, HardwareTarget, RuntimeState

# Global runtime instance
_runtime_instance: Optional[ORIONRuntime] = None

router = APIRouter(
    prefix="/api/v1/orion-runtime",
    tags=["orion-runtime"],
    responses={404: {"description": "Not found"}},
)


def get_runtime() -> ORIONRuntime:
    """Get or create runtime instance."""
    global _runtime_instance
    if _runtime_instance is None:
        _runtime_instance = ORIONRuntime(hardware_target=HardwareTarget.LAPTOP_CPU)
    return _runtime_instance


@router.post("/process-decision")
async def process_decision(
    confidence: float = Query(..., ge=0.0, le=1.0, description="Input confidence score"),
    sensor_data: Optional[Dict[str, Any]] = Query(None, description="Sensor input data"),
    timeout_ms: int = Query(100, ge=10, le=1000, description="Decision processing timeout in ms")
) -> Dict[str, Any]:
    """
    Process a decision through the deterministic temporal epistemic pipeline.
    
    Returns:
    - decision_id: Unique identifier for this decision
    - state: Final runtime state (VERIFIED, ABSTAIN, UNCERTAIN, PROCESSING, FAILED)
    - confidence: Input confidence score
    - consensus_score: Multi-agent consensus agreement ratio (0-1)
    - temporal_valid: Whether temporal epistemic validation passed
    - safe_to_execute: Whether the decision is safe to execute
    - audit_hash: SHA256 hash of audit chain entry
    - processing_time_ms: Time to process decision
    - fpga_latency_ns: FPGA decision FSM latency in nanoseconds
    """
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        runtime = get_runtime()
        
        input_data = {
            "confidence": confidence,
            "sensor_data": sensor_data or {},
            "timestamp": datetime.now().isoformat()
        }
        
        result = runtime.process_decision(input_data, timeout_ms)
        
        # Ensure no error details are exposed
        if "error" in result:
            logger.warning("Decision processing returned error state")
            return {
                "decision_id": result.get("decision_id", "unknown"),
                "state": "FAILED",
                "safe_to_execute": False
            }
        
        return result
    except Exception as e:
        # Log error internally but don't expose details to client
        logger.error(f"Decision processing error occurred", exc_info=True)
        
        return {
            "decision_id": "error-unknown",
            "state": "FAILED",
            "safe_to_execute": False
        }


@router.get("/status")
async def get_status() -> Dict[str, Any]:
    """
    Get comprehensive system status.
    
    Returns:
    - version: Runtime version
    - state: Current runtime state
    - hardware_target: Target hardware platform
    - uptime_seconds: System uptime
    - decision_count: Total decisions processed
    - verified_count: Decisions with VERIFIED state
    - abstain_count: Decisions with ABSTAIN state
    - failed_count: Failed decisions
    - audit_chain_valid: Audit chain integrity status
    - audit_chain_entries: Number of entries in audit chain
    - hardware_status: Real-time hardware metrics
    """
    runtime = get_runtime()
    return runtime.get_system_status()


@router.get("/verify-audit-chain")
async def verify_audit_chain() -> Dict[str, Any]:
    """
    Verify the integrity of the SHA256 audit chain.
    
    Returns:
    - valid: Whether the entire chain is valid
    - message: Verification status message
    - entry_count: Number of entries verified
    - last_hash: Last hash in the chain
    """
    runtime = get_runtime()
    is_valid, message = runtime.audit_chain.verify_chain()
    
    return {
        "valid": is_valid,
        "message": message,
        "entry_count": len(runtime.audit_chain.entries),
        "last_hash": runtime.audit_chain.last_hash
    }


@router.get("/audit-chain/entries")
async def get_audit_chain_entries(
    limit: int = Query(100, ge=1, le=1000, description="Maximum entries to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination")
) -> Dict[str, Any]:
    """
    Get entries from the audit chain with pagination.
    
    Returns:
    - entries: List of audit chain entries
    - total: Total number of entries
    - limit: Limit used
    - offset: Offset used
    """
    runtime = get_runtime()
    
    entries = runtime.audit_chain.entries[offset:offset + limit]
    
    return {
        "entries": [
            {
                "timestamp": e.timestamp,
                "component": e.component,
                "event_type": e.event_type,
                "state": e.state,
                "hash_id": e.hash_id,
                "prev_hash": e.prev_hash
            }
            for e in entries
        ],
        "total": len(runtime.audit_chain.entries),
        "limit": limit,
        "offset": offset
    }


@router.post("/reset-consensus")
async def reset_consensus() -> Dict[str, str]:
    """
    Reset the multi-agent consensus engine for the next decision cycle.
    
    Returns:
    - message: Confirmation message
    """
    runtime = get_runtime()
    runtime.reset_consensus()
    
    return {"message": "Consensus engine reset successfully"}


@router.get("/consensus-status")
async def get_consensus_status() -> Dict[str, Any]:
    """
    Get current consensus engine status.
    
    Returns:
    - agent_count: Expected number of agents
    - agents_voted: Number of agents that have voted
    - consensus_score: Current consensus agreement ratio (0-1)
    - votes_per_agent: Vote counts per agent
    """
    runtime = get_runtime()
    
    consensus_score, agent_count = runtime.consensus_engine.get_consensus_score()
    votes_per_agent = {agent_id: len(votes) for agent_id, votes in runtime.consensus_engine.votes.items()}
    
    return {
        "agent_count": runtime.consensus_engine.agent_count,
        "agents_voted": agent_count,
        "consensus_score": consensus_score,
        "votes_per_agent": votes_per_agent
    }
