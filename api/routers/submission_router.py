import logging
"""
ORION Architekt-AT — Behördeneinreichung REST-Router
/api/v1/submission/generate
"""

logger = logging.getLogger(__name__)
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from api.submission_generator import generate_submission_package

router = APIRouter()


class SubmissionRequest(BaseModel):
    bundesland: str = Field("tirol", examples=["tirol"])
    vorhaben: str = Field("neubau", examples=["neubau"])
    gebaudetyp: str = Field("wohnbau", examples=["wohnbau"])
    bgf_m2: float = Field(300.0, gt=0, examples=[500])
    bauherr: str = Field("", examples=["Fam. Muster"])
    grundstueck_kgez: str = Field("", examples=["KG 12345 EZ 67"])


@router.post("/generate")
async def generate_submission(req: SubmissionRequest):
    """
    📄 **Einreichunterlagen-Generator**

    Erstellt bundeslandspezifische Unterlagenliste für das Bauansuchen.
    Beinhaltet:
    - Pflicht- und optionale Dokumente
    - Zuständige Behörde + Portal-URL
    - Bearbeitungszeiten
    - Vorhabens- und größenspezifische Extras (Brandschutz, UVP)
    - Checkliste zur Vorbereitung
    """
    valid_vorhaben = ["neubau", "zubau", "umbau", "abbruch", "dachausbau"]
    if req.vorhaben not in valid_vorhaben:
        raise HTTPException(status_code=400, detail=f"vorhaben muss einer von {valid_vorhaben} sein")

    valid_bl = [
        "wien", "niederoesterreich", "oberoesterreich", "salzburg", "tirol",
        "vorarlberg", "steiermark", "kaernten", "burgenland",
    ]
    if req.bundesland not in valid_bl:
        raise HTTPException(status_code=400, detail=f"bundesland muss einer von {valid_bl} sein")

    try:
        return generate_submission_package(
            bundesland=req.bundesland,
            vorhaben=req.vorhaben,
            gebaudetyp=req.gebaudetyp,
            bgf_m2=req.bgf_m2,
            bauherr=req.bauherr,
            grundstueck_kgez=req.grundstueck_kgez,
        )
    except Exception as e:
        logger.error("Internal error: %s", e)
        raise HTTPException(status_code=500, detail="Interner Serverfehler")
