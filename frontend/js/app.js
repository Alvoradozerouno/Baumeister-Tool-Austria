/**
 * ORION Architekt-AT — Frontend JavaScript
 * Handles all API calls, WebSocket, FEM canvas drawing
 */

const API = '';  // same origin via FastAPI static files

// ── Navigation ──────────────────────────────────────────────────────────────

function showSection(name) {
  document.querySelectorAll('.section').forEach(s => s.classList.remove('active'));
  document.querySelectorAll('.nav-link').forEach(l => l.classList.remove('active'));
  const sec = document.getElementById('section-' + name);
  if (sec) sec.classList.add('active');
  const lnk = document.querySelector(`[data-section="${name}"]`);
  if (lnk) lnk.classList.add('active');
}

document.querySelectorAll('.nav-link').forEach(link => {
  link.addEventListener('click', e => {
    e.preventDefault();
    showSection(link.dataset.section);
  });
});

function switchTab(btn, id) {
  const container = btn.closest('.tabs').nextElementSibling;
  btn.closest('.tabs').querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
  btn.classList.add('active');
  // find all tab-contents in same parent
  const parent = btn.closest('section') || btn.closest('.tab-content')?.parentElement;
  if (parent) {
    parent.querySelectorAll('.tab-content').forEach(tc => tc.classList.remove('active'));
    const target = document.getElementById('tab-' + id);
    if (target) target.classList.add('active');
  }
}

// ── Security helpers ─────────────────────────────────────────────────────────

/**
 * Escape HTML special characters to prevent XSS when inserting user-provided
 * or server-provided text into innerHTML.
 */
function esc(str) {
  if (str === null || str === undefined) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}



async function checkAPIStatus() {
  try {
    const r = await fetch('/health', { signal: AbortSignal.timeout(3000) });
    if (r.ok) {
      document.getElementById('api-status').className = 'status-dot online';
      document.getElementById('api-status-text').textContent = 'API online';
    } else throw new Error();
  } catch {
    document.getElementById('api-status').className = 'status-dot offline';
    document.getElementById('api-status-text').textContent = 'API offline';
  }
}

// ── Loading helper ───────────────────────────────────────────────────────────

function showLoading(text = 'Berechne…') {
  document.getElementById('loading-text').textContent = text;
  document.getElementById('loading-overlay').classList.remove('hidden');
}
function hideLoading() {
  document.getElementById('loading-overlay').classList.add('hidden');
}

async function apiCall(url, body = null, method = 'POST') {
  const opts = {
    method,
    headers: { 'Content-Type': 'application/json' }
  };
  if (body) opts.body = JSON.stringify(body);
  const r = await fetch(url, opts);
  if (!r.ok) {
    const err = await r.json().catch(() => ({ detail: r.statusText }));
    throw new Error(err.detail || r.statusText);
  }
  return r.json();
}

function showResult(elemId, html, type = '') {
  const el = document.getElementById(elemId);
  el.innerHTML = html;
  el.className = 'result-box' + (type ? ' ' + type : '');
  el.classList.remove('hidden');
}

function kv(label, value, cls = '') {
  return `<div class="result-item"><div class="result-label">${label}</div><div class="result-value ${cls}">${value}</div></div>`;
}

function badge(text, type) {
  return `<span class="badge badge-${type}">${text}</span>`;
}

// ── Dashboard Quick Check ─────────────────────────────────────────────────────

async function runQuickCheck() {
  const bl = document.getElementById('bundesland-global').value;
  showLoading('OIB-Schnellcheck läuft…');
  try {
    const data = await apiCall('/api/v1/compliance/check-all', {
      bundesland: bl,
      gebaudetyp: 'mehrfamilienhaus',
      bgf_m2: 500,
      geschosse: 4
    });
    let html = `<h3>OIB-Schnellcheck — ${bl.toUpperCase()}</h3>
      <div class="result-grid">`;
    if (data.checks) {
      data.checks.forEach(c => {
        const b = c.status === 'pass' ? 'success' : c.status === 'warning' ? 'warning' : 'error';
        html += kv(c.name, badge(c.status.toUpperCase(), b));
      });
    } else {
      html += kv('Status', badge('OK', 'success'));
    }
    html += '</div>';
    showResult('dashboard-result', html, 'success');
  } catch (e) {
    showResult('dashboard-result', `<b>Fehler:</b> ${e.message}`, 'error');
  } finally {
    hideLoading();
  }
}

// ── U-Wert ────────────────────────────────────────────────────────────────────

async function calcUwert() {
  let schichten;
  try {
    schichten = JSON.parse(document.getElementById('uw-schichten').value);
  } catch {
    showResult('uwert-result', 'Ungültiges JSON in Schichten-Feld.', 'error');
    return;
  }
  showLoading('U-Wert wird berechnet…');
  try {
    const data = await apiCall('/api/v1/calculations/uwert-berechnung', {
      bauteiltyp: document.getElementById('uw-bauteiltyp').value,
      schichten
    });
    const u = data.u_wert_W_m2K ?? data.u_wert ?? data.uwert ?? '—';
    const limit = data.grenzwert ?? '—';
    const ok = data.oib_konform ?? data.konform;
    let html = `<h3>U-Wert Ergebnis</h3><div class="result-grid">
      ${kv('U-Wert', `${u} W/m²K`, ok === false ? 'text-danger' : '')}
      ${kv('Grenzwert OIB-RL6', `${limit} W/m²K`)}
      ${kv('OIB konform', badge(ok === false ? 'NEIN' : 'JA', ok === false ? 'error' : 'success'))}
    </div>`;
    if (data.schichten_detail) {
      html += '<table class="result-table"><thead><tr><th>Schicht</th><th>Dicke</th><th>λ</th><th>R-Wert</th></tr></thead><tbody>';
      data.schichten_detail.forEach(s => {
        html += `<tr><td>${s.material}</td><td>${s.dicke_m*100} cm</td><td>${s.lambda}</td><td>${(s.dicke_m/s.lambda).toFixed(3)}</td></tr>`;
      });
      html += '</tbody></table>';
    }
    showResult('uwert-result', html, ok === false ? 'error' : 'success');
  } catch (e) {
    // Fallback: calculate locally
    try {
      const schichten2 = JSON.parse(document.getElementById('uw-schichten').value);
      const Rsi = 0.13, Rse = 0.04;
      const Rges = schichten2.reduce((s, l) => s + l.dicke_m / l.lambda, 0);
      const Rt = Rsi + Rges + Rse;
      const U = (1 / Rt).toFixed(3);
      const html = `<h3>U-Wert (lokal berechnet)</h3>
        <div class="result-grid">${kv('U-Wert', `${U} W/m²K`)}${kv('R-ges', `${Rt.toFixed(3)} m²K/W`)}</div>
        <p style="color:var(--text-muted);font-size:.8rem;margin-top:.5rem">⚠ Offline-Berechnung (API nicht verfügbar)</p>`;
      showResult('uwert-result', html, 'warning');
    } catch {
      showResult('uwert-result', `Fehler: ${e.message}`, 'error');
    }
  } finally {
    hideLoading();
  }
}

// ── Stellplätze ───────────────────────────────────────────────────────────────

async function calcStellplaetze() {
  showLoading('Stellplätze berechnen…');
  try {
    const data = await apiCall('/api/v1/calculations/stellplaetze-berechnung', {
      gebaudetyp: document.getElementById('sp-typ').value,
      bgf_m2: +document.getElementById('sp-bgf').value,
      wohneinheiten: +document.getElementById('sp-we').value,
      bundesland: document.getElementById('sp-bl').value
    });
    const html = `<h3>Stellplatzberechnung</h3>
      <div class="result-grid">
        ${kv('Mindeststellplätze', data.mindest_stellplaetze ?? data.anzahl ?? '—')}
        ${kv('Fahrradstellplätze', data.fahrrad_stellplaetze ?? '—')}
        ${kv('Rechtsgrundlage', data.rechtsgrundlage ?? data.bundesland_regelung ?? '—')}
      </div>
      ${data.hinweise ? '<b>Hinweise:</b><ul>' + data.hinweise.map(h=>`<li>${h}</li>`).join('') + '</ul>' : ''}`;
    showResult('stellplaetze-result', html, 'success');
  } catch (e) {
    showResult('stellplaetze-result', `Fehler: ${e.message}`, 'error');
  } finally { hideLoading(); }
}

// ── Barrierefreiheit ──────────────────────────────────────────────────────────

async function calcBarrierefreiheit() {
  showLoading('Barrierefreiheit prüfen…');
  try {
    const data = await apiCall('/api/v1/calculations/barrierefreiheit-check', {
      bundesland: document.getElementById('bf-bl').value,
      gebaudeklasse: +document.getElementById('bf-gk').value,
      geschosse: +document.getElementById('bf-geschosse').value,
      wohneinheiten: +document.getElementById('bf-we').value
    });
    let html = `<h3>Barrierefreiheit (ÖNORM B 1600/1601)</h3><div class="result-grid">
      ${kv('Aufzugpflicht', badge(data.aufzug_pflicht ? 'JA' : 'NEIN', data.aufzug_pflicht ? 'warning' : 'success'))}
      ${kv('Konform', badge(data.barrierefrei_konform ?? data.konform ? 'JA' : 'NEIN', data.barrierefrei_konform ?? data.konform ? 'success' : 'error'))}
    </div>`;
    if (data.anforderungen?.length) {
      html += '<b>Anforderungen:</b><ul>' + data.anforderungen.map(a => `<li>${a}</li>`).join('') + '</ul>';
    }
    showResult('bf-result', html, 'success');
  } catch (e) {
    showResult('bf-result', `Fehler: ${e.message}`, 'error');
  } finally { hideLoading(); }
}

// ── Fluchtweg ─────────────────────────────────────────────────────────────────

async function calcFluchtweg() {
  showLoading('Fluchtwege prüfen…');
  try {
    const data = await apiCall('/api/v1/calculations/fluchtweg-check', {
      gebaudeklasse: +document.getElementById('fw-gk').value,
      max_fluchtweglange_m: +document.getElementById('fw-laenge').value,
      geschosse: +document.getElementById('fw-geschosse').value,
      nutzungseinheiten_pro_geschoss: +document.getElementById('fw-ne').value
    });
    const ok = data.konform ?? data.oib_konform ?? true;
    const html = `<h3>Fluchtweg-Prüfung (OIB-RL 4)</h3>
      <div class="result-grid">
        ${kv('Konform', badge(ok ? 'JA' : 'NEIN', ok ? 'success' : 'error'))}
        ${kv('Max. erlaubte Länge', `${data.max_erlaubt_m ?? '—'} m`)}
        ${kv('Stiegenhausbreite', `${data.min_stiegenbreite_m ?? '—'} m`)}
      </div>
      ${data.hinweise?.length ? '<b>Hinweise:</b><ul>' + data.hinweise.map(h=>`<li>${h}</li>`).join('') + '</ul>' : ''}`;
    showResult('fw-result', html, ok ? 'success' : 'error');
  } catch (e) {
    showResult('fw-result', `Fehler: ${e.message}`, 'error');
  } finally { hideLoading(); }
}

// ── Heizlast ──────────────────────────────────────────────────────────────────

async function calcHeizlast() {
  showLoading('Heizlast berechnen…');
  try {
    const data = await apiCall('/api/v1/calculations/heizlast-berechnung', {
      bgf_m2: +document.getElementById('hl-bgf').value,
      u_wert_wand: +document.getElementById('hl-uw').value,
      u_wert_fenster: +document.getElementById('hl-uwf').value,
      bundesland: document.getElementById('hl-bl').value
    });
    const html = `<h3>Heizlastberechnung (EN 12831)</h3>
      <div class="result-grid">
        ${kv('Heizlast', `${data.heizlast_kw ?? data.phi_HL_kW ?? '—'} kW`)}
        ${kv('HWB', `${data.hwb_kwh_m2a ?? '—'} kWh/m²a`)}
        ${kv('Energieklasse', data.energieklasse ?? '—')}
      </div>`;
    showResult('hl-result', html, 'success');
  } catch (e) {
    showResult('hl-result', `Fehler: ${e.message}`, 'error');
  } finally { hideLoading(); }
}

// ── Schallschutz ──────────────────────────────────────────────────────────────

async function calcSchallschutz() {
  showLoading('Schallschutz berechnen…');
  try {
    const data = await apiCall('/api/v1/calculations/schallschutz-berechnung', {
      bauteil_typ: document.getElementById('ss-typ').value,
      flaechengewicht_kg_m2: +document.getElementById('ss-masse').value,
      raumtyp: document.getElementById('ss-raum').value
    });
    const html = `<h3>Schallschutz (ÖNORM B 8115)</h3>
      <div class="result-grid">
        ${kv('Bewertetes Schalldämmmaß R\'w', `${data.rw_dB ?? data.schalldaemmass_rw ?? '—'} dB`)}
        ${kv('Anforderung', `${data.anforderung_dB ?? data.mindest_rw ?? '—'} dB`)}
        ${kv('Konform', badge(data.konform ? 'JA' : 'NEIN', data.konform ? 'success' : 'error'))}
      </div>`;
    showResult('ss-result', html, data.konform ? 'success' : 'error');
  } catch (e) {
    showResult('ss-result', `Fehler: ${e.message}`, 'error');
  } finally { hideLoading(); }
}

// ── BIM / IFC Upload ──────────────────────────────────────────────────────────

const dropzone = document.getElementById('ifc-dropzone');
if (dropzone) {
  dropzone.addEventListener('dragover', e => { e.preventDefault(); dropzone.classList.add('dragover'); });
  dropzone.addEventListener('dragleave', () => dropzone.classList.remove('dragover'));
  dropzone.addEventListener('drop', e => {
    e.preventDefault();
    dropzone.classList.remove('dragover');
    const file = e.dataTransfer.files[0];
    if (file) processIFCFile(file);
  });
}

async function uploadIFC() {
  const file = document.getElementById('ifc-file').files[0];
  if (file) processIFCFile(file);
}

async function processIFCFile(file) {
  if (!file.name.match(/\.ifc$/i)) {
    showResult('bim-result', 'Nur IFC-Dateien werden unterstützt.', 'error');
    return;
  }
  document.getElementById('bim-progress').classList.remove('hidden');
  showLoading('IFC-Datei wird analysiert…');
  try {
    const fd = new FormData();
    fd.append('file', file);
    const bl = document.getElementById('bim-bl').value;
    const typ = document.getElementById('bim-typ').value;
    const r = await fetch(`/api/v1/bim/upload-ifc?bundesland=${bl}&building_type=${typ}`, {
      method: 'POST', body: fd
    });
    if (!r.ok) throw new Error((await r.json()).detail || r.statusText);
    const data = await r.json();
    let html = `<h3>IFC-Analyse: ${data.file_name}</h3>
      <div class="result-grid">
        ${kv('IFC-Version', data.ifc_version)}
        ${kv('Geschosse', data.stories)}
        ${kv('Gesamtfläche', `${data.total_area_m2?.toFixed(1) ?? '—'} m²`)}
        ${kv('Volumen', `${data.total_volume_m3?.toFixed(1) ?? '—'} m³`)}
        ${kv('Geometrie OK', badge(data.geometry_valid ? 'JA' : 'NEIN', data.geometry_valid ? 'success' : 'error'))}
      </div>`;
    if (data.building_elements) {
      html += '<b>Bauelemente:</b><table class="result-table"><thead><tr><th>Typ</th><th>Anzahl</th></tr></thead><tbody>';
      Object.entries(data.building_elements).forEach(([k,v]) => {
        html += `<tr><td>${k}</td><td>${v}</td></tr>`;
      });
      html += '</tbody></table>';
    }
    if (data.compliance_checks?.length) {
      html += '<b>Compliance-Checks:</b>';
      data.compliance_checks.forEach(c => {
        const b = c.status === 'pass' ? 'success' : c.status === 'fail' ? 'error' : 'warning';
        html += `<div class="norm-card ${c.status === 'pass' ? 'unchanged' : 'changed'}" style="margin-top:.5rem">
          ${badge(c.status.toUpperCase(), b)} <b>${c.check}</b> — ${c.details}</div>`;
      });
    }
    showResult('bim-result', html, 'success');
  } catch (e) {
    showResult('bim-result', `Fehler: ${e.message}`, 'error');
  } finally {
    hideLoading();
    document.getElementById('bim-progress').classList.add('hidden');
  }
}

// ── ML Cost Prediction ────────────────────────────────────────────────────────

async function runMLCost() {
  showLoading('ML-Modell berechnet Kosten…');
  try {
    const data = await apiCall('/api/v1/ml/predict-cost', {
      bundesland: document.getElementById('ki-bl').value,
      gebaudetyp: document.getElementById('ki-typ').value,
      bgf_m2: +document.getElementById('ki-bgf').value,
      geschosse: +document.getElementById('ki-geschosse').value,
      energieziel: document.getElementById('ki-energieziel').value,
      budget_euro: +document.getElementById('ki-budget').value || null
    });
    const fmt = n => n ? n.toLocaleString('de-AT', {style:'currency', currency:'EUR', maximumFractionDigits:0}) : '—';
    const html = `<h3>ML Kostenprognose</h3>
      <div class="result-grid">
        ${kv('Gesamtkosten (Mitte)', fmt(data.predicted_cost_eur))}
        ${kv('Kostenbandbreite', `${fmt(data.cost_range_min)} – ${fmt(data.cost_range_max)}`)}
        ${kv('Konfidenz', `${(data.confidence_score*100).toFixed(0)}%`)}
        ${kv('€/m²', data.cost_per_m2 ? fmt(data.cost_per_m2) : '—')}
      </div>
      ${data.breakdown ? '<b>Kostenaufteilung:</b><table class="result-table"><thead><tr><th>Gewerk</th><th>Betrag</th><th>%</th></tr></thead><tbody>' +
        Object.entries(data.breakdown).map(([k,v]) =>
          `<tr><td>${k}</td><td>${fmt(v)}</td><td>${(v/data.predicted_cost_eur*100).toFixed(1)}%</td></tr>`
        ).join('') + '</tbody></table>' : ''}
      ${data.key_factors?.length ? '<p style="margin-top:.75rem"><b>Einflussfaktoren:</b> ' + data.key_factors.join(', ') + '</p>' : ''}`;
    showResult('ki-cost-result', html, 'success');
  } catch (e) {
    showResult('ki-cost-result', `Fehler: ${e.message}`, 'error');
  } finally { hideLoading(); }
}

// ── ML Energy Optimization ────────────────────────────────────────────────────

async function runMLEnergy() {
  showLoading('Energie-Optimierung berechnen…');
  try {
    const data = await apiCall('/api/v1/ml/optimize-energy', {
      u_wert_wand: +document.getElementById('ke-uw').value,
      u_wert_dach: +document.getElementById('ke-ud').value,
      fensterflaeche_proz: +document.getElementById('ke-ff').value,
      klimazone: +document.getElementById('ke-kz').value,
      ziel_energieklasse: document.getElementById('ke-ziel').value
    });
    let html = `<h3>Energie-Optimierung</h3>
      <div class="result-grid">
        ${kv('Aktuelle HWB', `${data.current_hwb ?? '—'} kWh/m²a`)}
        ${kv('Optimierte HWB', `${data.optimized_hwb ?? '—'} kWh/m²a`)}
        ${kv('Erreichte Klasse', data.achieved_class ?? '—')}
        ${kv('Jährl. Einsparung', `${data.annual_savings_kwh ?? '—'} kWh/m²`)}
      </div>`;
    if (data.measures?.length) {
      html += '<b>Empfohlene Maßnahmen:</b><ul>';
      data.measures.forEach(m => {
        html += `<li><b>${m.measure}</b>: ${m.description} — Kosten: ${m.cost_per_m2} €/m², Einsparung: ${m.savings_kwh} kWh/m²a</li>`;
      });
      html += '</ul>';
    }
    showResult('ki-energy-result', html, 'success');
  } catch (e) {
    showResult('ki-energy-result', `Fehler: ${e.message}`, 'error');
  } finally { hideLoading(); }
}

// ── ML Material Recommendation ────────────────────────────────────────────────

async function runMLMaterial() {
  showLoading('Materialempfehlung berechnen…');
  try {
    const data = await apiCall('/api/v1/ml/recommend-material', {
      bauteil_typ: document.getElementById('km-typ').value,
      prioritaet: document.getElementById('km-prio').value,
      ziel_uwert: +document.getElementById('km-uw').value
    });
    let html = `<h3>Materialempfehlungen</h3>`;
    if (data.recommendations?.length) {
      html += '<table class="result-table"><thead><tr><th>Material</th><th>Dicke</th><th>U-Wert</th><th>€/m²</th><th>Score</th></tr></thead><tbody>';
      data.recommendations.forEach(r => {
        html += `<tr><td><b>${r.material}</b></td><td>${r.dicke_cm} cm</td><td>${r.u_wert} W/m²K</td><td>${r.kosten_m2}</td>
          <td>${badge(r.score_label ?? r.score, r.score >= 80 ? 'success' : r.score >= 60 ? 'warning' : 'error')}</td></tr>`;
      });
      html += '</tbody></table>';
    }
    showResult('ki-material-result', html, 'success');
  } catch (e) {
    showResult('ki-material-result', `Fehler: ${e.message}`, 'error');
  } finally { hideLoading(); }
}

// ── FEM Balken ────────────────────────────────────────────────────────────────

async function calcFEM() {
  showLoading('FEM-Berechnung…');
  try {
    const data = await apiCall('/api/v1/fem/single-span-beam', {
      length_m: +document.getElementById('fem-l').value,
      E_GPa: +document.getElementById('fem-e').value,
      I_cm4: +document.getElementById('fem-i').value,
      q_kN_m: +document.getElementById('fem-q').value,
      F_kN: +document.getElementById('fem-f').value,
      F_pos_m: +document.getElementById('fem-fa').value,
      support_left: document.getElementById('fem-lager-l').value,
      support_right: document.getElementById('fem-lager-r').value
    });
    const html = buildFEMResult(data);
    showResult('fem-result', html, 'success');
    drawFEMDiagram('fem-canvas', data);
  } catch (e) {
    showResult('fem-result', `Fehler: ${e.message}`, 'error');
  } finally { hideLoading(); }
}

async function calcFEM2() {
  showLoading('FEM 2-Feld Berechnung…');
  try {
    const data = await apiCall('/api/v1/fem/continuous-beam', {
      spans_m: [+document.getElementById('fem2-l1').value, +document.getElementById('fem2-l2').value],
      E_GPa: +document.getElementById('fem2-e').value,
      I_cm4: +document.getElementById('fem2-i').value,
      q_kN_m: [+document.getElementById('fem2-q1').value, +document.getElementById('fem2-q2').value]
    });
    const html = buildFEMResult(data);
    showResult('fem2-result', html, 'success');
    drawFEMDiagram('fem2-canvas', data);
  } catch (e) {
    showResult('fem2-result', `Fehler: ${e.message}`, 'error');
  } finally { hideLoading(); }
}

async function calcRahmen() {
  showLoading('Rahmenberechnung…');
  try {
    const data = await apiCall('/api/v1/fem/simple-frame', {
      width_m: +document.getElementById('fr-b').value,
      height_m: +document.getElementById('fr-h').value,
      horizontal_load_kN: +document.getElementById('fr-fh').value,
      vertical_load_kN_m: +document.getElementById('fr-fv').value
    });
    const html = buildFEMResult(data);
    showResult('rahmen-result', html, 'success');
  } catch (e) {
    showResult('rahmen-result', `Fehler: ${e.message}`, 'error');
  } finally { hideLoading(); }
}

function buildFEMResult(data) {
  let html = `<h3>FEM-Ergebnisse</h3><div class="result-grid">`;
  if (data.max_moment_kNm !== undefined) html += kv('Max. Biegemoment', `${data.max_moment_kNm?.toFixed(2)} kNm`);
  if (data.max_shear_kN !== undefined) html += kv('Max. Querkraft', `${data.max_shear_kN?.toFixed(2)} kN`);
  if (data.max_deflection_mm !== undefined) html += kv('Max. Durchbiegung', `${data.max_deflection_mm?.toFixed(2)} mm`);
  if (data.reactions) {
    Object.entries(data.reactions).forEach(([k,v]) => html += kv(k, `${v?.toFixed(2)} kN`));
  }
  if (data.eurocode_check) {
    const ok = data.eurocode_check.deflection_ok;
    html += kv('Durchbiegung EC', badge(ok ? 'OK (L/250)' : 'ÜBERSCHRITTEN', ok ? 'success' : 'error'));
  }
  html += '</div>';
  if (data.moment_diagram?.length) {
    html += '<p style="margin-top:.5rem;color:var(--text-muted);font-size:.8rem">Biegemoment-Diagramm ↓</p>';
  }
  return html;
}

function drawFEMDiagram(canvasId, data) {
  const canvas = document.getElementById(canvasId);
  if (!canvas || !data.moment_diagram?.length) return;
  canvas.style.display = 'block';
  const ctx = canvas.getContext('2d');
  const W = canvas.clientWidth || 700;
  const H = 280;
  canvas.width = W; canvas.height = H;
  const pad = 40;
  const xs = data.moment_diagram.map(p => p[0]);
  const ys = data.moment_diagram.map(p => p[1]);
  const xmin = Math.min(...xs), xmax = Math.max(...xs);
  const ymin = Math.min(...ys, 0), ymax = Math.max(...ys, 0);
  const scX = (W - 2*pad) / (xmax - xmin || 1);
  const scY = (H - 2*pad) / (Math.max(Math.abs(ymin), Math.abs(ymax)) * 2 || 1);
  const cx = x => pad + (x - xmin) * scX;
  const cy = y => H/2 - y * scY;

  ctx.clearRect(0, 0, W, H);
  // Axis
  ctx.strokeStyle = '#94a3b8'; ctx.lineWidth = 1;
  ctx.beginPath(); ctx.moveTo(pad, H/2); ctx.lineTo(W-pad, H/2); ctx.stroke();
  ctx.beginPath(); ctx.moveTo(pad, pad); ctx.lineTo(pad, H-pad); ctx.stroke();

  // Moment diagram (filled)
  ctx.beginPath();
  ctx.moveTo(cx(xs[0]), H/2);
  ys.forEach((y, i) => ctx.lineTo(cx(xs[i]), cy(y)));
  ctx.lineTo(cx(xs[xs.length-1]), H/2);
  ctx.closePath();
  ctx.fillStyle = 'rgba(37,99,235,0.15)';
  ctx.fill();
  ctx.strokeStyle = '#2563eb'; ctx.lineWidth = 2;
  ctx.beginPath();
  ys.forEach((y, i) => i === 0 ? ctx.moveTo(cx(xs[i]), cy(y)) : ctx.lineTo(cx(xs[i]), cy(y)));
  ctx.stroke();

  // Labels
  ctx.fillStyle = '#64748b'; ctx.font = '11px sans-serif'; ctx.textAlign = 'center';
  ctx.fillText(`${xmin.toFixed(1)} m`, pad, H-8);
  ctx.fillText(`${xmax.toFixed(1)} m`, W-pad, H-8);
  ctx.fillText(`Biegemoment [kNm]`, W/2, 15);
  const Mmax = Math.max(...ys.map(Math.abs));
  ctx.textAlign = 'right';
  ctx.fillText(`+${Mmax.toFixed(1)}`, pad-4, cy(Mmax)+4);
}

// ── Normen Monitor ────────────────────────────────────────────────────────────

async function checkNorms() {
  showLoading('Normen werden geprüft…');
  try {
    const data = await fetch('/api/v1/norms/check').then(r => r.json());
    let html = `<h3>Normen-Monitor — ${new Date().toLocaleString('de-AT')}</h3>
      <div class="result-grid">
        ${kv('Geprüfte Quellen', data.sources_checked ?? '—')}
        ${kv('Änderungen', badge(data.changes_detected ?? 0, data.changes_detected > 0 ? 'warning' : 'success'))}
        ${kv('Letzter Check', data.last_check ?? '—')}
      </div>`;
    if (data.updates?.length) {
      html += '<h3 style="margin-top:1rem">Erkannte Änderungen</h3>';
      data.updates.forEach(u => {
        html += `<div class="norm-card ${u.type === 'changed' ? 'changed' : u.type === 'new' ? 'new' : 'unchanged'}">
          ${badge(u.type.toUpperCase(), u.type === 'changed' ? 'warning' : u.type === 'new' ? 'info' : 'success')}
          <b>${u.source}</b>: ${u.title}<br>
          <span style="font-size:.8rem;color:var(--text-muted)">${u.url ?? ''} — ${u.detected_at ?? ''}</span>
        </div>`;
      });
    } else {
      html += '<p style="margin-top:.5rem;color:var(--success)">✅ Keine neuen Änderungen gefunden.</p>';
    }
    showResult('normen-result', html, data.changes_detected > 0 ? 'warning' : 'success');
    document.getElementById('normen-count').textContent = `${data.changes_detected ?? 0} neue Änderungen`;
  } catch (e) {
    showResult('normen-result', `Fehler: ${e.message}`, 'error');
  } finally { hideLoading(); }
}

async function getNormHistory() {
  try {
    const data = await fetch('/api/v1/norms/history').then(r => r.json());
    let html = '<h3>Normen-Verlauf</h3>';
    if (data.history?.length) {
      html += '<table class="result-table"><thead><tr><th>Datum</th><th>Quelle</th><th>Titel</th><th>Typ</th></tr></thead><tbody>';
      data.history.forEach(h => {
        html += `<tr><td>${h.detected_at ?? ''}</td><td>${h.source ?? ''}</td><td>${h.title ?? ''}</td>
          <td>${badge(h.type ?? '', h.type === 'changed' ? 'warning' : 'info')}</td></tr>`;
      });
      html += '</tbody></table>';
    } else {
      html += '<p>Noch kein Verlauf.</p>';
    }
    showResult('normen-detail', html);
  } catch (e) {
    showResult('normen-detail', `Fehler: ${e.message}`, 'error');
  }
}

// ── Behördeneinreichung ───────────────────────────────────────────────────────

async function generateEinreichung() {
  showLoading('Einreichunterlagen werden erstellt…');
  try {
    const data = await apiCall('/api/v1/submission/generate', {
      bundesland: document.getElementById('ein-bl').value,
      vorhaben: document.getElementById('ein-vorhaben').value,
      gebaudetyp: document.getElementById('ein-typ').value,
      bgf_m2: +document.getElementById('ein-bgf').value,
      bauherr: document.getElementById('ein-bh').value,
      grundstueck_kgez: document.getElementById('ein-kgez').value
    });
    let html = `<h3>Einreichunterlagen — ${data.bundesland?.toUpperCase()}</h3>
      <p style="margin-bottom:1rem;color:var(--text-muted)">${data.vorhaben} · ${data.bauherr}</p>
      <h4>Erforderliche Unterlagen (${data.total_documents} Dokumente)</h4>
      <table class="result-table"><thead><tr><th>#</th><th>Dokument</th><th>Pflicht</th><th>Hinweis</th></tr></thead><tbody>`;
    data.documents?.forEach((d, i) => {
      html += `<tr><td>${i+1}</td><td><b>${d.name}</b></td>
        <td>${badge(d.pflicht ? 'Pflicht' : 'Optional', d.pflicht ? 'error' : 'info')}</td>
        <td>${d.hinweis ?? ''}</td></tr>`;
    });
    html += '</tbody></table>';
    if (data.behoerde) {
      html += `<div style="margin-top:1rem;padding:1rem;background:#f8fafc;border-radius:6px">
        <b>Zuständige Behörde:</b> ${data.behoerde}<br>
        <b>Einreichung:</b> ${data.einreichungsart}<br>
        ${data.portal_url ? `<b>Portal:</b> <a href="${data.portal_url}" target="_blank">${data.portal_url}</a>` : ''}
      </div>`;
    }
    if (data.checkliste?.length) {
      html += '<h4 style="margin-top:1rem">Checkliste</h4><ul>';
      data.checkliste.forEach(c => html += `<li>${c}</li>`);
      html += '</ul>';
    }
    showResult('einreichung-result', html, 'success');
  } catch (e) {
    showResult('einreichung-result', `Fehler: ${e.message}`, 'error');
  } finally { hideLoading(); }
}

// ── WebSocket Kollaboration ───────────────────────────────────────────────────

let ws = null;

function connectWS() {
  const pid = document.getElementById('kol-pid').value;
  const uid = document.getElementById('kol-uid').value;
  const host = location.host;
  const proto = location.protocol === 'https:' ? 'wss' : 'ws';
  const url = `${proto}://${host}/api/v1/collaboration/ws/${pid}/${uid}`;
  ws = new WebSocket(url);

  ws.onopen = () => {
    document.getElementById('ws-status').textContent = '● Verbunden';
    document.getElementById('ws-status').className = 'badge badge-success';
    document.getElementById('kol-users').classList.remove('hidden');
    document.getElementById('kol-users').innerHTML = `<b>Verbunden mit Projekt ${esc(pid)} als ${esc(uid)}</b>`;
    appendMessage('System', 'WebSocket verbunden', 'incoming');
  };
  ws.onmessage = e => {
    try {
      const msg = JSON.parse(e.data);
      if (msg.type === 'pong') return;
      appendMessage(msg.user_id || 'Server', JSON.stringify(msg, null, 2), 'incoming');
    } catch {
      appendMessage('Server', e.data, 'incoming');
    }
  };
  ws.onerror = () => appendMessage('System', 'Verbindungsfehler', 'incoming');
  ws.onclose = () => {
    document.getElementById('ws-status').textContent = 'Getrennt';
    document.getElementById('ws-status').className = 'badge badge-offline';
    appendMessage('System', 'WebSocket getrennt', 'incoming');
  };
}

function disconnectWS() {
  if (ws) { ws.close(); ws = null; }
}

function sendWSMsg() {
  const msg = document.getElementById('kol-msg').value;
  if (!msg || !ws || ws.readyState !== 1) return;
  const uid = document.getElementById('kol-uid').value;
  const name = document.getElementById('kol-name').value;
  ws.send(JSON.stringify({ type: 'chat', user_id: uid, user_name: name, text: msg, timestamp: new Date().toISOString() }));
  appendMessage('Du', msg, 'outgoing');
  document.getElementById('kol-msg').value = '';
}

function appendMessage(from, text, dir) {
  const box = document.getElementById('kol-messages');
  const el = document.createElement('div');
  el.className = `message-item ${dir}`;
  const msgDiv = document.createElement('div');
  msgDiv.textContent = text;
  const metaDiv = document.createElement('div');
  metaDiv.className = 'message-meta';
  metaDiv.textContent = `${from} · ${new Date().toLocaleTimeString('de-AT')}`;
  el.appendChild(msgDiv);
  el.appendChild(metaDiv);
  box.appendChild(el);
  box.scrollTop = box.scrollHeight;
}

// ── Init ──────────────────────────────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', () => {
  checkAPIStatus();
  setInterval(checkAPIStatus, 30000);
  // Show dashboard by default
  showSection('dashboard');
  // Ping normen count
  fetch('/api/v1/norms/check').then(r => r.json())
    .then(d => { document.getElementById('normen-count').textContent = `${d.changes_detected ?? 0} neue Änderungen`; })
    .catch(() => { document.getElementById('normen-count').textContent = 'Offline'; });
});

// Keyboard shortcut Enter in msg field
document.getElementById('kol-msg')?.addEventListener('keydown', e => {
  if (e.key === 'Enter') sendWSMsg();
});
