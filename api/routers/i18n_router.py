"""
ORION Architekt-AT — i18n / Mehrsprachigkeit Router
====================================================

Endpoints für Mehrsprachigkeit und Locale-Management.

Endpoints:
  GET /api/v1/i18n/sprachen           — Liste unterstützter Sprachen
  GET /api/v1/i18n/locale/{sprache}   — Alle Übersetzungen als Bundle
  GET /api/v1/i18n/{schluessel}       — Einzelne Übersetzung
  POST /api/v1/i18n/batch             — Mehrere Schlüssel auf einmal
"""

from typing import Dict, List, Optional

from fastapi import APIRouter, Header, HTTPException, Path, Query
from pydantic import BaseModel

from api.i18n import (
    SpracheCode,
    get_alle_schluessel,
    get_alle_uebersetzungen,
    parse_accept_language,
    t,
)

router = APIRouter()


SPRACHEN_INFO: Dict[str, Dict[str, str]] = {
    "de": {
        "code": "de",
        "name_de": "Deutsch",
        "name_native": "Deutsch",
        "region": "Österreich (alle Bundesländer)",
        "status": "vollständig",
        "bemerkung": "Arbeitssprache — alle Inhalte vollständig verfügbar",
    },
    "en": {
        "code": "en",
        "name_de": "Englisch",
        "name_native": "English",
        "region": "International",
        "status": "vollständig",
        "bemerkung": "Für internationale Investoren, Planer und Ingenieure",
    },
    "sl": {
        "code": "sl",
        "name_de": "Slowenisch",
        "name_native": "Slovenščina",
        "region": "Kärnten (Koroška) — autochthone Volksgruppe",
        "status": "kernübersetzungen",
        "bemerkung": (
            "Für Kärntner Slowenen (autochthone Volksgruppe gem. Art. 7 Staatsvertrag 1955). "
            "Betrifft v.a. Kärntner Bauordnung (Kärntner BauO), Ortsbildschutz und Zweisprachigkeit."
        ),
    },
    "hr": {
        "code": "hr",
        "name_de": "Kroatisch",
        "name_native": "Hrvatski",
        "region": "Burgenland (Gradišće) — autochthone Volksgruppe",
        "status": "kernübersetzungen",
        "bemerkung": (
            "Für burgenländische Kroaten (autochthone Volksgruppe). "
            "Betrifft v.a. Bgld Baugesetz, Wohnbauförderung Burgenland."
        ),
    },
    "hu": {
        "code": "hu",
        "name_de": "Ungarisch",
        "name_native": "Magyar",
        "region": "Burgenland (Gradišće) — autochthone Volksgruppe",
        "status": "kernübersetzungen",
        "bemerkung": (
            "Für burgenländische Ungarn (autochthone Volksgruppe). "
            "Betrifft v.a. Bgld Baugesetz, Wohnbauförderung Burgenland."
        ),
    },
}


class BatchRequest(BaseModel):
    schluessel: List[str]
    sprache: str = "de"


@router.get(
    "/sprachen",
    summary="Unterstützte Sprachen auflisten",
    tags=["i18n"],
)
async def list_sprachen() -> Dict:
    """
    Gibt alle in ORION Architekt-AT unterstützten Sprachen zurück.

    Sprachauswahl-Philosophie:
    - **Deutsch**: Vollständige Arbeitssprache
    - **Englisch**: Internationale Nutzer (Investoren, EU-Planer)
    - **Slowenisch**: Kärnten (verfassungsrechtlich geschützte Volksgruppe, Staatsvertrag 1955)
    - **Kroatisch**: Burgenland (Volksgruppengesetz 1976)
    - **Ungarisch**: Burgenland (Volksgruppengesetz 1976)
    """
    return {
        "sprachen": list(SPRACHEN_INFO.values()),
        "default": "de",
        "verwendung": "Accept-Language HTTP-Header oder ?sprache=en Query-Parameter",
        "beispiel": "GET /api/v1/i18n/locale/en",
    }


@router.get(
    "/locale/{sprache}",
    summary="Vollständiges Locale-Bundle",
    tags=["i18n"],
)
async def get_locale_bundle(
    sprache: str = Path(description="Sprachcode: de, en, sl, hr, hu"),
) -> Dict:
    """
    Gibt alle Übersetzungen für eine Sprache zurück.
    Nützlich für Frontend-Locale-Bundles (React, Vue, Angular).

    Format: { "schluessel": "übersetzter_text", ... }
    """
    if sprache not in SPRACHEN_INFO:
        raise HTTPException(
            status_code=404,
            detail=f"Sprache '{sprache}' nicht unterstützt. Verfügbar: {list(SPRACHEN_INFO)}",
        )
    bundle = get_alle_uebersetzungen(sprache)
    info = SPRACHEN_INFO[sprache]
    return {
        "sprache": sprache,
        "name_native": info["name_native"],
        "status": info["status"],
        "eintraege": len(bundle),
        "bundle": bundle,
    }


@router.get(
    "/{schluessel}",
    summary="Einzelne Übersetzung abrufen",
    tags=["i18n"],
)
async def get_uebersetzung(
    schluessel: str = Path(description="Übersetzungsschlüssel, z.B. 'compliance_ok'"),
    sprache: str = Query(default="de", description="Sprachcode: de, en, sl, hr, hu"),
    accept_language: Optional[str] = Header(default=None, alias="Accept-Language"),
) -> Dict:
    """
    Gibt die Übersetzung eines einzelnen Schlüssels zurück.

    Sprachpriorität:
    1. ?sprache= Query-Parameter
    2. Accept-Language HTTP-Header
    3. Fallback: Deutsch
    """
    # Sprache aus Query-Parameter oder Header bestimmen
    lang = sprache
    if lang == "de" and accept_language:
        detected = parse_accept_language(accept_language)
        lang = detected.value

    if lang not in SPRACHEN_INFO:
        raise HTTPException(
            status_code=400,
            detail=f"Sprache '{lang}' nicht unterstützt",
        )

    alle = get_alle_schluessel()
    if schluessel not in alle:
        raise HTTPException(
            status_code=404,
            detail=f"Schlüssel '{schluessel}' nicht gefunden",
        )

    return {
        "schluessel": schluessel,
        "sprache": lang,
        "text": t(schluessel, lang),
    }


@router.post(
    "/batch",
    summary="Mehrere Übersetzungen auf einmal abrufen",
    tags=["i18n"],
)
async def batch_uebersetzungen(req: BatchRequest) -> Dict:
    """
    Gibt mehrere Übersetzungen in einem Request zurück.
    Effizient für UI-Komponenten, die mehrere Labels benötigen.
    """
    if req.sprache not in SPRACHEN_INFO:
        raise HTTPException(
            status_code=400,
            detail=f"Sprache '{req.sprache}' nicht unterstützt",
        )

    result: Dict[str, str] = {}
    for key in req.schluessel:
        result[key] = t(key, req.sprache)

    return {
        "sprache": req.sprache,
        "count": len(result),
        "uebersetzungen": result,
    }
