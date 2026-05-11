"""
ORION Architekt-AT — Mehrsprachigkeit (i18n)
=============================================

Unterstützte Sprachen:
  de  — Deutsch (Standard, Arbeitssprache)
  en  — Englisch (internationale Investoren, Planer)
  sl  — Slowenisch (Kärnten — Kärntner Landessprache)
  hr  — Kroatisch (Burgenland — autochthone Volksgruppe)
  hu  — Ungarisch (Burgenland — autochthone Volksgruppe)

Verwendung im Code:
    from api.i18n import t, set_sprache, SpracheCode

    # In einem Endpoint:
    sprache = SpracheCode(request.headers.get("Accept-Language", "de")[:2])
    return {"meldung": t("compliance_ok", sprache)}

Conventions:
  - Schlüssel: snake_case, lowercase
  - Fallback: immer Deutsch (de) wenn Schlüssel in Zielsprache fehlt
  - Neue Schlüssel: zuerst Deutsch eintragen, dann Übersetzungen ergänzen
"""

from __future__ import annotations

import logging
from enum import Enum
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class SpracheCode(str, Enum):
    DE = "de"
    EN = "en"
    SL = "sl"  # Slowenisch / Slovenščina
    HR = "hr"  # Kroatisch / Hrvatski
    HU = "hu"  # Ungarisch / Magyar


# ---------------------------------------------------------------------------
# Übersetzungstabelle
# Format: { schluessel: { sprach_code: übersetzung } }
# ---------------------------------------------------------------------------

_TRANSLATIONS: Dict[str, Dict[str, str]] = {
    # ---- System-Meldungen ----
    "api_title": {
        "de": "ORION Architekt-AT API",
        "en": "ORION Architekt-AT API",
        "sl": "ORION Architekt-AT API",
        "hr": "ORION Architekt-AT API",
        "hu": "ORION Architekt-AT API",
    },
    "api_description": {
        "de": "Österreichisches Bauregelwerk — vollständige OIB-RL Compliance für alle 9 Bundesländer",
        "en": "Austrian Building Code System — full OIB-RL compliance for all 9 federal states",
        "sl": "Avstrijski gradbeni predpisi — popolna skladnost OIB-RL za vseh 9 zveznih dežel",
        "hr": "Austrijski sustav građevinskih propisa — potpuna usklađenost OIB-RL za svih 9 saveznih pokrajina",
        "hu": "Osztrák építési szabályzat rendszer — teljes OIB-RL megfelelőség mind a 9 szövetségi tartományban",
    },
    "compliance_ok": {
        "de": "Alle Anforderungen erfüllt",
        "en": "All requirements met",
        "sl": "Vse zahteve so izpolnjene",
        "hr": "Svi zahtjevi su ispunjeni",
        "hu": "Minden követelmény teljesítve",
    },
    "compliance_fail": {
        "de": "Anforderungen NICHT erfüllt",
        "en": "Requirements NOT met",
        "sl": "Zahteve NISO izpolnjene",
        "hr": "Zahtjevi NISU ispunjeni",
        "hu": "Követelmények NEM teljesítve",
    },
    "compliance_warning": {
        "de": "Warnungen vorhanden — Überprüfung empfohlen",
        "en": "Warnings present — review recommended",
        "sl": "Prisotna opozorila — priporočena preverba",
        "hr": "Prisutna upozorenja — preporučena provjera",
        "hu": "Figyelmeztetések vannak — ellenőrzés javasolt",
    },
    # ---- OIB-Richtlinien ----
    "oib_rl_1": {
        "de": "OIB-RL 1: Mechanische Festigkeit und Standsicherheit",
        "en": "OIB-RL 1: Mechanical resistance and stability",
        "sl": "OIB-RL 1: Mehanska odpornost in stabilnost",
        "hr": "OIB-RL 1: Mehanička otpornost i stabilnost",
        "hu": "OIB-RL 1: Mechanikai szilárdság és stabilitás",
    },
    "oib_rl_2": {
        "de": "OIB-RL 2: Brandschutz",
        "en": "OIB-RL 2: Fire safety",
        "sl": "OIB-RL 2: Požarna varnost",
        "hr": "OIB-RL 2: Zaštita od požara",
        "hu": "OIB-RL 2: Tűzvédelem",
    },
    "oib_rl_3": {
        "de": "OIB-RL 3: Hygiene, Gesundheit und Umweltschutz",
        "en": "OIB-RL 3: Hygiene, health and environment",
        "sl": "OIB-RL 3: Higiena, zdravje in varstvo okolja",
        "hr": "OIB-RL 3: Higijena, zdravlje i zaštita okoliša",
        "hu": "OIB-RL 3: Higiénia, egészség és környezetvédelem",
    },
    "oib_rl_4": {
        "de": "OIB-RL 4: Nutzungssicherheit und Barrierefreiheit",
        "en": "OIB-RL 4: Safety in use and accessibility",
        "sl": "OIB-RL 4: Varnost pri uporabi in dostopnost",
        "hr": "OIB-RL 4: Sigurnost u upotrebi i pristupačnost",
        "hu": "OIB-RL 4: Használati biztonság és akadálymentesség",
    },
    "oib_rl_5": {
        "de": "OIB-RL 5: Schallschutz",
        "en": "OIB-RL 5: Protection against noise",
        "sl": "OIB-RL 5: Zvočna zaščita",
        "hr": "OIB-RL 5: Zaštita od buke",
        "hu": "OIB-RL 5: Zajvédelem",
    },
    "oib_rl_6": {
        "de": "OIB-RL 6: Energieeinsparung und Wärmeschutz",
        "en": "OIB-RL 6: Energy saving and thermal insulation",
        "sl": "OIB-RL 6: Varčevanje z energijo in toplotna zaščita",
        "hr": "OIB-RL 6: Ušteda energije i toplinska zaštita",
        "hu": "OIB-RL 6: Energiatakarékosság és hővédelem",
    },
    # ---- Bundesländer ----
    "bundesland_wien": {
        "de": "Wien",
        "en": "Vienna",
        "sl": "Dunaj",
        "hr": "Beč",
        "hu": "Bécs",
    },
    "bundesland_steiermark": {
        "de": "Steiermark",
        "en": "Styria",
        "sl": "Štajerska",
        "hr": "Štajerska",
        "hu": "Stájerország",
    },
    "bundesland_kaernten": {
        "de": "Kärnten",
        "en": "Carinthia",
        "sl": "Koroška",
        "hr": "Koruška",
        "hu": "Karintia",
    },
    "bundesland_burgenland": {
        "de": "Burgenland",
        "en": "Burgenland",
        "sl": "Gradiščanska",
        "hr": "Gradišće",
        "hu": "Burgenland",
    },
    "bundesland_tirol": {
        "de": "Tirol",
        "en": "Tyrol",
        "sl": "Tirolska",
        "hr": "Tirolska",
        "hu": "Tirol",
    },
    "bundesland_salzburg": {
        "de": "Salzburg",
        "en": "Salzburg",
        "sl": "Salzburg",
        "hr": "Salzburg",
        "hu": "Salzburg",
    },
    "bundesland_oberoesterreich": {
        "de": "Oberösterreich",
        "en": "Upper Austria",
        "sl": "Zgornja Avstrija",
        "hr": "Gornja Austrija",
        "hu": "Felső-Ausztria",
    },
    "bundesland_niederoesterreich": {
        "de": "Niederösterreich",
        "en": "Lower Austria",
        "sl": "Spodnja Avstrija",
        "hr": "Donja Austrija",
        "hu": "Alsó-Ausztria",
    },
    "bundesland_vorarlberg": {
        "de": "Vorarlberg",
        "en": "Vorarlberg",
        "sl": "Predarlberg",
        "hr": "Vorarlberg",
        "hu": "Vorarlberg",
    },
    # ---- Energieklassen ----
    "energieklasse_a_plus_plus": {
        "de": "Energieklasse A++ (Nullenergiegebäude)",
        "en": "Energy class A++ (Zero Energy Building)",
        "sl": "Energetski razred A++ (Ničenergijska stavba)",
        "hr": "Energetski razred A++ (Nulto energetska zgrada)",
        "hu": "A++ energiaosztály (Nulla energiájú épület)",
    },
    "energieklasse_a_plus": {
        "de": "Energieklasse A+ (Niedrigstenergie)",
        "en": "Energy class A+ (Near-Zero Energy Building)",
        "sl": "Energetski razred A+ (Skoraj nič-energijska stavba)",
        "hr": "Energetski razred A+ (Gotovo nulto energetska zgrada)",
        "hu": "A+ energiaosztály (Közel nulla energiaigényű épület)",
    },
    "energieklasse_a": {
        "de": "Energieklasse A (Niedrigenergie)",
        "en": "Energy class A (Low Energy Building)",
        "sl": "Energetski razred A (Nizkoenergijska stavba)",
        "hr": "Energetski razred A (Niskoenergetska zgrada)",
        "hu": "A energiaosztály (Alacsony energiaigényű épület)",
    },
    # ---- Grundriss / Räume ----
    "raum_wohnzimmer": {
        "de": "Wohnzimmer",
        "en": "Living room",
        "sl": "Dnevna soba",
        "hr": "Dnevna soba",
        "hu": "Nappali szoba",
    },
    "raum_schlafzimmer": {
        "de": "Schlafzimmer",
        "en": "Bedroom",
        "sl": "Spalnica",
        "hr": "Spavaća soba",
        "hu": "Hálószoba",
    },
    "raum_kinderzimmer": {
        "de": "Kinderzimmer",
        "en": "Children's room",
        "sl": "Otroška soba",
        "hr": "Dječja soba",
        "hu": "Gyerekszoba",
    },
    "raum_kueche": {
        "de": "Küche",
        "en": "Kitchen",
        "sl": "Kuhinja",
        "hr": "Kuhinja",
        "hu": "Konyha",
    },
    "raum_bad": {
        "de": "Badezimmer",
        "en": "Bathroom",
        "sl": "Kopalnica",
        "hr": "Kupaonica",
        "hu": "Fürdőszoba",
    },
    "raum_wc": {
        "de": "WC / Gäste-WC",
        "en": "Toilet / Guest WC",
        "sl": "Stranišče",
        "hr": "WC / Gostinjski WC",
        "hu": "WC / Vendég WC",
    },
    "raum_vorraum": {
        "de": "Vorraum / Eingang",
        "en": "Hallway / Entrance",
        "sl": "Predsoba / Vhod",
        "hr": "Predsoblje / Ulaz",
        "hu": "Előszoba / Bejárat",
    },
    "raum_abstellraum": {
        "de": "Abstellraum",
        "en": "Storage room",
        "sl": "Shramba",
        "hr": "Ostava",
        "hu": "Tároló helyiség",
    },
    # ---- Berechnungen ----
    "berechnung_uwert": {
        "de": "U-Wert Berechnung (Wärmedurchgangskoeffizient)",
        "en": "U-value calculation (thermal transmittance)",
        "sl": "Izračun U-vrednosti (toplotna prehodnost)",
        "hr": "Izračun U-vrijednosti (toplinska propusnost)",
        "hu": "U-érték számítás (hőátbocsátási tényező)",
    },
    "berechnung_hwb": {
        "de": "Heizwärmebedarf (HWB) Berechnung",
        "en": "Heating energy demand (HWB) calculation",
        "sl": "Izračun potrebe po ogrevalni energiji (HWB)",
        "hr": "Izračun potrebe za grijanjem (HWB)",
        "hu": "Fűtési energiaigény (HWB) számítás",
    },
    "berechnung_fgee": {
        "de": "Gesamtenergieeffizienzfaktor (fGEE) Berechnung",
        "en": "Overall energy efficiency factor (fGEE) calculation",
        "sl": "Izračun celotnega faktorja energijske učinkovitosti (fGEE)",
        "hr": "Izračun faktora ukupne energetske učinkovitosti (fGEE)",
        "hu": "Összenergia-hatékonysági tényező (fGEE) számítás",
    },
    "berechnung_stellplaetze": {
        "de": "Stellplatzberechnung (Parkplätze)",
        "en": "Parking space calculation",
        "sl": "Izračun parkirnih mest",
        "hr": "Izračun parkirnih mjesta",
        "hu": "Parkolóhely számítás",
    },
    # ---- Barrierefreiheit ----
    "barrierefreiheit": {
        "de": "Barrierefreiheit (OIB-RL 4)",
        "en": "Accessibility (OIB-RL 4)",
        "sl": "Dostopnost za invalide (OIB-RL 4)",
        "hr": "Pristupačnost (OIB-RL 4)",
        "hu": "Akadálymentesség (OIB-RL 4)",
    },
    "barrierefreiheit_rollstuhl": {
        "de": "Rollstuhlgerecht",
        "en": "Wheelchair accessible",
        "sl": "Primerno za invalidske vozičke",
        "hr": "Prilagođeno za invalidska kolica",
        "hu": "Kerekesszékes hozzáférés",
    },
    # ---- Ausschreibung ----
    "ausschreibung": {
        "de": "Ausschreibung (ÖNORM A 2063)",
        "en": "Tendering (ÖNORM A 2063)",
        "sl": "Razpis (ÖNORM A 2063)",
        "hr": "Nadmetanje (ÖNORM A 2063)",
        "hu": "Közbeszerzés (ÖNORM A 2063)",
    },
    "leistungsverzeichnis": {
        "de": "Leistungsverzeichnis (LV)",
        "en": "Bill of quantities (BoQ)",
        "sl": "Seznam del (LV)",
        "hr": "Popis radova (LV)",
        "hu": "Tételjegyzék (LV)",
    },
    # ---- Digital Twin ----
    "digital_twin": {
        "de": "Digitaler Zwilling",
        "en": "Digital Twin",
        "sl": "Digitalni dvojnik",
        "hr": "Digitalni dvojnik",
        "hu": "Digitális iker",
    },
    "energiemonitoring": {
        "de": "Energiemonitoring",
        "en": "Energy monitoring",
        "sl": "Energetski nadzor",
        "hr": "Energetski nadzor",
        "hu": "Energiafelügyelet",
    },
    "wartungsplan": {
        "de": "Wartungsplan",
        "en": "Maintenance plan",
        "sl": "Načrt vzdrževanja",
        "hr": "Plan održavanja",
        "hu": "Karbantartási terv",
    },
    # ---- Grundriss-KI ----
    "grundriss_ki": {
        "de": "KI-gestützte Grundrissoptimierung",
        "en": "AI-powered floor plan optimization",
        "sl": "Optimizacija tlorisa z umetno inteligenco",
        "hr": "Optimizacija tlocrta uz pomoć UI",
        "hu": "MI-alapú alaprajz-optimalizálás",
    },
    "grundriss_normkonform": {
        "de": "Normkonform gemäß Landesbauordnung",
        "en": "Compliant with state building code",
        "sl": "Skladno z deželno gradbeno uredbo",
        "hr": "Usklađeno s pokrajinskim građevinskim propisima",
        "hu": "Megfelel az állami építési kódexnek",
    },
    # ---- Fehler-Meldungen ----
    "fehler_bundesland_unbekannt": {
        "de": "Unbekanntes Bundesland. Gültig: Wien, NÖ, OÖ, Stmk, Ktn, Bgld, Sbg, Tirol, Vbg",
        "en": "Unknown federal state. Valid: Wien, NÖ, OÖ, Stmk, Ktn, Bgld, Sbg, Tirol, Vbg",
        "sl": "Neznana zvezna dežela. Veljavne: Wien, NÖ, OÖ, Stmk, Ktn, Bgld, Sbg, Tirol, Vbg",
        "hr": "Nepoznata savezna pokrajina. Valjane: Wien, NÖ, OÖ, Stmk, Ktn, Bgld, Sbg, Tirol, Vbg",
        "hu": "Ismeretlen szövetségi tartomány. Érvényes: Wien, NÖ, OÖ, Stmk, Ktn, Bgld, Sbg, Tirol, Vbg",
    },
    "fehler_wert_ungueltig": {
        "de": "Ungültiger Wert. Bitte Eingabe prüfen.",
        "en": "Invalid value. Please check your input.",
        "sl": "Neveljavna vrednost. Prosimo, preverite vnos.",
        "hr": "Nevažeća vrijednost. Provjerite unos.",
        "hu": "Érvénytelen érték. Kérjük ellenőrizze a bemenetet.",
    },
    # ---- Förderungen ----
    "foerderungen": {
        "de": "Förderungen und Zuschüsse",
        "en": "Grants and subsidies",
        "sl": "Subvencije in dotacije",
        "hr": "Potpore i subvencije",
        "hu": "Támogatások és ösztönzők",
    },
    "wohnbaufoerderung": {
        "de": "Wohnbauförderung",
        "en": "Housing construction subsidy",
        "sl": "Subvencija za stanovanjsko gradnjo",
        "hr": "Potpora za stambenu gradnju",
        "hu": "Lakásépítési támogatás",
    },
    # ---- Einreichung ----
    "einreichung": {
        "de": "Baueinreichung",
        "en": "Building permit application",
        "sl": "Gradbena vloga",
        "hr": "Zahtjev za građevinsku dozvolu",
        "hu": "Építési engedély kérelem",
    },
    "baugenehmigung": {
        "de": "Baugenehmigung",
        "en": "Building permit",
        "sl": "Gradbeno dovoljenje",
        "hr": "Građevinska dozvola",
        "hu": "Építési engedély",
    },
    # ---- Allgemein ----
    "berechnen": {
        "de": "Berechnen",
        "en": "Calculate",
        "sl": "Izračunaj",
        "hr": "Izračunaj",
        "hu": "Számítás",
    },
    "pruefe": {
        "de": "Prüfen",
        "en": "Check",
        "sl": "Preveri",
        "hr": "Provjeri",
        "hu": "Ellenőrzés",
    },
    "ergebnis": {
        "de": "Ergebnis",
        "en": "Result",
        "sl": "Rezultat",
        "hr": "Rezultat",
        "hu": "Eredmény",
    },
    "hinweis": {
        "de": "Hinweis",
        "en": "Note",
        "sl": "Opomba",
        "hr": "Napomena",
        "hu": "Megjegyzés",
    },
    "warnung": {
        "de": "Warnung",
        "en": "Warning",
        "sl": "Opozorilo",
        "hr": "Upozorenje",
        "hu": "Figyelmeztetés",
    },
    "disclaimer": {
        "de": (
            "ORION Architekt-AT dient als Planungshilfe. "
            "Alle Angaben ohne Gewähr. Verbindliche Auskünfte nur durch zugelassene Ziviltechniker."
        ),
        "en": (
            "ORION Architekt-AT serves as a planning aid. "
            "All information without guarantee. Binding advice only from licensed engineers."
        ),
        "sl": (
            "ORION Architekt-AT služi kot plansko orodje. "
            "Vsi podatki brez jamstva. Zavezujoče informacije le od pooblaščenih inženirjev."
        ),
        "hr": (
            "ORION Architekt-AT služi kao pomoć pri planiranju. "
            "Svi podaci bez jamstva. Obvezujući savjeti samo od ovlaštenih inženjera."
        ),
        "hu": (
            "Az ORION Architekt-AT tervezési segédeszköz. "
            "Minden adat garancia nélkül. Kötelező érvényű tanácsadás csak engedéllyel rendelkező mérnököktől."
        ),
    },
    # ---- Sprache ----
    "sprache_geaendert": {
        "de": "Sprache wurde auf Deutsch geändert",
        "en": "Language changed to English",
        "sl": "Jezik je spremenjen na slovenščino",
        "hr": "Jezik je promijenjen na hrvatski",
        "hu": "A nyelv magyarra változott",
    },
}


# ---------------------------------------------------------------------------
# Öffentliche API
# ---------------------------------------------------------------------------


def t(schluessel: str, sprache: str | SpracheCode = SpracheCode.DE) -> str:
    """
    Gibt die Übersetzung eines Schlüssels in der angegebenen Sprache zurück.
    Fallback: Deutsch, dann der Schlüssel selbst.

    Args:
        schluessel: Übersetzungsschlüssel (snake_case)
        sprache: SpracheCode oder zweistelliger Sprachcode ("de", "en", "sl", "hr", "hu")

    Returns:
        Übersetzter String
    """
    lang = sprache.value if isinstance(sprache, SpracheCode) else str(sprache).lower()[:2]

    eintrag = _TRANSLATIONS.get(schluessel)
    if eintrag is None:
        logger.debug("i18n: Schlüssel '%s' nicht gefunden", schluessel)
        return schluessel

    if lang in eintrag:
        return eintrag[lang]
    # Fallback Deutsch
    if "de" in eintrag:
        logger.debug("i18n: Kein '%s' für Sprache '%s', Fallback auf Deutsch", schluessel, lang)
        return eintrag["de"]
    return schluessel


def get_alle_schluessel() -> list[str]:
    """Gibt alle verfügbaren Übersetzungsschlüssel zurück."""
    return list(_TRANSLATIONS)


def get_alle_uebersetzungen(sprache: str | SpracheCode) -> Dict[str, str]:
    """
    Gibt alle Übersetzungen für eine Sprache als Dict zurück.
    Nützlich für Frontend-Locale-Bundles.
    """
    lang = sprache.value if isinstance(sprache, SpracheCode) else str(sprache).lower()[:2]
    return {k: (v.get(lang) or v.get("de") or k) for k, v in _TRANSLATIONS.items()}


def parse_accept_language(accept_language_header: Optional[str]) -> SpracheCode:
    """
    Parst den HTTP Accept-Language Header und gibt den besten SpracheCode zurück.

    Beispiel: "sl-SI,sl;q=0.9,de;q=0.8,en;q=0.7" → SpracheCode.SL
    """
    if not accept_language_header:
        return SpracheCode.DE

    bekannte = {s.value for s in SpracheCode}
    # Accept-Language parsen: "lang-REGION;q=0.9, lang2;q=0.8"
    for teil in accept_language_header.replace(" ", "").split(","):
        lang_q = teil.split(";")[0]
        lang_code = lang_q.split("-")[0].lower()
        if lang_code in bekannte:
            return SpracheCode(lang_code)

    return SpracheCode.DE
