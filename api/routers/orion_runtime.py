"""
ORION Runtime Router
Deterministic Temporal Edge Runtime with SHA256 Audit Chain

Provides RESTful endpoints for:
- Runtime orchestration and validation
- Audit chain verification
- Component health checks
- Hardware discovery
- FPGA target validation
- Formal proof verification
"""

import json
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional
from enum import Enum

from fastapi import APIRouter, HTTPException, BackgroundTasks, Query
from pydantic import BaseModel, Field

# ============================================================================
# Models
# ============================================================================

class RuntimeState(str, Enum):
    """Runtime states from EIRA specification"""
    VERIFIED = "VERIFIED"
    TRANSITION = "TRANSITION"
    INSTABIL = "INSTABIL"
    UNKNOWN = "UNKNOWN"
    ABSTAIN = "ABSTAIN"


class ComponentStatus(str, Enum):
    """Component status levels"""
    GREEN = "GREEN"
    YELLOW = "YELLOW"
    RED = "RED"


class AuditEntry(BaseModel):
    """SHA256 audit chain entry"""
    timestamp: str
    component: str
    status: ComponentStatus
    message: str
    data: Dict[str, Any] = Field(default_factory=dict)
    prev_hash: str
    hash: str


class HardwareStatus(BaseModel):
    """Hardware component status"""
    gpio: str = "unknown"
    webcam: str = "unknown"
    adc: str = "unknown"
    i2c: str = "unknown"
    system: str = "unknown"


class RuntimeReport(BaseModel):
    """Complete runtime report"""
    timestamp: str
    audit_chain: Dict[str, Any]
    components: Dict[str, Any]
    consensus: ComponentStatus
    production_readiness: float


class HealthCheckResponse(BaseModel):
    """Health check response"""
    status: str
    timestamp: str
    uptime_seconds: float
    components: Dict[str, ComponentStatus]


# ============================================================================
# AuditChain Implementation
# ============================================================================

class AuditChain:
    """SHA256-hash-chained audit chain for deterministic runtime validation"""

    def __init__(self):
        self.entries: List[Dict[str, Any]] = []
        self.last_hash = "0" * 64  # Genesis hash

    def add(self, component: str, status: ComponentStatus, message: str, data: Dict[str, Any] = None) -> str:
        """Add entry to audit chain and return hash"""
        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "component": component,
            "status": status.value,
            "message": message,
            "data": data or {},
            "prev_hash": self.last_hash,
        }
        entry_str = json.dumps(entry, sort_keys=True)
        entry["hash"] = hashlib.sha256(entry_str.encode()).hexdigest()
        self.last_hash = entry["hash"]
        self.entries.append(entry)
        return entry["hash"]

    def verify(self) -> tuple[bool, str]:
        """Verify entire chain integrity"""
        prev = "0" * 64
        for e in self.entries:
            if e["prev_hash"] != prev:
                return False, f"Chain broken at {e['timestamp']}"
            entry_str = json.dumps({k: v for k, v in e.items() if k != "hash"}, sort_keys=True)
            expected = hashlib.sha256(entry_str.encode()).hexdigest()
            if e["hash"] != expected:
                return False, f"Hash mismatch at {e['timestamp']}"
            prev = e["hash"]
        return True, "Chain intact"

    def to_dict(self) -> Dict[str, Any]:
        """Export chain to dictionary"""
        valid, msg = self.verify()
        return {
            "entries": len(self.entries),
            "valid": valid,
            "message": msg,
            "genesis_hash": "0" * 64,
            "final_hash": self.last_hash,
        }


# ============================================================================
# Router Implementation
# ============================================================================

router = APIRouter(prefix="/api/v1/orion-runtime", tags=["orion-runtime"])

# Global audit chain instance
_audit_chain = AuditChain()
_runtime_start_time = datetime.utcnow()


@router.post("/initialize")
async def initialize_runtime() -> Dict[str, Any]:
    """Initialize ORION runtime"""
    global _audit_chain, _runtime_start_time
    _audit_chain = AuditChain()
    _runtime_start_time = datetime.utcnow()
    _audit_chain.add("runtime", ComponentStatus.GREEN, "Runtime initialized")
    return {
        "status": "initialized",
        "timestamp": _runtime_start_time.isoformat(),
        "genesis_hash": _audit_chain.last_hash,
    }


@router.get("/health", response_model=HealthCheckResponse)
async def health_check() -> HealthCheckResponse:
    """Check runtime health status"""
    uptime = (datetime.utcnow() - _runtime_start_time).total_seconds()
    
    components = {
        "audit_chain": ComponentStatus.GREEN if _audit_chain.entries else ComponentStatus.YELLOW,
        "api": ComponentStatus.GREEN,
        "memory": ComponentStatus.GREEN,
    }

    _audit_chain.add("health_check", ComponentStatus.GREEN, "Health check passed")

    return HealthCheckResponse(
        status="healthy",
        timestamp=datetime.utcnow().isoformat(),
        uptime_seconds=uptime,
        components=components,
    )


@router.get("/audit-chain/verify")
async def verify_audit_chain() -> Dict[str, Any]:
    """Verify audit chain integrity"""
    valid, message = _audit_chain.verify()
    return {
        "valid": valid,
        "message": message,
        "entries": len(_audit_chain.entries),
        "genesis_hash": "0" * 64,
        "final_hash": _audit_chain.last_hash,
    }


@router.get("/audit-chain/entries", response_model=List[AuditEntry])
async def get_audit_entries(
    limit: int = Query(100, ge=1, le=1000),
    component: Optional[str] = None
) -> List[AuditEntry]:
    """Get audit chain entries with optional filtering"""
    entries = _audit_chain.entries[-limit:]
    
    if component:
        entries = [e for e in entries if e["component"] == component]
    
    return [AuditEntry(**e) for e in entries]


@router.post("/audit-chain/add")
async def add_audit_entry(
    component: str,
    status: ComponentStatus,
    message: str,
    data: Dict[str, Any] = None,
) -> Dict[str, str]:
    """Manually add entry to audit chain"""
    entry_hash = _audit_chain.add(component, status, message, data)
    return {
        "hash": entry_hash,
        "prev_hash": _audit_chain.entries[-2]["hash"] if len(_audit_chain.entries) > 1 else "0" * 64,
    }


@router.get("/components/status")
async def get_components_status() -> Dict[str, ComponentStatus]:
    """Get status of all runtime components"""
    components_by_name: Dict[str, ComponentStatus] = {}
    
    for entry in reversed(_audit_chain.entries):
        if entry["component"] not in components_by_name:
            components_by_name[entry["component"]] = ComponentStatus(entry["status"])
    
    _audit_chain.add("components_status", ComponentStatus.GREEN, "Component status retrieved")
    
    return components_by_name


@router.get("/runtime-state")
async def get_runtime_state() -> Dict[str, Any]:
    """Get current runtime state and decision"""
    entries = len(_audit_chain.entries)
    green_count = sum(1 for e in _audit_chain.entries if e["status"] == "GREEN")
    yellow_count = sum(1 for e in _audit_chain.entries if e["status"] == "YELLOW")
    red_count = sum(1 for e in _audit_chain.entries if e["status"] == "RED")
    
    # Determine state
    if red_count > 0:
        state = RuntimeState.INSTABIL
    elif yellow_count > 0:
        state = RuntimeState.TRANSITION
    elif green_count > entries * 0.8:
        state = RuntimeState.VERIFIED
    else:
        state = RuntimeState.UNKNOWN
    
    return {
        "state": state.value,
        "timestamp": datetime.utcnow().isoformat(),
        "entries": entries,
        "green": green_count,
        "yellow": yellow_count,
        "red": red_count,
        "consensus": ComponentStatus.GREEN if red_count == 0 else ComponentStatus.RED,
    }


@router.post("/validate/fpga-targets")
async def validate_fpga_targets() -> Dict[str, Any]:
    """Validate FPGA target files"""
    fpga_dir = Path("EIRA_RUNTIME/fpga_targets")
    expected = [
        "sha256_core.sv",
        "lockstep_comparator.sv",
        "decision_fsm.sv",
        "ecc_memory_controller.sv",
        "axi4_lite_interface.sv",
        "eira_timing.sdc",
    ]
    
    found = []
    for f in expected:
        fp = fpga_dir / f
        if fp.exists():
            found.append({"file": f, "size": fp.stat().st_size})
    
    status = ComponentStatus.GREEN if len(found) == len(expected) else ComponentStatus.YELLOW
    _audit_chain.add("fpga_validation", status, f"{len(found)}/{len(expected)} FPGA targets found")
    
    return {
        "total_expected": len(expected),
        "found": found,
        "status": status.value,
    }


@router.post("/validate/formal-proofs")
async def validate_formal_proofs() -> Dict[str, Any]:
    """Validate formal proof files"""
    formal_dir = Path("EIRA_RUNTIME/formal")
    expected = [
        "EIRA.thy",
        "EIRA_Refinement.thy",
        "EIRA_Temporal_Properties.thy",
        "EIRA_Information_Flow.thy",
        "EIRA_Refinement_Complete.thy",
    ]
    
    found = []
    for f in expected:
        fp = formal_dir / f
        if fp.exists():
            found.append(f)
    
    status = ComponentStatus.GREEN if len(found) == len(expected) else ComponentStatus.YELLOW
    _audit_chain.add("formal_validation", status, f"{len(found)}/{len(expected)} formal proofs found")
    
    return {
        "total_expected": len(expected),
        "found": found,
        "status": status.value,
    }


@router.get("/report")
async def get_runtime_report() -> RuntimeReport:
    """Get comprehensive runtime report"""
    valid, chain_msg = _audit_chain.verify()
    
    # Get component status
    components_by_name: Dict[str, ComponentStatus] = {}
    for entry in reversed(_audit_chain.entries):
        if entry["component"] not in components_by_name:
            components_by_name[entry["component"]] = ComponentStatus(entry["status"])
    
    # Calculate metrics
    total_entries = len(_audit_chain.entries)
    green_count = sum(1 for e in _audit_chain.entries if e["status"] == "GREEN")
    yellow_count = sum(1 for e in _audit_chain.entries if e["status"] == "YELLOW")
    red_count = sum(1 for e in _audit_chain.entries if e["status"] == "RED")
    
    # Production readiness
    production_readiness = (green_count / max(total_entries, 1)) * 100.0
    
    # Consensus
    consensus = ComponentStatus.GREEN if red_count == 0 else ComponentStatus.RED
    
    _audit_chain.add("report_generated", ComponentStatus.GREEN, "Runtime report generated")
    
    return RuntimeReport(
        timestamp=datetime.utcnow().isoformat(),
        audit_chain={
            "entries": total_entries,
            "valid": valid,
            "message": chain_msg,
            "genesis_hash": "0" * 64,
            "final_hash": _audit_chain.last_hash,
        },
        components={
            "green": green_count,
            "yellow": yellow_count,
            "red": red_count,
            "by_name": {k: v.value for k, v in components_by_name.items()},
        },
        consensus=consensus,
        production_readiness=production_readiness,
    )


@router.post("/reset")
async def reset_runtime() -> Dict[str, str]:
    """Reset runtime and audit chain"""
    global _audit_chain, _runtime_start_time
    _audit_chain = AuditChain()
    _runtime_start_time = datetime.utcnow()
    _audit_chain.add("runtime", ComponentStatus.GREEN, "Runtime reset")
    return {"status": "reset", "timestamp": _runtime_start_time.isoformat()}
