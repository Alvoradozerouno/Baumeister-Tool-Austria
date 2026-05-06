import logging
"""
ORION Architekt-AT — ML REST-Router
/api/v1/ml/predict-cost
/api/v1/ml/optimize-energy
/api/v1/ml/recommend-material
"""

from typing import Optional

logger = logging.getLogger(__name__)
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from api.ml import get_cost_model, get_energy_model, recommend_material

router = APIRouter()


class CostRequest(BaseModel):
    bundesland: str = Field("tirol", examples=["tirol"])
    gebaudetyp: str = Field("mehrfamilienhaus", examples=["mehrfamilienhaus"])
    bgf_m2: float = Field(..., gt=10, examples=[500])
    geschosse: int = Field(3, gt=0, examples=[4])
    energieziel: str = Field("A", examples=["A+"])
    budget_euro: Optional[float] = Field(None, examples=[1500000])


class EnergyRequest(BaseModel):
    u_wert_wand: float = Field(0.35, gt=0, examples=[0.35])
    u_wert_dach: float = Field(0.20, gt=0, examples=[0.20])
    fensterflaeche_proz: float = Field(20.0, gt=0, le=80, examples=[20])
    klimazone: int = Field(2, ge=1, le=3, examples=[3])
    ziel_energieklasse: str = Field("A+", examples=["A+"])


class MaterialRequest(BaseModel):
    bauteil_typ: str = Field("aussenwand", examples=["aussenwand"])
    prioritaet: str = Field("kosten", examples=["energie"])
    ziel_uwert: float = Field(0.15, gt=0, examples=[0.15])


@router.post("/predict-cost")
async def predict_cost(req: CostRequest):
    """
    🤖 **ML Kostenprognose** — Gradient Boosting, trainiert auf AT-Baudaten 2020–2025.

    Liefert: Gesamtkosten (Mitte + Bandbreite), €/m², Aufschlüsselung nach Gewerk,
    Einflussfaktoren, Budget-Delta.
    """
    try:
        model = get_cost_model()
        return model.predict(
            bundesland=req.bundesland,
            gebaudetyp=req.gebaudetyp,
            bgf_m2=req.bgf_m2,
            geschosse=req.geschosse,
            energieziel=req.energieziel,
            budget_euro=req.budget_euro,
        )
    except Exception as e:
        logger.error("Internal error: %s", e)
        raise HTTPException(status_code=500, detail="Interner Serverfehler")


@router.post("/optimize-energy")
async def optimize_energy(req: EnergyRequest):
    """
    ⚡ **ML Energieoptimierung** — wählt kosteneffiziente Maßnahmen zum Erreichen der Zielklasse.

    Liefert: aktuelle/optimierte HWB, Energieklasse, empfohlene Maßnahmen mit Kosten.
    """
    try:
        model = get_energy_model()
        return model.optimise(
            u_wert_wand=req.u_wert_wand,
            u_wert_dach=req.u_wert_dach,
            fensterflaeche_proz=req.fensterflaeche_proz,
            klimazone=req.klimazone,
            ziel_energieklasse=req.ziel_energieklasse,
        )
    except Exception as e:
        logger.error("Internal error: %s", e)
        raise HTTPException(status_code=500, detail="Interner Serverfehler")


@router.post("/recommend-material")
async def recommend_material_endpoint(req: MaterialRequest):
    """
    🏗️ **Materialempfehlung** — nach Priorität (Kosten / Energie / Nachhaltigkeit).

    Liefert: Top-5 Materialien mit U-Wert, Kosten, CO₂, Score.
    """
    valid_typen = ["aussenwand", "dach", "boden"]
    if req.bauteil_typ not in valid_typen:
        raise HTTPException(status_code=400, detail=f"bauteil_typ muss einer von {valid_typen} sein")
    valid_prio = ["kosten", "energie", "nachhaltigkeit"]
    if req.prioritaet not in valid_prio:
        raise HTTPException(status_code=400, detail=f"prioritaet muss einer von {valid_prio} sein")
    try:
        return recommend_material(req.bauteil_typ, req.prioritaet, req.ziel_uwert)
    except Exception as e:
        logger.error("Internal error: %s", e)
        raise HTTPException(status_code=500, detail="Interner Serverfehler")
