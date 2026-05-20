"""
GUARDIAN HITL-Bridge Router
Human-in-the-Loop Freigabe mit HMAC-Signatur und 3 Rollen.
"""

import os, sys, json, hashlib, hmac, time
from datetime import datetime
from typing import Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/api/v1/hitl", tags=["hitl"])

# ============================================================
# ROLLEN-DEFINITION
# ============================================================

ROLES = {
    "architekt": {"label": "Architekt", "domains": ["design", "aesthetics", "space", "revision"]},
    "statiker": {"label": "Statiker", "domains": ["structural", "fundament", "beton", "stahl", "tragwerk"]},
    "bauleitung": {"label": "Bauleitung", "domains": ["execution", "timeline", "cost", "safety", "brandschutz"]},
}

# HMAC Secret (in Produktion aus env)
HITL_SECRET = os.environ.get("HITL_SECRET", "paradoxonai_baumeister_2026")

# Pending Approvals Store (in Produktion: Datenbank)
PENDING_APPROVALS: dict = {}
APPROVAL_LOG: list = []


class ApprovalRequest(BaseModel):
    plan_name: str
    elsa_decision: str  # EXECUTE, DEFER, ABSTAIN
    reason: str
    risk_level: str
    required_role: str
    details: dict = {}


class ApprovalResponse(BaseModel):
    approval_id: str
    role: str
    approved: bool
    signature: str
    timestamp: str
    comment: str = ""


class ApprovalCheck(BaseModel):
    approval_id: str
    role: str
    signature: str


@router.post("/request", description="HITL-Freigabe anfordern")
async def request_approval(req: ApprovalRequest):
    """Anforderung fuer HITL-Freigabe erstellen."""
    if req.required_role not in ROLES:
        raise HTTPException(400, f"Unbekannte Rolle: {req.required_role}. Gueltig: {list(ROLES.keys())}")
    
    approval_id = hashlib.sha256(
        f"{req.plan_name}{req.elsa_decision}{time.time()}".encode()
    ).hexdigest()[:16]
    
    PENDING_APPROVALS[approval_id] = {
        "approval_id": approval_id,
        "plan_name": req.plan_name,
        "elsa_decision": req.elsa_decision,
        "reason": req.reason,
        "risk_level": req.risk_level,
        "required_role": req.required_role,
        "details": req.details,
        "status": "pending",
        "created_at": datetime.now().isoformat(),
        "approvals": {},
    }
    
    return {
        "approval_id": approval_id,
        "status": "pending",
        "required_role": ROLES[req.required_role]["label"],
        "plan_name": req.plan_name,
        "elsa_decision": req.elsa_decision,
        "reason": req.reason,
    }


@router.post("/approve", description="HITL-Freigabe erteilen")
async def approve(approval_id: str, role: str, comment: str = ""):
    """Freigabe durch verantwortliche Person."""
    if role not in ROLES:
        raise HTTPException(400, f"Unbekannte Rolle: {role}")
    
    if approval_id not in PENDING_APPROVALS:
        raise HTTPException(404, "Approval nicht gefunden")
    
    approval = PENDING_APPROVALS[approval_id]
    if approval["status"] == "approved":
        return {"approval_id": approval_id, "status": "already_approved", "approvals": approval["approvals"]}
    
    # HMAC-Signatur erstellen
    sig_data = f"{approval_id}:{role}:{comment}:{time.time()}"
    signature = hmac.new(HITL_SECRET.encode(), sig_data.encode(), hashlib.sha256).hexdigest()
    
    approval["approvals"][role] = {
        "role": role,
        "comment": comment,
        "signature": signature,
        "timestamp": datetime.now().isoformat(),
    }
    
    # Pruefen ob alle required roles freigegeben haben
    required_role = approval["required_role"]
    if required_role in approval["approvals"]:
        approval["status"] = "approved"
        approval["approved_at"] = datetime.now().isoformat()
    
    APPROVAL_LOG.append({
        "approval_id": approval_id,
        "action": "approve",
        "role": role,
        "timestamp": datetime.now().isoformat(),
    })
    
    return {
        "approval_id": approval_id,
        "status": approval["status"],
        "role_approved": ROLES[role]["label"],
        "signature": signature[:16] + "...",
    }


@router.get("/status/{approval_id}", description="Approval-Status pruefen")
async def check_status(approval_id: str):
    """Status einer Approval-Anfrage."""
    if approval_id not in PENDING_APPROVALS:
        raise HTTPException(404, "Approval nicht gefunden")
    
    approval = PENDING_APPROVALS[approval_id]
    return {
        "approval_id": approval_id,
        "status": approval["status"],
        "plan_name": approval["plan_name"],
        "elsa_decision": approval["elsa_decision"],
        "required_role": ROLES[approval["required_role"]]["label"],
        "approvals_received": list(approval["approvals"].keys()),
        "created_at": approval["created_at"],
    }


@router.get("/pending", description="Alle offenen Approvals")
async def list_pending():
    """Liste aller offenen Freigaben."""
    pending = {k: v for k, v in PENDING_APPROVALS.items() if v["status"] == "pending"}
    return {
        "pending_count": len(pending),
        "approvals": [
            {
                "approval_id": k,
                "plan_name": v["plan_name"],
                "elsa_decision": v["elsa_decision"],
                "required_role": ROLES[v["required_role"]]["label"],
                "created_at": v["created_at"],
            }
            for k, v in pending.items()
        ],
    }


@router.get("/log", description="Audit-Log aller Approvals")
async def get_log():
    """Vollstaendiges Audit-Log."""
    return {
        "log_entries": len(APPROVAL_LOG),
        "log": APPROVAL_LOG[-100:],  # Letzte 100 Eintraege
    }


@router.post("/verify", description="HMAC-Signatur verifizieren")
async def verify_signature(approval_id: str, role: str, signature: str):
    """Verifiziert eine HMAC-Signatur."""
    if approval_id not in PENDING_APPROVALS:
        return {"valid": False, "reason": "Approval nicht gefunden"}
    
    approval = PENDING_APPROVALS[approval_id]
    if role not in approval.get("approvals", {}):
        return {"valid": False, "reason": "Rolle hat nicht freigegeben"}
    
    stored_sig = approval["approvals"][role]["signature"]
    is_valid = hmac.compare_digest(stored_sig, signature)
    
    return {
        "valid": is_valid,
        "role": ROLES[role]["label"],
        "timestamp": approval["approvals"][role]["timestamp"],
    }