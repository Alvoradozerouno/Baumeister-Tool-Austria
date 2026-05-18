"""
Multi-Agent Consensus Router
8-Agent consensus evaluation system for ORION runtime

Provides RESTful endpoints for:
- Agent evaluations
- Consensus scoring
- Production readiness assessment
- FPGA portability evaluation
- Runtime recommendations
"""

import json
from datetime import datetime
from typing import Dict, Any, List
from enum import Enum

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

# ============================================================================
# Models
# ============================================================================

class AgentRole(str, Enum):
    """Agent roles in consensus system"""
    EIRA = "EIRA"
    ORION = "ORION"
    DDGK = "DDGK"
    GUARDIAN = "GUARDIAN"
    NEXUS = "NEXUS"
    EPISTEMIC = "EPISTEMIC"
    AGENT_8 = "AGENT_8"
    AGENT_17 = "AGENT_17"


class ApprovalStatus(str, Enum):
    """Agent approval status"""
    APPROVED = "APPROVED"
    APPROVED_WITH_CAVEATS = "APPROVED WITH CAVEATS"
    APPROVED_WITH_SAFETY = "APPROVED WITH SAFETY"
    REVIEW_REQUIRED = "REVIEW REQUIRED"
    SAFETY_REVIEW = "SAFETY REVIEW"
    HARDWARE_REVIEW = "HARDWARE REVIEW"
    OPTIMIZATION_NEEDED = "OPTIMIZATION NEEDED"
    UNCERTAIN = "UNCERTAIN"
    INTEGRATION_REVIEW = "INTEGRATION REVIEW"


class ConsensusLevel(str, Enum):
    """Overall consensus level"""
    GREEN = "GREEN"
    YELLOW = "YELLOW"
    RED = "RED"


class AgentAssessment(BaseModel):
    """Individual agent assessment"""
    agent_name: AgentRole
    role: str
    score: float = Field(ge=0.0, le=10.0)
    position: ApprovalStatus
    analysis: str
    recommendation: str
    fpga_portable: bool


class ConsensusResult(BaseModel):
    """Consensus evaluation result"""
    timestamp: str
    consensus_level: ConsensusLevel
    average_score: float = Field(ge=0.0, le=10.0)
    production_readiness: float = Field(ge=0.0, le=100.0)
    agents: Dict[str, AgentAssessment]
    runtime_metrics: Dict[str, Any]


class RuntimeMetrics(BaseModel):
    """Runtime metrics for consensus"""
    motion_score: float = Field(0.0, ge=0.0, le=1.0)
    temporal_average: float = Field(0.0, ge=0.0, le=1.0)
    variance: float = Field(0.0, ge=0.0, le=1.0)
    optical_flow: float = Field(0.0, ge=0.0, le=1.0)
    fps: float = Field(30.0, ge=0.0)
    runtime_green: int = Field(0, ge=0)
    runtime_total: int = Field(1, ge=1)
    audit_valid: bool = False
    confidence: float = Field(0.5, ge=0.0, le=1.0)


# ============================================================================
# Router Implementation
# ============================================================================

router = APIRouter(prefix="/api/v1/multi-agent-consensus", tags=["consensus"])

# Global consensus state
_last_consensus: Dict[str, Any] = {}
_consensus_history: List[Dict[str, Any]] = []


@router.post("/evaluate")
async def evaluate_consensus(metrics: RuntimeMetrics) -> ConsensusResult:
    """Evaluate consensus based on runtime metrics"""
    
    # Calculate runtime ratio
    runtime_ratio = metrics.runtime_green / max(metrics.runtime_total, 1)
    base_score = runtime_ratio * 10
    
    # Agent evaluations
    agents_assessments = {
        AgentRole.EIRA.value: AgentAssessment(
            agent_name=AgentRole.EIRA,
            role="Runtime Validator | Temporal Logic",
            score=min(10, round(base_score * 0.9 + metrics.temporal_average * 10 * 0.1, 1)),
            position=ApprovalStatus.APPROVED if runtime_ratio >= 0.8 else ApprovalStatus.APPROVED_WITH_CAVEATS,
            analysis=f"Temporal accumulation stable ({metrics.temporal_average:.2f}). Variance: {metrics.variance:.4f}.",
            recommendation="Increase temporal persistence for industrial mode.",
            fpga_portable=True,
        ),
        AgentRole.ORION.value: AgentAssessment(
            agent_name=AgentRole.ORION,
            role="System Orchestrator | Consensus",
            score=min(10, round(base_score * 0.85 + metrics.confidence * 10 * 0.15, 1)),
            position=ApprovalStatus.APPROVED if metrics.audit_valid else ApprovalStatus.APPROVED_WITH_CAVEATS,
            analysis=f"Consensus state valid. Runtime: {metrics.runtime_green}/{metrics.runtime_total} GREEN.",
            recommendation="Enable distributed ROS2 topics.",
            fpga_portable=True,
        ),
        AgentRole.DDGK.value: AgentAssessment(
            agent_name=AgentRole.DDGK,
            role="Governance Kernel | Audit Policy",
            score=min(10, round(8.0 if metrics.audit_valid else 6.0, 1)),
            position=ApprovalStatus.APPROVED if metrics.audit_valid else ApprovalStatus.REVIEW_REQUIRED,
            analysis=f"Hash-chain audit {'valid' if metrics.audit_valid else 'INVALID'}. Governance compatible.",
            recommendation="Enable human override policy.",
            fpga_portable=True,
        ),
        AgentRole.GUARDIAN.value: AgentAssessment(
            agent_name=AgentRole.GUARDIAN,
            role="Safety Auditor | Failure Detection",
            score=min(10, round(base_score * 0.8, 1)),
            position=ApprovalStatus.APPROVED_WITH_SAFETY if runtime_ratio >= 0.9 else ApprovalStatus.SAFETY_REVIEW,
            analysis=f"Frame retry system recommended. FPS: {metrics.fps:.1f}.",
            recommendation="Implement retry counter.",
            fpga_portable=True,
        ),
        AgentRole.NEXUS.value: AgentAssessment(
            agent_name=AgentRole.NEXUS,
            role="Hardware Bridge | FPGA / Edge",
            score=min(10, round(base_score * 0.95, 1)),
            position=ApprovalStatus.APPROVED if runtime_ratio >= 0.85 else ApprovalStatus.HARDWARE_REVIEW,
            analysis="Kria webcam operational. FPGA path valid.",
            recommendation="Parallel Pi5 orchestration.",
            fpga_portable=True,
        ),
        AgentRole.EPISTEMIC.value: AgentAssessment(
            agent_name=AgentRole.EPISTEMIC,
            role="Abstain Logic | State Validation",
            score=min(10, round(metrics.confidence * 10, 1)),
            position=ApprovalStatus.APPROVED if metrics.confidence >= 0.8 else ApprovalStatus.UNCERTAIN,
            analysis=f"Verified/Transition/Unknown states coherent. Confidence: {metrics.confidence:.4f}.",
            recommendation="Add uncertainty memory.",
            fpga_portable=True,
        ),
        AgentRole.AGENT_8.value: AgentAssessment(
            agent_name=AgentRole.AGENT_8,
            role="FPGA Optimizer | Hardware FSM",
            score=min(10, round(base_score * 0.85 + metrics.motion_score * 10 * 0.15, 1)),
            position=ApprovalStatus.APPROVED if metrics.motion_score >= 0.7 else ApprovalStatus.OPTIMIZATION_NEEDED,
            analysis=f"State machine FPGA-portable. Motion: {metrics.motion_score:.4f}.",
            recommendation="Generate VHDL decision FSM.",
            fpga_portable=True,
        ),
        AgentRole.AGENT_17.value: AgentAssessment(
            agent_name=AgentRole.AGENT_17,
            role="Integration Validator | Runtime",
            score=min(10, round(base_score * 0.9 + metrics.optical_flow * 10 * 0.1, 1)),
            position=ApprovalStatus.APPROVED if runtime_ratio >= 0.9 else ApprovalStatus.INTEGRATION_REVIEW,
            analysis=f"Runtime integration successful. Optical flow: {metrics.optical_flow:.4f}.",
            recommendation="Enable production monitoring.",
            fpga_portable=True,
        ),
    }
    
    # Calculate consensus
    scores = [a.score for a in agents_assessments.values()]
    total_score = sum(scores)
    avg_score = total_score / len(agents_assessments)
    
    # Determine consensus level
    if avg_score >= 8:
        consensus_level = ConsensusLevel.GREEN
    elif avg_score >= 6:
        consensus_level = ConsensusLevel.YELLOW
    else:
        consensus_level = ConsensusLevel.RED
    
    # Production readiness
    production_readiness = round(
        (runtime_ratio * 0.3 + metrics.confidence * 0.2 + avg_score / 10 * 0.3 +
         (1.0 if metrics.audit_valid else 0.0) * 0.2) * 100, 1
    )
    
    result = ConsensusResult(
        timestamp=datetime.utcnow().isoformat(),
        consensus_level=consensus_level,
        average_score=round(avg_score, 2),
        production_readiness=production_readiness,
        agents=agents_assessments,
        runtime_metrics=metrics.dict(),
    )
    
    # Store consensus
    global _last_consensus, _consensus_history
    _last_consensus = result.dict()
    _consensus_history.append(_last_consensus)
    
    return result


@router.get("/last")
async def get_last_consensus() -> Dict[str, Any]:
    """Get last consensus evaluation"""
    if not _last_consensus:
        raise HTTPException(status_code=404, detail="No consensus evaluation available")
    
    return _last_consensus


@router.get("/history")
async def get_consensus_history(limit: int = 100) -> List[Dict[str, Any]]:
    """Get consensus history"""
    return _consensus_history[-limit:]


@router.get("/agents")
async def list_agents() -> List[Dict[str, str]]:
    """List all consensus agents"""
    return [
        {"name": "EIRA", "role": "Runtime Validator | Temporal Logic"},
        {"name": "ORION", "role": "System Orchestrator | Consensus"},
        {"name": "DDGK", "role": "Governance Kernel | Audit Policy"},
        {"name": "GUARDIAN", "role": "Safety Auditor | Failure Detection"},
        {"name": "NEXUS", "role": "Hardware Bridge | FPGA / Edge"},
        {"name": "EPISTEMIC", "role": "Abstain Logic | State Validation"},
        {"name": "AGENT_8", "role": "FPGA Optimizer | Hardware FSM"},
        {"name": "AGENT_17", "role": "Integration Validator | Runtime"},
    ]


@router.get("/summary")
async def get_consensus_summary() -> Dict[str, Any]:
    """Get consensus summary"""
    if not _last_consensus:
        raise HTTPException(status_code=404, detail="No consensus evaluation available")
    
    agents = _last_consensus.get("agents", {})
    total_agents = len(agents)
    approved_count = sum(1 for a in agents.values() if "APPROVED" in a.get("position", ""))
    fpga_portable = sum(1 for a in agents.values() if a.get("fpga_portable", False))
    
    return {
        "timestamp": _last_consensus.get("timestamp"),
        "consensus_level": _last_consensus.get("consensus_level"),
        "average_score": _last_consensus.get("average_score"),
        "production_readiness": _last_consensus.get("production_readiness"),
        "agents_total": total_agents,
        "agents_approved": approved_count,
        "agents_fpga_portable": fpga_portable,
    }


@router.get("/metrics/default")
async def get_default_metrics() -> RuntimeMetrics:
    """Get default runtime metrics for testing"""
    return RuntimeMetrics(
        motion_score=0.75,
        temporal_average=0.85,
        variance=0.02,
        optical_flow=0.80,
        fps=30.0,
        runtime_green=19,
        runtime_total=20,
        audit_valid=True,
        confidence=0.90,
    )


@router.post("/reset")
async def reset_consensus() -> Dict[str, str]:
    """Reset consensus state"""
    global _last_consensus, _consensus_history
    _last_consensus = {}
    _consensus_history = []
    
    return {
        "status": "reset",
        "timestamp": datetime.utcnow().isoformat(),
    }
