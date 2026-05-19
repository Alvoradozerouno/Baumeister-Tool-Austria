"""
Multi-Agent Consensus Router - FastAPI Endpoints

Provides REST API endpoints for the 8-agent consensus decision-making system.
Integrated from STEURER-ROS2-Node with 4 endpoints covering:
- Agent vote registration
- Consensus score calculation
- Agreement analysis
- Consensus state management
"""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query, Body
from datetime import datetime

from api.orion_runtime import ORIONRuntime, HardwareTarget

router = APIRouter(
    prefix="/api/v1/multi-agent-consensus",
    tags=["multi-agent-consensus"],
    responses={404: {"description": "Not found"}},
)

# Global consensus instance
_consensus_runtime: Optional[ORIONRuntime] = None

def get_consensus_runtime() -> ORIONRuntime:
    """Get or create consensus runtime instance."""
    global _consensus_runtime
    if _consensus_runtime is None:
        _consensus_runtime = ORIONRuntime(hardware_target=HardwareTarget.LAPTOP_CPU)
    return _consensus_runtime


@router.post("/register-agent-vote")
async def register_agent_vote(
    agent_id: str = Body(..., description="Unique agent identifier"),
    confidence: float = Body(..., ge=0.0, le=1.0, description="Agent's decision confidence"),
    reasoning: Optional[str] = Body(None, description="Agent's reasoning for vote"),
    metadata: Optional[Dict[str, Any]] = Body(None, description="Additional agent metadata")
) -> Dict[str, Any]:
    """
    Register a vote from an autonomous agent in the consensus pool.
    
    Parameters:
    - agent_id: Unique identifier for the agent (e.g., "agent_1", "agent_ml_v2")
    - confidence: Confidence score for this agent's decision (0-1)
    - reasoning: Optional explanation of the agent's decision
    - metadata: Optional metadata about the agent or decision
    
    Returns:
    - agent_id: The agent that voted
    - vote_count: Number of votes from this agent
    - consensus_score: Current consensus agreement ratio
    - agents_voting: Number of unique agents voting
    """
    runtime = get_consensus_runtime()
    
    runtime.consensus_engine.register_agent_vote(agent_id, confidence)
    
    consensus_score, agents_voting = runtime.consensus_engine.get_consensus_score()
    agent_vote_count = len(runtime.consensus_engine.votes.get(agent_id, []))
    
    return {
        "agent_id": agent_id,
        "confidence": confidence,
        "vote_count": agent_vote_count,
        "consensus_score": consensus_score,
        "agents_voting": agents_voting,
        "metadata": metadata,
        "registered_at": datetime.now().isoformat()
    }


@router.get("/consensus-score")
async def get_consensus_score() -> Dict[str, Any]:
    """
    Calculate and return the current multi-agent consensus score.
    
    The consensus score measures agreement among all registered agents:
    - 1.0 = Perfect agreement (all agents have same confidence)
    - 0.5 = Medium agreement
    - 0.0 = No agreement (agents completely disagree)
    
    Returns:
    - consensus_score: Agreement ratio (0-1)
    - agents_count_expected: Expected number of agents
    - agents_voting: Number of agents that have voted
    - quality: Quality assessment (LOW, MEDIUM, HIGH)
    - interpretation: Human-readable interpretation
    """
    runtime = get_consensus_runtime()
    
    consensus_score, agents_voting = runtime.consensus_engine.get_consensus_score()
    
    # Quality assessment
    if agents_voting < 3:
        quality = "LOW"
    elif consensus_score < 0.70:
        quality = "MEDIUM"
    else:
        quality = "HIGH"
    
    # Human-readable interpretation
    if consensus_score >= 0.90:
        interpretation = "Agents strongly agree on decision"
    elif consensus_score >= 0.70:
        interpretation = "Agents moderately agree on decision"
    else:
        interpretation = "Agents have significant disagreement"
    
    return {
        "consensus_score": consensus_score,
        "agents_count_expected": runtime.consensus_engine.agent_count,
        "agents_voting": agents_voting,
        "quality": quality,
        "interpretation": interpretation,
        "calculated_at": datetime.now().isoformat()
    }


@router.get("/agent-votes")
async def get_agent_votes(
    detailed: bool = Query(False, description="Include detailed vote history")
) -> Dict[str, Any]:
    """
    Get information about all registered agent votes.
    
    Parameters:
    - detailed: If true, include full vote history for each agent
    
    Returns:
    - agents: List of agents and their vote statistics
    - total_votes: Total number of votes cast
    - consensus_strength: How strongly agents agree
    """
    runtime = get_consensus_runtime()
    
    agents_info = []
    for agent_id, votes in runtime.consensus_engine.votes.items():
        if votes:
            avg_confidence = sum(votes) / len(votes)
            agents_info.append({
                "agent_id": agent_id,
                "vote_count": len(votes),
                "average_confidence": avg_confidence,
                "min_confidence": min(votes),
                "max_confidence": max(votes),
                "votes": votes if detailed else None
            })
    
    total_votes = sum(len(votes) for votes in runtime.consensus_engine.votes.values())
    consensus_score, _ = runtime.consensus_engine.get_consensus_score()
    
    return {
        "agents": agents_info,
        "total_votes": total_votes,
        "consensus_strength": consensus_score,
        "agent_count": len(agents_info),
        "retrieved_at": datetime.now().isoformat()
    }


@router.post("/reset-consensus")
async def reset_consensus() -> Dict[str, Any]:
    """
    Reset the consensus engine for a new decision cycle.
    
    This clears all agent votes and prepares for a new consensus round.
    
    Returns:
    - message: Confirmation message
    - previous_agent_count: Number of agents in previous consensus
    - previous_total_votes: Total votes in previous round
    - reset_at: Timestamp of reset
    """
    runtime = get_consensus_runtime()
    
    # Get stats before reset
    previous_agent_count = len(runtime.consensus_engine.votes)
    previous_total_votes = sum(len(votes) for votes in runtime.consensus_engine.votes.values())
    
    # Reset
    runtime.reset_consensus()
    
    return {
        "message": "Consensus engine reset successfully",
        "previous_agent_count": previous_agent_count,
        "previous_total_votes": previous_total_votes,
        "reset_at": datetime.now().isoformat(),
        "ready_for_new_round": True
    }


@router.post("/validate-agreement")
async def validate_agreement(
    minimum_threshold: float = Body(0.75, ge=0.0, le=1.0, description="Minimum consensus threshold"),
    minimum_agents: int = Body(3, ge=1, le=10, description="Minimum agents required for consensus")
) -> Dict[str, Any]:
    """
    Validate whether current consensus meets specified requirements.
    
    Parameters:
    - minimum_threshold: Minimum consensus score required (0-1)
    - minimum_agents: Minimum number of agents required
    
    Returns:
    - valid: Whether consensus meets requirements
    - current_consensus: Current consensus score
    - current_agents: Number of agents voting
    - meets_threshold: Whether consensus threshold is met
    - meets_agent_count: Whether agent count requirement is met
    - safe_to_proceed: Whether safe to proceed with decision
    """
    runtime = get_consensus_runtime()
    
    consensus_score, agents_voting = runtime.consensus_engine.get_consensus_score()
    
    meets_threshold = consensus_score >= minimum_threshold
    meets_agent_count = agents_voting >= minimum_agents
    
    valid = meets_threshold and meets_agent_count
    
    return {
        "valid": valid,
        "current_consensus": consensus_score,
        "current_agents": agents_voting,
        "meets_threshold": meets_threshold,
        "minimum_threshold": minimum_threshold,
        "meets_agent_count": meets_agent_count,
        "minimum_agents": minimum_agents,
        "safe_to_proceed": valid,
        "validated_at": datetime.now().isoformat()
    }
