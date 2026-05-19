import os
import sys

from fastapi.testclient import TestClient

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api.main import app

client = TestClient(app)


class TestPlanIngestion:
    def test_upload_pdf_plan_runs_downstream_checks(self):
        pdf_content = """%PDF-1.4
Projekt: Wohnpark Donaustadt
Bundesland: Wien
Gebäudetyp: Wohngebäude
BGF: 1280 m2
Geschosse: 4
Wohnungen: 12
Fenster: 24
Türen: 18
Räume: 16
U-Wert Wand: 0.22
U-Wert Dach: 0.14
U-Wert Fenster: 0.85
%%EOF
""".encode("utf-8")
        response = client.post(
            "/api/v1/bim/upload-plan",
            files={"file": ("musterplan.pdf", pdf_content, "application/pdf")},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["source_type"] == "PDF"
        assert data["ingestion_mode"] == "heuristic_text_scan"
        assert data["epistemic_state"] == "ESTIMATED"
        assert data["extracted_plan"]["bundesland"] == "wien"
        assert data["extracted_plan"]["building_type"] == "wohngebaeude"
        assert data["extracted_plan"]["bgf_m2"] == 1280.0
        assert data["extracted_plan"]["geschosse"] == 4
        assert data["extracted_plan"]["wohnungen"] == 12
        assert data["plan_ready_for_api"] is True
        assert data["downstream_results"]["compliance"]["checked"] is True
        assert data["downstream_results"]["parking"]["checked"] is True
        assert data["downstream_results"]["parking"]["result"]["factor"] == 1.2
        assert data["downstream_results"]["parking"]["result"]["required_stellplaetze"] == 14
        assert data["derived_metrics"]["project_name"] == "Wohnpark Donaustadt"
        assert data["derived_metrics"]["fenster_anzahl"] == 24
        assert data["derived_metrics"]["tueren_anzahl"] == 18
        assert data["derived_metrics"]["raeume_anzahl"] == 16
        assert data["derived_metrics"]["thermal_inputs"]["uwert_wand"] == 0.22
        assert data["derived_metrics"]["heating_load"]["bundesland"] == "wien"
        assert data["field_source_metadata"]["bgf_m2"]["verification_level"] == "predicted"
        assert data["epistemic_trace"]["policy_assessment"]["mode"] == "probabilistic"
        assert data["epistemic_trace"]["input_states"]["bgf_m2"]["knowledge_type"] == "estimated"
        assert any(source["source"] == "genesis.framework" for source in data["information_sources"])

    def test_upload_dwg_plan_uses_defaults_and_runs_compliance(self):
        dwg_content = b"""AC1027
PROJECT=Planstudie Seestadt
LAYER_WALL
BGF 950
Geschosse 3
Office Building / Buerohaus
Windows 30
"""
        response = client.post(
            "/api/v1/bim/upload-plan",
            files={"file": ("planstudie.dwg", dwg_content, "application/octet-stream")},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["source_type"] == "DWG"
        assert data["extracted_plan"]["bundesland"] == "wien"
        assert data["extracted_plan"]["building_type"] == "buerogebaeude"
        assert data["defaulted_fields"] == ["bundesland"]
        assert data["plan_ready_for_api"] is True
        assert data["downstream_results"]["compliance"]["checked"] is True
        assert data["downstream_results"]["parking"]["checked"] is False
        assert data["derived_metrics"]["project_name"] == "Planstudie Seestadt"
        assert data["derived_metrics"]["fenster_anzahl"] == 30
        assert data["derived_metrics"]["cad_layers_detected"] == ["cad_layer_metadata"]
        assert data["field_source_metadata"]["bundesland"]["verification_level"] == "assumed"

    def test_upload_pdf_plan_bridges_missing_wohnungen_for_parking(self):
        pdf_content = """%PDF-1.4
Projekt: Wohnbau Linz
Bundesland: Oberoesterreich
Gebäudetyp: Mehrfamilienhaus
BGF: 850 m2
Geschosse: 3
%%EOF
""".encode("utf-8")
        response = client.post(
            "/api/v1/bim/upload-plan",
            files={"file": ("wohnbau.pdf", pdf_content, "application/pdf")},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["downstream_results"]["estimated_fields"]["wohnungen"]["value"] == 10
        assert data["downstream_results"]["parking"]["checked"] is True
        assert data["field_source_metadata"]["wohnungen"]["status"] == "estimated"
        assert data["field_source_metadata"]["wohnungen"]["source_layer"] == "deterministic_area_ratio_bridge"

    def test_upload_plan_report_returns_report_and_heating_load(self):
        pdf_content = """%PDF-1.4
Projekt: Bauvorhaben Graz
Bundesland: Steiermark
Gebäudetyp: Wohngebäude
BGF: 980 m2
Geschosse: 3
Wohnungen: 8
Fenster: 14
U-Wert Wand: 0.24
U-Wert Dach: 0.16
U-Wert Fenster: 0.35
OCR scan layer
%%EOF
""".encode("utf-8")
        response = client.post(
            "/api/v1/bim/upload-plan-report",
            files={"file": ("bauvorhaben.pdf", pdf_content, "application/pdf")},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["ingestion"]["derived_metrics"]["project_name"] == "Bauvorhaben Graz"
        assert data["ingestion"]["derived_metrics"]["heating_load"]["bundesland"] == "steiermark"
        assert data["report"]["project"]["project_name"] == "Bauvorhaben Graz"
        assert data["report"]["calculations"]["estimated_energy_class"] == "B"
        assert data["report"]["calculations"]["heating_load"]["standard"] == "ÖNORM EN 12831"
        assert data["report"]["epistemic_state"] == "ESTIMATED"
        assert data["report"]["governance"]["human_review_required"] is True
        assert data["report"]["governance"]["policy_decision"]["mode"] == "fallback"
        assert data["report"]["field_source_metadata"]["bgf_m2"]["standards"] == ["ÖNORM B 1800", "OIB-RL 6"]

    def test_upload_plan_rejects_unsupported_extension(self):
        response = client.post(
            "/api/v1/bim/upload-plan",
            files={"file": ("not-supported.txt", b"plain text", "text/plain")},
        )

        assert response.status_code == 400
        assert "Supported formats" in response.json()["error"]
