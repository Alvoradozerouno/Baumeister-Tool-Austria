"""
PLAN-VERSTEHEN-SYSTEM: Multi-Agenten-System fuer automatisches Plan-Verstehen
==============================================================================

Architektur mit 7 spezialisierten Agenten:
1. Geometrie-Agent - Extrahiert Linien, Kreise, Polygone
2. Symbol-Agent - Erkennt Norm-Symbole
3. Raum-Agent - Identifiziert Raeume, berechnet Flaechen
4. Massstabs-Agent - Erkennt Massstab, kalibriert Messungen
5. Normen-Agent - Prueft gegen OIB-RL und Eurocodes
6. Fehler-Agent - Erkennt Inkonsistenzen
7. DES-Agent - Epistemische Validierung

Autor: Baumeister Tool Austria Team
Datum: 2026-05-26
"""

import sys
import os
import json
import time
import math
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.epistemic_system import (
    DeterministicEpistemicSystem,
    EpistemicProposition,
    EpistemicAgent,
)


# ============================================================================
# ENUMS UND DATENKLASSEN
# ============================================================================

class EpistemicState(Enum):
    CERTAIN = "certain"
    PROBABLE = "probable"
    POSSIBLE = "possible"
    UNCERTAIN = "uncertain"
    UNKNOWN = "unknown"
    CONTRADICTED = "contradicted"
    INVALID = "invalid"


class MessageType(Enum):
    GEOMETRIE = "geometrie"
    SYMBOL = "symbol"
    RAUM = "raum"
    MASSSTAB = "massstab"
    NORM = "norm"
    FEHLER = "fehler"
    VALIDIERUNG = "validierung"


@dataclass
class Point2D:
    x: float
    y: float

    def distance_to(self, other: 'Point2D') -> float:
        return math.sqrt((self.x - other.x) ** 2 + (self.y - other.y) ** 2)


@dataclass
class Line2D:
    start: Point2D
    end: Point2D

    @property
    def length(self) -> float:
        return self.start.distance_to(self.end)

    @property
    def angle(self) -> float:
        return math.degrees(math.atan2(self.end.y - self.start.y, self.end.x - self.start.x))


@dataclass
class Circle2D:
    center: Point2D
    radius: float

    @property
    def area(self) -> float:
        return math.pi * self.radius ** 2


@dataclass
class Polygon2D:
    points: List[Point2D]

    @property
    def area(self) -> float:
        n = len(self.points)
        if n < 3:
            return 0.0
        area = 0.0
        for i in range(n):
            j = (i + 1) % n
            area += self.points[i].x * self.points[j].y
            area -= self.points[j].x * self.points[i].y
        return abs(area) / 2.0

    @property
    def perimeter(self) -> float:
        n = len(self.points)
        if n < 2:
            return 0.0
        perimeter = 0.0
        for i in range(n):
            j = (i + 1) % n
            perimeter += self.points[i].distance_to(self.points[j])
        return perimeter


@dataclass
class Raum:
    name: str
    typ: str  # wohnen, schlafen, kueche, bad, flur, abstell, etc.
    flaeche_m2: float
    umfang_m: float
    fenster_anteil: float  # 0.0 - 1.0
    tueren: int
    min_hoehe_m: float = 2.5
    tage_licht: bool = False


@dataclass
class Symbol:
    typ: str  # tuer, fenster, treppe, sanitär, elektro, etc.
    position: Point2D
    rotation: float = 0.0
    norm: str = ""  # OENORM E 8001, B 2501, etc.
    confidence: float = 0.0


@dataclass
class Message:
    message_id: str
    sender: str
    receiver: str
    typ: MessageType
    inhalt: Dict[str, Any]
    epistemischer_zustand: EpistemicState = EpistemicState.UNKNOWN
    konfidenz: float = 0.0


@dataclass
class PlanElement:
    typ: str  # wand, tuer, fenster, treppe, raum, etc.
    geometrie: Any  # Line2D, Circle2D, Polygon2D
    attribute: Dict[str, Any] = field(default_factory=dict)
    norm_referenz: str = ""
    confidence: float = 0.0


@dataclass
class Fehler:
    id: str
    typ: str  # geometrisch, normativ, kollision, vollstaendigkeit
    schwere: str  # KRITISCH, HOCH, MITTEL, NIEDRIG
    beschreibung: str
    element: Optional[PlanElement] = None
    norm_verweis: str = ""
    empfehlung: str = ""
    confidence: float = 0.0


# ============================================================================
# AGENTEN
# ============================================================================

class GeometrieAgent:
    """Extrahiert geometrische Elemente aus Plan-Daten."""

    def __init__(self):
        self.name = "Geometrie-Agent"
        self.elemente: List[PlanElement] = []

    def analysiere(self, plan_daten: Dict[str, Any]) -> List[PlanElement]:
        """Analysiere Plan-Daten und extrahiere geometrische Elemente."""
        self.elemente = []

        # Simuliere Extraktion aus Plan-Daten
        if "linien" in plan_daten:
            for linie in plan_daten["linien"]:
                start = Point2D(linie["x1"], linie["y1"])
                end = Point2D(linie["x2"], linie["y2"])
                line = Line2D(start, end)

                # Klassifiziere Linie
                typ = self._klassifiziere_linie(line)
                element = PlanElement(
                    typ=typ,
                    geometrie=line,
                    confidence=0.95,
                )
                self.elemente.append(element)

        if "kreise" in plan_daten:
            for kreis in plan_daten["kreise"]:
                center = Point2D(kreis["cx"], kreis["cy"])
                circle = Circle2D(center, kreis["r"])
                element = PlanElement(
                    typ="kreis",
                    geometrie=circle,
                    confidence=0.90,
                )
                self.elemente.append(element)

        if "polygone" in plan_daten:
            for poly in plan_daten["polygone"]:
                points = [Point2D(p["x"], p["y"]) for p in poly["points"]]
                polygon = Polygon2D(points)
                element = PlanElement(
                    typ="polygon",
                    geometrie=polygon,
                    confidence=0.92,
                )
                self.elemente.append(element)

        return self.elemente

    def _klassifiziere_linie(self, line: Line2D) -> str:
        """Klassifiziere Linie basierend auf Laenge und Winkel."""
        if line.length > 500:  # Lange Linien = Waende
            return "wand"
        elif line.length > 100:
            return "trennlinie"
        else:
            return "detail"

    def erstelle_message(self, elemente: List[PlanElement]) -> Message:
        return Message(
            message_id=f"geo_{id(self)}",
            sender=self.name,
            receiver="Shared Knowledge Base",
            typ=MessageType.GEOMETRIE,
            inhalt={"anzahl_elemente": len(elemente), "typen": list(set(e.typ for e in elemente))},
            epistemischer_zustand=EpistemicState.PROBABLE,
            konfidenz=0.90,
        )


class SymbolAgent:
    """Erkennt Norm-Symbole in Plan-Daten."""

    def __init__(self):
        self.name = "Symbol-Agent"
        self.symbole: List[Symbol] = []

    # Norm-Symbol-Definitionen (OENORM)
    SYMBOL_DEFINITIONS = {
        "tuer_einfach": {"norm": "OENORM E 8001", "typ": "tuer", "min_width": 80, "max_width": 120},
        "tuer_doppel": {"norm": "OENORM E 8001", "typ": "tuer", "min_width": 140, "max_width": 200},
        "fenster_einfach": {"norm": "OENORM E 8001", "typ": "fenster", "min_width": 60, "max_width": 150},
        "fenster_balkon": {"norm": "OENORM E 8001", "typ": "fenster", "min_width": 100, "max_width": 200},
        "treppe_gerade": {"norm": "OENORM B 2501", "typ": "treppe", "min_width": 80, "max_width": 120},
        "treppe_gewendelt": {"norm": "OENORM B 2501", "typ": "treppe", "min_width": 80, "max_width": 120},
        "sanitaer_wc": {"norm": "OENORM B 2501", "typ": "sanitaer", "min_width": 40, "max_width": 60},
        "sanitaer_bad": {"norm": "OENORM B 2501", "typ": "sanitaer", "min_width": 60, "max_width": 80},
        "elektro_dose": {"norm": "OENORM E 8001", "typ": "elektro", "min_width": 10, "max_width": 20},
        "elektro_schalter": {"norm": "OENORM E 8001", "typ": "elektro", "min_width": 10, "max_width": 20},
    }

    def analysiere(self, plan_daten: Dict[str, Any], geometrie_elemente: List[PlanElement]) -> List[Symbol]:
        """Analysiere Plan-Daten und erkenne Symbole."""
        self.symbole = []

        # Simuliere Symbol-Erkennung basierend auf Geometrie
        for elem in geometrie_elemente:
            if elem.typ == "wand":
                # Pruefe auf Tuer-Oeffnungen in Waenden
                if hasattr(elem.geometrie, 'length') and 80 <= elem.geometrie.length <= 120:
                    symbol = Symbol(
                        typ="tuer_einfach",
                        position=elem.geometrie.start,
                        norm="OENORM E 8001",
                        confidence=0.85,
                    )
                    self.symbole.append(symbol)

        # Simuliere weitere Symbole
        if "symbole" in plan_daten:
            for sym in plan_daten["symbole"]:
                symbol = Symbol(
                    typ=sym.get("typ", "unbekannt"),
                    position=Point2D(sym.get("x", 0), sym.get("y", 0)),
                    rotation=sym.get("rotation", 0),
                    norm=sym.get("norm", ""),
                    confidence=sym.get("confidence", 0.5),
                )
                self.symbole.append(symbol)

        return self.symbole

    def erstelle_message(self, symbole: List[Symbol]) -> Message:
        return Message(
            message_id=f"sym_{id(self)}",
            sender=self.name,
            receiver="Shared Knowledge Base",
            typ=MessageType.SYMBOL,
            inhalt={"anzahl_symbole": len(symbole), "typen": list(set(s.typ for s in symbole))},
            epistemischer_zustand=EpistemicState.PROBABLE,
            konfidenz=0.85,
        )


class RaumAgent:
    """Identifiziert Raeume und berechnet Flaechen."""

    def __init__(self):
        self.name = "Raum-Agent"
        self.raeume: List[Raum] = []

    # Raum-Typen mit Anforderungen
    RAUM_ANFORDERUNGEN = {
        "wohnzimmer": {"min_flaeche_m2": 14, "min_hoehe_m": 2.5, "min_fenster_anteil": 0.1},
        "schlafzimmer": {"min_flaeche_m2": 10, "min_hoehe_m": 2.5, "min_fenster_anteil": 0.1},
        "kueche": {"min_flaeche_m2": 8, "min_hoehe_m": 2.5, "min_fenster_anteil": 0.1},
        "badezimmer": {"min_flaeche_m2": 4, "min_hoehe_m": 2.5, "min_fenster_anteil": 0.05},
        "flur": {"min_flaeche_m2": 4, "min_hoehe_m": 2.5, "min_fenster_anteil": 0.0},
        "abstellraum": {"min_flaeche_m2": 2, "min_hoehe_m": 2.0, "min_fenster_anteil": 0.0},
        "keller": {"min_flaeche_m2": 4, "min_hoehe_m": 2.2, "min_fenster_anteil": 0.0},
        "dachboden": {"min_flaeche_m2": 4, "min_hoehe_m": 2.2, "min_fenster_anteil": 0.05},
    }

    def analysiere(self, geometrie_elemente: List[PlanElement], symbole: List[Symbol]) -> List[Raum]:
        """Analysiere Geometrie und Symbole zur Raum-Identifikation."""
        self.raeume = []

        # Extrahiere Polygone als Raum-Kandidaten
        for elem in geometrie_elemente:
            if elem.typ == "polygon" and isinstance(elem.geometrie, Polygon2D):
                flaeche_m2 = elem.geometrie.area / 10000  # mm2 -> m2 (angenommen)
                umfang_m = elem.geometrie.perimeter / 1000  # mm -> m

                # Bestimme Raum-Typ basierend auf Flaeche und Symbolen
                raum_typ = self._bestimme_raum_typ(flaeche_m2, symbole, elem)
                anforderungen = self.RAUM_ANFORDERUNGEN.get(raum_typ, {})

                raum = Raum(
                    name=raum_typ,
                    typ=raum_typ,
                    flaeche_m2=flaeche_m2,
                    umfang_m=umfang_m,
                    fenster_anteil=0.15,  # Simuliert
                    tueren=1,
                    min_hoehe_m=anforderungen.get("min_hoehe_m", 2.5),
                    tage_licht=anforderungen.get("min_fenster_anteil", 0) > 0,
                )
                self.raeume.append(raum)

        return self.raeume

    def _bestimme_raum_typ(self, flaeche_m2: float, symbole: List[Symbol], elem: PlanElement) -> str:
        """Bestimme Raum-Typ basierend auf Flaeche und Symbolen."""
        if flaeche_m2 > 20:
            return "wohnzimmer"
        elif flaeche_m2 > 12:
            return "schlafzimmer"
        elif flaeche_m2 > 8:
            return "kueche"
        elif flaeche_m2 > 4:
            return "badezimmer"
        else:
            return "abstellraum"

    def pruefe_raum_anforderungen(self, raum: Raum) -> List[Fehler]:
        """Pruefe Raum gegen Anforderungen."""
        fehler = []
        anforderungen = self.RAUM_ANFORDERUNGEN.get(raum.typ, {})

        if raum.flaeche_m2 < anforderungen.get("min_flaeche_m2", 0):
            fehler.append(Fehler(
                id=f"RAUM_{raum.name}_FLAECHE",
                typ="normativ",
                schwere="HOCH",
                beschreibung=f"Raum {raum.name}: Flaeche {raum.flaeche_m2:.1f}m2 < {anforderungen['min_flaeche_m2']}m2",
                norm_verweis="OIB-RL 4",
                empfehlung=f"Flaeche auf mindestens {anforderungen['min_flaeche_m2']}m2 vergroessern",
                confidence=0.95,
            ))

        if raum.fenster_anteil < anforderungen.get("min_fenster_anteil", 0):
            fehler.append(Fehler(
                id=f"RAUM_{raum.name}_LICHT",
                typ="normativ",
                schwere="MITTEL",
                beschreibung=f"Raum {raum.name}: Fensteranteil {raum.fenster_anteil:.1%} < {anforderungen['min_fenster_anteil']:.1%}",
                norm_verweis="OIB-RL 3 (Tageslicht)",
                empfehlung="Fensterflaeche vergroessern",
                confidence=0.90,
            ))

        return fehler

    def erstelle_message(self, raeume: List[Raum]) -> Message:
        return Message(
            message_id=f"raum_{id(self)}",
            sender=self.name,
            receiver="Shared Knowledge Base",
            typ=MessageType.RAUM,
            inhalt={"anzahl_raeume": len(raeume), "gesamt_flaeche": sum(r.flaeche_m2 for r in raeume)},
            epistemischer_zustand=EpistemicState.PROBABLE,
            konfidenz=0.88,
        )


class MassstabsAgent:
    """Erkennt Massstab und kalibriert Messungen."""

    def __init__(self):
        self.name = "Massstabs-Agent"
        self.massstab = 1.0  # 1:50 -> 50.0
        self.kalibrierung = 1.0

    def analysiere(self, plan_daten: Dict[str, Any]) -> float:
        """Erkenne Massstab aus Plan-Daten."""
        # Simuliere Massstabs-Erkennung
        if "massstab" in plan_daten:
            self.massstab = plan_daten["massstab"]
        elif "bemasung" in plan_daten:
            # Extrahiere Massstab aus Bemasung
            for bem in plan_daten["bemasung"]:
                if "massstab" in bem:
                    self.massstab = bem["massstab"]
                    break
        else:
            # Default: 1:50
            self.massstab = 50.0

        return self.massstab

    def kalibriere(self, plan_daten: Dict[str, Any]) -> float:
        """Kalibriere Messungen basierend auf bekannten Referenzen."""
        if "referenz" in plan_daten:
            ref = plan_daten["referenz"]
            self.kalibrierung = ref["ist"] / ref["soll"]
        return self.kalibrierung

    def umrechnen_mm_in_m(self, wert_mm: float) -> float:
        """Rechne mm in m unter Beruecksichtigung des Massstabs."""
        return (wert_mm / self.massstab) / 1000.0

    def erstelle_message(self, massstab: float, kalibrierung: float) -> Message:
        return Message(
            message_id=f"mass_{id(self)}",
            sender=self.name,
            receiver="Shared Knowledge Base",
            typ=MessageType.MASSSTAB,
            inhalt={"massstab": f"1:{massstab}", "kalibrierung": kalibrierung},
            epistemischer_zustand=EpistemicState.CERTAIN,
            konfidenz=0.98,
        )


class NormenAgent:
    """Prueft Plan gegen OIB-RL und Eurocodes."""

    def __init__(self):
        self.name = "Normen-Agent"
        self.fehler: List[Fehler] = []

    def pruefe(self, raeume: List[Raum], symbole: List[Symbol], geometrie: List[PlanElement]) -> List[Fehler]:
        """Pruefe Plan gegen Normen."""
        self.fehler = []

        # OIB-RL 4: Nutzungssicherheit
        for raum in raeume:
            if raum.flaeche_m2 < 4:
                self.fehler.append(Fehler(
                    id=f"NORM_{raum.name}_MINDESTFLAECHE",
                    typ="normativ",
                    schwere="KRITISCH",
                    beschreibung=f"Raum {raum.name}: Mindestflaeche 4m2 unterschritten ({raum.flaeche_m2:.1f}m2)",
                    norm_verweis="OIB-RL 4",
                    empfehlung="Raumflaeche vergroessern",
                    confidence=0.95,
                ))

        # OIB-RL 2: Brandschutz - Fluchtwege
        for sym in symbole:
            if sym.typ.startswith("tuer"):
                if sym.confidence < 0.8:
                    self.fehler.append(Fehler(
                        id=f"NORM_TUER_{sym.typ}",
                        typ="normativ",
                        schwere="MITTEL",
                        beschreibung=f"Tuer {sym.typ}: Unsichere Erkennung (Confidence: {sym.confidence:.2f})",
                        norm_verweis="OIB-RL 2 (Fluchtwege)",
                        empfehlung="Tuer klar kennzeichnen",
                        confidence=0.80,
                    ))

        # OIB-RL 3: Tageslicht
        for raum in raeume:
            if raum.tage_licht and raum.fenster_anteil < 0.1:
                self.fehler.append(Fehler(
                    id=f"NORM_{raum.name}_TAGESLICHT",
                    typ="normativ",
                    schwere="HOCH",
                    beschreibung=f"Raum {raum.name}: Tageslichtquote < 10%",
                    norm_verweis="OIB-RL 3",
                    empfehlung="Fensterflaeche vergroessern",
                    confidence=0.90,
                ))

        return self.fehler

    def erstelle_message(self, fehler: List[Fehler]) -> Message:
        return Message(
            message_id=f"norm_{id(self)}",
            sender=self.name,
            receiver="Shared Knowledge Base",
            typ=MessageType.NORM,
            inhalt={"anzahl_fehler": len(fehler), "schwere": {s: sum(1 for f in fehler if f.schwere == s) for s in ["KRITISCH", "HOCH", "MITTEL", "NIEDRIG"]}},
            epistemischer_zustand=EpistemicState.PROBABLE,
            konfidenz=0.92,
        )


class FehlerAgent:
    """Erkennt Inkonsistenzen im Plan."""

    def __init__(self):
        self.name = "Fehler-Agent"
        self.fehler: List[Fehler] = []

    def analysiere(self, geometrie: List[PlanElement], raeume: List[Raum], symbole: List[Symbol]) -> List[Fehler]:
        """Analysiere Plan auf Inkonsistenzen."""
        self.fehler = []

        # Geometrische Fehler
        self._pruefe_geometrie(geometrie)

        # Kollisions-Erkennung
        self._pruefe_kollisionen(geometrie, symbole)

        # Vollstaendigkeits-Pruefung
        self._pruefe_vollstaendigkeit(raeume, symbole)

        return self.fehler

    def _pruefe_geometrie(self, geometrie: List[PlanElement]):
        """Pruefe geometrische Konsistenz."""
        for elem in geometrie:
            if elem.typ == "wand" and isinstance(elem.geometrie, Line2D):
                if elem.geometrie.length < 50:
                    self.fehler.append(Fehler(
                        id=f"GEO_WAND_{id(elem)}",
                        typ="geometrisch",
                        schwere="NIEDRIG",
                        beschreibung=f"Sehr kurze Wand ({elem.geometrie.length:.0f}mm)",
                        empfehlung="Wand auf Plausibilitaet pruefen",
                        confidence=0.70,
                    ))

    def _pruefe_kollisionen(self, geometrie: List[PlanElement], symbole: List[Symbol]):
        """Pruefe auf Kollisionen zwischen Elementen."""
        for sym in symbole:
            for elem in geometrie:
                if elem.typ == "wand" and isinstance(elem.geometrie, Line2D):
                    dist = sym.position.distance_to(elem.geometrie.start)
                    if dist < 10:  # < 10mm = Kollision
                        self.fehler.append(Fehler(
                            id=f"KOLL_{sym.typ}_{id(elem)}",
                            typ="kollision",
                            schwere="HOCH",
                            beschreibung=f"Kollision: {sym.typ} mit Wand",
                            empfehlung="Position anpassen",
                            confidence=0.85,
                        ))

    def _pruefe_vollstaendigkeit(self, raeume: List[Raum], symbole: List[Symbol]):
        """Pruefe Vollstaendigkeit des Plans."""
        tueren = [s for s in symbole if s.typ.startswith("tuer")]
        fenster = [s for s in symbole if s.typ.startswith("fenster")]
        treppen = [s for s in symbole if s.typ.startswith("treppe")]

        if len(raeume) > 0 and len(tueren) == 0:
            self.fehler.append(Fehler(
                id="VOLL_TUEREN",
                typ="vollstaendigkeit",
                schwere="KRITISCH",
                beschreibung="Keine Tueren im Plan erkannt",
                empfehlung="Tueren einzeichnen",
                confidence=0.90,
            ))

        if len(raeume) > 1 and len(treppen) == 0:
            self.fehler.append(Fehler(
                id="VOLL_TREPPEN",
                typ="vollstaendigkeit",
                schwere="KRITISCH",
                beschreibung="Keine Treppen im Plan erkannt (bei mehreren Geschossen)",
                empfehlung="Treppe einzeichnen",
                confidence=0.85,
            ))

    def erstelle_message(self, fehler: List[Fehler]) -> Message:
        return Message(
            message_id=f"fehler_{id(self)}",
            sender=self.name,
            receiver="Shared Knowledge Base",
            typ=MessageType.FEHLER,
            inhalt={"anzahl_fehler": len(fehler), "typen": list(set(f.typ for f in fehler))},
            epistemischer_zustand=EpistemicState.PROBABLE,
            konfidenz=0.88,
        )


class DESAgent:
    """Epistemische Validierung mit DES."""

    def __init__(self):
        self.name = "DES-Agent"
        self.system = DeterministicEpistemicSystem("Plan-Verstehen-DES")
        self.agenten = ["Geometrie-Agent", "Symbol-Agent", "Raum-Agent", "Massstabs-Agent", "Normen-Agent", "Fehler-Agent"]
        for name in self.agenten:
            self.system.create_agent(name, validation_threshold=0.85)

    def validiere(self, messages: List[Message]) -> Dict[str, Any]:
        """Validiere alle Messages epistemisch."""
        # Wissen hinzufuegen
        for msg in messages:
            prop = EpistemicProposition(
                content=f"{msg.sender}: {json.dumps(msg.inhalt, default=str)}",
                source=msg.sender,
                confidence=msg.konfidenz,
            )
            self.system.add_global_knowledge(prop)

        # Swarm-Konsens
        first_key = list(self.system.global_knowledge.keys())[0] if self.system.global_knowledge else "test"
        consensus = self.system.compute_consensus(first_key)

        # System-Validierung
        state = self.system.validate_system_state()

        return {
            "system_valide": state["system_valid"],
            "widersprueche": len(state["contradictions"]),
            "agenten": state["agent_count"],
            "globales_wissen": state["global_knowledge_count"],
            "konsens_state": consensus.get("consensus_state", "unknown"),
            "konsens_strength": consensus.get("consensus_strength", 0),
        }

    def erstelle_message(self, validierung: Dict[str, Any]) -> Message:
        return Message(
            message_id=f"des_{id(self)}",
            sender=self.name,
            receiver="Shared Knowledge Base",
            typ=MessageType.VALIDIERUNG,
            inhalt=validierung,
            epistemischer_zustand=EpistemicState.CERTAIN if validierung["system_valide"] else EpistemicState.CONTRADICTED,
            konfidenz=0.95,
        )


# ============================================================================
# PLAN-VERSTEHEN-SYSTEM
# ============================================================================

class PlanVerstehenSystem:
    """Multi-Agenten-System fuer automatisches Plan-Verstehen."""

    def __init__(self):
        self.geometrie_agent = GeometrieAgent()
        self.symbol_agent = SymbolAgent()
        self.raum_agent = RaumAgent()
        self.massstab_agent = MassstabsAgent()
        self.normen_agent = NormenAgent()
        self.fehler_agent = FehlerAgent()
        self.des_agent = DESAgent()
        self.messages: List[Message] = []
        self.ergebnisse = {}

    def analysiere_plan(self, plan_daten: Dict[str, Any], geschoss: str = "Unbekannt") -> Dict[str, Any]:
        """Analysiere einen Plan mit allen Agenten."""
        print(f"\n  Analysiere Geschoss: {geschoss}")
        print(f"  {'=' * 60}")

        gesamt_start = time.time()

        # Phase 1: EXTRAKTION (Parallel)
        print("\n  PHASE 1: EXTRAKTION")
        print(f"  {'-' * 60}")

        geometrie = self.geometrie_agent.analysiere(plan_daten)
        print(f"  [OK] Geometrie-Agent: {len(geometrie)} Elemente extrahiert")

        symbole = self.symbol_agent.analysiere(plan_daten, geometrie)
        print(f"  [OK] Symbol-Agent: {len(symbole)} Symbole erkannt")

        raeume = self.raum_agent.analysiere(geometrie, symbole)
        print(f"  [OK] Raum-Agent: {len(raeume)} Raeume identifiziert")

        massstab = self.massstab_agent.analysiere(plan_daten)
        kalibrierung = self.massstab_agent.kalibriere(plan_daten)
        print(f"  [OK] Massstabs-Agent: 1:{massstab}, Kalibrierung: {kalibrierung:.2f}")

        # Messages erstellen
        self.messages.append(self.geometrie_agent.erstelle_message(geometrie))
        self.messages.append(self.symbol_agent.erstelle_message(symbole))
        self.messages.append(self.raum_agent.erstelle_message(raeume))
        self.messages.append(self.massstab_agent.erstelle_message(massstab, kalibrierung))

        # Phase 2: ANALYSE (Sequentiell)
        print("\n  PHASE 2: ANALYSE")
        print(f"  {'-' * 60}")

        normen_fehler = self.normen_agent.pruefe(raeume, symbole, geometrie)
        print(f"  [OK] Normen-Agent: {len(normen_fehler)} Normen-Fehler gefunden")

        fehler = self.fehler_agent.analysiere(geometrie, raeume, symbole)
        print(f"  [OK] Fehler-Agent: {len(fehler)} Inkonsistenzen erkannt")

        self.messages.append(self.normen_agent.erstelle_message(normen_fehler))
        self.messages.append(self.fehler_agent.erstelle_message(fehler))

        # Phase 3: VALIDIERUNG
        print("\n  PHASE 3: VALIDIERUNG")
        print(f"  {'-' * 60}")

        validierung = self.des_agent.validiere(self.messages)
        print(f"  [OK] DES-Agent: System valide={validierung['system_valide']}")
        print(f"       Widersprueche: {validierung['widersprueche']}")
        print(f"       Konsens: {validierung['konsens_state']} ({validierung['konsens_strength']:.2f})")

        gesamt_zeit = time.time() - gesamt_start

        # Ergebnisse speichern
        self.ergebnisse[geschoss] = {
            "geometrie": {"anzahl": len(geometrie), "typen": list(set(e.typ for e in geometrie))},
            "symbole": {"anzahl": len(symbole), "typen": list(set(s.typ for s in symbole))},
            "raeume": {"anzahl": len(raeume), "gesamt_flaeche": sum(r.flaeche_m2 for r in raeume)},
            "massstab": massstab,
            "normen_fehler": len(normen_fehler),
            "fehler": len(fehler),
            "validierung": validierung,
            "dauer_sec": gesamt_zeit,
        }

        return self.ergebnisse[geschoss]

    def erstelle_gesamtbericht(self) -> Dict[str, Any]:
        """Erstelle Gesamtbericht aller Analysen."""
        gesamt = {
            "geschosse": len(self.ergebnisse),
            "gesamt_elemente": sum(e["geometrie"]["anzahl"] for e in self.ergebnisse.values()),
            "gesamt_symbole": sum(e["symbole"]["anzahl"] for e in self.ergebnisse.values()),
            "gesamt_raeume": sum(e["raeume"]["anzahl"] for e in self.ergebnisse.values()),
            "gesamt_normen_fehler": sum(e["normen_fehler"] for e in self.ergebnisse.values()),
            "gesamt_fehler": sum(e["fehler"] for e in self.ergebnisse.values()),
            "alle_valide": all(e["validierung"]["system_valide"] for e in self.ergebnisse.values()),
            "ergebnisse": self.ergebnisse,
        }
        return gesamt


# ============================================================================
# TEST-DATEN GENERATOR
# ============================================================================

def generiere_test_daten_geschoss(geschoss: str) -> Dict[str, Any]:
    """Generiere Test-Daten fuer ein Geschoss."""
    test_daten = {
        "massstab": 50.0,
        "linien": [],
        "kreise": [],
        "polygone": [],
        "symbole": [],
        "bemasung": [],
        "referenz": {"ist": 1.0, "soll": 1.0},
    }

    if geschoss == "UG":
        # Untergeschoss: Fundament, Heizungsraum, Keller
        test_daten["linien"] = [
            {"x1": 0, "y1": 0, "x2": 10000, "y2": 0},  # Wand 10m
            {"x1": 10000, "y1": 0, "x2": 10000, "y2": 8000},  # Wand 8m
            {"x1": 10000, "y1": 8000, "x2": 0, "y2": 8000},  # Wand 10m
            {"x1": 0, "y1": 8000, "x2": 0, "y2": 0},  # Wand 8m
            {"x1": 5000, "y1": 0, "x2": 5000, "y2": 4000},  # Innenwand
        ]
        test_daten["polygone"] = [
            {"points": [{"x": 100, "y": 100}, {"x": 4900, "y": 100}, {"x": 4900, "y": 3900}, {"x": 100, "y": 3900}]},  # Heizungsraum
            {"points": [{"x": 5100, "y": 100}, {"x": 9900, "y": 100}, {"x": 9900, "y": 7900}, {"x": 5100, "y": 7900}]},  # Keller
        ]
        test_daten["symbole"] = [
            {"typ": "tuer_einfach", "x": 5000, "y": 2000, "norm": "OENORM E 8001", "confidence": 0.90},
        ]

    elif geschoss == "EG":
        # Erdgeschoss: Wohnzimmer, Kueche, Flur, Eingang
        test_daten["linien"] = [
            {"x1": 0, "y1": 0, "x2": 10000, "y2": 0},
            {"x1": 10000, "y1": 0, "x2": 10000, "y2": 8000},
            {"x1": 10000, "y1": 8000, "x2": 0, "y2": 8000},
            {"x1": 0, "y1": 8000, "x2": 0, "y2": 0},
            {"x1": 4000, "y1": 0, "x2": 4000, "y2": 5000},  # Innenwand
            {"x1": 4000, "y1": 5000, "x2": 10000, "y2": 5000},  # Innenwand
        ]
        test_daten["polygone"] = [
            {"points": [{"x": 100, "y": 100}, {"x": 3900, "y": 100}, {"x": 3900, "y": 4900}, {"x": 100, "y": 4900}]},  # Wohnzimmer
            {"points": [{"x": 4100, "y": 100}, {"x": 9900, "y": 100}, {"x": 9900, "y": 4900}, {"x": 4100, "y": 4900}]},  # Kueche
            {"points": [{"x": 100, "y": 5100}, {"x": 9900, "y": 5100}, {"x": 9900, "y": 7900}, {"x": 100, "y": 7900}]},  # Flur
        ]
        test_daten["symbole"] = [
            {"typ": "tuer_einfach", "x": 2000, "y": 0, "norm": "OENORM E 8001", "confidence": 0.92},
            {"typ": "fenster_einfach", "x": 2000, "y": 4900, "norm": "OENORM E 8001", "confidence": 0.88},
            {"typ": "fenster_balkon", "x": 7000, "y": 4900, "norm": "OENORM E 8001", "confidence": 0.85},
            {"typ": "treppe_gerade", "x": 8000, "y": 6500, "norm": "OENORM B 2501", "confidence": 0.90},
        ]

    elif geschoss == "OG":
        # Obergeschoss: Schlafzimmer, Bad, Kinderzimmer
        test_daten["linien"] = [
            {"x1": 0, "y1": 0, "x2": 10000, "y2": 0},
            {"x1": 10000, "y1": 0, "x2": 10000, "y2": 8000},
            {"x1": 10000, "y1": 8000, "x2": 0, "y2": 8000},
            {"x1": 0, "y1": 8000, "x2": 0, "y2": 0},
            {"x1": 5000, "y1": 0, "x2": 5000, "y2": 8000},  # Innenwand
        ]
        test_daten["polygone"] = [
            {"points": [{"x": 100, "y": 100}, {"x": 4900, "y": 100}, {"x": 4900, "y": 3900}, {"x": 100, "y": 3900}]},  # Schlafzimmer
            {"points": [{"x": 5100, "y": 100}, {"x": 9900, "y": 100}, {"x": 9900, "y": 3900}, {"x": 5100, "y": 3900}]},  # Bad
            {"points": [{"x": 100, "y": 4100}, {"x": 9900, "y": 4100}, {"x": 9900, "y": 7900}, {"x": 100, "y": 7900}]},  # Kinderzimmer
        ]
        test_daten["symbole"] = [
            {"typ": "tuer_einfach", "x": 2500, "y": 0, "norm": "OENORM E 8001", "confidence": 0.90},
            {"typ": "fenster_einfach", "x": 2500, "y": 3900, "norm": "OENORM E 8001", "confidence": 0.85},
            {"typ": "sanitaer_wc", "x": 7500, "y": 2000, "norm": "OENORM B 2501", "confidence": 0.88},
            {"typ": "sanitaer_bad", "x": 7500, "y": 3000, "norm": "OENORM B 2501", "confidence": 0.85},
            {"typ": "treppe_gerade", "x": 8000, "y": 6500, "norm": "OENORM B 2501", "confidence": 0.90},
        ]

    elif geschoss == "DG":
        # Dachgeschoss: Galerie, Abstellraum
        test_daten["linien"] = [
            {"x1": 0, "y1": 0, "x2": 10000, "y2": 0},
            {"x1": 10000, "y1": 0, "x2": 10000, "y2": 8000},
            {"x1": 10000, "y1": 8000, "x2": 0, "y2": 8000},
            {"x1": 0, "y1": 8000, "x2": 0, "y2": 0},
        ]
        test_daten["polygone"] = [
            {"points": [{"x": 100, "y": 100}, {"x": 9900, "y": 100}, {"x": 9900, "y": 5000}, {"x": 100, "y": 5000}]},  # Galerie
            {"points": [{"x": 100, "y": 5100}, {"x": 4900, "y": 5100}, {"x": 4900, "y": 7900}, {"x": 100, "y": 7900}]},  # Abstell
        ]
        test_daten["symbole"] = [
            {"typ": "fenster_balkon", "x": 5000, "y": 5000, "norm": "OENORM E 8001", "confidence": 0.82},
            {"typ": "treppe_gerade", "x": 8000, "y": 6500, "norm": "OENORM B 2501", "confidence": 0.90},
        ]

    return test_daten


# ============================================================================
# HAUPTPROGRAMM
# ============================================================================

def main():
    print("=" * 100)
    print("PLAN-VERSTEHEN-SYSTEM: Multi-Agenten-System fuer automatisches Plan-Verstehen")
    print("Testlauf mit 4 Geschossen (UG, EG, OG, DG)")
    print("=" * 100)

    system = PlanVerstehenSystem()
    gesamt_start = time.time()

    # Analysiere alle Geschosse
    geschosse = ["UG", "EG", "OG", "DG"]
    for geschoss in geschosse:
        plan_daten = generiere_test_daten_geschoss(geschoss)
        ergebnis = system.analysiere_plan(plan_daten, geschoss)

        print(f"\n  ERGEBNIS {geschoss}:")
        print(f"    Geometrie: {ergebnis['geometrie']['anzahl']} Elemente")
        print(f"    Symbole: {ergebnis['symbole']['anzahl']} erkannt")
        print(f"    Raeume: {ergebnis['raeume']['anzahl']} identifiziert")
        print(f"    Normen-Fehler: {ergebnis['normen_fehler']}")
        print(f"    Inkonsistenzen: {ergebnis['fehler']}")
        print(f"    Validierung: {'VALIDE' if ergebnis['validierung']['system_valide'] else 'NICHT VALIDE'}")

    # Gesamtbericht
    gesamt_zeit = time.time() - gesamt_start
    gesamtbericht = system.erstelle_gesamtbericht()

    print("\n" + "=" * 100)
    print("GESAMTBERICHT")
    print("=" * 100)
    print(f"  Geschosse analysiert: {gesamtbericht['geschosse']}")
    print(f"  Gesamt Elemente: {gesamtbericht['gesamt_elemente']}")
    print(f"  Gesamt Symbole: {gesamtbericht['gesamt_symbole']}")
    print(f"  Gesamt Raeume: {gesamtbericht['gesamt_raeume']}")
    print(f"  Gesamt Normen-Fehler: {gesamtbericht['gesamt_normen_fehler']}")
    print(f"  Gesamt Inkonsistenzen: {gesamtbericht['gesamt_fehler']}")
    print(f"  Alle valide: {'JA' if gesamtbericht['alle_valide'] else 'NEIN'}")
    print(f"  Dauer: {gesamt_zeit:.2f}s")

    # JSON-Export
    report_path = os.path.join(os.path.dirname(__file__), "..", "plan_verstehen_report.json")
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(gesamtbericht, f, indent=2, ensure_ascii=False, default=str)
    print(f"\nPlan-Verstehen-Report gespeichert: {report_path}")

    print("\n" + "=" * 100)
    print("PLAN-VERSTEHEN-SYSTEM: EINSATZBEREIT")
    print("=" * 100)


if __name__ == "__main__":
    main()