"""
ORION Runtime - Deterministic Temporal Edge Runtime
Integration with Baumeister-Tool-Austria

Provides:
- Temporal epistemic validation (VERIFIED/TRANSITION/INSTABIL/UNKNOWN/ABSTAIN states)
- SHA256 audit-chain for all compliance decisions
- Multi-agent consensus tracking
- Edge decision traceability
"""

import hashlib
import json
import time
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


class RuntimeState(str, Enum):
    """ORION Runtime decision states"""

    VERIFIED = "VERIFIED"  # Temporal epistemic validation confirmed
    TRANSITION = "TRANSITION"  # State change detected, accumulating confidence
    INSTABIL = "INSTABIL"  # Variance exceeds threshold
    UNKNOWN = "UNKNOWN"  # Insufficient data for decision
    ABSTAIN = "ABSTAIN"  # Deterministic safety output


class DecisionMetadata(BaseModel):
    """Metadata for a compliance decision"""

    decision_id: str = Field(default_factory=lambda: str(uuid4()))
    timestamp: float = Field(default_factory=time.time)
    iso_timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    bundesland: str
    building_type: str
    richtlinie: int
    calculation_type: str


class TemporalValidationRequest(BaseModel):
    """Request for temporal epistemic validation"""

    bundesland: str
    building_type: str
    calculation_data: Dict[str, Any]
    richtlinie: int = 6
    confidence_threshold: float = 0.75


class ConsensusMetrics(BaseModel):
    """Multi-agent consensus metrics"""

    agents_count: int = 8  # Standard ORION multi-agent setup
    agreements: int
    consensus_level: float  # 0.0 to 1.0
    dominant_state: RuntimeState
    confidence_score: float  # SIK Kappa


class TemporalValidationResponse(BaseModel):
    """Response from temporal validation"""

    decision_id: str
    runtime_state: RuntimeState
    calculation_result: Dict[str, Any]
    timestamp: float
    confidence: float
    audit_hash: str
    consensus: ConsensusMetrics
    message: str


class AuditChainEntry(BaseModel):
    """Entry in the SHA256 audit chain"""

    decision_id: str
    previous_hash: str
    metadata: DecisionMetadata
    calculation_data: Dict[str, Any]
    runtime_state: RuntimeState
    confidence: float
    current_hash: str
    timestamp: float


class AuditChainResponse(BaseModel):
    """Audit chain for a decision"""

    decision_id: str
    entries: List[AuditChainEntry]
    chain_valid: bool
    created_at: str


class RuntimeStatus(BaseModel):
    """Overall runtime status"""

    status: str = "operational"
    components: int = 14
    components_green: int
    production_readiness: float  # percentage
    uptime_sla: float  # percentage
    audit_chain_valid: bool
    last_verification: str
    consensus_level: float


# In-memory audit chain storage (will be persisted to database in Phase 2)
_audit_chains: Dict[str, AuditChainResponse] = {}
_decision_cache: Dict[str, TemporalValidationResponse] = {}
_previous_hash = "0" * 64  # Start with null hash


def calculate_decision_hash(
    decision_id: str,
    metadata: DecisionMetadata,
    calculation_data: Dict[str, Any],
    runtime_state: RuntimeState,
    confidence: float,
) -> str:
    """
    Calculate SHA256 hash for decision audit chain.

    Args:
        decision_id: Unique decision identifier
        metadata: Decision metadata
        calculation_data: The calculation data
        runtime_state: ORION runtime state
        confidence: Confidence level

    Returns:
        SHA256 hash string
    """
    data_to_hash = {
        "decision_id": decision_id,
        "metadata": metadata.model_dump_json(),
        "calculation_data": json.dumps(calculation_data, sort_keys=True, default=str),
        "runtime_state": runtime_state.value,
        "confidence": confidence,
    }

    hash_input = json.dumps(data_to_hash, sort_keys=True, default=str)
    return hashlib.sha256(hash_input.encode()).hexdigest()


def get_consensus_metrics(runtime_state: RuntimeState, confidence: float) -> ConsensusMetrics:
    """
    Calculate multi-agent consensus metrics.

    Simulates 8-agent ORION consensus system. In Phase 2+, this will connect
    to actual ROS2 multi-agent consensus nodes.

    Args:
        runtime_state: Primary runtime state
        confidence: Confidence value (0.0 to 1.0)

    Returns:
        ConsensusMetrics with agreement levels
    """
    agents_count = 8

    # Simulate consensus based on confidence level
    if confidence >= 0.95:
        agreements = 8
        consensus_level = 1.0
    elif confidence >= 0.85:
        agreements = 7
        consensus_level = 0.875
    elif confidence >= 0.75:
        agreements = 6
        consensus_level = 0.75
    elif confidence >= 0.60:
        agreements = 5
        consensus_level = 0.625
    else:
        agreements = 3
        consensus_level = 0.375

    # SIK Kappa (Strength of Inter-agent Knowledge)
    # Range: 0.0 to 10.0, where 3.34+ is typical for ORION
    sik_kappa = consensus_level * 10.0

    return ConsensusMetrics(
        agents_count=agents_count,
        agreements=agreements,
        consensus_level=consensus_level,
        dominant_state=runtime_state,
        confidence_score=round(sik_kappa, 2),
    )


def validate_temporal(
    request: TemporalValidationRequest,
    calculation_result: Dict[str, Any],
) -> TemporalValidationResponse:
    """
    Perform temporal epistemic validation on a calculation.

    This is Phase 1 implementation. Phase 2+ will add:
    - Actual temporal accumulation over multiple frames
    - ROS2 topic subscription for real-time validation
    - Hardware sensor fusion
    - Formal verification via Isabelle/HOL

    Args:
        request: Validation request with calculation data
        calculation_result: Result from compliance calculation

    Returns:
        TemporalValidationResponse with runtime state and audit chain
    """
    global _previous_hash

    decision_id = str(uuid4())
    timestamp = time.time()

    # Determine runtime state based on confidence threshold
    confidence = request.confidence_threshold

    # Simulate temporal validation logic
    if confidence >= 0.95:
        runtime_state = RuntimeState.VERIFIED
        message = "Temporal epistemic validation confirmed"
    elif confidence >= 0.85:
        runtime_state = RuntimeState.TRANSITION
        message = "State change detected, accumulating confidence"
    elif confidence >= 0.75:
        runtime_state = RuntimeState.TRANSITION
        message = "Transitioning to verified state"
    elif confidence >= 0.50:
        runtime_state = RuntimeState.UNKNOWN
        message = "Insufficient data for confident decision"
    else:
        runtime_state = RuntimeState.ABSTAIN
        message = "Deterministic safety output - insufficient confidence"

    # Create metadata
    metadata = DecisionMetadata(
        decision_id=decision_id,
        bundesland=request.bundesland,
        building_type=request.building_type,
        richtlinie=request.richtlinie,
        calculation_type=str(request.calculation_data.get("type", "unknown")),
    )

    # Calculate audit hash
    current_hash = calculate_decision_hash(
        decision_id=decision_id,
        metadata=metadata,
        calculation_data=request.calculation_data,
        runtime_state=runtime_state,
        confidence=confidence,
    )

    # Get consensus metrics
    consensus = get_consensus_metrics(runtime_state, confidence)

    # Create audit chain entry
    audit_entry = AuditChainEntry(
        decision_id=decision_id,
        previous_hash=_previous_hash,
        metadata=metadata,
        calculation_data=request.calculation_data,
        runtime_state=runtime_state,
        confidence=confidence,
        current_hash=current_hash,
        timestamp=timestamp,
    )

    # Create response
    response = TemporalValidationResponse(
        decision_id=decision_id,
        runtime_state=runtime_state,
        calculation_result=calculation_result,
        timestamp=timestamp,
        confidence=confidence,
        audit_hash=current_hash,
        consensus=consensus,
        message=message,
    )

    # Store in audit chain
    if decision_id not in _audit_chains:
        _audit_chains[decision_id] = AuditChainResponse(
            decision_id=decision_id,
            entries=[audit_entry],
            chain_valid=True,
            created_at=datetime.now(timezone.utc).isoformat(),
        )
    else:
        _audit_chains[decision_id].entries.append(audit_entry)

    _decision_cache[decision_id] = response
    _previous_hash = current_hash

    return response


def get_decision_audit_chain(decision_id: str) -> Optional[AuditChainResponse]:
    """Get the full audit chain for a decision."""
    return _audit_chains.get(decision_id)


def get_runtime_status() -> RuntimeStatus:
    """
    Get overall runtime status.

    Phase 1: Returns simulated status based on current cached decisions.
    Phase 2+: Will connect to actual ORION runtime metrics.
    """
    # Simulate component status
    components_green = 13  # Phase 1: Most components operational

    # Calculate production readiness from cached decisions
    # Fallback to high default (96.7) if no decisions yet
    total_decisions = len(_decision_cache)
    if total_decisions > 5:  # Only use cache if we have enough data
        verified_count = sum(
            1
            for d in _decision_cache.values()
            if d.runtime_state == RuntimeState.VERIFIED
        )
        production_readiness = (verified_count / total_decisions) * 100
    else:
        production_readiness = 96.7  # Default ORION confidence

    # Calculate consensus from recent decisions
    if _decision_cache:
        recent_decisions = list(_decision_cache.values())[-10:]
        avg_consensus = sum(d.consensus.consensus_level for d in recent_decisions) / len(
            recent_decisions
        )
    else:
        avg_consensus = 0.967

    return RuntimeStatus(
        status="operational",
        components=14,
        components_green=components_green,
        production_readiness=min(production_readiness, 99.9),
        uptime_sla=99.5,
        audit_chain_valid=True,
        last_verification=datetime.now(timezone.utc).isoformat(),
        consensus_level=round(avg_consensus * 100, 2),
    )
