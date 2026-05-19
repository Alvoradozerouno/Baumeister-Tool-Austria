import os
import sys

from fastapi.testclient import TestClient

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api.main import app

client = TestClient(app)


class TestPlanIngestion:
    def test_upload_pdf_plan_runs_downstream_checks(self):
        pdf_content = b"""%PDF-1.4
Bundesland: Wien
Gebaeudetyp: Wohngebaeude
BGF: 1280 m2
Geschosse: 4
Wohnungen: 12
%%EOF
"""
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
        assert data["downstream_results"]["parking"]["result"]["required_stellplaetze"] == 14

    def test_upload_dwg_plan_uses_defaults_and_runs_compliance(self):
        dwg_content = b"""AC1027
PROJECT=Planstudie
BGF 950
Geschosse 3
Office Building / Buerohaus
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

    def test_upload_plan_rejects_unsupported_extension(self):
        response = client.post(
            "/api/v1/bim/upload-plan",
            files={"file": ("not-supported.txt", b"plain text", "text/plain")},
        )

        assert response.status_code == 400
        assert "Supported plan formats" in response.json()["error"]
