"""
ORION Architekt-AT — Normen-Monitor REST-Router
/api/v1/norms/check
/api/v1/norms/history
/api/v1/norms/ris-updates
/api/v1/norms/hora/{lat}/{lon}
"""

from fastapi import APIRouter, HTTPException

from api.external_data import (
    check_norm_changes,
    fetch_hora_hazards,
    fetch_ris_updates,
    get_norm_history,
)

router = APIRouter()


@router.get("/check")
async def check_norms():
    """
    🔍 **Normen-Monitor — Änderungserkennung**

    Prüft OIB, RIS Austria, ASI auf Änderungen via SHA-256-Hash-Vergleich.
    Ergebnisse werden 6h gecacht.
    """
    try:
        return await check_norm_changes()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history")
async def norm_history():
    """📜 Verlauf der erkannten Normenänderungen"""
    return get_norm_history()


@router.get("/ris-updates")
async def ris_updates(bundesland: str = None):
    """
    📋 **RIS Austria — Aktuelle Baurechtsänderungen**

    Scrapet RIS Austria BGBl für aktuelle Bauordnungsänderungen.
    Filterbar nach Bundesland.
    """
    try:
        return {"updates": await fetch_ris_updates(bundesland)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/hora/{lat}/{lon}")
async def hora_hazards(lat: float, lon: float):
    """
    🗺️ **hora.gv.at — Naturgefahren für Standort**

    Abfrage von Hochwasser-, Lawinen-, Steinschlag-Zonen für GPS-Koordinaten.
    Beispiel: /api/v1/norms/hora/47.52/12.21 (St. Johann in Tirol)
    """
    if not (46.0 <= lat <= 49.0) or not (9.5 <= lon <= 17.2):
        raise HTTPException(status_code=400, detail="Koordinaten außerhalb Österreich (lat 46-49, lon 9.5-17.2)")
    try:
        return await fetch_hora_hazards(lat, lon)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
