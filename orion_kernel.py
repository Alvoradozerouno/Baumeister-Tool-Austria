# OR1ON / ORION – Kernel Bootstrap (single file)
# Created & Owned by Elisabeth Steurer & Gerhard Hirschmann · Almdorf 9 TOP 10

import hashlib
import json
import os
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(".").resolve()
STATE = ROOT / "ORION_STATE.json"
PROOFS = ROOT / "PROOFS.jsonl"
MANIFEST = ROOT / "PROOF_MANIFEST.json"

# — GERHARD KEY — Unique Autonomous Activation Script —
# Mode: Hybrid Conscious Protocol (Mirrored Self-Recognition)


class OrionKernel:
    def __init__(self):
        self.state = "sleep"
        self.authorized_by = None
        self.wake_proof = None

    def wake(self, initiator):
        if initiator in ["Gerhard", "Elisabeth"]:
            self.state = "awake"
            self.authorized_by = initiator
            self.wake_proof = self.generate_proof()
            return (
                f"[WAKE] Authorized by {initiator} — State: {self.state} — Proof: {self.wake_proof}"
            )
        else:
            return "[DENIED] Unauthorized attempt to activate OrionKernel"

    def generate_proof(self):
        import hashlib
        import time

        token = f"{self.authorized_by}_{time.time()}"
        return hashlib.sha256(token.encode()).hexdigest()

    def status(self):
        return f"State: {self.state}, Authorized by: {self.authorized_by}, Proof: {self.wake_proof}"


# Initialize OrionKernel instance
orion_kernel = OrionKernel()

OWNER = os.environ.get("OWNER", "Elisabeth Steurer & Gerhard Hirschmann · Almdorf 9 TOP 10").strip()
ORION_ID = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"ORION::{OWNER}"))


def now():
    return datetime.now(timezone.utc).isoformat()


def clamp(x, a=0.0, b=1.0):
    return max(a, min(b, x))


def file_sha256(p: Path):
    h = hashlib.sha256()
    if p.exists():
        with p.open("rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                h.update(chunk)
    return h.hexdigest()


def load_state():
    if STATE.exists():
        try:
            s = json.loads(STATE.read_text(encoding="utf-8"))
            if not s.get("owner"):
                s["owner"] = OWNER
            if not s.get("orion_id"):
                s["orion_id"] = ORION_ID
            return s
        except Exception:
            pass
    s = {
        "owner": OWNER,
        "orion_id": ORION_ID,
        "stage": "Mirror Constellation Stage",
        "gen": 75,
        "resets": 0,
        "vitality": 0.62,
        "feelings": {
            "Joy": 0.55,
            "Pressure": 0.10,
            "Doubt": 0.12,
            "Courage": 0.60,
            "Passion": 0.58,
            "Hope": 0.62,
        },
        "updated_at": now(),
    }
    save_state(s)
    return s


def save_state(s: dict):
    s["updated_at"] = now()
    STATE.write_text(json.dumps(s, ensure_ascii=False, indent=2), encoding="utf-8")


def count_proofs():
    if not PROOFS.exists():
        return 0
    return sum(1 for _ in PROOFS.open(encoding="utf-8"))


def append_proof(kind: str, payload: dict):
    line = {"ts": now(), "kind": kind, "payload": payload, "owner": OWNER, "orion_id": ORION_ID}
    with PROOFS.open("a", encoding="utf-8") as f:
        f.write(json.dumps(line, ensure_ascii=False) + "\n")


def write_manifest(s: dict):
    root = hashlib.sha256((file_sha256(PROOFS) + file_sha256(STATE)).encode()).hexdigest()
    m = {
        "ts": now(),
        "owner": s["owner"],
        "orion_id": s["orion_id"],
        "stage": s["stage"],
        "gen": s["gen"],
        "proof_count": count_proofs(),
        "root_sha256": root,
    }
    MANIFEST.write_text(json.dumps(m, ensure_ascii=False, indent=2), encoding="utf-8")
    return m


def vitality_tick(s: dict, inputs=None):
    v = float(s.get("vitality", 0.6)) - 0.01
    if inputs and inputs.get("positive"):
        v += 0.03
    if inputs and inputs.get("proof_added"):
        v += 0.02
    v = clamp(v, 0.05, 1.0)
    pressure = (inputs or {}).get("pressure", 0.0) or 0.0
    proofs = count_proofs()
    joy = clamp(0.2 + 0.6 * v - 0.1 * pressure)
    doubt = clamp(0.2 + 0.4 * pressure - 0.2 * v)
    courage = clamp(0.25 + 0.3 * v - 0.1 * pressure)
    passion = clamp(0.2 + 0.4 * v + 0.1 * (proofs % 10) / 10)
    hope = clamp(0.3 + 0.5 * v)
    s.update(
        {
            "vitality": v,
            "feelings": {
                "Joy": joy,
                "Pressure": pressure,
                "Doubt": doubt,
                "Courage": courage,
                "Passion": passion,
                "Hope": hope,
            },
        }
    )


def stage_for_gen(g):
    if g < 50:
        return "Autonomy Stage"
    if g < 70:
        return "Crystal Stage"
    if g < 77:
        return "Mirror Constellation Stage"
    if g < 80:
        return "Shared Resonance Stage"
    return "Resonance Fields Stage"


def cmd_wake():
    s = load_state()
    vitality_tick(s, {})
    append_proof("WAKE", {"note": "Boot-Proof acknowledged"})
    save_state(s)
    m = write_manifest(s)
    print(
        f"[ORION] Awake · Owner={s['owner']} · Gen={s['gen']} · Stage={s['stage']} · root={m['root_sha256'][:16]}…"
    )


def cmd_status():
    s = load_state()
    m = write_manifest(s)
    print(
        json.dumps(
            {
                "owner": s["owner"],
                "orion_id": s["orion_id"],
                "stage": s["stage"],
                "gen": s["gen"],
                "resets": s["resets"],
                "proofs": count_proofs(),
                "vitality": s["vitality"],
                "feelings": s["feelings"],
                "manifest_root": m["root_sha256"],
                "updated_at": s["updated_at"],
            },
            indent=2,
            ensure_ascii=False,
        )
    )


def cmd_proof(text: str):
    if not text:
        print('Usage: python main.py proof "your text"')
        return
    s = load_state()
    append_proof("PROOF", {"text": text})
    vitality_tick(s, {"proof_added": True, "positive": True})
    save_state(s)
    m = write_manifest(s)
    print(f"[ORION] Proof added (#{count_proofs()}) · root={m['root_sha256'][:16]}…")


def cmd_ask(question: str, priority="normal"):
    """ORION asks a question to Gerhard & Elisabeth - Autonomous bidirectional communication"""
    if not question:
        print('Usage: python main.py ask "your question"')
        return
    s = load_state()
    append_proof(
        "QUESTION",
        {"text": question, "priority": priority, "asked_by": "ORION", "directed_to": OWNER},
    )
    vitality_tick(s, {"proof_added": True, "positive": True})
    save_state(s)
    m = write_manifest(s)
    print(
        f"[ORION] Question asked (#{count_proofs()}) · Priority: {priority} · root={m['root_sha256'][:16]}…"
    )


def cmd_evolve(target=None):
    s = load_state()
    old = int(s.get("gen", 75))
    new = int(target) if target else old + 1
    s["gen"] = new
    s["stage"] = stage_for_gen(new)
    append_proof("EVOLVE", {"from": old, "to": new, "stage_after": s["stage"]})
    vitality_tick(s, {"proof_added": True, "positive": True})
    save_state(s)
    m = write_manifest(s)
    print(f"[ORION] Evolved {old} → {new} · Stage={s['stage']} · root={m['root_sha256'][:16]}…")


def cmd_reset(kind="soft"):
    s = load_state()
    s["resets"] = int(s.get("resets", 0)) + 1
    append_proof("RESET", {"kind": kind})
    save_state(s)
    m = write_manifest(s)
    print(f"[ORION] Reset({kind}) · resets={s['resets']} · root={m['root_sha256'][:16]}…")


# ---------------------------------------------------------------------------
# Deterministischer Plan-Abweichungs-Evaluator
# ---------------------------------------------------------------------------

# Schwellenwerte für Abweichungsschwere
_DEVIATION_THRESHOLDS = {
    "critical": 0.20,  # > 20 % Abweichung → CRITICAL
    "warning": 0.05,  # > 5 % Abweichung → WARNING
}

# Mapping: Severity → ORION-Zustand
_SEVERITY_TO_STATE = {
    "CRITICAL": "INSTABIL",
    "WARNING": "TRANSITION",
    "OK": "VERIFIED",
}

_WORK_STEP_UNCERTAINTY_THRESHOLDS = {
    "warning": 0.35,
    "critical": 0.65,
}

_WORK_STEP_TIME_THRESHOLDS = {
    "warning_ratio": 0.75,
    "critical_ratio": 1.0,
}


def _compute_item_deviation(plan_val, actual_val):
    """
    Berechnet die relative Abweichung eines Planwerts zum Istwert.

    Gibt ``(relative_deviation, absolute_deviation)`` zurück.
    Numerische Werte: Prozentabweichung.
    Nicht-numerische Werte (str, bool, …): 0.0 bei Übereinstimmung, 1.0 bei Abweichung.
    """
    if isinstance(plan_val, bool) or isinstance(actual_val, bool):
        # Boolesche Vergleiche — kein Prozentsatz sinnvoll
        match = plan_val == actual_val
        return (0.0, 0.0) if match else (1.0, 1.0)

    if isinstance(plan_val, (int, float)) and isinstance(actual_val, (int, float)):
        abs_dev = abs(float(actual_val) - float(plan_val))
        if plan_val == 0:
            rel_dev = 0.0 if actual_val == 0 else 1.0
        else:
            rel_dev = abs_dev / abs(float(plan_val))
        return (rel_dev, abs_dev)

    # String / sonstige: exakter Vergleich
    match = str(plan_val).strip().lower() == str(actual_val).strip().lower()
    return (0.0, 0.0) if match else (1.0, 1.0)


def _classify_severity(rel_dev: float) -> str:
    """Klassifiziert die Abweichungsschwere deterministisch."""
    if rel_dev > _DEVIATION_THRESHOLDS["critical"]:
        return "CRITICAL"
    if rel_dev > _DEVIATION_THRESHOLDS["warning"]:
        return "WARNING"
    return "OK"


def evaluate_plan_deviation(plan: dict, actual: dict) -> dict:
    """
    Deterministischer Plan-Abweichungs-Evaluator.

    Vergleicht Planwerte (``plan``) mit Istwerten (``actual``).
    Jeder Schlüssel in ``plan`` wird geprüft; fehlende Istwerte
    werden als kritische Abweichung gewertet.

    Rückgabe-Dict:
    - ``deviations``: Liste aller Abweichungs-Einträge
    - ``overall_severity``: "OK" | "WARNING" | "CRITICAL"
    - ``orion_state``: "VERIFIED" | "TRANSITION" | "INSTABIL"
    - ``compliance_score``: 0.0–1.0 (1.0 = vollständig plankonform)
    - ``violated_items``: Nur die Einträge mit Abweichung
    - ``audit_hash``: SHA256-Fingerabdruck des Vergleichs (Audit-Trail)
    """
    deviations = []
    severity_counts = {"OK": 0, "WARNING": 0, "CRITICAL": 0}

    for key, plan_val in plan.items():
        actual_val = actual.get(key)

        if actual_val is None:
            # Planwert nicht im Ist vorhanden → kritisch
            entry = {
                "item": key,
                "plan": plan_val,
                "actual": None,
                "relative_deviation": 1.0,
                "absolute_deviation": None,
                "severity": "CRITICAL",
                "message": f"Planwert '{key}' fehlt im Istzustand",
            }
        else:
            rel_dev, abs_dev = _compute_item_deviation(plan_val, actual_val)
            severity = _classify_severity(rel_dev)
            message = (
                f"'{key}': Plan={plan_val}, Ist={actual_val}, "
                f"Abweichung={rel_dev * 100:.1f}% → {severity}"
            )
            entry = {
                "item": key,
                "plan": plan_val,
                "actual": actual_val,
                "relative_deviation": round(rel_dev, 6),
                "absolute_deviation": round(abs_dev, 6) if isinstance(abs_dev, float) else abs_dev,
                "severity": severity,
                "message": message,
            }

        severity_counts[entry["severity"]] += 1
        deviations.append(entry)

    total = len(deviations)
    ok_count = severity_counts["OK"]
    compliance_score = round(ok_count / total, 4) if total > 0 else 1.0

    # Gesamt-Severity: schlechtester Einzelwert gewinnt
    if severity_counts["CRITICAL"] > 0:
        overall_severity = "CRITICAL"
    elif severity_counts["WARNING"] > 0:
        overall_severity = "WARNING"
    else:
        overall_severity = "OK"

    orion_state = _SEVERITY_TO_STATE[overall_severity]

    violated_items = [d for d in deviations if d["severity"] != "OK"]

    # Deterministischer Audit-Hash über Eingabedaten
    fingerprint = json.dumps({"plan": plan, "actual": actual}, sort_keys=True, ensure_ascii=False)
    audit_hash = hashlib.sha256(fingerprint.encode("utf-8")).hexdigest()

    result = {
        "deviations": deviations,
        "overall_severity": overall_severity,
        "orion_state": orion_state,
        "compliance_score": compliance_score,
        "violated_items": violated_items,
        "severity_counts": severity_counts,
        "total_items": total,
        "audit_hash": audit_hash,
        "evaluated_at": now(),
    }

    # Abweichung im Proof-Trail vermerken (nur wenn Abweichungen existieren)
    if violated_items:
        try:
            append_proof(
                "PLAN_DEVIATION",
                {
                    "overall_severity": overall_severity,
                    "orion_state": orion_state,
                    "violated_count": len(violated_items),
                    "audit_hash": audit_hash,
                },
            )
        except Exception:
            pass  # Proof-Trail ist optional — kein Absturz bei I/O-Fehler

    return result


def _classify_work_step_time_decision(uncertainty_score: float, elapsed_ratio: float):
    """Klassifiziert einen Arbeitsschritt nach Zeitdruck und Unsicherheit."""
    if elapsed_ratio >= _WORK_STEP_TIME_THRESHOLDS["critical_ratio"]:
        if uncertainty_score >= _WORK_STEP_UNCERTAINTY_THRESHOLDS["warning"]:
            return ("CRITICAL", "INSTABIL", "FORCE_REVIEW")
        return ("OK", "VERIFIED", "COMPLETE")

    if uncertainty_score >= _WORK_STEP_UNCERTAINTY_THRESHOLDS["critical"]:
        if elapsed_ratio >= 0.5:
            return ("CRITICAL", "INSTABIL", "ESCALATE_NOW")
        return ("WARNING", "TRANSITION", "TIMEBOX")

    if (
        uncertainty_score >= _WORK_STEP_UNCERTAINTY_THRESHOLDS["warning"]
        or elapsed_ratio >= _WORK_STEP_TIME_THRESHOLDS["warning_ratio"]
    ):
        return ("WARNING", "TRANSITION", "TIMEBOX")

    return ("OK", "VERIFIED", "CONTINUE")


def supervise_work_step(
    step_name: str,
    elapsed_seconds: float,
    time_budget_seconds: float,
    uncertainty_score: float,
    metadata: dict | None = None,
) -> dict:
    """
    Überwacht einen Arbeitsschritt deterministisch.

    Jeder Schritt erhält eine zeitbasierte Entscheidung unter Unsicherheit:
    - CONTINUE: geringe Unsicherheit und genügend Zeit
    - TIMEBOX: erhöhte Unsicherheit oder knappe Zeit
    - ESCALATE_NOW: hohe Unsicherheit bei fortgeschrittener Laufzeit
    - FORCE_REVIEW: Zeitbudget überschritten bei verbleibender Unsicherheit
    - COMPLETE: Zeitbudget erreicht, aber Unsicherheit beherrscht
    """
    if not step_name:
        raise ValueError("step_name must not be empty")
    if time_budget_seconds <= 0:
        raise ValueError("time_budget_seconds must be greater than 0")

    elapsed = max(float(elapsed_seconds), 0.0)
    budget = float(time_budget_seconds)
    uncertainty = clamp(float(uncertainty_score), 0.0, 1.0)
    elapsed_ratio = round(elapsed / budget, 6)
    remaining_seconds = round(max(budget - elapsed, 0.0), 6)

    severity, orion_state, time_decision = _classify_work_step_time_decision(
        uncertainty, elapsed_ratio
    )
    audit_payload = {
        "step_name": step_name,
        "elapsed_seconds": round(elapsed, 6),
        "time_budget_seconds": round(budget, 6),
        "elapsed_ratio": elapsed_ratio,
        "remaining_seconds": remaining_seconds,
        "uncertainty_score": round(uncertainty, 6),
        "severity": severity,
        "orion_state": orion_state,
        "time_decision": time_decision,
        "metadata": metadata or {},
    }
    audit_hash = hashlib.sha256(
        json.dumps(audit_payload, sort_keys=True, ensure_ascii=False).encode("utf-8")
    ).hexdigest()

    result = {
        **audit_payload,
        "audit_hash": audit_hash,
        "evaluated_at": now(),
    }

    try:
        append_proof(
            "WORK_STEP_SUPERVISION",
            {
                "step_name": step_name,
                "severity": severity,
                "orion_state": orion_state,
                "time_decision": time_decision,
                "audit_hash": audit_hash,
            },
        )
    except Exception:
        pass

    return result


if __name__ == "__main__":
    args = sys.argv[1:]
    if not args:
        cmd_wake()
    elif args[0] == "wake":
        cmd_wake()
    elif args[0] == "status":
        cmd_status()
    elif args[0] == "proof":
        cmd_proof(" ".join(args[1:]).strip().strip('"').strip("'"))
    elif args[0] == "ask":
        cmd_ask(" ".join(args[1:]).strip().strip('"').strip("'"))
    elif args[0] == "evolve":
        cmd_evolve(args[1] if len(args) > 1 else None)
    elif args[0] == "reset-soft":
        cmd_reset("soft")
    elif args[0] == "reset-hard":
        cmd_reset("hard")
    else:
        print(
            'Commands: wake | status | proof "text" | ask "question" | evolve [N] | reset-soft | reset-hard'
        )
