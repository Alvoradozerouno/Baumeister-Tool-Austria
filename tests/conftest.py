"""
Pytest configuration and shared fixtures for ORION Architekt-AT test suite.
Provides common fixtures, mocks, and utilities for all tests.
"""

import json
import os
import sys
from typing import Any, Dict, Generator
from unittest.mock import MagicMock, patch

import pytest

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ============================================================================
# API FIXTURES
# ============================================================================


@pytest.fixture
def mock_fastapi_app():
    """Create mock FastAPI app for testing without dependencies"""
    try:
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        app = FastAPI()
        return TestClient(app)
    except ImportError:
        return None


@pytest.fixture
def api_headers():
    """Standard API request headers"""
    return {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "User-Agent": "ORION-Test-Suite/1.0",
    }


@pytest.fixture
def auth_headers():
    """Auth headers with test token"""
    return {
        "Authorization": "Bearer test_token_12345",
        "Content-Type": "application/json",
    }


# ============================================================================
# BUILDING DATA FIXTURES
# ============================================================================


@pytest.fixture
def minimal_building_data() -> Dict[str, Any]:
    """Minimal valid building data"""
    return {
        "name": "Test Building",
        "bundesland": "wien",
        "building_type": "RESIDENTIAL",
        "gross_floor_area_m2": 1000,
        "total_stories": 3,
    }


@pytest.fixture
def complete_building_data() -> Dict[str, Any]:
    """Complete building data with all fields"""
    return {
        "name": "Complete Test Building",
        "bundesland": "wien",
        "building_type": "RESIDENTIAL",
        "construction_date": "2023-01-15",
        "renovation_date": "2024-01-15",
        "gross_floor_area_m2": 5000,
        "usable_floor_area_m2": 4000,
        "total_stories": 5,
        "underground_stories": 1,
        "thermal_mass": "HIGH",
        "window_ratio": 0.35,
        "orientation": "NORTH",
        "location_coordinates": {"latitude": 48.2082, "longitude": 16.3738},
    }


@pytest.fixture
def material_layer_data() -> Dict[str, Any]:
    """Wall material layer for U-value calculation"""
    return {
        "material": "Beton C30/37",
        "thickness_mm": 200,
        "lambda_value": 2.3,
        "density": 2400,
        "specific_heat": 1000,
    }


@pytest.fixture
def hwb_calculation_data() -> Dict[str, Any]:
    """HWB (heating water balance) calculation input"""
    return {
        "building_area_m2": 1500,
        "heating_demand_kwh_a": 45000,
        "hot_water_demand_kwh_a": 12000,
        "renewable_energy_kwh_a": 5000,
        "grid_feed_kwh_a": 2000,
    }


@pytest.fixture
def floorplan_data() -> Dict[str, Any]:
    """Floor plan data for area calculations"""
    return {
        "rooms": [
            {
                "name": "Living Room",
                "length_m": 5.0,
                "width_m": 4.0,
                "height_m": 2.8,
                "usage": "LIVING",
            },
            {
                "name": "Bedroom",
                "length_m": 4.0,
                "width_m": 3.5,
                "height_m": 2.8,
                "usage": "BEDROOM",
            },
            {
                "name": "Kitchen",
                "length_m": 3.0,
                "width_m": 2.5,
                "height_m": 2.8,
                "usage": "KITCHEN",
            },
        ],
        "total_area_m2": 52.5,
    }


# ============================================================================
# COMPLIANCE FIXTURES
# ============================================================================


@pytest.fixture
def oib_richtlinien_inputs() -> Dict[str, Any]:
    """OIB Richtlinien compliance check inputs"""
    return {
        "hwb_kwh_m2_a": 35.0,
        "fgee": 0.65,
        "heating_system": "Gas Condensing Boiler",
        "building_envelope_quality": "GOOD",
        "renewable_energy_percentage": 25.0,
    }


@pytest.fixture
def oenorm_a2060_inputs() -> Dict[str, Any]:
    """ÖNORM A 2060 energy calculation inputs"""
    return {
        "q_h": 40,  # Heating load
        "q_c": 20,  # Cooling load
        "renewable_fraction": 0.30,
        "storage_capacity_kwh": 10,
    }


@pytest.fixture
def bauordnung_compliance() -> Dict[str, Any]:
    """Bauordnung compliance test data"""
    return {
        "escape_route_length_m": 35,
        "parking_spaces": 15,
        "min_room_height_m": 2.8,
        "accessible_entrance": True,
        "fire_rating": "F90",
    }


# ============================================================================
# CALCULATION FIXTURES
# ============================================================================


@pytest.fixture
def load_case_permanent() -> Dict[str, Any]:
    """Permanent load case for structural calculation"""
    return {
        "dead_load_kn_m2": 5.5,
        "live_load_kn_m2": 0.0,
        "partial_factor": 1.35,
    }


@pytest.fixture
def load_case_variable() -> Dict[str, Any]:
    """Variable load case for structural calculation"""
    return {
        "dead_load_kn_m2": 0.0,
        "live_load_kn_m2": 5.0,
        "partial_factor": 1.5,
    }


@pytest.fixture
def eurocode_beam_data() -> Dict[str, Any]:
    """Eurocode beam calculation data"""
    return {
        "span_m": 6.0,
        "cross_section": "IPE 400",
        "material": "S235",
        "load_kn_m": 25.0,
        "supports": ["FIXED", "PINNED"],
    }


# ============================================================================
# BIM/IFC FIXTURES
# ============================================================================


@pytest.fixture
def ifc_element_data() -> Dict[str, Any]:
    """Sample IFC element data"""
    return {
        "element_type": "IfcWall",
        "name": "Outer Wall North",
        "guid": "0IH_6Z7xr0NRLH7XbmBEJG",
        "layers": [
            {"material": "Concrete", "thickness": 0.2},
            {"material": "Insulation", "thickness": 0.16},
            {"material": "Plaster", "thickness": 0.015},
        ],
        "u_value": 0.25,
    }


@pytest.fixture
def bim_model_metadata() -> Dict[str, Any]:
    """BIM model metadata"""
    return {
        "model_name": "ORF Building Design v1",
        "ifc_version": "IFC4",
        "origin_project": "wien_residential_2024",
        "created_date": "2024-01-15",
        "author": "Test Architect",
        "total_volume_m3": 5000,
    }


# ============================================================================
# MOCK IMPLEMENTATIONS
# ============================================================================


class MockDatabase:
    """Mock database for testing without real connections"""

    def __init__(self):
        self.data = {}
        self.transaction_active = False

    def query(self, table: str, **kwargs):
        """Mock database query"""
        return self.data.get(table, [])

    def insert(self, table: str, data: Dict[str, Any]):
        """Mock database insert"""
        if table not in self.data:
            self.data[table] = []
        self.data[table].append(data)
        return True

    def update(self, table: str, data: Dict[str, Any], **kwargs):
        """Mock database update"""
        return True

    def delete(self, table: str, **kwargs):
        """Mock database delete"""
        return True

    def begin_transaction(self):
        """Mock transaction begin"""
        self.transaction_active = True

    def commit(self):
        """Mock transaction commit"""
        self.transaction_active = False

    def rollback(self):
        """Mock transaction rollback"""
        self.transaction_active = False


@pytest.fixture
def mock_db() -> MockDatabase:
    """Provide mock database for tests"""
    return MockDatabase()


class MockExternalService:
    """Mock external service responses"""

    def __init__(self):
        self.calls = []

    def fetch_building_data(self, address: str):
        """Mock fetch building data"""
        self.calls.append(("fetch_building_data", address))
        return {"success": True, "data": {}}

    def calculate_energy(self, inputs: Dict[str, Any]):
        """Mock energy calculation"""
        self.calls.append(("calculate_energy", inputs))
        return {"hwb": 45.0, "fgee": 0.68}

    def verify_compliance(self, compliance_type: str, data: Dict[str, Any]):
        """Mock compliance verification"""
        self.calls.append(("verify_compliance", compliance_type, data))
        return {"compliant": True, "details": {}}


@pytest.fixture
def mock_service() -> MockExternalService:
    """Provide mock external service"""
    return MockExternalService()


# ============================================================================
# CONTEXT MANAGERS
# ============================================================================


@pytest.fixture
def mock_file_operations():
    """Mock file operations for testing"""
    from unittest.mock import mock_open, patch

    with patch("builtins.open", mock_open(read_data='{"test": "data"}')):
        yield


# ============================================================================
# TEST MARKERS AND UTILITIES
# ============================================================================


def pytest_configure(config):
    """Configure pytest with custom markers"""
    config.addinivalue_line(
        "markers", "api: mark test as API endpoint test"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )
    config.addinivalue_line(
        "markers", "integration: mark test as integration test"
    )
    config.addinivalue_line(
        "markers", "unit: mark test as unit test"
    )
    config.addinivalue_line(
        "markers", "security: mark test as security test"
    )


# ============================================================================
# PARAMETRIZATION FIXTURES
# ============================================================================


@pytest.fixture(
    params=[
        "burgenland",
        "kaernten",
        "niederoesterreich",
        "oberoesterreich",
        "salzburg",
        "steiermark",
        "tirol",
        "vorarlberg",
        "wien",
    ]
)
def all_bundeslaender(request):
    """Parametrized fixture for all 9 Austrian Bundesländer"""
    return request.param


@pytest.fixture(
    params=[
        "RESIDENTIAL",
        "OFFICE",
        "INDUSTRIAL",
        "AGRICULTURAL",
        "MIXED_USE",
    ]
)
def building_types(request):
    """Parametrized fixture for building types"""
    return request.param


@pytest.fixture(
    params=[
        {"input": -10, "expected": False},
        {"input": 0, "expected": True},
        {"input": 50, "expected": True},
        {"input": 100, "expected": True},
        {"input": 200, "expected": False},
    ]
)
def valid_numeric_ranges(request):
    """Parametrized fixture for numeric validation"""
    return request.param
