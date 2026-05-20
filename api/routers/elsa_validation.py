"""
ELSA Bauplan-Validierungs-Router
Deterministische Validierung mit EXECUTE/DEFER/ABSTAIN Entscheidungen.
"""

import os, sys, json, hashlib, re
from datetime import datetime
from typing import Optional
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from fastapi import APIRouter, UploadFile, File, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/api/v1/elsa", tags=["elsa"])

class ELSADecision(BaseModel):
    state: str
    reason: str
    risk_level: str
    timestamp: str
    sha256: str
    details: dict = {}

class PlanValidationResult(BaseModel):
    plan_name: str
    revision: str
    decision: ELSADecision
    mass_ketten: list = []
    critical_elements: list = []
    audit_hash: str
    timestamp: str

MASS_KETTEN_PATTERNS = [
    re.compile(r'(\d+[,.]\d{2})\s*m\b', re.IGNORECASE),
    re.compile(r'(\d+[,.]\d{2})\s*(?:m\b|Meter|laufende?m)', re.IGNORECASE),
    re.compile(r'(?:H[=oe]*\s*|OKF\s*|Hoehe\s*)([+-]?\d+[,.]\d{2})\s*m?', re.IGNORECASE),
    re.compile(r'(\d+[,.]\d{2})\s*m[\u00b22]', re.IGNORECASE),
    re.compile(r'(\d+[,.]\d{2})\s*m[\u00b33]', re.IGNORECASE),
]

NORMEN_DB = {
    "EN 1992": {"name": "Eurocode 2 - Stahlbeton", "domain": "structural", "required_for": ["fundament", "beton", "stahlbeton"]},
    "EN 1993": {"name": "Eurocode 3 - Stahlbau", "domain": "structural", "required_for": ["stahl", "tragrahmen"]},
    "EN 1995": {"name": "Eurocode 5 - Holzbau", "domain": "structural", "required_for": ["holz", "dachstuhl"]},
    "EN 1997": {"name": "Eurocode 7 - Geotechnik", "domain": "geotechnical", "required_for": ["fundament", "boden", "erdung"]},
    "EN 1998": {"name": "Eurocode 8 - Erdbeben", "domain": "seismic", "required_for": ["erdbeben"]},
    "EN 40": {"name": "EN 40 - Lichtmasten", "domain": "electrical", "required_for": ["lichtmast"]},
    "DIN 18531": {"name": "DIN 18531 - Dachabdichtung", "domain": "roofing", "required_for": ["dach", "abdichtung"]},
    "OeNORM B 1991": {"name": "OeNORM B 1991 - Einwirkungen", "domain": "structural", "required_for": ["last"]},
    "OIB-RL 1": {"name": "OIB-RL 1 - Tragfaehigkeit", "domain": "structural", "required_for": ["tragfaehigkeit"]},
    "OIB-RL 2": {"name": "OIB-RL 2 - Brandschutz", "domain": "fire", "required_for": ["brandschutz", "feuer"]},
    "OIB-RL 3": {"name": "OIB-RL 3 - Hygiene", "domain": "hygiene", "required_for": ["hygiene", "wasser"]},
    "OIB-RL 4": {"name": "OIB-RL 4 - Sicherheit", "domain": "safety", "required_for": ["sicherheit", "sturz"]},
    "OIB-RL 5": {"name": "OIB-RL 5 - Schallschutz", "domain": "acoustic", "required_for": ["schall", "laerm"]},
    "OIB-RL 6": {"name": "OIB-RL 6 - Energie", "domain": "energy", "required_for": ["energie", "waerme"]},
}

BOM_PATTERNS = [
    ("beton", re.compile(r'(\d+[,.]?\d*)\s*m[\u00b33].*?(?:beton|c20/25|c25/30|c30/37)', re.IGNORECASE)),
    ("stahl", re.compile(r'(\d+[,.]?\d*)\s*(?:kg|t).*?(?:stahl|bewehrung|b500)', re.IGNORECASE)),
    ("holz", re.compile(r'(\d+[,.]?\d*)\s*m[\u00b33].*?(?:holz|bsh|kvh|bs)', re.IGNORECASE)),
    ("dachbahn", re.compile(r'(\d+[,.]?\d*)\s*m[\u00b22].*?(?:dachbahn|abdichtung|bahn)', re.IGNORECASE)),
    ("daemmung", re.compile(r'(\d+[,.]?\d*)\s*m[\u00b22].*?(?:daemm|isol|eps|xps)', re.IGNORECASE)),
    ("fenster", re.compile(r'(\d+)\s*(?:fenster|vergla|glas)', re.IGNORECASE)),
    ("tuer", re.compile(r'(\d+)\s*(?:tuer|tor)', re.IGNORECASE)),
]

def extract_mass_ketten(text):
    results, seen = [], set()
    for pattern in MASS_KETTEN_PATTERNS:
        for match in pattern.finditer(text):
            value = match.group(1).replace(",", ".")
            context = text[max(0,match.start()-40):min(len(text),match.end()+40)].strip()
            key = f"{value}_{match.start()}"
            if key not in seen:
                seen.add(key)
                results.append({"value": float(value), "raw": match.group(0), "position": match.start(), "context": context, "type": _classify_dimension(value, context)})
    return sorted(results, key=lambda x: x["position"])

def _classify_dimension(value, context):
    ctx = context.lower()
    if any(k in ctx for k in ["hoehe", "h =", "okf", "ok", "niveau"]): return "hoehe"
    if any(k in ctx for k in ["flaeche", "m2", "m\u00b2", "qm"]): return "flaeche"
    if any(k in ctx for k in ["volumen", "m3", "m\u00b3", "raum"]): return "volumen"
    if any(k in ctx for k in ["breite", "breit", "b ="]): return "breite"
    if any(k in ctx for k in ["laenge", "lang", "l =", "lfm"]): return "laenge"
    if value > 100: return "hoehe"
    if value > 20: return "laenge"
    return "unbekannt"

def detect_normen(text):
    detected, text_lower = [], text.lower()
    for norm_id, info in NORMEN_DB.items():
        for kw in info["required_for"]:
            if kw in text_lower:
                if norm_id not in [d["id"] for d in detected]:
                    detected.append({"id": norm_id, "name": info["name"], "domain": info["domain"], "trigger": kw})
                break
    return detected

def generate_bom(text):
    bom = []
    for material, pattern in BOM_PATTERNS:
        for match in pattern.finditer(text):
            value = match.group(1).replace(",", ".")
            units = {"beton": "m3", "stahl": "kg", "holz": "m3", "dachbahn": "m2", "daemmung": "m2", "fenster": "Stk", "tuer": "Stk"}
            bom.append({"material": material, "quantity": float(value), "unit": units.get(material, "Stk"), "context": match.group(0)[:80]})
    return bom

def elsa_decide(plan_text, plan_name):
    text_lower = plan_text.lower()
    issues, risk_score = [], 0
    mass_ketten = extract_mass_ketten(plan_text)
    laengen = [m for m in mass_ketten if m["type"] == "laenge"]
    if len(laengen) >= 2:
        diff = abs(laengen[0]["value"] - laengen[1]["value"])
        if 0.01 < diff < 5.0:
            issues.append(f"Mass-Ketten-Differenz: {laengen[0]['value']:.2f}m vs {laengen[1]['value']:.2f}m")
            risk_score += 3
    hoehen = [m for m in mass_ketten if m["type"] == "hoehe"]
    if len(hoehen) >= 2:
        diff = abs(hoehen[0]["value"] - hoehen[1]["value"])
        if 0.01 < diff < 10.0:
            issues.append(f"Hoehen-Differenz: {hoehen[0]['value']:.2f} vs {hoehen[1]['value']:.2f}")
            risk_score += 2
    critical_keywords = {"notstromaggregat": ("Notstromaggregat", 4), "notstrom": ("Notstrom", 3), "fundament": ("Fundament", 2), "trag": ("Tragwerk", 3), "brandschutz": ("Brandschutz", 3), "stb": ("Stahlbeton", 2), "erdung": ("Erdung", 2), "blitzschutz": ("Blitzschutz", 2)}
    critical_elements = []
    for kw, (label, score) in critical_keywords.items():
        if kw in text_lower:
            critical_elements.append({"label": label, "risk_score": score})
            risk_score += score
    has_revision = bool(re.search(r"rev(?:ision)?\s*(\w+)", plan_text, re.IGNORECASE))
    if has_revision: risk_score += 1
    normen = detect_normen(plan_text)
    if risk_score >= 8: state, reason, risk_level = "ABSTAIN", f"Kritische Unsicherheit (Score={risk_score}). {len(issues)} Fehler.", "CRITICAL"
    elif risk_score >= 4: state, reason, risk_level = "DEFER", f"HITL-Freigabe erforderlich (Score={risk_score}). {len(issues)} Auffaelligkeiten.", "HIGH"
    elif risk_score >= 2: state, reason, risk_level = "DEFER", f"Leichte Unsicherheit (Score={risk_score}). {len(issues)} Hinweise.", "MEDIUM"
    else: state, reason, risk_level = "EXECUTE", f"Alle Checks bestanden (Score={risk_score}).", "LOW"
    sha256 = hashlib.sha256(plan_text.encode()).hexdigest()
    return ELSADecision(state=state, reason=reason, risk_level=risk_level, timestamp=datetime.now().isoformat(), sha256=sha256, details={"risk_score": risk_score, "issues": issues, "critical_elements": critical_elements, "normen_detected": normen, "mass_ketten_count": len(mass_ketten), "has_revision": has_revision})

class ValidateTextRequest(BaseModel):
    text: str
    plan_name: str = "unknown"

@router.post("/validate", response_model=PlanValidationResult)
async def validate_plan(file: UploadFile = File(None), text_request: ValidateTextRequest = None):
    plan_text, plan_name = "", "unknown"
    if file:
        if not file.filename.lower().endswith(".pdf"): raise HTTPException(400, "Nur PDF-Dateien")
        try:
            import fitz
            content = await file.read()
            doc = fitz.open(stream=content, filetype="pdf")
            for page in doc: plan_text += page.get_text()
            doc.close()
            plan_name = file.filename
        except ImportError: raise HTTPException(500, "PyMuPDF nicht installiert")
        except Exception as e: raise HTTPException(400, f"PDF-Fehler: {e}")
    elif text_request:
        plan_text, plan_name = text_request.text, text_request.plan_name
    else: raise HTTPException(400, "Datei oder Text erforderlich")
    if not plan_text.strip(): raise HTTPException(400, "Leerer Text")
    decision = elsa_decide(plan_text, plan_name)
    mass_ketten = extract_mass_ketten(plan_text)
    critical_elements = decision.details.get("critical_elements", [])
    bom = generate_bom(plan_text)
    normen = detect_normen(plan_text)
    audit_hash = hashlib.sha256(f"{plan_name}{decision.sha256}{decision.timestamp}".encode()).hexdigest()
    revision = "unknown"
    rev_match = re.search(r"rev(?:ision)?\s*(\w+)", plan_text, re.IGNORECASE)
    if rev_match: revision = rev_match.group(1)
    return PlanValidationResult(plan_name=plan_name, revision=revision, decision=decision, mass_ketten=mass_ketten[:50], critical_elements=critical_elements, audit_hash=audit_hash, timestamp=datetime.now().isoformat())

@router.get("/normen")
async def get_normen():
    return {"normen": list(NORMEN_DB.values()), "count": len(NORMEN_DB)}

@router.post("/extract-massketten")
async def extract_massketten_endpoint(text: str):
    mk = extract_mass_ketten(text)
    groups = {}
    for m in mk:
        t = m["type"]
        if t not in groups: groups[t] = []
        groups[t].append(m["value"])
    return {"mass_ketten": mk, "count": len(mk), "by_type": {k: {"count": len(v), "values": v[:10]} for k, v in groups.items()}}

@router.post("/generate-bom")
async def generate_bom_endpoint(text: str):
    bom = generate_bom(text)
    return {"bom": bom, "count": len(bom)}

@router.post("/detect-normen")
async def detect_normen_endpoint(text: str):
    normen = detect_normen(text)
    return {"normen": normen, "count": len(normen), "domains": list(set(n["domain"] for n in normen))}