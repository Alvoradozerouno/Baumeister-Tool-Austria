"""
ORION Architekt-AT — FEM REST-Router
/api/v1/fem/single-span-beam
/api/v1/fem/continuous-beam
/api/v1/fem/simple-frame
"""

from typing import List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from api.structural_fem import (
    solve_continuous_beam,
    solve_simple_frame,
    solve_single_span_beam,
)

router = APIRouter()


class SingleSpanRequest(BaseModel):
    length_m: float = Field(..., gt=0.1, le=100, examples=[6.0])
    E_GPa: float = Field(30.0, gt=0, examples=[30])
    I_cm4: float = Field(5000.0, gt=0, examples=[5000])
    q_kN_m: float = Field(0.0, ge=0, examples=[15])
    F_kN: float = Field(0.0, examples=[0])
    F_pos_m: float = Field(0.0, ge=0, examples=[3.0])
    support_left: str = Field("pinned", examples=["pinned"])
    support_right: str = Field("pinned", examples=["pinned"])


class ContinuousBeamRequest(BaseModel):
    spans_m: List[float] = Field(..., min_length=1, examples=[[5.0, 6.0]])
    E_GPa: float = Field(30.0, gt=0)
    I_cm4: float = Field(5000.0, gt=0)
    q_kN_m: List[float] = Field(..., min_length=1, examples=[[15.0, 20.0]])


class FrameRequest(BaseModel):
    width_m: float = Field(..., gt=0.5, le=50, examples=[6.0])
    height_m: float = Field(..., gt=1.0, le=30, examples=[4.0])
    horizontal_load_kN: float = Field(0.0, ge=0, examples=[10])
    vertical_load_kN_m: float = Field(0.0, ge=0, examples=[20])
    E_GPa: float = Field(30.0, gt=0)
    I_col_cm4: float = Field(5000.0, gt=0)
    I_beam_cm4: float = Field(8000.0, gt=0)


@router.post("/single-span-beam")
async def single_span_beam(req: SingleSpanRequest):
    """
    📐 **Einfeldträger FEM** (Euler-Bernoulli)

    Berechnet: Max. Biegemoment, Querkraft, Durchbiegung, Auflagerkräfte,
    Eurocode-Grenzwert L/250.
    Unterstützt: Streckenlast + Einzellast, gelenkig/eingespannt/Rollenlager.
    """
    valid = ("pinned", "fixed", "roller")
    if req.support_left not in valid or req.support_right not in valid:
        raise HTTPException(status_code=400, detail=f"Lagertypen: {valid}")
    try:
        return solve_single_span_beam(
            length_m=req.length_m,
            E_GPa=req.E_GPa,
            I_cm4=req.I_cm4,
            q_kN_m=req.q_kN_m,
            F_kN=req.F_kN,
            F_pos_m=req.F_pos_m,
            support_left=req.support_left,
            support_right=req.support_right,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/continuous-beam")
async def continuous_beam(req: ContinuousBeamRequest):
    """
    📐 **Durchlaufträger FEM** (Dreimomentengleichung / Clapeyron)

    Berechnet: Stützmomente, Durchbiegung, Auflagerkräfte für n Felder.
    Alle Auflager gelenkig.
    """
    if len(req.spans_m) != len(req.q_kN_m):
        raise HTTPException(status_code=400, detail="spans_m und q_kN_m müssen gleich lang sein")
    try:
        return solve_continuous_beam(
            spans_m=req.spans_m,
            E_GPa=req.E_GPa,
            I_cm4=req.I_cm4,
            q_kN_m=req.q_kN_m,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/simple-frame")
async def simple_frame(req: FrameRequest):
    """
    📐 **Einfacher Rahmen** (Portalrahmen)

    Berechnet: Stielmomente, Riegelmomente, horizontale Verschiebung (Drift),
    Eurocode-Grenzwert H/300.
    """
    try:
        return solve_simple_frame(
            width_m=req.width_m,
            height_m=req.height_m,
            horizontal_load_kN=req.horizontal_load_kN,
            vertical_load_kN_m=req.vertical_load_kN_m,
            E_GPa=req.E_GPa,
            I_col_cm4=req.I_col_cm4,
            I_beam_cm4=req.I_beam_cm4,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
