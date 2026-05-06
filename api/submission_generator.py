"""
ORION Architekt-AT — Behördeneinreichungs-Generator
====================================================
Erstellt bundeslandspezifische Unterlagenlisten und Formulare für das Bauansuchen.
Basiert auf den 9 Landesbauordnungen + OIB-RL Anforderungen.
"""

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Unterlagen-Datenbank pro Vorhaben / Bundesland
# ---------------------------------------------------------------------------

_PFLICHTDOKUMENTE_ALLGEMEIN = [
    {
        "name": "Bauansuchen (formular)",
        "pflicht": True,
        "hinweis": "Offizielles Formular der zuständigen Baubehörde verwenden",
        "kategorie": "Antragsformular",
    },
    {
        "name": "Lageplan (Katasterplan)",
        "pflicht": True,
        "hinweis": "Amtlicher Katasterplan, max. 3 Monate alt, M 1:500 oder 1:1000",
        "kategorie": "Pläne",
    },
    {
        "name": "Einreichplan — Grundrisse alle Geschosse",
        "pflicht": True,
        "hinweis": "M 1:100, bemaßt, mit Raumbezeichnungen",
        "kategorie": "Pläne",
    },
    {
        "name": "Einreichplan — Ansichten (alle 4 Seiten)",
        "pflicht": True,
        "hinweis": "M 1:100, mit Geländeverlauf, Gebäudehöhen",
        "kategorie": "Pläne",
    },
    {
        "name": "Einreichplan — Schnitte (mind. 2)",
        "pflicht": True,
        "hinweis": "Quer- und Längsschnitt, M 1:100",
        "kategorie": "Pläne",
    },
    {
        "name": "Baubeschreibung",
        "pflicht": True,
        "hinweis": "Beschreibung der Bauausführung, Materialien, Konstruktion",
        "kategorie": "Beschreibungen",
    },
    {
        "name": "Nachweis Eigentumsrecht / Zustimmung Eigentümer",
        "pflicht": True,
        "hinweis": "Grundbuchauszug + Zustimmungserklärung bei Fremdgrundstück",
        "kategorie": "Rechtsdokumente",
    },
    {
        "name": "Statik / Standsicherheitsnachweis",
        "pflicht": True,
        "hinweis": "Vorentwurfsstatik oder Statisches Konzept vom ZT",
        "kategorie": "Nachweise",
    },
    {
        "name": "OIB-RL Nachweise (alle 6)",
        "pflicht": True,
        "hinweis": "Konformitätserklärungen zu OIB-RL 1-6",
        "kategorie": "Nachweise",
    },
]

_VORHABEN_EXTRAS: Dict[str, List[Dict]] = {
    "neubau": [
        {"name": "Energieausweis (Vorausweis / Planungsausweis)", "pflicht": True,
         "hinweis": "Vorausweis nach OIB-RL 6 vom befugten Planer", "kategorie": "Energie"},
        {"name": "Entwässerungskonzept", "pflicht": True,
         "hinweis": "Anschluss Kanal / Sickerschacht, Niederschlagswasser", "kategorie": "Haustechnik"},
        {"name": "Brandschutzkonzept (ab GK 3)", "pflicht": False,
         "hinweis": "Nur bei GK 3-5 oder besonderen Gebäudetypen erforderlich", "kategorie": "Brandschutz"},
        {"name": "Verschattungsstudie (wenn Nachbarn betroffen)", "pflicht": False,
         "hinweis": "Bei engen Baugrundstücken empfohlen", "kategorie": "Nachbarrecht"},
    ],
    "zubau": [
        {"name": "Bestandspläne des bestehenden Gebäudes", "pflicht": True,
         "hinweis": "Als-built-Pläne des Bestands", "kategorie": "Pläne"},
        {"name": "Nachweis Bestandskonsens (Baugenehmigung Bestand)", "pflicht": True,
         "hinweis": "Bestehende Baugenehmigung oder Baubescheid", "kategorie": "Rechtsdokumente"},
    ],
    "umbau": [
        {"name": "Bestandspläne mit Eintragungs-/Änderungsplan", "pflicht": True,
         "hinweis": "Bestand (gelb), Abbruch (rot), Neu (grün)", "kategorie": "Pläne"},
        {"name": "Brandschutznachweis bei Nutzungsänderung", "pflicht": False,
         "hinweis": "Wenn Nutzung geändert wird", "kategorie": "Brandschutz"},
    ],
    "dachausbau": [
        {"name": "Bestandspläne Dachgeschoss", "pflicht": True,
         "hinweis": "Aktueller Bestand, AS-BUILT", "kategorie": "Pläne"},
        {"name": "Wärmeschutznachweis Dach", "pflicht": True,
         "hinweis": "U-Wert-Berechnung nach OIB-RL 6", "kategorie": "Energie"},
        {"name": "Schallschutznachweis (wenn neue Wohneinheiten)", "pflicht": False,
         "hinweis": "ÖNORM B 8115 bei neuen Wohneinheiten", "kategorie": "Schallschutz"},
    ],
    "abbruch": [
        {"name": "Abbruchantrag", "pflicht": True,
         "hinweis": "Separates Abbruchformular", "kategorie": "Antragsformular"},
        {"name": "Entsorgungskonzept (Schadstofferhebung)", "pflicht": True,
         "hinweis": "Asbestkataster, Schadstoffe bei Gebäuden vor 1990", "kategorie": "Entsorgung"},
    ],
}

_BUNDESLAND_BEHOERDE: Dict[str, Dict[str, Any]] = {
    "wien": {
        "behoerde": "MA 37 – Baupolizei Wien",
        "einreichungsart": "Digital via Wien Baut (MA 37 Online)",
        "portal_url": "https://www.wien.gv.at/amtshelfer/bauen-wohnen/",
        "besonderheiten": [
            "Digitale Einreichung via ELAK möglich",
            "Vorbescheid (§ 7 BO Wien) empfohlen für komplexe Vorhaben",
        ],
        "bearbeitungszeit": "6–12 Monate (Neubau)",
    },
    "tirol": {
        "behoerde": "Gemeindeamt (zuständige Gemeinde)",
        "einreichungsart": "Analog bei Gemeindeamt, teilweise digital",
        "portal_url": "https://www.tirol.gv.at/bauen-wohnen/",
        "besonderheiten": [
            "TROG 2022 beachten",
            "Lawinenschutz-Nachweis in Gefahrenzonen (Kat A/B)",
            "Waalwege: Servitut prüfen",
        ],
        "bearbeitungszeit": "3–8 Monate",
    },
    "salzburg": {
        "behoerde": "Stadtgemeinde Salzburg (BauR) oder Gemeindeamt",
        "einreichungsart": "Analog, Salzburg-Stadt teilweise digital",
        "portal_url": "https://www.salzburg.gv.at/bauen",
        "besonderheiten": [
            "Sbg BauTG 2015 beachten",
            "WSchVO (nicht OIB-RL 6) für Energienachweise!",
            "Gestaltungssatzungen in Altstadtbereichen",
        ],
        "bearbeitungszeit": "4–10 Monate",
    },
    "niederoesterreich": {
        "behoerde": "Gemeindeamt (BH bei besonderen Vorhaben)",
        "einreichungsart": "NÖ Baubehörde Online für Formulare",
        "portal_url": "https://www.noe.gv.at/bauen",
        "besonderheiten": [
            "NÖ BO 2014 + NÖ Bautechnikverordnung",
            "Bebauungsplan der Gemeinde prüfen",
            "Waldviertel: Radon-Schutzmaßnahmen empfohlen",
        ],
        "bearbeitungszeit": "3–8 Monate",
    },
    "oberoesterreich": {
        "behoerde": "Gemeindeamt",
        "einreichungsart": "Analog, eForm OÖ verfügbar",
        "portal_url": "https://www.ooe.gv.at/bauen",
        "besonderheiten": [
            "OÖ BauO 1994 + OÖ BauTG",
            "Solaranlagen: vereinfachtes Verfahren möglich",
            "10% Besucher-Stellplätze bei MFH",
        ],
        "bearbeitungszeit": "3–7 Monate",
    },
    "vorarlberg": {
        "behoerde": "Gemeindeamt",
        "einreichungsart": "Analog, einzelne Gemeinden digital",
        "portal_url": "https://www.vorarlberg.at/bauen",
        "besonderheiten": [
            "Vbg BG (Baugesetz) + Vbg BTV",
            "1:1 Fahrradstellplätze verpflichtend",
            "Passivhausstandard teilweise gefördert",
        ],
        "bearbeitungszeit": "3–8 Monate",
    },
    "steiermark": {
        "behoerde": "Gemeindeamt (BH in Graz)",
        "einreichungsart": "Analog, eGov Steiermark verfügbar",
        "portal_url": "https://www.steiermark.gv.at/bauen",
        "besonderheiten": [
            "Stmk BauG 1995 + Stmk BauTV",
            "Grazer Altstadterhaltungsgesetz bei Denkmalschutz",
        ],
        "bearbeitungszeit": "4–10 Monate",
    },
    "kaernten": {
        "behoerde": "Gemeindeamt (BH für größere Vorhaben)",
        "einreichungsart": "Analog bei Gemeindeamt",
        "portal_url": "https://www.kaernten.gv.at/bauen",
        "besonderheiten": [
            "K-BO 1996 + K-BTV",
            "Seenlandschaft: Uferzone prüfen!",
            "Zweisprachige Beschilderung in Gebieten mit sloven. Ortsnamen",
        ],
        "bearbeitungszeit": "4–9 Monate",
    },
    "burgenland": {
        "behoerde": "Gemeindeamt",
        "einreichungsart": "Analog",
        "portal_url": "https://www.burgenland.gv.at/bauen",
        "besonderheiten": [
            "Bgld BauG 1997",
            "Weinbaugebiete: Gestaltungsvorschriften",
            "Neusiedler See: Landschaftsschutz prüfen",
        ],
        "bearbeitungszeit": "3–7 Monate",
    },
}

_CHECKLISTE_VORBEREITUNG = [
    "Befugten Ziviltechniker oder Architekten beauftragen (Einreichung erfordert Planverfasser)",
    "Grundbuchauszug einholen (Rechtsmittelfähigkeit des Grundstücks prüfen)",
    "Bebauungsplan / Flächenwidmungsplan der Gemeinde prüfen",
    "Gefahrenzonen prüfen (hora.gv.at: Hochwasser, Lawine, Steinschlag)",
    "Leitungsauskünfte einholen (Strom, Gas, Wasser, Abwasser, Telekom)",
    "Nachbarbekanntgabe vorbereiten (Parteienstellung der Nachbarn)",
    "OIB-Richtlinien 1–6 Konformität sicherstellen",
    "Energieausweis (Vorausweis) in Auftrag geben",
    "Budget für Behördengebühren einplanen (ca. 1–3% der Bausumme)",
]


def generate_submission_package(
    bundesland: str,
    vorhaben: str,
    gebaudetyp: str,
    bgf_m2: float,
    bauherr: str = "",
    grundstueck_kgez: str = "",
) -> Dict[str, Any]:
    """
    Generiert die vollständige Unterlagenliste für das Bauansuchen.
    Bundesland-spezifisch + vorhabenspezifisch.
    """
    documents = list(_PFLICHTDOKUMENTE_ALLGEMEIN)

    # Vorhaben-spezifische Extras
    extras = _VORHABEN_EXTRAS.get(vorhaben, _VORHABEN_EXTRAS.get("neubau", []))
    documents.extend(extras)

    # Größenspezifische Extras
    if bgf_m2 > 1500:
        documents.append({
            "name": "Brandschutzkonzept (Großvorhaben)",
            "pflicht": True,
            "hinweis": "Verpflichtend ab BGF > 1.500 m² oder Sonderbau",
            "kategorie": "Brandschutz",
        })
    if bgf_m2 > 3000:
        documents.append({
            "name": "Umweltverträglichkeitsprüfung (UVP-Vorprüfung)",
            "pflicht": False,
            "hinweis": "UVP-Vorprüfung empfohlen ab BGF > 3.000 m²",
            "kategorie": "Umwelt",
        })

    bl_info = _BUNDESLAND_BEHOERDE.get(bundesland, _BUNDESLAND_BEHOERDE["tirol"])

    checkliste = list(_CHECKLISTE_VORBEREITUNG)
    checkliste.extend(bl_info.get("besonderheiten", []))

    return {
        "bundesland": bundesland,
        "vorhaben": vorhaben,
        "gebaudetyp": gebaudetyp,
        "bgf_m2": bgf_m2,
        "bauherr": bauherr,
        "grundstueck_kgez": grundstueck_kgez,
        "behoerde": bl_info["behoerde"],
        "einreichungsart": bl_info["einreichungsart"],
        "portal_url": bl_info.get("portal_url"),
        "bearbeitungszeit": bl_info.get("bearbeitungszeit", "3–12 Monate"),
        "total_documents": len(documents),
        "documents": documents,
        "checkliste": checkliste,
        "hinweis": (
            "Diese Unterlagenliste dient als Orientierung. "
            "Die genauen Anforderungen sind mit der zuständigen Baubehörde abzuklären. "
            "Einreichungen erfordern einen befugten Ziviltechniker / Architekten."
        ),
    }
