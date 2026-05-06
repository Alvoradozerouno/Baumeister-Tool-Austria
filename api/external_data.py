"""
ORION Architekt-AT — Echte externe Datenzugriffe
=================================================
RIS Austria, OIB, hora.gv.at — HTTP-Scraping mit TTL-Cache.

RIS Austria hat KEINE öffentliche REST-API, deshalb HTML-Scraping + RSS.
OIB (oib.or.at) bietet RSS-Feed für News.
hora.gv.at bietet eine GeoJSON/WMS-API für Gefahrenzonenpläne.
"""

import asyncio
import hashlib
import json
import logging
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Cache (file-based, TTL = 6h)
# ---------------------------------------------------------------------------

_CACHE_DIR = Path("/tmp/orion_external_cache")
_CACHE_DIR.mkdir(exist_ok=True)
_TTL_SECONDS = 6 * 3600   # 6 hours


def _cache_key(key: str) -> Path:
    h = hashlib.sha256(key.encode()).hexdigest()[:16]
    return _CACHE_DIR / f"{h}.json"


def _cache_get(key: str) -> Optional[Any]:
    p = _cache_key(key)
    if p.exists():
        data = json.loads(p.read_text())
        if time.time() - data.get("ts", 0) < _TTL_SECONDS:
            return data.get("value")
    return None


def _cache_set(key: str, value: Any) -> None:
    p = _cache_key(key)
    p.write_text(json.dumps({"ts": time.time(), "value": value}))


# ---------------------------------------------------------------------------
# RIS Austria — Bundesrecht aktuell
# ---------------------------------------------------------------------------

_RIS_BASE = "https://www.ris.bka.gv.at"
_RIS_SEARCH = (
    "https://www.ris.bka.gv.at/Ergebnis.wxe"
    "?Abfrage=BgblAuth&Titel=Bauordnung&SuchTyp=Unscharf&ImRisSeit=Undefined&ResultPageSize=10"
)

_OIB_NEWS_URL = "https://www.oib.or.at/de/news-und-publikationen/neuigkeiten"
_OIB_RSS = "https://www.oib.or.at/rss.xml"

# hora.gv.at WMS/REST-Endpunkte (öffentlich zugänglich)
_HORA_API = "https://hora.gv.at/webservices/rest/hazard"

# Österreichisches Normeninstitut (ASI) Neuigkeiten
_ASI_URL = "https://www.austrian-standards.at/de/news"


async def fetch_ris_updates(bundesland: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Scrape RIS Austria für aktuelle Baurechts-Änderungen.
    Gibt die neuesten BGBl-Einträge zurück.
    """
    cache_key = f"ris_updates_{bundesland or 'all'}"
    cached = _cache_get(cache_key)
    if cached:
        return cached

    results: List[Dict[str, Any]] = []
    try:
        async with httpx.AsyncClient(timeout=15, follow_redirects=True,
                                     headers={"User-Agent": "ORION-ArchitektAT/3.0"}) as client:
            # Search BGBl for recent Baurecht entries
            params = {
                "Abfrage": "BgblAuth",
                "Titel": "Bauordnung" if not bundesland else f"Bauordnung {bundesland}",
                "ImRisSeit": "EinemMonat",
                "ResultPageSize": "20",
                "SuchTyp": "Unscharf",
            }
            r = await client.get(
                "https://www.ris.bka.gv.at/Ergebnis.wxe",
                params=params,
            )
            if r.status_code == 200:
                soup = BeautifulSoup(r.text, "lxml")
                # RIS result rows
                for row in soup.select("table.search-result tr")[:15]:
                    cells = row.select("td")
                    if len(cells) >= 3:
                        title = cells[0].get_text(strip=True)
                        date_text = cells[1].get_text(strip=True) if len(cells) > 1 else ""
                        link = cells[0].find("a")
                        url = (_RIS_BASE + link["href"]) if link and link.get("href") else _RIS_BASE
                        if title:
                            results.append({
                                "source": "RIS Austria (BGBl)",
                                "title": title,
                                "date": date_text,
                                "url": url,
                                "type": "legislation",
                            })

            # Also try OIB news page
            r2 = await client.get(_OIB_NEWS_URL)
            if r2.status_code == 200:
                soup2 = BeautifulSoup(r2.text, "lxml")
                for article in soup2.select("article, .news-item, .teaser")[:8]:
                    title_el = article.find(["h2", "h3", "h4"])
                    link_el = article.find("a")
                    date_el = article.find(["time", ".date", "span"])
                    if title_el:
                        title = title_el.get_text(strip=True)
                        url = link_el["href"] if link_el and link_el.get("href") else _OIB_NEWS_URL
                        if url.startswith("/"):
                            url = "https://www.oib.or.at" + url
                        date_text = date_el.get_text(strip=True) if date_el else ""
                        results.append({
                            "source": "OIB (oib.or.at)",
                            "title": title,
                            "date": date_text,
                            "url": url,
                            "type": "standard_update",
                        })

    except httpx.RequestError as e:
        logger.warning("RIS/OIB fetch failed: %s", e)
        # Return informative placeholder
        results = [
            {
                "source": "RIS Austria",
                "title": "Österreichisches Baurecht — manuelle Prüfung empfohlen",
                "date": "",
                "url": "https://www.ris.bka.gv.at/",
                "type": "info",
                "note": f"Netzwerkfehler: {e}",
            }
        ]

    _cache_set(cache_key, results)
    return results


# ---------------------------------------------------------------------------
# hora.gv.at — Gefahrenzonenpläne
# ---------------------------------------------------------------------------

async def fetch_hora_hazards(lat: float, lon: float) -> Dict[str, Any]:
    """
    Abfrage von Naturgefahren für einen Standort via hora.gv.at REST-API.
    Returns: Hochwasser, Lawinen, Steinschlag, Erdrutsch Zonierung.
    """
    cache_key = f"hora_{lat:.4f}_{lon:.4f}"
    cached = _cache_get(cache_key)
    if cached:
        return cached

    result: Dict[str, Any] = {
        "lat": lat, "lon": lon,
        "source": "hora.gv.at",
        "hazards": {},
    }

    try:
        async with httpx.AsyncClient(timeout=15,
                                     headers={"User-Agent": "ORION-ArchitektAT/3.0"}) as client:
            # hora.gv.at WMS GetFeatureInfo (OGC standard)
            params = {
                "SERVICE": "WMS",
                "VERSION": "1.3.0",
                "REQUEST": "GetFeatureInfo",
                "LAYERS": "HZGKM_HW30,HZGKM_HW100,HZGKM_HW300",
                "QUERY_LAYERS": "HZGKM_HW30,HZGKM_HW100,HZGKM_HW300",
                "INFO_FORMAT": "application/json",
                "CRS": "EPSG:4326",
                "BBOX": f"{lat-0.001},{lon-0.001},{lat+0.001},{lon+0.001}",
                "WIDTH": "10", "HEIGHT": "10",
                "I": "5", "J": "5",
            }
            r = await client.get(
                "https://www.hora.gv.at/webservices/wms/public.aspx",
                params=params,
            )
            if r.status_code == 200:
                try:
                    data = r.json()
                    result["hazards"]["hochwasser"] = data
                except Exception:
                    result["hazards"]["hochwasser_raw"] = r.text[:500]

            # Try JSON API endpoint
            r2 = await client.get(
                f"https://hora.gv.at/webservices/rest/hazard?lat={lat}&lon={lon}&format=json",
            )
            if r2.status_code == 200:
                try:
                    result["hazards"]["all"] = r2.json()
                except Exception:
                    pass

    except httpx.RequestError as e:
        logger.warning("hora.gv.at fetch failed: %s", e)
        result["note"] = f"hora.gv.at nicht erreichbar: {e}. Manuelle Prüfung unter https://www.hora.gv.at/"
        result["manual_url"] = f"https://www.hora.gv.at/#lat={lat}&lon={lon}"

    _cache_set(cache_key, result)
    return result


# ---------------------------------------------------------------------------
# Norm change monitoring
# ---------------------------------------------------------------------------

_MONITORED_SOURCES = [
    {
        "name": "OIB — Richtlinien aktuell",
        "url": "https://www.oib.or.at/de/richtlinien",
        "selector": "main",
    },
    {
        "name": "RIS — Bundesrecht Baurecht",
        "url": "https://www.ris.bka.gv.at/GeltendeFassung.wxe?Abfrage=Bundesnormen&Gesetzesnummer=10010154",
        "selector": "body",
    },
    {
        "name": "ASI — ÖNORM Neuigkeiten",
        "url": "https://www.austrian-standards.at/de/news",
        "selector": "main, article",
    },
]

_HASH_FILE = _CACHE_DIR / "norm_hashes.json"


def _load_hashes() -> Dict[str, str]:
    if _HASH_FILE.exists():
        return json.loads(_HASH_FILE.read_text())
    return {}


def _save_hashes(hashes: Dict[str, str]) -> None:
    _HASH_FILE.write_text(json.dumps(hashes))


def _load_history() -> List[Dict]:
    hist_file = _CACHE_DIR / "norm_history.json"
    if hist_file.exists():
        return json.loads(hist_file.read_text())
    return []


def _save_history(history: List[Dict]) -> None:
    hist_file = _CACHE_DIR / "norm_history.json"
    hist_file.write_text(json.dumps(history[-100:]))  # keep last 100


async def check_norm_changes() -> Dict[str, Any]:
    """
    Prüft alle überwachten Normquellen auf Änderungen.
    Erkennt Änderungen durch SHA-256-Hash-Vergleich des Seiteninhalts.
    """
    hashes = _load_hashes()
    history = _load_history()
    updates: List[Dict] = []
    checked = 0

    now_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())

    async with httpx.AsyncClient(
        timeout=20, follow_redirects=True,
        headers={"User-Agent": "ORION-ArchitektAT/3.0 NormMonitor"}
    ) as client:
        tasks = [_check_source(client, src, hashes) for src in _MONITORED_SOURCES]
        results = await asyncio.gather(*tasks, return_exceptions=True)

    for src, result in zip(_MONITORED_SOURCES, results):
        checked += 1
        if isinstance(result, Exception):
            updates.append({
                "source": src["name"], "type": "error",
                "title": f"Fehler beim Abrufen: {result}",
                "url": src["url"], "detected_at": now_str,
            })
            continue
        changed, new_hash, old_hash = result
        if changed:
            entry = {
                "source": src["name"],
                "type": "changed" if old_hash else "new",
                "title": f"Änderung erkannt auf {src['name']}",
                "url": src["url"],
                "detected_at": now_str,
                "hash_old": old_hash or "",
                "hash_new": new_hash,
            }
            updates.append(entry)
            history.append(entry)
        hashes[src["url"]] = new_hash

    _save_hashes(hashes)
    _save_history(history)

    return {
        "sources_checked": checked,
        "changes_detected": len([u for u in updates if u.get("type") in ("changed", "new")]),
        "last_check": now_str,
        "updates": updates,
    }


async def _check_source(
    client: httpx.AsyncClient,
    source: Dict,
    hashes: Dict[str, str],
) -> tuple:
    """Fetch a source and return (changed, new_hash, old_hash)."""
    try:
        r = await client.get(source["url"])
        if r.status_code != 200:
            return False, "", hashes.get(source["url"], "")
        soup = BeautifulSoup(r.text, "lxml")
        el = soup.select_one(source.get("selector", "main"))
        content = el.get_text(separator=" ", strip=True) if el else r.text[:5000]
        new_hash = hashlib.sha256(content.encode()).hexdigest()[:32]
        old_hash = hashes.get(source["url"], "")
        changed = new_hash != old_hash and bool(old_hash)
        return changed, new_hash, old_hash
    except Exception as e:
        raise RuntimeError(str(e))


def get_norm_history() -> Dict[str, Any]:
    return {"history": _load_history()}
