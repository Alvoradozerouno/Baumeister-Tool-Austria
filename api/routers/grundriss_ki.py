"""
ORION Architekt-AT — KI-gestützte Grundrissoptimierung
=======================================================

Generiert und optimiert Grundrisse unter Berücksichtigung aller österreichischen
Bauordnungsanforderungen (OIB-RL, Mindestflächen, Barrierefreiheit je Bundesland).

Inspiriert von: Maket.ai, Architechtures, Sloyd.AI — aber vollständig AT-normkonform.

Endpoints:
  POST /api/v1/grundriss/generiere          — Neuen Grundriss generieren
  POST /api/v1/grundriss/optimiere          — Bestehenden Grundriss verbessern
  GET  /api/v1/grundriss/anforderungen/{bl} — Mindestanforderungen je Bundesland
  POST /api/v1/grundriss/validiere          — Normkonformität prüfen
"""

import logging
import math
import random
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field, field_validator

logger = logging.getLogger(__name__)
router = APIRouter()


# ---------------------------------------------------------------------------
# Österreichische Mindestanforderungen je Bundesland
# Quellen: OIB-RL 3, BO für Wien § 86 ff., Stmk BauG § 51 ff., etc.
# ---------------------------------------------------------------------------

MINDESTANFORDERUNGEN: Dict[str, Dict[str, Any]] = {
    "wien": {
        "raumhoehe_min_m": 2.50,
        "raumhoehe_altbau_m": 2.40,
        "wohnzimmer_min_m2": 14.0,
        "schlafzimmer_min_m2": 10.0,
        "kinderzimmer_min_m2": 8.0,
        "kueche_min_m2": 6.0,
        "bad_min_m2": 4.0,
        "wc_min_m2": 1.2,
        "vorraum_min_m2": 2.5,
        "abstellraum_min_m2": 2.0,
        "fensterflaecheanteile": 0.10,  # 10 % der Bodenfläche
        "belichtung_seitenlichtverhältnis": 0.10,
        "barrierefreiheit_pflicht_ab_wohneinheiten": 3,
        "aufzug_ab_geschosse": 6,
        "quellen": ["BO Wien § 86-92", "OIB-RL 3", "OIB-RL 4"],
    },
    "steiermark": {
        "raumhoehe_min_m": 2.50,
        "wohnzimmer_min_m2": 12.0,
        "schlafzimmer_min_m2": 8.0,
        "kinderzimmer_min_m2": 8.0,
        "kueche_min_m2": 6.0,
        "bad_min_m2": 4.0,
        "wc_min_m2": 1.2,
        "vorraum_min_m2": 2.0,
        "abstellraum_min_m2": 2.0,
        "fensterflaecheanteile": 0.10,
        "barrierefreiheit_pflicht_ab_wohneinheiten": 3,
        "aufzug_ab_geschosse": 4,
        "quellen": ["Stmk BauG § 51-56", "OIB-RL 3", "OIB-RL 4"],
    },
    "tirol": {
        "raumhoehe_min_m": 2.50,
        "wohnzimmer_min_m2": 12.0,
        "schlafzimmer_min_m2": 10.0,
        "kinderzimmer_min_m2": 8.0,
        "kueche_min_m2": 5.0,
        "bad_min_m2": 4.0,
        "wc_min_m2": 1.2,
        "vorraum_min_m2": 2.0,
        "abstellraum_min_m2": 2.0,
        "fensterflaecheanteile": 0.125,  # 1/8
        "barrierefreiheit_pflicht_ab_wohneinheiten": 4,
        "aufzug_ab_geschosse": 4,
        "quellen": ["Tiroler BauO § 40 ff.", "OIB-RL 3", "OIB-RL 4"],
    },
    "salzburg": {
        "raumhoehe_min_m": 2.50,
        "wohnzimmer_min_m2": 12.0,
        "schlafzimmer_min_m2": 10.0,
        "kinderzimmer_min_m2": 8.0,
        "kueche_min_m2": 5.0,
        "bad_min_m2": 4.0,
        "wc_min_m2": 1.2,
        "vorraum_min_m2": 2.0,
        "abstellraum_min_m2": 2.0,
        "fensterflaecheanteile": 0.10,
        "barrierefreiheit_pflicht_ab_wohneinheiten": 4,
        "aufzug_ab_geschosse": 5,
        "quellen": ["Sbg BauTG § 38 ff.", "OIB-RL 3", "OIB-RL 4"],
    },
    "niederoesterreich": {
        "raumhoehe_min_m": 2.50,
        "wohnzimmer_min_m2": 12.0,
        "schlafzimmer_min_m2": 10.0,
        "kinderzimmer_min_m2": 8.0,
        "kueche_min_m2": 6.0,
        "bad_min_m2": 4.0,
        "wc_min_m2": 1.2,
        "vorraum_min_m2": 2.0,
        "abstellraum_min_m2": 2.0,
        "fensterflaecheanteile": 0.10,
        "barrierefreiheit_pflicht_ab_wohneinheiten": 4,
        "aufzug_ab_geschosse": 5,
        "quellen": ["NÖ BauO 2014 § 52 ff.", "OIB-RL 3", "OIB-RL 4"],
    },
    "oberoesterreich": {
        "raumhoehe_min_m": 2.40,
        "wohnzimmer_min_m2": 12.0,
        "schlafzimmer_min_m2": 10.0,
        "kinderzimmer_min_m2": 8.0,
        "kueche_min_m2": 5.0,
        "bad_min_m2": 3.5,
        "wc_min_m2": 1.2,
        "vorraum_min_m2": 2.0,
        "abstellraum_min_m2": 1.5,
        "fensterflaecheanteile": 0.125,
        "barrierefreiheit_pflicht_ab_wohneinheiten": 4,
        "aufzug_ab_geschosse": 5,
        "quellen": ["OÖ BauTG § 3 ff.", "OIB-RL 3", "OIB-RL 4"],
    },
    "kaernten": {
        "raumhoehe_min_m": 2.50,
        "wohnzimmer_min_m2": 12.0,
        "schlafzimmer_min_m2": 10.0,
        "kinderzimmer_min_m2": 8.0,
        "kueche_min_m2": 6.0,
        "bad_min_m2": 4.0,
        "wc_min_m2": 1.2,
        "vorraum_min_m2": 2.0,
        "abstellraum_min_m2": 2.0,
        "fensterflaecheanteile": 0.10,
        "barrierefreiheit_pflicht_ab_wohneinheiten": 4,
        "aufzug_ab_geschosse": 5,
        "quellen": ["Kärntner BauO § 44 ff.", "OIB-RL 3", "OIB-RL 4"],
    },
    "burgenland": {
        "raumhoehe_min_m": 2.50,
        "wohnzimmer_min_m2": 12.0,
        "schlafzimmer_min_m2": 10.0,
        "kinderzimmer_min_m2": 8.0,
        "kueche_min_m2": 5.0,
        "bad_min_m2": 4.0,
        "wc_min_m2": 1.2,
        "vorraum_min_m2": 2.0,
        "abstellraum_min_m2": 1.5,
        "fensterflaecheanteile": 0.10,
        "barrierefreiheit_pflicht_ab_wohneinheiten": 4,
        "aufzug_ab_geschosse": 5,
        "quellen": ["Bgld BauG § 40 ff.", "OIB-RL 3", "OIB-RL 4"],
    },
    "vorarlberg": {
        "raumhoehe_min_m": 2.50,
        "wohnzimmer_min_m2": 12.0,
        "schlafzimmer_min_m2": 10.0,
        "kinderzimmer_min_m2": 8.0,
        "kueche_min_m2": 5.0,
        "bad_min_m2": 4.0,
        "wc_min_m2": 1.2,
        "vorraum_min_m2": 2.0,
        "abstellraum_min_m2": 2.0,
        "fensterflaecheanteile": 0.125,
        "barrierefreiheit_pflicht_ab_wohneinheiten": 3,
        "aufzug_ab_geschosse": 4,
        "quellen": ["Vbg BauG § 38 ff.", "OIB-RL 3", "OIB-RL 4"],
    },
}

# Alias-Normalisierung
_BL_ALIAS: Dict[str, str] = {
    "noe": "niederoesterreich",
    "niederösterreich": "niederoesterreich",
    "ooe": "oberoesterreich",
    "oberösterreich": "oberoesterreich",
    "stmk": "steiermark",
    "ktn": "kaernten",
    "kärnten": "kaernten",
    "bgld": "burgenland",
    "vbg": "vorarlberg",
    "sbg": "salzburg",
}


def _normiere_bl(bl: str) -> str:
    key = bl.lower().strip()
    return _BL_ALIAS.get(key, key)


# ---------------------------------------------------------------------------
# Pydantic-Modelle
# ---------------------------------------------------------------------------


class RaumTyp(str, Enum):
    WOHNZIMMER = "wohnzimmer"
    SCHLAFZIMMER = "schlafzimmer"
    KINDERZIMMER = "kinderzimmer"
    KUECHE = "kueche"
    BAD = "bad"
    WC = "wc"
    VORRAUM = "vorraum"
    ABSTELLRAUM = "abstellraum"
    BUERO = "buero"
    ESSBEREICH = "essbereich"
    HOBBYRAUM = "hobbyraum"
    GARAGE = "garage"


class NutzungsTyp(str, Enum):
    WOHNEN = "wohnen"
    BUERO = "buero"
    GEWERBE = "gewerbe"
    GEMISCHT = "gemischt"


class OptimierungsZiel(str, Enum):
    FLAECHE = "flaeche"           # Kompaktheit maximieren
    BELICHTUNG = "belichtung"     # Tageslicht maximieren
    BARRIEREFREIHEIT = "barrierefreiheit"  # Rollstuhl optimiert
    ENERGIEEFFIZIENZ = "energieeffizienz"  # A/V-Verhältnis minimieren
    KOSTEN = "kosten"             # Baukosten minimieren
    KOMFORT = "komfort"           # Großzügige Raumgrößen


class Raum(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    name: str
    typ: RaumTyp
    flaeche_m2: float = Field(gt=0)
    breite_m: Optional[float] = None
    tiefe_m: Optional[float] = None
    stockwerk: int = Field(default=0, ge=0)
    ausrichtung: Optional[str] = None  # "N", "S", "O", "W", "NW", etc.
    tageslicht_erforderlich: bool = True


class GrundrissGenerierungRequest(BaseModel):
    """Anfrage zur KI-basierten Grundrissgenerierung"""

    model_config = ConfigDict(use_enum_values=True)

    bundesland: str = Field(default="wien", description="Österreichisches Bundesland")
    nutzung: NutzungsTyp = Field(default=NutzungsTyp.WOHNEN)
    ziel: OptimierungsZiel = Field(default=OptimierungsZiel.KOMFORT)
    geschosse: int = Field(default=1, ge=1, le=10)
    grundstueck_breite_m: float = Field(default=12.0, gt=0)
    grundstueck_tiefe_m: float = Field(default=14.0, gt=0)
    anzahl_bewohner: int = Field(default=3, ge=1, le=20)
    anzahl_schlafzimmer: int = Field(default=2, ge=1, le=10)
    barrierefreiheit: bool = Field(default=False)
    keller: bool = Field(default=False)
    terrasse: bool = Field(default=True)
    carport_oder_garage: bool = Field(default=False)
    zielflaeche_netto_m2: Optional[float] = Field(
        default=None, description="Gewünschte Nettofläche (optional)"
    )
    budget_eur: Optional[float] = Field(default=None, description="Baukostenbudget (optional)")

    @field_validator("bundesland")
    @classmethod
    def validate_bundesland(cls, v: str) -> str:
        normalized = _normiere_bl(v)
        if normalized not in MINDESTANFORDERUNGEN:
            raise ValueError(
                f"Unbekanntes Bundesland '{v}'. Gültig: {list(MINDESTANFORDERUNGEN)}"
            )
        return normalized


class GrundrissOptimierungRequest(BaseModel):
    """Anfrage zur Optimierung eines bestehenden Grundrisses"""

    model_config = ConfigDict(use_enum_values=True)

    bundesland: str = Field(default="wien")
    raeume: List[Raum] = Field(min_length=1)
    ziel: OptimierungsZiel = Field(default=OptimierungsZiel.FLAECHE)
    barrierefreiheit: bool = Field(default=False)

    @field_validator("bundesland")
    @classmethod
    def validate_bundesland(cls, v: str) -> str:
        normalized = _normiere_bl(v)
        if normalized not in MINDESTANFORDERUNGEN:
            raise ValueError(f"Unbekanntes Bundesland '{v}'")
        return normalized


class GrundrissValidierungRequest(BaseModel):
    """Anfrage zur Normkonformitätsprüfung eines Grundrisses"""

    model_config = ConfigDict(use_enum_values=True)

    bundesland: str = Field(default="wien")
    raeume: List[Raum] = Field(min_length=1)
    anzahl_wohneinheiten: int = Field(default=1, ge=1)
    geschosse: int = Field(default=1, ge=1)

    @field_validator("bundesland")
    @classmethod
    def validate_bundesland(cls, v: str) -> str:
        return _normiere_bl(v)


class RaumVorschlag(BaseModel):
    name: str
    typ: str
    flaeche_m2: float
    breite_m: float
    tiefe_m: float
    stockwerk: int
    ausrichtung: str
    tageslicht_erforderlich: bool = True
    normkonform: bool
    min_flaeche_m2: float
    hinweis: Optional[str] = None


class GrundrissErgebnis(BaseModel):
    bundesland: str
    nutzung: str
    ziel: str
    raeume: List[RaumVorschlag]
    gesamtflaeche_netto_m2: float
    gesamtflaeche_bgf_m2: float
    a_v_verhaeltnis: float
    geschosse: int
    barrierefreiheit_erfuellt: bool
    normkonformitaet_pct: float
    optimierungshinweise: List[str]
    ki_score: float  # 0–100
    quellen: List[str]


class ValidierungsErgebnis(BaseModel):
    bundesland: str
    normkonform: bool
    verstösse: List[Dict[str, Any]]
    warnungen: List[Dict[str, Any]]
    empfehlungen: List[str]
    score_pct: float
    quellen: List[str]


# ---------------------------------------------------------------------------
# KI-Logik: Grundrissgenerierung
# ---------------------------------------------------------------------------


def _berechne_raumgroessen(
    req: GrundrissGenerierungRequest,
    anforderungen: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """
    Generiert Raumgrößen basierend auf Bewohnerzahl, Bundesland-Mindestanforderungen
    und dem gewählten Optimierungsziel.

    Algorithmus:
    1. Pflichtanforderungen aus der Bauordnung als Untergrenze setzen
    2. Komfort-/Effizienz-Faktor je nach OptimierungsZiel anwenden
    3. A/V-Verhältnis für Energieeffizienz berücksichtigen
    """
    ziel = req.ziel
    n = req.anzahl_bewohner

    # Skalierungsfaktoren je Optimierungsziel
    faktor: Dict[str, float] = {
        OptimierungsZiel.FLAECHE: 1.0,
        OptimierungsZiel.BELICHTUNG: 1.15,
        OptimierungsZiel.BARRIEREFREIHEIT: 1.20,
        OptimierungsZiel.ENERGIEEFFIZIENZ: 0.95,
        OptimierungsZiel.KOSTEN: 0.90,
        OptimierungsZiel.KOMFORT: 1.30,
    }
    f = faktor.get(ziel, 1.0)

    # Barrierefreiheit-Bonus
    bf = 1.20 if req.barrierefreiheit else 1.0

    raeume: List[Dict[str, Any]] = []

    def _add(
        name: str,
        typ: str,
        min_m2: float,
        extra_m2: float = 0.0,
        stockwerk: int = 0,
        ausrichtung: str = "S",
        tageslicht: bool = True,
    ) -> None:
        flaeche = max(min_m2, (min_m2 + extra_m2) * f * (bf if typ in ("bad", "wc") else 1.0))
        # Seitenverhältnis: Goldener Schnitt ~1.618 als Richtwert
        ratio = 1.4
        tiefe = math.sqrt(flaeche / ratio)
        breite = flaeche / tiefe
        raeume.append(
            {
                "name": name,
                "typ": typ,
                "flaeche_m2": round(flaeche, 1),
                "breite_m": round(breite, 2),
                "tiefe_m": round(tiefe, 2),
                "stockwerk": stockwerk,
                "ausrichtung": ausrichtung,
                "tageslicht_erforderlich": tageslicht,
                "min_flaeche_m2": min_m2,
                "normkonform": flaeche >= min_m2,
                "hinweis": None,
            }
        )

    # Eingangsgeschoß (EG)
    _add("Vorraum/Eingang", "vorraum", anforderungen["vorraum_min_m2"], 1.0, stockwerk=0, ausrichtung="N", tageslicht=False)
    _add("WC Gast", "wc", anforderungen["wc_min_m2"], 0.3, stockwerk=0, ausrichtung="N", tageslicht=False)

    # Wohnbereich
    if n <= 2:
        wz_extra = 4.0
    elif n <= 4:
        wz_extra = 8.0
    else:
        wz_extra = 12.0
    _add("Wohnzimmer", "wohnzimmer", anforderungen["wohnzimmer_min_m2"], wz_extra, stockwerk=0, ausrichtung="S")

    # Küche / Essbereich
    _add("Küche", "kueche", anforderungen["kueche_min_m2"], 2.0, stockwerk=0, ausrichtung="W")

    # Schlafzimmer (im OG bei Mehrgeschoßig, sonst EG)
    for i in range(req.anzahl_schlafzimmer):
        stw = 1 if req.geschosse > 1 else 0
        if i == 0:
            extra_sz = 4.0 if n > 2 else 2.0
            _add("Schlafzimmer Eltern", "schlafzimmer", anforderungen["schlafzimmer_min_m2"], extra_sz, stockwerk=stw, ausrichtung="O")
        else:
            extra_kz = 1.0
            _add(f"Kinderzimmer {i}", "kinderzimmer", anforderungen["kinderzimmer_min_m2"], extra_kz, stockwerk=stw, ausrichtung="S")

    # Bad (OG bei Mehrgeschoßig)
    stw_bad = 1 if req.geschosse > 1 else 0
    _add("Bad", "bad", anforderungen["bad_min_m2"], 2.0, stockwerk=stw_bad, ausrichtung="N", tageslicht=False)

    # Abstellraum
    _add("Abstellraum", "abstellraum", anforderungen["abstellraum_min_m2"], 1.0, stockwerk=0, ausrichtung="N", tageslicht=False)

    # Barrierefreiheits-Anpassungen
    if req.barrierefreiheit:
        for r in raeume:
            if r["typ"] == "wc":
                r["flaeche_m2"] = max(r["flaeche_m2"], 4.0)  # Rollstuhl: mind. 4 m²
                r["hinweis"] = "Rollstuhlgereicht: mind. 4 m², Drehraumø 150 cm erforderlich (OIB-RL 4)"
            if r["typ"] == "bad":
                r["flaeche_m2"] = max(r["flaeche_m2"], 6.5)
                r["hinweis"] = "Rollstuhlgerecht: mind. 6,5 m², unterfahrbare Waschbecken, Haltegriffe (OIB-RL 4)"
            if r["typ"] == "vorraum":
                r["flaeche_m2"] = max(r["flaeche_m2"], 4.5)
                r["hinweis"] = "Bewegungsfläche mind. 150×150 cm (OIB-RL 4 § 5)"

    return raeume


def _berechne_a_v(
    netto_m2: float, geschosse: int, breite: float, tiefe: float
) -> float:
    """Vereinfachtes A/V-Verhältnis (kompaktere Form = bessere Energieeffizienz)"""
    h = 2.70 * geschosse
    v = breite * tiefe * h
    # Hüllfläche: 2×(B×T) + 2×(B+T)×H + optional Dach
    a = 2 * (breite * tiefe) + 2 * (breite + tiefe) * h
    if v > 0:
        return round(a / v, 3)
    return 0.0


def _ki_score(
    raeume: List[Dict],
    netto_m2: float,
    a_v: float,
    ziel: str,
    barrierefreiheit_ok: bool,
) -> float:
    """
    Berechnet einen KI-Score 0–100 für die Grundrissqualität.
    Gewichtung abhängig vom Optimierungsziel.
    """
    normkonform = sum(1 for r in raeume if r["normkonform"]) / len(raeume) if raeume else 0
    flaechen_score = min(1.0, netto_m2 / max(netto_m2 * 1.2, 1))
    av_score = max(0, 1.0 - (a_v - 0.3) / 0.7)  # optimales A/V ~0.3–0.5

    gewichte: Dict[str, Dict[str, float]] = {
        OptimierungsZiel.FLAECHE: {"norm": 0.4, "flaeche": 0.4, "av": 0.2},
        OptimierungsZiel.ENERGIEEFFIZIENZ: {"norm": 0.3, "flaeche": 0.1, "av": 0.6},
        OptimierungsZiel.BARRIEREFREIHEIT: {"norm": 0.5, "flaeche": 0.3, "av": 0.2},
        OptimierungsZiel.KOSTEN: {"norm": 0.3, "flaeche": 0.5, "av": 0.2},
        OptimierungsZiel.KOMFORT: {"norm": 0.5, "flaeche": 0.4, "av": 0.1},
        OptimierungsZiel.BELICHTUNG: {"norm": 0.4, "flaeche": 0.3, "av": 0.3},
    }
    gew = gewichte.get(ziel, {"norm": 0.4, "flaeche": 0.3, "av": 0.3})
    score = (normkonform * gew["norm"] + flaechen_score * gew["flaeche"] + av_score * gew["av"]) * 100
    if not barrierefreiheit_ok:
        score *= 0.9
    return round(min(100.0, max(0.0, score)), 1)


def _generiere_hinweise(
    raeume: List[Dict],
    anforderungen: Dict,
    ziel: str,
    a_v: float,
    barrierefreiheit: bool,
    geschosse: int,
) -> List[str]:
    hinweise: List[str] = []

    verstösse = [r for r in raeume if not r["normkonform"]]
    if verstösse:
        for v in verstösse:
            hinweise.append(
                f"⚠️ {v['name']}: {v['flaeche_m2']} m² < Mindestfläche {v['min_flaeche_m2']} m² laut Bauordnung"
            )

    if a_v > 0.8:
        hinweise.append(f"💡 Kompakteren Gebäudekörper wählen — A/V-Verhältnis {a_v:.2f} ist ungünstig für OIB-RL 6")
    elif a_v < 0.4:
        hinweise.append(f"✅ Ausgezeichnetes A/V-Verhältnis {a_v:.2f} — ideal für Energieeffizienz (OIB-RL 6)")

    if ziel == OptimierungsZiel.BARRIEREFREIHEIT or barrierefreiheit:
        hinweise.append("♿ Türbreiten: mind. 90 cm lichte Breite (OIB-RL 4 § 4.3)")
        hinweise.append(f"♿ Aufzug prüfen: ab {anforderungen['aufzug_ab_geschosse']} Geschoßen Pflicht (lokale BO)")

    if ziel == OptimierungsZiel.BELICHTUNG:
        hinweise.append(f"☀️ Fensterflächen: mind. {anforderungen['fensterflaecheanteile'] * 100:.0f}% der Bodenfläche pro Aufenthaltsraum (lokale BO)")
        hinweise.append("☀️ Südausrichtung von Wohn- und Schlafräumen maximiert passive Solargewinne")

    if geschosse >= anforderungen.get("aufzug_ab_geschosse", 5):
        hinweise.append(
            "🏗️ Aufzugspflicht: Ab {} Geschoßen ist ein barrierefreier Aufzug erforderlich (lokale BO)".format(anforderungen["aufzug_ab_geschosse"])
        )

    return hinweise


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get(
    "/anforderungen/{bundesland}",
    summary="Mindestanforderungen je Bundesland",
    tags=["grundriss-ki"],
)
async def get_anforderungen(bundesland: str) -> Dict[str, Any]:
    """
    Liefert die Mindestanforderungen an Raumgrößen und -höhen
    gemäß der jeweiligen österreichischen Landesbauordnung.
    """
    bl = _normiere_bl(bundesland)
    if bl not in MINDESTANFORDERUNGEN:
        raise HTTPException(
            status_code=404,
            detail=f"Unbekanntes Bundesland '{bundesland}'. Verfügbar: {list(MINDESTANFORDERUNGEN)}",
        )
    return {
        "bundesland": bl,
        "anforderungen": MINDESTANFORDERUNGEN[bl],
        "hinweis": "Werte gem. OIB-RL 3 + jeweiliger Landesbauordnung (Stand 2025). Immer lokale Behörde konsultieren.",
    }


@router.post(
    "/generiere",
    response_model=GrundrissErgebnis,
    summary="KI-Grundriss generieren",
    tags=["grundriss-ki"],
)
async def generiere_grundriss(req: GrundrissGenerierungRequest) -> GrundrissErgebnis:
    """
    Generiert einen normkonformen Grundriss basierend auf österreichischen BO-Anforderungen.

    Die KI berücksichtigt:
    - Mindestflächen und Raumhöhen gem. Landesbauordnung
    - OIB-RL 3 (Hygiene/Gesundheit) & OIB-RL 4 (Barrierefreiheit)
    - A/V-Verhältnis für OIB-RL 6 (Energieeffizienz)
    - Bewohnerzahl, Schlafzimmeranzahl, Optimierungsziel
    """
    anforderungen = MINDESTANFORDERUNGEN[req.bundesland]

    raeume = _berechne_raumgroessen(req, anforderungen)

    netto_m2 = sum(r["flaeche_m2"] for r in raeume)
    bgf_m2 = round(netto_m2 * 1.20, 1)  # +20% Konstruktion/Erschließung

    a_v = _berechne_a_v(
        netto_m2=netto_m2,
        geschosse=req.geschosse,
        breite=req.grundstueck_breite_m,
        tiefe=req.grundstueck_tiefe_m,
    )

    bf_ok = req.barrierefreiheit  # vereinfacht: wenn gewünscht → ja
    normkonform_count = sum(1 for r in raeume if r["normkonform"])
    norm_pct = round(normkonform_count / len(raeume) * 100, 1) if raeume else 0.0

    hinweise = _generiere_hinweise(raeume, anforderungen, req.ziel, a_v, req.barrierefreiheit, req.geschosse)

    ki = _ki_score(raeume, netto_m2, a_v, req.ziel, bf_ok)

    vorschlaege = [
        RaumVorschlag(
            name=r["name"],
            typ=r["typ"],
            flaeche_m2=r["flaeche_m2"],
            breite_m=r["breite_m"],
            tiefe_m=r["tiefe_m"],
            stockwerk=r["stockwerk"],
            ausrichtung=r["ausrichtung"],
            tageslicht_erforderlich=r.get("tageslicht_erforderlich", True),
            normkonform=r["normkonform"],
            min_flaeche_m2=r["min_flaeche_m2"],
            hinweis=r.get("hinweis"),
        )
        for r in raeume
    ]

    return GrundrissErgebnis(
        bundesland=req.bundesland,
        nutzung=req.nutzung if isinstance(req.nutzung, str) else req.nutzung.value,
        ziel=req.ziel if isinstance(req.ziel, str) else req.ziel.value,
        raeume=vorschlaege,
        gesamtflaeche_netto_m2=round(netto_m2, 1),
        gesamtflaeche_bgf_m2=bgf_m2,
        a_v_verhaeltnis=a_v,
        geschosse=req.geschosse,
        barrierefreiheit_erfuellt=bf_ok,
        normkonformitaet_pct=norm_pct,
        optimierungshinweise=hinweise,
        ki_score=ki,
        quellen=anforderungen["quellen"] + ["OIB-RL 6:2025", "OIB-RL 4:2019"],
    )


@router.post(
    "/optimiere",
    response_model=GrundrissErgebnis,
    summary="Bestehenden Grundriss optimieren",
    tags=["grundriss-ki"],
)
async def optimiere_grundriss(req: GrundrissOptimierungRequest) -> GrundrissErgebnis:
    """
    Optimiert einen bestehenden Grundriss (als Raumliste) nach österreichischen Anforderungen.

    Die KI:
    1. Prüft Normkonformität gegen lokale BO
    2. Schlägt Flächenumverteilungen vor
    3. Gibt Barrierefreiheitshinweise (OIB-RL 4)
    """
    anforderungen = MINDESTANFORDERUNGEN[req.bundesland]

    MIN_MAP: Dict[str, str] = {
        "wohnzimmer": "wohnzimmer_min_m2",
        "schlafzimmer": "schlafzimmer_min_m2",
        "kinderzimmer": "kinderzimmer_min_m2",
        "kueche": "kueche_min_m2",
        "bad": "bad_min_m2",
        "wc": "wc_min_m2",
        "vorraum": "vorraum_min_m2",
        "abstellraum": "abstellraum_min_m2",
    }

    raeume_opt: List[Dict[str, Any]] = []
    for raum in req.raeume:
        typ = raum.typ if isinstance(raum.typ, str) else raum.typ.value
        min_key = MIN_MAP.get(typ)
        min_m2 = anforderungen.get(min_key, 0.0) if min_key else 0.0

        normkonform = raum.flaeche_m2 >= min_m2
        hinweis = None
        if not normkonform:
            hinweis = (
                f"Zu klein: {raum.flaeche_m2} m² < Mindestfläche {min_m2} m² "
                f"laut {anforderungen['quellen'][0]}"
            )

        # Barrierefreiheit: WC-Mindestfläche erhöhen
        if req.barrierefreiheit and typ == "wc" and raum.flaeche_m2 < 4.0:
            hinweis = "Für Rollstuhl: mind. 4 m², Drehraumø 150 cm (OIB-RL 4)"

        # Abmessungen ableiten falls nicht angegeben
        breite = raum.breite_m if raum.breite_m else round(math.sqrt(raum.flaeche_m2 / 1.4), 2)
        tiefe = raum.tiefe_m if raum.tiefe_m else round(raum.flaeche_m2 / breite, 2)

        raeume_opt.append(
            {
                "name": raum.name,
                "typ": typ,
                "flaeche_m2": raum.flaeche_m2,
                "breite_m": breite,
                "tiefe_m": tiefe,
                "stockwerk": raum.stockwerk,
                "ausrichtung": raum.ausrichtung or "S",
                "min_flaeche_m2": min_m2,
                "normkonform": normkonform,
                "hinweis": hinweis,
            }
        )

    netto_m2 = sum(r["flaeche_m2"] for r in raeume_opt)
    bgf_m2 = round(netto_m2 * 1.20, 1)
    max_stw = max((r["stockwerk"] for r in raeume_opt), default=0)
    a_v = _berechne_a_v(netto_m2=netto_m2, geschosse=max_stw + 1, breite=12, tiefe=10)
    bf_ok = req.barrierefreiheit
    norm_pct = round(sum(1 for r in raeume_opt if r["normkonform"]) / len(raeume_opt) * 100, 1)
    hinweise = _generiere_hinweise(raeume_opt, anforderungen, req.ziel, a_v, req.barrierefreiheit, max_stw + 1)
    ki = _ki_score(raeume_opt, netto_m2, a_v, req.ziel, bf_ok)

    vorschlaege = [
        RaumVorschlag(
            name=r["name"],
            typ=r["typ"],
            flaeche_m2=r["flaeche_m2"],
            breite_m=r["breite_m"],
            tiefe_m=r["tiefe_m"],
            stockwerk=r["stockwerk"],
            ausrichtung=r["ausrichtung"],
            tageslicht_erforderlich=r.get("tageslicht_erforderlich", True),
            normkonform=r["normkonform"],
            min_flaeche_m2=r["min_flaeche_m2"],
            hinweis=r.get("hinweis"),
        )
        for r in raeume_opt
    ]

    return GrundrissErgebnis(
        bundesland=req.bundesland,
        nutzung="wohnen",
        ziel=req.ziel if isinstance(req.ziel, str) else req.ziel.value,
        raeume=vorschlaege,
        gesamtflaeche_netto_m2=round(netto_m2, 1),
        gesamtflaeche_bgf_m2=bgf_m2,
        a_v_verhaeltnis=a_v,
        geschosse=max_stw + 1,
        barrierefreiheit_erfuellt=bf_ok,
        normkonformitaet_pct=norm_pct,
        optimierungshinweise=hinweise,
        ki_score=ki,
        quellen=anforderungen["quellen"] + ["OIB-RL 4:2019"],
    )


@router.post(
    "/validiere",
    response_model=ValidierungsErgebnis,
    summary="Grundriss auf Normkonformität prüfen",
    tags=["grundriss-ki"],
)
async def validiere_grundriss(req: GrundrissValidierungRequest) -> ValidierungsErgebnis:
    """
    Prüft einen gegebenen Grundriss auf Konformität mit der lokalen Bauordnung.

    Geprüfte Normen:
    - Mindestflächen und Raumhöhen (lokale BO)
    - OIB-RL 3: Hygiene und Gesundheit
    - OIB-RL 4: Barrierefreiheit (ab definierten Wohneinheiten)
    """
    bl_key = _normiere_bl(req.bundesland)
    if bl_key not in MINDESTANFORDERUNGEN:
        raise HTTPException(status_code=404, detail=f"Bundesland '{req.bundesland}' nicht gefunden")

    anforderungen = MINDESTANFORDERUNGEN[bl_key]

    MIN_MAP: Dict[str, Tuple[str, str]] = {
        "wohnzimmer": ("wohnzimmer_min_m2", "OIB-RL 3 / lokale BO"),
        "schlafzimmer": ("schlafzimmer_min_m2", "OIB-RL 3 / lokale BO"),
        "kinderzimmer": ("kinderzimmer_min_m2", "OIB-RL 3 / lokale BO"),
        "kueche": ("kueche_min_m2", "OIB-RL 3 / lokale BO"),
        "bad": ("bad_min_m2", "OIB-RL 3 / lokale BO"),
        "wc": ("wc_min_m2", "OIB-RL 3 / lokale BO"),
        "vorraum": ("vorraum_min_m2", "OIB-RL 3 / lokale BO"),
        "abstellraum": ("abstellraum_min_m2", "OIB-RL 3 / lokale BO"),
    }

    verstösse: List[Dict[str, Any]] = []
    warnungen: List[Dict[str, Any]] = []
    empfehlungen: List[str] = []

    for raum in req.raeume:
        typ = raum.typ if isinstance(raum.typ, str) else raum.typ.value
        if typ in MIN_MAP:
            min_key, quelle = MIN_MAP[typ]
            min_m2 = anforderungen.get(min_key, 0.0)
            if raum.flaeche_m2 < min_m2:
                verstösse.append(
                    {
                        "raum": raum.name,
                        "typ": typ,
                        "ist": raum.flaeche_m2,
                        "soll_min": min_m2,
                        "differenz": round(min_m2 - raum.flaeche_m2, 2),
                        "norm": quelle,
                        "bundesland_quelle": anforderungen["quellen"][0],
                    }
                )
            elif raum.flaeche_m2 < min_m2 * 1.1:
                warnungen.append(
                    {
                        "raum": raum.name,
                        "typ": typ,
                        "flaeche": raum.flaeche_m2,
                        "hinweis": f"Nur knapp über Mindestmaß ({min_m2} m²) — Pufferzone empfehlenswert",
                    }
                )

    # Barrierefreiheit prüfen
    bf_pflicht = (
        req.anzahl_wohneinheiten >= anforderungen["barrierefreiheit_pflicht_ab_wohneinheiten"]
    )
    if bf_pflicht:
        wc_raeume = [r for r in req.raeume if (r.typ if isinstance(r.typ, str) else r.typ.value) == "wc"]
        if not any(r.flaeche_m2 >= 4.0 for r in wc_raeume):
            verstösse.append(
                {
                    "raum": "WC (Barrierefreiheit)",
                    "typ": "wc",
                    "ist": min((r.flaeche_m2 for r in wc_raeume), default=0),
                    "soll_min": 4.0,
                    "differenz": 4.0,
                    "norm": "OIB-RL 4 § 5",
                    "bundesland_quelle": anforderungen["quellen"][0],
                }
            )
        empfehlungen.append(
            f"Ab {anforderungen['barrierefreiheit_pflicht_ab_wohneinheiten']} Wohneinheiten: "
            "mind. eine barrierefreie Wohneinheit pro Aufgang erforderlich (OIB-RL 4)"
        )

    # Aufzugspflicht prüfen
    if req.geschosse >= anforderungen["aufzug_ab_geschosse"]:
        empfehlungen.append(
            f"Ab {anforderungen['aufzug_ab_geschosse']} Geschoßen: Aufzug/barrierefreier Zugang erforderlich (lokale BO)"
        )

    score = max(0.0, 100.0 - len(verstösse) * 15.0 - len(warnungen) * 5.0)

    return ValidierungsErgebnis(
        bundesland=bl_key,
        normkonform=len(verstösse) == 0,
        verstösse=verstösse,
        warnungen=warnungen,
        empfehlungen=empfehlungen,
        score_pct=round(score, 1),
        quellen=anforderungen["quellen"] + ["OIB-RL 3:2019", "OIB-RL 4:2019"],
    )
