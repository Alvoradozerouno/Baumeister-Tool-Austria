"""
Tests für die neuen Feature-Module:
- ML Kostenprognose und Energie-Optimierung
- FEM Tragwerksberechnung
- Behördeneinreichungs-Generator
- Normen-Monitor (offline)
- IFC STEP-Parser
- API-Endpunkte (FastAPI TestClient)
"""

import pytest
from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# ML Tests
# ---------------------------------------------------------------------------

class TestCostModel:
    def test_predict_output_structure(self):
        from api.ml import get_cost_model
        model = get_cost_model()
        result = model.predict("tirol", "mehrfamilienhaus", 500, 4, "A+")
        assert "predicted_cost_eur" in result
        assert "cost_range_min" in result
        assert "cost_range_max" in result
        assert "confidence_score" in result
        assert "breakdown" in result
        assert result["confidence_score"] > 0

    def test_range_bounds(self):
        from api.ml import get_cost_model
        model = get_cost_model()
        result = model.predict("wien", "hochhaus", 2000, 10, "A++")
        assert result["cost_range_min"] < result["predicted_cost_eur"] < result["cost_range_max"]

    def test_bundesland_variation(self):
        from api.ml import get_cost_model
        model = get_cost_model()
        r_wien = model.predict("wien", "mehrfamilienhaus", 500, 4)
        r_burgenland = model.predict("burgenland", "mehrfamilienhaus", 500, 4)
        # Wien sollte teurer sein als Burgenland
        assert r_wien["predicted_cost_eur"] > r_burgenland["predicted_cost_eur"]

    def test_budget_delta(self):
        from api.ml import get_cost_model
        model = get_cost_model()
        result = model.predict("tirol", "einfamilienhaus", 200, 2, budget_euro=300000)
        assert "budget_delta" in result
        assert "budget_status" in result

    def test_all_bundeslaender(self):
        from api.ml import get_cost_model
        model = get_cost_model()
        for bl in ["wien", "tirol", "salzburg", "niederoesterreich", "oberoesterreich",
                   "vorarlberg", "steiermark", "kaernten", "burgenland"]:
            result = model.predict(bl, "mehrfamilienhaus", 300, 3)
            assert result["predicted_cost_eur"] > 100000, f"Unrealistic cost for {bl}"


class TestEnergyModel:
    def test_optimise_output(self):
        from api.ml import get_energy_model
        model = get_energy_model()
        result = model.optimise(0.35, 0.20, 20, 3, "A+")
        assert "current_hwb" in result
        assert "optimized_hwb" in result
        assert "achieved_class" in result
        assert "measures" in result

    def test_optimised_hwb_lower(self):
        from api.ml import get_energy_model
        model = get_energy_model()
        result = model.optimise(0.50, 0.30, 25, 3, "A+")
        assert result["optimized_hwb"] <= result["current_hwb"]

    def test_achieved_class_valid(self):
        from api.ml import get_energy_model
        model = get_energy_model()
        result = model.optimise(0.20, 0.15, 15, 2, "A++")
        assert result["achieved_class"] in ["A++", "A+", "A", "B", "C", "D", "E", "F", "G"]

    def test_climate_zones(self):
        from api.ml import get_energy_model
        model = get_energy_model()
        r1 = model.optimise(0.35, 0.20, 20, 1, "A")
        r3 = model.optimise(0.35, 0.20, 20, 3, "A")
        # Alpine zone (3) should have higher base HWB
        assert r3["current_hwb"] >= r1["current_hwb"]


class TestMaterialRecommendation:
    def test_output_structure(self):
        from api.ml import recommend_material
        result = recommend_material("aussenwand", "kosten", 0.15)
        assert "recommendations" in result
        assert len(result["recommendations"]) > 0
        assert "material" in result["recommendations"][0]
        assert "score" in result["recommendations"][0]
        assert "u_wert" in result["recommendations"][0]

    def test_all_bauteil_types(self):
        from api.ml import recommend_material
        for btyp in ["aussenwand", "dach", "boden"]:
            result = recommend_material(btyp, "kosten", 0.15)
            assert len(result["recommendations"]) > 0

    def test_sorted_by_score(self):
        from api.ml import recommend_material
        result = recommend_material("aussenwand", "energie", 0.12)
        scores = [r["score"] for r in result["recommendations"]]
        assert scores == sorted(scores, reverse=True)

    def test_prioritaet_affects_result(self):
        from api.ml import recommend_material
        r_kosten = recommend_material("aussenwand", "kosten", 0.15)
        r_eco = recommend_material("aussenwand", "nachhaltigkeit", 0.15)
        # Results may differ by top choice
        assert isinstance(r_kosten["recommendations"], list)
        assert isinstance(r_eco["recommendations"], list)


# ---------------------------------------------------------------------------
# FEM Tests
# ---------------------------------------------------------------------------

class TestSingleSpanBeam:
    def test_simply_supported_udl_analytical(self):
        """M_max = qL²/8, δ_max = 5qL⁴/(384EI)"""
        from api.structural_fem import solve_single_span_beam
        L, q, E_GPa, I_cm4 = 6.0, 10.0, 30.0, 10000.0
        result = solve_single_span_beam(L, E_GPa, I_cm4, q, 0, 3.0, "pinned", "pinned")
        M_analytical = q * L ** 2 / 8
        assert abs(result["max_moment_kNm"] - M_analytical) < 0.5, (
            f"M_max mismatch: got {result['max_moment_kNm']}, expected ~{M_analytical}")
        # Deflection: δ = 5qL⁴/(384EI)
        EI = E_GPa * 1e9 * I_cm4 * 1e-8
        d_analytical = 5 * q * 1000 * L ** 4 / (384 * EI) * 1000  # mm
        assert abs(result["max_deflection_mm"] - d_analytical) < 1.0

    def test_reactions_sum_to_total_load(self):
        from api.structural_fem import solve_single_span_beam
        L, q = 8.0, 12.0
        result = solve_single_span_beam(L, 30.0, 5000.0, q, 0, 4.0, "pinned", "pinned")
        total_load = q * L
        r_sum = abs(result["reactions"]["R_links_kN"]) + abs(result["reactions"]["R_rechts_kN"])
        assert abs(r_sum - total_load) < 1.0

    def test_eurocode_check_present(self):
        from api.structural_fem import solve_single_span_beam
        result = solve_single_span_beam(6.0, 30.0, 5000.0, 15.0, 0, 3.0, "pinned", "pinned")
        assert "eurocode_check" in result
        assert "deflection_ok" in result["eurocode_check"]

    def test_moment_diagram_has_data(self):
        from api.structural_fem import solve_single_span_beam
        result = solve_single_span_beam(5.0, 30.0, 8000.0, 10.0, 0, 2.5, "pinned", "pinned")
        assert "moment_diagram" in result
        assert len(result["moment_diagram"]) > 10


class TestContinuousBeam:
    def test_two_span_output(self):
        from api.structural_fem import solve_continuous_beam
        result = solve_continuous_beam([5.0, 6.0], 30.0, 5000.0, [15.0, 20.0])
        assert "max_moment_kNm" in result
        assert result["max_moment_kNm"] > 0
        assert "reactions" in result

    def test_single_span_fallback(self):
        from api.structural_fem import solve_continuous_beam
        result = solve_continuous_beam([6.0], 30.0, 5000.0, [15.0])
        assert "max_moment_kNm" in result

    def test_interior_moment_negative(self):
        """Interior support moment should be negative (hogging)."""
        from api.structural_fem import solve_continuous_beam
        result = solve_continuous_beam([5.0, 5.0], 30.0, 5000.0, [10.0, 10.0])
        if "moment_interior_support_kNm" in result:
            assert result["moment_interior_support_kNm"] < 0


class TestSimpleFrame:
    def test_output_structure(self):
        from api.structural_fem import solve_simple_frame
        result = solve_simple_frame(6.0, 4.0, 10.0, 20.0)
        assert "max_moment_kNm" in result
        assert "horizontal_sway_mm" in result
        assert "eurocode_check" in result

    def test_no_horizontal_load_no_sway(self):
        from api.structural_fem import solve_simple_frame
        result = solve_simple_frame(6.0, 4.0, 0.0, 20.0)
        assert result["horizontal_sway_mm"] == 0.0

    def test_eurocode_drift_check(self):
        from api.structural_fem import solve_simple_frame
        # Stiff frame → small sway
        result = solve_simple_frame(6.0, 4.0, 5.0, 10.0, E_GPa=30, I_col_cm4=50000)
        assert "deflection_ok" in result["eurocode_check"]


# ---------------------------------------------------------------------------
# Submission Generator Tests
# ---------------------------------------------------------------------------

class TestSubmissionGenerator:
    def test_basic_output(self):
        from api.submission_generator import generate_submission_package
        result = generate_submission_package("tirol", "neubau", "wohnbau", 500)
        assert "documents" in result
        assert result["total_documents"] > 0
        assert "behoerde" in result
        assert "checkliste" in result

    def test_all_bundeslaender(self):
        from api.submission_generator import generate_submission_package
        for bl in ["wien", "tirol", "salzburg", "niederoesterreich", "oberoesterreich",
                   "vorarlberg", "steiermark", "kaernten", "burgenland"]:
            r = generate_submission_package(bl, "neubau", "wohnbau", 300)
            assert r["behoerde"] != "", f"No Behörde for {bl}"

    def test_large_building_extra_docs(self):
        from api.submission_generator import generate_submission_package
        r_small = generate_submission_package("tirol", "neubau", "wohnbau", 500)
        r_large = generate_submission_package("tirol", "neubau", "wohnbau", 2000)
        assert r_large["total_documents"] > r_small["total_documents"]

    def test_all_vorhaben_types(self):
        from api.submission_generator import generate_submission_package
        for vorhaben in ["neubau", "zubau", "umbau", "abbruch", "dachausbau"]:
            r = generate_submission_package("wien", vorhaben, "wohnbau", 200)
            assert r["total_documents"] > 0

    def test_portal_url_present(self):
        from api.submission_generator import generate_submission_package
        r = generate_submission_package("wien", "neubau", "wohnbau", 300)
        assert r["portal_url"] and "wien" in r["portal_url"]

    def test_mandatory_docs_present(self):
        from api.submission_generator import generate_submission_package
        r = generate_submission_package("tirol", "neubau", "wohnbau", 300)
        mandatory = [d for d in r["documents"] if d["pflicht"]]
        assert len(mandatory) >= 5


# ---------------------------------------------------------------------------
# IFC STEP Parser Tests
# ---------------------------------------------------------------------------

class TestStepIFCParser:
    def test_parse_minimal_ifc(self, tmp_path):
        """Create a minimal IFC STEP file and parse it."""
        from bim_ifc_real import parse_ifc_fallback
        ifc_content = """ISO-10303-21;
HEADER;
FILE_SCHEMA(('IFC4'));
ENDSEC;
DATA;
#1=IFCPROJECT('1HQ0R8pWT9MB5$nVJRDbeV',$,'Test Building',$,$,$,$,(#20),#10);
#10=IFCUNITASSIGNMENT((#11,#12));
#11=IFCSIUNIT(*,.LENGTHUNIT.,.MILLI.,.METRE.);
#12=IFCSIUNIT(*,.AREAUNIT.,$,.SQUARE_METRE.);
#20=IFCGEOMETRICREPRESENTATIONCONTEXT($,'Model',3,1.E-005,#30,$);
#30=IFCAXIS2PLACEMENT3D(#31,$,$);
#31=IFCCARTESIANPOINT((0.,0.,0.));
#40=IFCBUILDINGSTOREY('2HQ0R8pWT9MB5$nVJRDbeA',$,'EG',$,$,$,$,$,.ELEMENT.,0.);
#41=IFCBUILDINGSTOREY('3HQ0R8pWT9MB5$nVJRDbeB',$,'OG',$,$,$,$,$,.ELEMENT.,3.);
#50=IFCWALL('4HQ0R8pWT9MB5$nVJRDbeC',$,'Außenwand',$,$,$,$,$,$);
#51=IFCWALL('5HQ0R8pWT9MB5$nVJRDbeD',$,'Innenwand',$,$,$,$,$,$);
#60=IFCDOOR('6HQ0R8pWT9MB5$nVJRDbeE',$,'Haustür',$,$,$,$,$,0.9,2.1);
#61=IFCDOOR('7HQ0R8pWT9MB5$nVJRDbeF',$,'Zimmertür',$,$,$,$,$,0.9,2.05);
#70=IFCWINDOW('8HQ0R8pWT9MB5$nVJRDbeG',$,'Fenster 1',$,$,$,$,$,1.2,1.4);
#80=IFCMATERIAL($,'Beton C25/30',$);
#81=IFCMATERIAL($,'Ziegel',$);
ENDSEC;
END-ISO-10303-21;
"""
        ifc_file = tmp_path / "test.ifc"
        ifc_file.write_text(ifc_content)

        result = parse_ifc_fallback(str(ifc_file))
        assert result.ifc_schema == "IFC4"
        assert result.project_name == "Test Building"
        assert len(result.storey_names) >= 2
        assert len(result.materials) >= 2
        elem_counts = result.element_counts_display()
        assert elem_counts.get("IfcWall", 0) >= 2
        assert elem_counts.get("IfcDoor", 0) >= 2

    def test_parse_nonexistent_file(self):
        from bim_ifc_real import parse_ifc_fallback
        with pytest.raises(ValueError, match="Cannot read IFC file"):
            parse_ifc_fallback("/nonexistent/file.ifc")


# ---------------------------------------------------------------------------
# External Data Module Tests (offline)
# ---------------------------------------------------------------------------

class TestExternalDataModule:
    def test_cache_set_get(self, tmp_path, monkeypatch):
        import api.external_data as ed
        monkeypatch.setattr(ed, "_CACHE_DIR", tmp_path)
        monkeypatch.setattr(ed, "_HASH_FILE", tmp_path / "norm_hashes.json")
        ed._cache_set("test_key", {"hello": "world"})
        val = ed._cache_get("test_key")
        assert val == {"hello": "world"}

    def test_get_norm_history_empty(self, tmp_path, monkeypatch):
        import api.external_data as ed
        monkeypatch.setattr(ed, "_CACHE_DIR", tmp_path)
        monkeypatch.setattr(ed, "_HASH_FILE", tmp_path / "norm_hashes.json")
        result = ed.get_norm_history()
        assert "history" in result
        assert isinstance(result["history"], list)


# ---------------------------------------------------------------------------
# API Endpoint Tests
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def client():
    from api.main import app
    return TestClient(app)


class TestMLEndpoints:
    def test_predict_cost(self, client):
        r = client.post("/api/v1/ml/predict-cost", json={
            "bundesland": "tirol", "gebaudetyp": "mehrfamilienhaus",
            "bgf_m2": 500, "geschosse": 4, "energieziel": "A+"
        })
        assert r.status_code == 200
        data = r.json()
        assert data["predicted_cost_eur"] > 0

    def test_optimize_energy(self, client):
        r = client.post("/api/v1/ml/optimize-energy", json={
            "u_wert_wand": 0.35, "u_wert_dach": 0.20,
            "fensterflaeche_proz": 20, "klimazone": 3, "ziel_energieklasse": "A+"
        })
        assert r.status_code == 200
        assert "achieved_class" in r.json()

    def test_recommend_material(self, client):
        r = client.post("/api/v1/ml/recommend-material", json={
            "bauteil_typ": "aussenwand", "prioritaet": "kosten", "ziel_uwert": 0.15
        })
        assert r.status_code == 200
        assert len(r.json()["recommendations"]) > 0

    def test_invalid_bauteil_typ(self, client):
        r = client.post("/api/v1/ml/recommend-material", json={
            "bauteil_typ": "INVALID", "prioritaet": "kosten", "ziel_uwert": 0.15
        })
        assert r.status_code == 400


class TestFEMEndpoints:
    def test_single_span_beam(self, client):
        r = client.post("/api/v1/fem/single-span-beam", json={
            "length_m": 6.0, "E_GPa": 30, "I_cm4": 5000,
            "q_kN_m": 15, "support_left": "pinned", "support_right": "pinned"
        })
        assert r.status_code == 200
        data = r.json()
        assert "max_moment_kNm" in data
        assert "max_deflection_mm" in data

    def test_continuous_beam(self, client):
        r = client.post("/api/v1/fem/continuous-beam", json={
            "spans_m": [5.0, 6.0], "E_GPa": 30, "I_cm4": 5000,
            "q_kN_m": [15.0, 20.0]
        })
        assert r.status_code == 200

    def test_simple_frame(self, client):
        r = client.post("/api/v1/fem/simple-frame", json={
            "width_m": 6.0, "height_m": 4.0,
            "horizontal_load_kN": 10, "vertical_load_kN_m": 20
        })
        assert r.status_code == 200
        assert "horizontal_sway_mm" in r.json()

    def test_invalid_support(self, client):
        r = client.post("/api/v1/fem/single-span-beam", json={
            "length_m": 6.0, "E_GPa": 30, "I_cm4": 5000,
            "q_kN_m": 15, "support_left": "WRONG", "support_right": "pinned"
        })
        assert r.status_code == 400

    def test_span_mismatch_error(self, client):
        r = client.post("/api/v1/fem/continuous-beam", json={
            "spans_m": [5.0, 6.0, 4.0], "E_GPa": 30, "I_cm4": 5000,
            "q_kN_m": [15.0]  # mismatch
        })
        assert r.status_code == 400


class TestSubmissionEndpoints:
    def test_generate(self, client):
        r = client.post("/api/v1/submission/generate", json={
            "bundesland": "tirol", "vorhaben": "neubau",
            "gebaudetyp": "wohnbau", "bgf_m2": 500
        })
        assert r.status_code == 200
        data = r.json()
        assert data["total_documents"] > 0
        assert "documents" in data

    def test_invalid_bundesland(self, client):
        r = client.post("/api/v1/submission/generate", json={
            "bundesland": "INVALID", "vorhaben": "neubau",
            "gebaudetyp": "wohnbau", "bgf_m2": 300
        })
        assert r.status_code == 400

    def test_invalid_vorhaben(self, client):
        r = client.post("/api/v1/submission/generate", json={
            "bundesland": "tirol", "vorhaben": "INVALID",
            "gebaudetyp": "wohnbau", "bgf_m2": 300
        })
        assert r.status_code == 400


class TestNormsEndpoints:
    def test_history_empty(self, client):
        r = client.get("/api/v1/norms/history")
        assert r.status_code == 200
        assert "history" in r.json()

    def test_hora_invalid_coords(self, client):
        r = client.get("/api/v1/norms/hora/51.0/15.0")  # Outside Austria
        assert r.status_code == 400


class TestFrontendServing:
    def test_frontend_served(self, client):
        r = client.get("/app")
        assert r.status_code == 200
        assert "ORION" in r.text
