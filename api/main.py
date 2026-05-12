"""
ORION Architekt-AT FastAPI Main Application
Production-ready API with all Austrian building regulations endpoints
"""

import os
import sys
import time
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.openapi.utils import get_openapi
from fastapi.responses import HTMLResponse, JSONResponse
from prometheus_fastapi_instrumentator import Instrumentator

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api.database import Base, engine
from api.middleware import LoggingMiddleware, RateLimitMiddleware, SecurityHeadersMiddleware
from api.middleware.auth import router as auth_router
from api.models import User
from api.routers import (
    ai_recommendations,
    at_datasources,
    bim_integration,
    bundesland,
    calculations,
    collaboration,
    compliance,
    projects,
    reports,
    tendering,
    validation,
)
from orion_logging import get_logger, setup_default_logging

# Setup logging
setup_default_logging()
logger = get_logger(__name__)

# Create database tables
Base.metadata.create_all(bind=engine)


@asynccontextmanager
async def lifespan(application: FastAPI):
    logger.info("🚀 ORION Architekt-AT API starting up...")
    logger.info("✅ Database initialized")
    logger.info("✅ All routers loaded")
    logger.info("🌐 API ready at http://0.0.0.0:8000")
    logger.info("📚 Documentation at http://0.0.0.0:8000/docs")
    yield
    logger.info("🛑 ORION Architekt-AT API shutting down...")


# Initialize FastAPI app
app = FastAPI(
    lifespan=lifespan,
    title="ORION Architekt-AT API",
    description="""
    🏗️ **Comprehensive Austrian Building Regulations API**

    Complete OIB-RL compliance, ÖNORM standards, and building calculations for all 9 Austrian Bundesländer.

    ## Features

    * 🎯 **30+ Calculation Functions** - U-Wert, Stellplätze, Barrierefreiheit, Fluchtwege, etc.
    * 📋 **OIB-RL 1-6 Complete** - Full compliance checking
    * 🗺️ **9 Bundesländer** - Wien, Tirol, Salzburg, etc.
    * 🔍 **Knowledge Base Validation** - RIS Austria, OIB, ÖNORM, hora.gv.at
    * 🤖 **AI-Powered Recommendations** - UNIQUE: ML-based optimization
    * 🏗️ **BIM Integration** - UNIQUE: IFC file processing
    * 👥 **Real-time Collaboration** - UNIQUE: Multi-user project work
    * 📊 **Advanced Analytics** - Performance metrics and insights
    * 📝 **ÖNORM A 2063 Tendering** - UNIQUE: Professional Austrian tendering system

    ## Authentication

    Most endpoints require JWT authentication. Get your token from `/auth/token`.

    ## Rate Limits

    * Anonymous: 100 requests/hour
    * Authenticated: 1000 requests/hour
    * Premium: Unlimited
    """,
    version="3.0.0",
    contact={
        "name": "ORION Architekt-AT Team",
        "url": "https://github.com/Alvoradozerouno/ORION-Architekt-AT",
        "email": "support@orion-architekt.at",
    },
    license_info={"name": "MIT License", "url": "https://opensource.org/licenses/MIT"},
    openapi_tags=[
        {"name": "calculations", "description": "Building calculations (U-Wert, Stellplätze, etc.)"},
        {"name": "compliance", "description": "OIB-RL & ÖNORM compliance checks"},
        {"name": "validation", "description": "Knowledge base validation"},
        {"name": "bundesland", "description": "🗺️ Alle 9 Bundesländer — Bauordnung, Stellplätze, Aufzug, Förderungen, Vergleich"},
        {"name": "reports", "description": "Generate comprehensive reports"},
        {"name": "tendering", "description": "📝 ÖNORM A 2063 Tendering & Bid Management (UNIQUE)"},
        {"name": "ai", "description": "🤖 AI-powered recommendations (UNIQUE)"},
        {"name": "bim", "description": "🏗️ BIM integration (UNIQUE)"},
        {"name": "collaboration", "description": "👥 Real-time collaboration (UNIQUE)"},
        {"name": "projects", "description": "📁 Projekt- und Büroverwaltung — Austria-first Arbeitseinheit"},
        {"name": "at-data", "description": "🇦🇹 Österreichische Datenquellen — OIB-RL, Baupreisindex, Kostenrichtwerte, Materialien"},
        {"name": "auth", "description": "Authentication & authorization"},
        {"name": "health", "description": "Health & monitoring"},
    ],
)

# Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(LoggingMiddleware)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(SecurityHeadersMiddleware)

# Prometheus metrics
Instrumentator().instrument(app).expose(app)

# Include routers
app.include_router(calculations.router, prefix="/api/v1/calculations", tags=["calculations"])
app.include_router(compliance.router, prefix="/api/v1/compliance", tags=["compliance"])
app.include_router(validation.router, prefix="/api/v1/validation", tags=["validation"])
app.include_router(bundesland.router, prefix="/api/v1/bundesland", tags=["bundesland"])
app.include_router(reports.router, prefix="/api/v1/reports", tags=["reports"])
app.include_router(tendering.router, tags=["tendering"])  # Uses own prefix
app.include_router(ai_recommendations.router, prefix="/api/v1/ai", tags=["ai"])
app.include_router(bim_integration.router, prefix="/api/v1/bim", tags=["bim"])
app.include_router(collaboration.router, prefix="/api/v1/collaboration", tags=["collaboration"])
app.include_router(projects.router, prefix="/api/v1/projects", tags=["projects"])
app.include_router(at_datasources.router, prefix="/api/v1/at-data", tags=["at-data"])
app.include_router(auth_router, prefix="/auth", tags=["auth"])


# Health check endpoints
@app.get("/health", tags=["health"])
async def health_check():
    """Health check endpoint for monitoring"""
    return {"status": "healthy", "version": "3.0.0", "timestamp": time.time()}


@app.get("/health/ready", tags=["health"])
async def readiness_check():
    """Readiness check for kubernetes/docker"""
    from sqlalchemy import text

    from api.database import get_db

    db_gen = get_db()
    db = next(db_gen)
    try:
        db.execute(text("SELECT 1"))
        return {"status": "ready", "database": "connected", "timestamp": time.time()}
    except Exception as e:
        logger.error(f"Readiness check failed: {e}")
        raise HTTPException(status_code=503, detail="Service not ready")
    finally:
        try:
            next(db_gen)
        except StopIteration:
            pass


@app.get("/health/live", tags=["health"])
async def liveness_check():
    """Liveness check for kubernetes/docker"""
    return {"status": "alive", "timestamp": time.time()}


# Root endpoint
@app.get("/", tags=["health"])
async def root():
    """Root endpoint with API information"""
    return {
        "name": "ORION Architekt-AT API",
        "version": "3.0.0",
        "description": "Österreichische Baurechts-API — Austria-leading",
        "fokus": "Alle 9 Bundesländer · OIB-RL 1-7 · ÖNORM · BIM · Förderungen",
        "docs_url": "/docs",
        "redoc_url": "/redoc",
        "unique_features": [
            "Alle 9 Bundesländer mit vollständigen Baurechts-Daten",
            "OIB-RL 1-7 (2023) vollständig — inkl. Salzburg-Sonderweg",
            "Bundesländer-Vergleich (Stellplätze, Aufzug, Schneelasten, Kosten)",
            "Österreichische Förderungsübersicht (Bund + alle Bundesländer)",
            "Baupreisindex Österreich (Statistik Austria, Stand Q4 2025)",
            "Kostenrichtwerte 2026 mit regionalen Faktoren",
            "AI-gestützte Gebäudeoptimierung",
            "BIM/IFC-Integration (IFC2x3, IFC4, IFC4.3)",
            "Echtzeit-Zusammenarbeit im Büro",
            "Projekt- und Büroverwaltung",
            "ÖNORM A 2063 Ausschreibung",
            "Audit-Trail für Compliance-Nachweise",
        ],
    }


# Custom OpenAPI schema
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title="ORION Architekt-AT API",
        version="3.0.0",
        description=app.description,
        routes=app.routes,
    )

    # Add security schemes
    openapi_schema["components"]["securitySchemes"] = {
        "Bearer": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
        }
    }

    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi


# Austria-first dashboard
@app.get("/dashboard", response_class=HTMLResponse, tags=["health"])
async def austria_dashboard():
    """
    🇦🇹 **Austria-first Dashboard**

    Fokussiertes Dashboard für österreichische Anwendungsfälle:
    Projektprüfung, Bundesland-Vergleich, OIB/ÖNORM-Checks, API-Status.
    """
    html = """<!DOCTYPE html>
<html lang="de">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>ORION Architekt-AT — Austria Dashboard</title>
  <style>
    :root {
      --rot: #ED2939; --weiss: #FFFFFF; --dunkel: #1a1a2e; --karte: #16213e;
      --akzent: #0f3460; --text: #e0e0e0; --gruen: #4caf50; --gelb: #ff9800;
    }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body { font-family: 'Segoe UI', sans-serif; background: var(--dunkel); color: var(--text); }
    header {
      background: linear-gradient(135deg, var(--rot), var(--akzent));
      padding: 1.5rem 2rem; display: flex; align-items: center; gap: 1rem;
    }
    header h1 { font-size: 1.6rem; color: var(--weiss); }
    header .badge { background: rgba(255,255,255,0.2); padding: 0.3rem 0.8rem;
      border-radius: 20px; font-size: 0.8rem; color: var(--weiss); }
    .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px,1fr));
      gap: 1.2rem; padding: 2rem; }
    .card { background: var(--karte); border-radius: 12px; padding: 1.5rem;
      border-left: 4px solid var(--rot); }
    .card h2 { font-size: 1rem; color: var(--rot); margin-bottom: 0.8rem; }
    .card .metric { font-size: 2.5rem; font-weight: bold; color: var(--weiss); }
    .card .label { font-size: 0.8rem; color: #888; margin-top: 0.3rem; }
    .bl-grid { display: grid; grid-template-columns: repeat(3,1fr); gap: 0.5rem; margin-top: 0.8rem; }
    .bl-chip { background: var(--akzent); border-radius: 6px; padding: 0.4rem 0.6rem;
      font-size: 0.75rem; text-align: center; cursor: pointer; transition: background 0.2s; }
    .bl-chip:hover { background: var(--rot); }
    .link-grid { display: flex; flex-direction: column; gap: 0.5rem; margin-top: 0.8rem; }
    .api-link { display: block; background: var(--akzent); border-radius: 6px;
      padding: 0.5rem 0.8rem; text-decoration: none; color: var(--text);
      font-size: 0.82rem; transition: background 0.2s; }
    .api-link:hover { background: var(--rot); color: var(--weiss); }
    .api-link .method { display: inline-block; min-width: 36px; font-weight: bold;
      font-size: 0.7rem; opacity: 0.8; }
    .status-ok { color: var(--gruen); }
    .status-warn { color: var(--gelb); }
    .progress { background: #333; border-radius: 4px; height: 8px; margin-top: 0.5rem; }
    .progress-bar { background: var(--gruen); height: 100%; border-radius: 4px; }
    footer { text-align: center; padding: 2rem; color: #555; font-size: 0.8rem; }
    footer a { color: var(--rot); text-decoration: none; }
    #result { background: var(--karte); border-radius: 8px; padding: 1rem;
      font-family: monospace; font-size: 0.8rem; white-space: pre-wrap;
      max-height: 300px; overflow-y: auto; margin-top: 0.8rem; display: none; }
    select, input { width: 100%; background: var(--akzent); color: var(--text);
      border: 1px solid #444; border-radius: 6px; padding: 0.5rem; margin-top: 0.4rem;
      font-size: 0.85rem; }
    button { background: var(--rot); color: var(--weiss); border: none; border-radius: 6px;
      padding: 0.5rem 1.2rem; cursor: pointer; margin-top: 0.5rem; font-size: 0.85rem; }
    button:hover { opacity: 0.85; }
    .oib-list { list-style: none; margin-top: 0.6rem; }
    .oib-list li { padding: 0.3rem 0; border-bottom: 1px solid #2a2a4a; font-size: 0.82rem; }
    .oib-list li:last-child { border: none; }
    .tag { display: inline-block; background: var(--akzent); border-radius: 4px;
      padding: 0.1rem 0.4rem; font-size: 0.7rem; margin-right: 0.3rem; }
  </style>
</head>
<body>
<header>
  <div>
    <h1>🇦🇹 ORION Architekt-AT</h1>
    <p style="color:rgba(255,255,255,0.7);font-size:0.85rem">Austria-leading Building Regulations API</p>
  </div>
  <span class="badge">v3.0.0</span>
  <span class="badge" id="statusBadge">⟳ Prüfe...</span>
</header>

<div class="grid">

  <!-- KPI: Bundesländer -->
  <div class="card">
    <h2>🗺️ Bundesland-Abdeckung</h2>
    <div class="metric">9/9</div>
    <div class="label">Alle Bundesländer vollständig implementiert</div>
    <div class="progress"><div class="progress-bar" style="width:100%"></div></div>
    <div class="bl-grid" id="blGrid">
      <div class="bl-chip" onclick="showBl('wien')">Wien</div>
      <div class="bl-chip" onclick="showBl('niederoesterreich')">NÖ</div>
      <div class="bl-chip" onclick="showBl('oberoesterreich')">OÖ</div>
      <div class="bl-chip" onclick="showBl('steiermark')">Stmk</div>
      <div class="bl-chip" onclick="showBl('tirol')">Tirol</div>
      <div class="bl-chip" onclick="showBl('salzburg')">Sbg ⚠️</div>
      <div class="bl-chip" onclick="showBl('vorarlberg')">Vbg</div>
      <div class="bl-chip" onclick="showBl('kaernten')">Ktn</div>
      <div class="bl-chip" onclick="showBl('burgenland')">Bgld</div>
    </div>
    <div id="blResult" class="result" style="display:none;margin-top:0.8rem;
      background:#111;padding:0.8rem;border-radius:6px;font-size:0.75rem;
      font-family:monospace;white-space:pre-wrap;max-height:200px;overflow-y:auto"></div>
  </div>

  <!-- KPI: OIB-RL -->
  <div class="card">
    <h2>📋 OIB-Richtlinien 2023</h2>
    <div class="metric">7/7</div>
    <div class="label">Vollständige Abdeckung, inkl. Bundesland-Abweichungen</div>
    <div class="progress"><div class="progress-bar" style="width:100%"></div></div>
    <ul class="oib-list">
      <li><span class="tag">OIB-RL 1</span> Mechanische Festigkeit</li>
      <li><span class="tag">OIB-RL 2</span> Brandschutz</li>
      <li><span class="tag">OIB-RL 3</span> Hygiene, Gesundheit</li>
      <li><span class="tag">OIB-RL 4</span> Barrierefreiheit</li>
      <li><span class="tag">OIB-RL 5</span> Schallschutz</li>
      <li><span class="tag">OIB-RL 6</span> Energieeinsparung <span style="color:var(--gelb)">⚠️ Sbg Sonderweg</span></li>
      <li><span class="tag">OIB-RL 7</span> Nachhaltige Nutzung</li>
    </ul>
  </div>

  <!-- Bundesland-Vergleich -->
  <div class="card">
    <h2>⚖️ Bundesland-Vergleich</h2>
    <div class="label">Zwei Bundesländer vergleichen</div>
    <select id="bl1">
      <option value="wien">Wien</option>
      <option value="tirol">Tirol</option>
      <option value="salzburg">Salzburg</option>
      <option value="niederoesterreich">Niederösterreich</option>
      <option value="oberoesterreich">Oberösterreich</option>
      <option value="steiermark">Steiermark</option>
      <option value="vorarlberg">Vorarlberg</option>
      <option value="kaernten">Kärnten</option>
      <option value="burgenland">Burgenland</option>
    </select>
    <select id="bl2" style="margin-top:0.4rem">
      <option value="tirol">Tirol</option>
      <option value="wien">Wien</option>
      <option value="salzburg">Salzburg</option>
      <option value="niederoesterreich">Niederösterreich</option>
      <option value="oberoesterreich">Oberösterreich</option>
      <option value="steiermark">Steiermark</option>
      <option value="vorarlberg">Vorarlberg</option>
      <option value="kaernten">Kärnten</option>
      <option value="burgenland">Burgenland</option>
    </select>
    <button onclick="comparebl()">Vergleichen</button>
    <div id="compareResult"></div>
  </div>

  <!-- Baupreisindex -->
  <div class="card">
    <h2>📈 Baupreisindex (Statistik Austria)</h2>
    <div class="label">Q1 2020 – Q4 2025, Basis 2020=100</div>
    <button onclick="loadBpi()">Index laden</button>
    <div id="bpiResult"></div>
  </div>

  <!-- U-Wert Check -->
  <div class="card">
    <h2>🧱 Schnell-U-Wert</h2>
    <div class="label">Außenwand Neubau: Zielwert ≤ 0,35 W/m²K (OIB-RL 6)</div>
    <div style="margin-top:0.8rem">
      <input type="number" id="uwEps" placeholder="EPS-Dicke mm (z.B. 160)" value="160">
      <input type="number" id="uwBeton" placeholder="Beton-Dicke mm (z.B. 200)" value="200" style="margin-top:0.4rem">
      <button onclick="calcUwert()">Berechnen</button>
    </div>
    <div id="uwResult" style="margin-top:0.8rem;font-size:0.85rem"></div>
  </div>

  <!-- API Links -->
  <div class="card">
    <h2>🔗 Austria-first API Endpunkte</h2>
    <div class="link-grid">
      <a class="api-link" href="/api/v1/bundesland/" target="_blank">
        <span class="method">GET</span> /api/v1/bundesland/</a>
      <a class="api-link" href="/api/v1/bundesland/compare?bundeslaender=wien&bundeslaender=tirol" target="_blank">
        <span class="method">GET</span> /api/v1/bundesland/compare</a>
      <a class="api-link" href="/api/v1/at-data/oib-richtlinien" target="_blank">
        <span class="method">GET</span> /api/v1/at-data/oib-richtlinien</a>
      <a class="api-link" href="/api/v1/at-data/baupreisindex" target="_blank">
        <span class="method">GET</span> /api/v1/at-data/baupreisindex</a>
      <a class="api-link" href="/api/v1/at-data/kostenrichtwerte" target="_blank">
        <span class="method">GET</span> /api/v1/at-data/kostenrichtwerte</a>
      <a class="api-link" href="/api/v1/at-data/at-kpis" target="_blank">
        <span class="method">GET</span> /api/v1/at-data/at-kpis</a>
      <a class="api-link" href="/api/v1/at-data/changelog" target="_blank">
        <span class="method">GET</span> /api/v1/at-data/changelog</a>
      <a class="api-link" href="/docs" target="_blank">
        <span class="method">📚</span> Swagger API Docs</a>
    </div>
  </div>

  <!-- Vertrauen / Status -->
  <div class="card">
    <h2>✅ Vertrauen &amp; Qualität</h2>
    <div class="link-grid" style="margin-top:0.5rem">
      <div style="display:flex;justify-content:space-between;padding:0.4rem 0;
        border-bottom:1px solid #2a2a4a;font-size:0.82rem">
        <span>Öffentliches Changelog</span><span class="status-ok">✓ aktiv</span></div>
      <div style="display:flex;justify-content:space-between;padding:0.4rem 0;
        border-bottom:1px solid #2a2a4a;font-size:0.82rem">
        <span>Audit-Trail (SHA-256)</span><span class="status-ok">✓ aktiv</span></div>
      <div style="display:flex;justify-content:space-between;padding:0.4rem 0;
        border-bottom:1px solid #2a2a4a;font-size:0.82rem">
        <span>DSGVO / EU-Betrieb</span><span class="status-ok">✓ aktiv</span></div>
      <div style="display:flex;justify-content:space-between;padding:0.4rem 0;
        border-bottom:1px solid #2a2a4a;font-size:0.82rem">
        <span>OIB-RL Quellennachweise</span><span class="status-ok">✓ aktiv</span></div>
      <div style="display:flex;justify-content:space-between;padding:0.4rem 0;
        border-bottom:1px solid #2a2a4a;font-size:0.82rem">
        <span>RIS / hora live</span><span class="status-warn">⏳ geplant</span></div>
      <div style="display:flex;justify-content:space-between;padding:0.4rem 0;
        font-size:0.82rem">
        <span>Salzburg OIB-RL 6 Sonderweg</span><span class="status-ok">✓ korrekt</span></div>
    </div>
  </div>

</div>

<footer>
  <p>ORION Architekt-AT · Austria-leading Building Regulations API ·
    <a href="/docs">API Docs</a> · <a href="/api/v1/at-data/changelog">Changelog</a> ·
    <a href="/api/v1/at-data/at-kpis">KPIs</a></p>
  <p style="margin-top:0.4rem">OIB-RL 1-7 (2023) · Alle 9 Bundesländer · DSGVO-konform</p>
</footer>

<script>
async function fetchJson(url) {
  try {
    const r = await fetch(url);
    return await r.json();
  } catch(e) { return {error: e.message}; }
}

// Status check
fetch('/health').then(r => r.json()).then(d => {
  const b = document.getElementById('statusBadge');
  b.textContent = d.status === 'healthy' ? '✅ Online' : '⚠️ ' + d.status;
  b.style.background = d.status === 'healthy' ? 'rgba(76,175,80,0.3)' : 'rgba(255,152,0,0.3)';
}).catch(() => {
  document.getElementById('statusBadge').textContent = '❌ Offline';
});

async function showBl(bl) {
  const el = document.getElementById('blResult');
  el.style.display = 'block';
  el.textContent = 'Lade...';
  const d = await fetchJson('/api/v1/bundesland/' + bl);
  const out = [
    'Bundesland: ' + (d.name || bl),
    'Bauordnung: ' + (d.bauordnung || '—'),
    'OIB-2023 Status: ' + (d.oib_2023_status || '—'),
    'Aufzug ab OG: ' + (d.aufzug_ab_geschoss || '—'),
    'Schneelastzone: ' + (d.schneelastzone || '—'),
    'Digitale Einreichung: ' + (d.digitale_einreichung ? '✓' : '⏳'),
  ].join('\\n');
  el.textContent = out;
}

async function comparebl() {
  const bl1 = document.getElementById('bl1').value;
  const bl2 = document.getElementById('bl2').value;
  const el = document.getElementById('compareResult');
  el.innerHTML = '<div style="font-size:0.8rem;margin-top:0.5rem">Lade...</div>';
  const d = await fetchJson('/api/v1/bundesland/compare?bundeslaender=' + bl1 + '&bundeslaender=' + bl2);
  if (d.error) { el.innerHTML = '<div style="color:red;font-size:0.8rem">' + d.error + '</div>'; return; }
  const rows = Object.entries(d.daten || {}).map(([k,v]) =>
    '<tr><td style="padding:0.2rem 0.5rem;border-bottom:1px solid #333;font-size:0.75rem">' + k + '</td>' +
    Object.values(v).map(x => '<td style="padding:0.2rem 0.5rem;border-bottom:1px solid #333;font-size:0.75rem">' + JSON.stringify(x) + '</td>').join('') + '</tr>'
  ).join('');
  el.innerHTML = '<table style="width:100%;margin-top:0.5rem;border-collapse:collapse">' + rows + '</table>';
}

async function loadBpi() {
  const el = document.getElementById('bpiResult');
  el.innerHTML = '<div style="font-size:0.8rem;margin-top:0.5rem">Lade...</div>';
  const d = await fetchJson('/api/v1/at-data/baupreisindex');
  if (!d.zeitreihe) { el.innerHTML = '<div style="color:red;font-size:0.8rem">Fehler</div>'; return; }
  const last5 = d.zeitreihe.slice(-5);
  const rows = last5.map(e =>
    '<tr><td style="padding:0.2rem 0.4rem;font-size:0.75rem">' + e.quartal + '</td>' +
    '<td style="padding:0.2rem 0.4rem;font-size:0.75rem;text-align:right">' + e.index + '</td></tr>'
  ).join('');
  el.innerHTML = '<table style="width:100%;margin-top:0.5rem"><tr><th style="font-size:0.7rem;text-align:left">Quartal</th><th style="font-size:0.7rem;text-align:right">Index</th></tr>' + rows + '</table>';
}

async function calcUwert() {
  const eps = parseFloat(document.getElementById('uwEps').value) || 160;
  const beton = parseFloat(document.getElementById('uwBeton').value) || 200;
  const el = document.getElementById('uwResult');
  const payload = {
    schichten: [
      {material: "Außenputz", dicke_mm: 10, lambda_wert: 0.7},
      {material: "Beton", dicke_mm: beton, lambda_wert: 2.1},
      {material: "Dämmung EPS", dicke_mm: eps, lambda_wert: 0.035},
      {material: "Innenputz", dicke_mm: 15, lambda_wert: 0.7}
    ],
    innen_uebergang: 0.13, aussen_uebergang: 0.04
  };
  el.textContent = 'Berechne...';
  try {
    const r = await fetch('/api/v1/calculations/uwert', {
      method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify(payload)
    });
    const d = await r.json();
    const u = d.u_wert;
    const ok = u <= 0.35;
    el.innerHTML = '<strong style="font-size:1.3rem;color:' + (ok ? 'var(--gruen)' : 'var(--gelb)') + '">' +
      'U = ' + u.toFixed(3) + ' W/m²K</strong><br>' +
      '<span style="font-size:0.78rem">' + (ok ? '✅ OIB-RL 6 Anforderung erfüllt (≤ 0,35)' : '⚠️ Über OIB-RL 6 Grenzwert (≤ 0,35)') + '</span>';
  } catch(e) { el.textContent = 'Fehler: ' + e.message; }
}
</script>
</body>
</html>"""
    return HTMLResponse(content=html)



# Exception handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    logger.error(f"HTTP error: {exc.status_code} - {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code, content={"error": exc.detail, "status_code": exc.status_code}
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500, content={"error": "Internal server error", "detail": str(exc)}
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True, log_level="info")
