"""
Bundesland-specific regulations Router
All 9 Austrian Bundesländer with complete building regulation data.
"""

from typing import Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

router = APIRouter()


class BundeslandInfo(BaseModel):
    """Bundesland information"""

    name: str
    kuerzel: str
    bauordnung: str
    bauordnung_kurz: str
    raumordnung: str
    oib_2023_status: str
    stellplatz_factor: float
    aufzug_ab_geschoss: int
    schneelastzone: str
    erdbebenzone: str
    windzone: str
    digitale_einreichung: str
    kontakt: str
    besonderheiten: List[str]
    regionale_kostenfaktor: float


class BundeslandSummary(BaseModel):
    """Reduced Bundesland summary for list views"""

    kuerzel: str
    name: str
    bauordnung_kurz: str
    oib_2023_status: str
    digitale_einreichung: str


# Complete data for all 9 Austrian Bundesländer
_BUNDESLAND_DATA: Dict[str, BundeslandInfo] = {
    "burgenland": BundeslandInfo(
        name="Burgenland",
        kuerzel="B",
        bauordnung="Burgenländisches Baugesetz 1997 (idF LGBl. 2023)",
        bauordnung_kurz="Bgld. BauG 1997",
        raumordnung="Burgenländisches Raumplanungsgesetz 2019",
        oib_2023_status="OIB-RL 1-5: in Kraft, OIB-RL 6: in Kraft",
        stellplatz_factor=1.0,
        aufzug_ab_geschoss=4,
        schneelastzone="1-2",
        erdbebenzone="1-3 (Südburgenland höher)",
        windzone="2-3 (Pannonische Tiefebene windreich)",
        digitale_einreichung="Teilweise verfügbar, gemeindespezifisch",
        kontakt="Amt der Burgenländischen Landesregierung, Abt. 5 - Baudirektion",
        besonderheiten=[
            "Neusiedler See: Landschaftsschutz-Sonderregelungen",
            "Grenznahe Gebiete: besondere Widmungsvorschriften",
            "Weinbaugebiete: Gestaltungsvorschriften für Kellergassen",
            "Thermenregion: touristische Sonderwidmungen",
        ],
        regionale_kostenfaktor=0.90,
    ),
    "kaernten": BundeslandInfo(
        name="Kärnten",
        kuerzel="K",
        bauordnung="Kärntner Bauordnung 1996 (idF LGBl. 2024)",
        bauordnung_kurz="K-BO 1996",
        raumordnung="Kärntner Gemeindeplanungsgesetz 1995",
        oib_2023_status="OIB-RL 1-5: in Kraft, OIB-RL 6: in Kraft",
        stellplatz_factor=1.0,
        aufzug_ab_geschoss=4,
        schneelastzone="2-4 (Oberkärnten alpin)",
        erdbebenzone="3-4 (seismisch aktiv!)",
        windzone="1-2",
        digitale_einreichung="Einzelne Gemeinden, kein flächendeckendes System",
        kontakt="Amt der Kärntner Landesregierung, Abt. 7 - Wirtschaftsrecht und Infrastruktur",
        besonderheiten=[
            "Seenlandschaft: Uferzonenwidmung und Seenschutz",
            "Zweisprachige Gebiete: Slowenisch/Deutsch — Beschilderung beachten",
            "Alpine Lagen: erhöhte Schneelasten in Oberkärnten",
            "Holzbau-Tradition: vereinfachte Verfahren für Holzbauten teilweise",
            "Oberkärnten (Mölltal, Liesertal): erhöhtes Radonpotenzial",
        ],
        regionale_kostenfaktor=0.93,
    ),
    "niederoesterreich": BundeslandInfo(
        name="Niederösterreich",
        kuerzel="NÖ",
        bauordnung="NÖ Bauordnung 2014 (idF LGBl. 2024)",
        bauordnung_kurz="NÖ BO 2014",
        raumordnung="NÖ Raumordnungsgesetz 2014",
        oib_2023_status="OIB-RL 1-5: in Kraft, OIB-RL 6: in Kraft",
        stellplatz_factor=1.0,
        aufzug_ab_geschoss=4,
        schneelastzone="1-3 (Waldviertel/Alpen höher)",
        erdbebenzone="1-3 (Wiener Becken seismisch aktiv)",
        windzone="1-3",
        digitale_einreichung="NÖ Baubehörde-Online für Formulare, Plan-Upload teilweise",
        kontakt="Amt der NÖ Landesregierung, Gruppe Raumordnung, Umwelt und Verkehr",
        besonderheiten=[
            "Größtes Bundesland: sehr unterschiedliche Klimazonen",
            "Weinviertel: Kellergassen-Schutzgebiete",
            "Wachau: UNESCO-Welterbe — strenge Gestaltungsvorschriften",
            "Speckgürtel Wien: hohe Nachverdichtung, Bebauungspläne prüfen!",
            "Waldviertel: Radonvorsorgegebiet",
        ],
        regionale_kostenfaktor=0.98,
    ),
    "oberoesterreich": BundeslandInfo(
        name="Oberösterreich",
        kuerzel="OÖ",
        bauordnung="OÖ Bauordnung 1994 (idF LGBl. 2024)",
        bauordnung_kurz="OÖ BauO 1994",
        raumordnung="OÖ Raumordnungsgesetz 1994",
        oib_2023_status="OIB-RL 1-5: in Kraft, OIB-RL 6: in Kraft",
        stellplatz_factor=1.0,
        aufzug_ab_geschoss=4,
        schneelastzone="1-3 (Alpenvorland bis alpin)",
        erdbebenzone="1-2",
        windzone="1-2",
        digitale_einreichung="Über Amtswege OÖ teilweise digital",
        kontakt="Amt der OÖ Landesregierung, Direktion Straßenbau und Verkehr, Abt. Bau- und Raumordnung",
        besonderheiten=[
            "Industriegebiet Linz: Sonderwidmungen für Betriebsbauten",
            "Salzkammergut: Landschaftsschutz und Seenregelungen",
            "Innviertel: Hochwasserschutz besonders relevant",
            "Mühlviertel: Radonvorsorge beachten",
            "Traunviertel: alpine Schneelastzonen",
        ],
        regionale_kostenfaktor=1.00,
    ),
    "salzburg": BundeslandInfo(
        name="Salzburg",
        kuerzel="S",
        bauordnung="Salzburger Baupolizeigesetz 1997 (idF LGBl. 2024)",
        bauordnung_kurz="Sbg. BauPolG 1997",
        raumordnung="Salzburger Raumordnungsgesetz 2009",
        oib_2023_status="OIB-RL 1-5: in Kraft, ⚠️ OIB-RL 6: NICHT übernommen (Sonderweg!)",
        stellplatz_factor=1.3,
        aufzug_ab_geschoss=4,
        schneelastzone="2-5 (Innergebirg sehr hoch!)",
        erdbebenzone="2-4",
        windzone="1-2",
        digitale_einreichung="Baurechtsportal Salzburg teilweise verfügbar",
        kontakt="Amt der Salzburger Landesregierung, Abt. 10 - Wohnen und Raumplanung",
        besonderheiten=[
            "⚠️ SONDERWEG ENERGIE: OIB-RL 6 wurde NICHT übernommen! Salzburger WSchVO gilt stattdessen.",
            "Altstadt Salzburg: UNESCO-Welterbe — strenge Denkmalschutzauflagen",
            "Pinzgau/Pongau: extreme Schneelasten, alpine Bauweise erforderlich",
            "Flachgau: Speckgürtel Salzburg — Nachverdichtungsvorschriften",
            "Lungau und Teile des Pinzgau: erhöhte Radonkonzentrationen",
        ],
        regionale_kostenfaktor=1.10,
    ),
    "steiermark": BundeslandInfo(
        name="Steiermark",
        kuerzel="ST",
        bauordnung="Steiermärkisches Baugesetz 1995 (idF LGBl. 2024)",
        bauordnung_kurz="Stmk. BauG 1995",
        raumordnung="Steiermärkisches Raumordnungsgesetz 2010",
        oib_2023_status="OIB-RL 1-5: in Kraft, OIB-RL 6: in Kraft",
        stellplatz_factor=1.0,
        aufzug_ab_geschoss=4,
        schneelastzone="1-4 (Dachstein/Obersteiermark hoch)",
        erdbebenzone="2-4 (Mürztal seismisch aktiv!)",
        windzone="1-2",
        digitale_einreichung="Baubehörde Graz digital, Land unterschiedlich",
        kontakt="Amt der Steiermärkischen Landesregierung, A13 - Umwelt und Raumordnung",
        besonderheiten=[
            "Graz: eigene Altstadterhaltungszone — Gestaltungsrichtlinien",
            "Weinbaugebiete Südsteiermark: Landschaftsschutz",
            "Mur-Mürz-Furche: Hochwasserschutz-Auflagen",
            "Obersteiermark: alpine Schneelastzonen, Erdbebenzone beachten",
            "Weststeiermark und Teile des Mürztal: Radonvorsorge prüfen",
        ],
        regionale_kostenfaktor=0.95,
    ),
    "tirol": BundeslandInfo(
        name="Tirol",
        kuerzel="T",
        bauordnung="Tiroler Bauordnung 2022 (TBO 2022, idF LGBl. 7/2025)",
        bauordnung_kurz="TBO 2022",
        raumordnung="Tiroler Raumordnungsgesetz 2022",
        oib_2023_status="OIB-RL 1-5: in Kraft, OIB-RL 6: in Kraft",
        stellplatz_factor=1.5,
        aufzug_ab_geschoss=4,
        schneelastzone="3-5 (hochalpin, seehöhenabhängig)",
        erdbebenzone="3-4 (seismisch aktiv!)",
        windzone="1-2 (Föhn beachten!)",
        digitale_einreichung="Ja, seit 01.07.2024 über tiris.gv.at",
        kontakt="Amt der Tiroler Landesregierung, Abt. Bau- und Raumordnungsrecht",
        besonderheiten=[
            "Bauunterlagenverordnung 2024 (LGBl. 42/2024, ab 18.07.2024)",
            "Digitale Einreichung seit 01.07.2024 möglich",
            "Lawinenschutz und Hangwasserschutz bei alpinen Lagen",
            "Radonvorsorgegebiet — Radonschutzmaßnahmen im Keller",
            "Tourismuszone — besondere Gestaltungsvorschriften",
            "PV-Anlagen: 1. Tiroler Erneuerbaren Ausbaugesetz seit 15.11.2024",
        ],
        regionale_kostenfaktor=1.12,
    ),
    "vorarlberg": BundeslandInfo(
        name="Vorarlberg",
        kuerzel="V",
        bauordnung="Vorarlberger Baugesetz (idF LGBl. 2024)",
        bauordnung_kurz="Vlbg. BauG",
        raumordnung="Vorarlberger Raumplanungsgesetz",
        oib_2023_status="OIB-RL 1-5: in Kraft (zuletzt übernommen Jan 2022), OIB-RL 6: in Kraft",
        stellplatz_factor=1.4,
        aufzug_ab_geschoss=4,
        schneelastzone="3-5 (hochalpin)",
        erdbebenzone="2-3",
        windzone="1-2",
        digitale_einreichung="Teilweise über Gemeinde-Portale",
        kontakt="Amt der Vorarlberger Landesregierung, Abt. Raumplanung und Baurecht (VIIa)",
        besonderheiten=[
            "Vorarlberger Holzbau-Tradition: führend in nachhaltigem Bauen",
            "Rheintal: Hochwasserschutz und Grundwasserschutz",
            "Bregenzerwald: Landschaftsschutz-Auflagen",
            "Montafon/Arlberg: extreme Schneelasten",
            "Passivhaus-Standard: Vorarlberg hat strengere Energiestandards als OIB-RL 6",
            "Bregenzerwald/Großwalsertal: Radonpotenzial prüfen",
        ],
        regionale_kostenfaktor=1.10,
    ),
    "wien": BundeslandInfo(
        name="Wien",
        kuerzel="W",
        bauordnung="Wiener Bauordnung (BO für Wien, idF LGBl. 2024)",
        bauordnung_kurz="BO für Wien",
        raumordnung="In Bauordnung integriert (Flächenwidmungs- und Bebauungsplan)",
        oib_2023_status="OIB-RL 1-5: in Kraft, OIB-RL 6: in Kraft",
        stellplatz_factor=1.2,
        aufzug_ab_geschoss=3,
        schneelastzone="1-2",
        erdbebenzone="2-3 (Wiener Becken)",
        windzone="1-2",
        digitale_einreichung="Ja, BRISE-Vienna Pilotbetrieb + mein.wien.gv.at",
        kontakt="MA 37 — Baupolizei, tdi@ma37.wien.gv.at, +43 1 4000 37300",
        besonderheiten=[
            "BRISE-Vienna: Digitale Baugenehmigung mit BIM (Pilotbetrieb)",
            "86% der Prüfpunkte automatisiert prüfbar",
            "IFC-Format für BIM-Einreichung (openBIM)",
            "Wiener Altstadterhaltung: Schutzzonen 1-4",
            "Hochhauskonzept Wien: ab 35m Höhe Sonderverfahren",
            "Gründerzeit-Gebiete: Fassadenerhaltung",
            "MA 37 (Baupolizei) als zentrale Baubehörde",
            "Aufzugspflicht bereits ab 3 Obergeschoß (strenger als andere BL)",
        ],
        regionale_kostenfaktor=1.15,
    ),
}


@router.get("/", response_model=List[BundeslandSummary])
async def list_bundeslaender():
    """
    🗺️ **Alle 9 Österreichischen Bundesländer**

    Listet alle Bundesländer mit Kurzinfos zu Bauordnung und OIB-Status.
    """
    return [
        BundeslandSummary(
            kuerzel=bl.kuerzel,
            name=bl.name,
            bauordnung_kurz=bl.bauordnung_kurz,
            oib_2023_status=bl.oib_2023_status,
            digitale_einreichung=bl.digitale_einreichung,
        )
        for bl in _BUNDESLAND_DATA.values()
    ]


@router.get("/compare")
async def compare_bundeslaender(
    bundeslaender: List[str] = Query(
        ...,
        description="Komma-getrennte Liste von Bundesland-Schlüsseln (z.B. wien,tirol,salzburg)",
        min_length=1,
    ),
):
    """
    🔍 **Bundesländer-Vergleich**

    Vergleicht Bauvorschriften mehrerer Bundesländer side-by-side.
    Ideal für Projektstandort-Entscheidungen.

    Parameter: ?bundeslaender=wien&bundeslaender=tirol&bundeslaender=salzburg
    """
    result = {}
    unknown = []
    for key in bundeslaender:
        bl_key = key.lower().strip()
        if bl_key not in _BUNDESLAND_DATA:
            unknown.append(key)
        else:
            result[bl_key] = _BUNDESLAND_DATA[bl_key]

    if unknown:
        raise HTTPException(
            status_code=404,
            detail=f"Unbekannte Bundesländer: {unknown}. Gültige Werte: {list(_BUNDESLAND_DATA.keys())}",
        )

    return {
        "verglichen": list(result.keys()),
        "daten": {
            key: {
                "name": bl.name,
                "kuerzel": bl.kuerzel,
                "bauordnung": bl.bauordnung,
                "oib_2023_status": bl.oib_2023_status,
                "stellplatz_factor": bl.stellplatz_factor,
                "aufzug_ab_geschoss": bl.aufzug_ab_geschoss,
                "schneelastzone": bl.schneelastzone,
                "erdbebenzone": bl.erdbebenzone,
                "digitale_einreichung": bl.digitale_einreichung,
                "regionale_kostenfaktor": bl.regionale_kostenfaktor,
                "besonderheiten": bl.besonderheiten,
            }
            for key, bl in result.items()
        },
        "hinweis": (
            "Alle Angaben nach Stand der aktuellen Landesgesetze. "
            "Maßgeblich ist immer die aktuelle Fassung auf ris.bka.gv.at."
        ),
    }


@router.get("/{bundesland}", response_model=BundeslandInfo)
async def get_bundesland_info(bundesland: str):
    """
    🗺️ **Bundesland-Detailinformation**

    Vollständige Baurechts-Information für ein Bundesland:
    - Bauordnung und Raumordnung (aktueller Stand)
    - OIB-RL 2023 Übernahmestatus (inkl. Salzburg-Sonderweg!)
    - Stellplatz-Faktor, Aufzugspflicht
    - Schneelastzonen, Erdbebenzonen, Windzonen
    - Digitale Einreichung (Stand 2024/25)
    - Behördenkontakt
    - Bundesland-spezifische Besonderheiten
    """
    bundesland_lower = bundesland.lower()
    if bundesland_lower not in _BUNDESLAND_DATA:
        raise HTTPException(
            status_code=404,
            detail=(
                f"Bundesland '{bundesland}' nicht gefunden. "
                f"Gültige Werte: {list(_BUNDESLAND_DATA.keys())}"
            ),
        )
    return _BUNDESLAND_DATA[bundesland_lower]


@router.get("/{bundesland}/stellplaetze")
async def get_stellplatz_requirements(bundesland: str, wohnungen: int):
    """
    🅿️ **Stellplatz-Anforderungen je Bundesland**

    Berechnet die erforderliche Anzahl an PKW-Stellplätzen nach der
    bundeslandspezifischen Bauordnung.
    """
    info = await get_bundesland_info(bundesland)
    required = int(wohnungen * info.stellplatz_factor)

    return {
        "bundesland": bundesland,
        "bundesland_name": info.name,
        "wohnungen": wohnungen,
        "stellplatz_faktor": info.stellplatz_factor,
        "erforderliche_stellplaetze": required,
        "bauordnung": info.bauordnung,
        "hinweis": (
            "Der Faktor gibt die Mindestanzahl je Wohnung an. "
            "Bebauungsplan und Gemeindesatzungen können abweichen."
        ),
    }


@router.get("/{bundesland}/aufzug")
async def get_aufzug_requirements(bundesland: str, geschosse: int):
    """
    🛗 **Aufzugspflicht je Bundesland**

    Prüft ob ein Aufzug nach der Bauordnung des Bundeslandes erforderlich ist.
    Achtung: Wien verlangt Aufzug bereits ab dem 3. Obergeschoß!
    """
    info = await get_bundesland_info(bundesland)
    required = geschosse >= info.aufzug_ab_geschoss

    return {
        "bundesland": bundesland,
        "bundesland_name": info.name,
        "geschosse": geschosse,
        "aufzug_erforderlich": required,
        "aufzugspflicht_ab_geschoss": info.aufzug_ab_geschoss,
        "bauordnung": info.bauordnung,
        "hinweis": (
            "Aufzüge müssen nach ÖNORM B 1600 (Barrierefreiheit) ausgeführt werden. "
            "Dimensionen: mind. 1,10m × 1,40m Kabine (Rollstuhl-tauglich)."
        ),
    }


@router.get("/{bundesland}/foerderungen")
async def get_foerderungen(bundesland: str):
    """
    💶 **Wohnbauförderung je Bundesland**

    Übersicht der wichtigsten Bundes- und Landesförderungen für Neubau und Sanierung.
    Quellen: Bundesministerium, Landesregierungen (Stand 2025/2026).

    ⚠️ Förderungsbeträge können sich ändern — immer aktuelle Info beim Bundesland einholen.
    """
    bundesland_lower = bundesland.lower()
    if bundesland_lower not in _BUNDESLAND_DATA:
        raise HTTPException(
            status_code=404,
            detail=f"Bundesland '{bundesland}' nicht gefunden. Gültige Werte: {list(_BUNDESLAND_DATA.keys())}",
        )

    bl = _BUNDESLAND_DATA[bundesland_lower]

    # Bundesweite Förderungen (immer verfügbar)
    bundes_foerderungen = [
        {
            "name": "Sanierungsbonus 2025/2026",
            "betrag": "bis 42.000 € (thermische Sanierung)",
            "voraussetzung": "Umfassende thermische Sanierung, Energieausweis vorher/nachher",
            "info_url": "https://www.sanierungsbonus.at",
            "typ": "Bundesförderung",
        },
        {
            "name": "Raus aus Öl und Gas",
            "betrag": "bis 7.500 € (Heiztausch)",
            "voraussetzung": "Tausch fossiler Heizung (Öl/Gas) gegen erneuerbare Energie",
            "info_url": "https://www.raus-aus-oel.at",
            "typ": "Bundesförderung",
        },
        {
            "name": "Photovoltaik-Förderung (EAG)",
            "betrag": "bis 285 €/kWp",
            "voraussetzung": "Neuanlagen, Erweiterungen, Speicher",
            "info_url": "https://www.oem-ag.at",
            "typ": "Bundesförderung",
        },
    ]

    # Landesspezifische Förderungen
    landes_foerderungen: Dict[str, List[Dict]] = {
        "burgenland": [
            {
                "name": "Bgld. Wohnbauförderung",
                "betrag": "bis 55.000 € Darlehen",
                "info_url": "https://www.wohnbau.bgld.gv.at",
                "typ": "Landesförderung",
            },
            {
                "name": "Öko-Zuschlag Burgenland",
                "betrag": "Zusatzförderung für Passivhaus/Klimaaktiv",
                "info_url": "https://www.wohnbau.bgld.gv.at",
                "typ": "Landesförderung",
            },
        ],
        "kaernten": [
            {
                "name": "Kärntner Wohnbauförderung",
                "betrag": "bis 60.000 € Darlehen (Eigenheim)",
                "info_url": "https://www.ktn.gv.at/wohnbau",
                "typ": "Landesförderung",
            },
            {
                "name": "Energiebonus Kärnten",
                "betrag": "Zuschlag für Klimaaktiv-Standard",
                "info_url": "https://www.ktn.gv.at",
                "typ": "Landesförderung",
            },
        ],
        "niederoesterreich": [
            {
                "name": "NÖ Wohnbauförderung (Eigenheimerrichtung)",
                "betrag": "bis 85.000 € Darlehen",
                "info_url": "https://www.noe.gv.at/wohnbau",
                "typ": "Landesförderung",
            },
            {
                "name": "NÖ Sanierungsförderung",
                "betrag": "bis 30.000 € Zuschuss",
                "info_url": "https://www.noe.gv.at/wohnbau",
                "typ": "Landesförderung",
            },
        ],
        "oberoesterreich": [
            {
                "name": "OÖ Wohnbauförderung",
                "betrag": "bis 72.000 € Darlehen (Eigenheim)",
                "info_url": "https://www.land-oberoesterreich.gv.at",
                "typ": "Landesförderung",
            },
            {
                "name": "OÖ Energiespar-Bonus",
                "betrag": "Zusatzförderung bei HWB < 30 kWh/m²a",
                "info_url": "https://www.land-oberoesterreich.gv.at",
                "typ": "Landesförderung",
            },
        ],
        "salzburg": [
            {
                "name": "Sbg. Wohnbauförderung",
                "betrag": "bis 78.000 € Darlehen",
                "info_url": "https://www.salzburg.gv.at/wohnbau",
                "typ": "Landesförderung",
            },
            {
                "name": "Sbg. Nachhaltigkeitsbonus",
                "betrag": "bis 15.000 € Zuschuss für Passivhaus",
                "info_url": "https://www.salzburg.gv.at",
                "typ": "Landesförderung",
            },
        ],
        "steiermark": [
            {
                "name": "Stmk. Wohnbauförderung",
                "betrag": "bis 70.000 € Darlehen",
                "info_url": "https://www.wohnbau.steiermark.at",
                "typ": "Landesförderung",
            },
            {
                "name": "Stmk. Ökobonus",
                "betrag": "Zuschlag für Holzbau/Passivhaus",
                "info_url": "https://www.wohnbau.steiermark.at",
                "typ": "Landesförderung",
            },
        ],
        "tirol": [
            {
                "name": "Tiroler Wohnbauförderung (Eigenheim)",
                "betrag": "bis 66.000 € Darlehen + Annuitätenzuschuss",
                "info_url": "https://www.tirol.gv.at/wohnbau",
                "typ": "Landesförderung",
            },
            {
                "name": "Tiroler Sanierungsförderung",
                "betrag": "bis 30.000 € Zuschuss/Darlehen",
                "info_url": "https://www.tirol.gv.at/wohnbau",
                "typ": "Landesförderung",
            },
            {
                "name": "PV-Förderung Tirol",
                "betrag": "Zusatzförderung zu Bundesförderung",
                "info_url": "https://www.tirol.gv.at/energie",
                "typ": "Landesförderung",
            },
        ],
        "vorarlberg": [
            {
                "name": "Vlbg. Wohnbauförderung",
                "betrag": "bis 80.000 € Darlehen",
                "info_url": "https://www.vorarlberg.at/wohnbau",
                "typ": "Landesförderung",
            },
            {
                "name": "Vlbg. Energieautonomiebonus",
                "betrag": "Zuschlag für Plusenergiehaus",
                "info_url": "https://www.vorarlberg.at/energieautonomie",
                "typ": "Landesförderung",
            },
        ],
        "wien": [
            {
                "name": "Wiener Wohnbauförderung",
                "betrag": "bis 90.000 € Darlehen",
                "info_url": "https://www.wohnberatung-wien.at",
                "typ": "Landesförderung",
            },
            {
                "name": "Wiener Sanierungsförderung",
                "betrag": "bis 35.000 € Zuschuss",
                "info_url": "https://www.wohnberatung-wien.at",
                "typ": "Landesförderung",
            },
            {
                "name": "Wien Energie Förderung (PV, Speicher, Wärmepumpe)",
                "betrag": "je nach Anlage",
                "info_url": "https://www.wienenergie.at",
                "typ": "Landesförderung",
            },
        ],
    }

    return {
        "bundesland": bundesland_lower,
        "bundesland_name": bl.name,
        "bundesfoerderungen": bundes_foerderungen,
        "landesfoerderungen": landes_foerderungen.get(bundesland_lower, []),
        "hinweis": (
            "⚠️ Förderungsbeträge und -bedingungen ändern sich regelmäßig. "
            "Immer aktuelle Konditionen beim Bundesland und beim Bundesministerium prüfen. "
            "Stand: 2025/2026."
        ),
        "quellen": [
            "https://www.sanierungsbonus.at",
            f"https://ris.bka.gv.at (Gesetze {bl.name})",
        ],
    }
