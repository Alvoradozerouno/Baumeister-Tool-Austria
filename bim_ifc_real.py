"""
BIM/IFC Real Implementation - Production Ready
==============================================

Real IFC file processing using ifcopenshell library.
Replaces all mocked IFC functions with production implementations.

Author: ORION Engineering Team
Date: 2026-04-10
Status: PRODUCTION
"""

import json
import logging
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Production IFC library
try:
    import ifcopenshell
    import ifcopenshell.geom
    import ifcopenshell.util.element
    import ifcopenshell.util.unit

    IFC_AVAILABLE = True
except ImportError:
    IFC_AVAILABLE = False
    logging.warning("ifcopenshell not installed. Install with: pip install ifcopenshell")


class IFCElementType(Enum):
    """IFC element types"""

    WALL = "IfcWall"
    SLAB = "IfcSlab"
    BEAM = "IfcBeam"
    COLUMN = "IfcColumn"
    WINDOW = "IfcWindow"
    DOOR = "IfcDoor"
    ROOF = "IfcRoof"
    STAIR = "IfcStair"
    RAILING = "IfcRailing"
    SPACE = "IfcSpace"
    BUILDING = "IfcBuilding"
    STOREY = "IfcBuildingStorey"


@dataclass
class IFCGeometry:
    """IFC geometry representation"""

    element_id: str
    element_type: str
    vertices: List[Tuple[float, float, float]]
    faces: List[List[int]]
    volume: float
    surface_area: float
    bounding_box: Dict[str, Tuple[float, float, float]]


@dataclass
class IFCElement:
    """IFC building element"""

    global_id: str
    element_type: str
    name: Optional[str]
    description: Optional[str]
    properties: Dict[str, Any]
    geometry: Optional[IFCGeometry]
    material: Optional[str]
    quantities: Dict[str, float]
    storey: Optional[str]


@dataclass
class IFCProject:
    """Complete IFC project data"""

    project_name: str
    project_id: str
    site_name: Optional[str]
    building_name: Optional[str]
    storeys: List[str]
    elements: List[IFCElement]
    total_volume: float
    total_area: float
    ifc_version: str


class IFCProcessor:
    """Production IFC file processor"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        if not IFC_AVAILABLE:
            raise RuntimeError("ifcopenshell not available. Install with: pip install ifcopenshell")

    def load_ifc_file(self, file_path: str):
        """Load IFC file"""
        self.logger.info(f"Loading IFC file: {file_path}")

        if not Path(file_path).exists():
            raise FileNotFoundError(f"IFC file not found: {file_path}")

        try:
            ifc_file = ifcopenshell.open(file_path)
            self.logger.info(f"IFC file loaded successfully. Schema: {ifc_file.schema}")
            return ifc_file
        except Exception as e:
            self.logger.error(f"Failed to load IFC file: {e}")
            raise

    def extract_project_info(self, ifc_file: Any) -> Dict[str, Any]:
        """Extract project metadata"""
        project = ifc_file.by_type("IfcProject")[0]

        project_info = {
            "project_name": project.Name or "Unnamed Project",
            "project_id": project.GlobalId,
            "description": project.Description or "",
            "ifc_version": ifc_file.schema,
        }

        # Get site
        sites = ifc_file.by_type("IfcSite")
        if sites:
            project_info["site_name"] = sites[0].Name
            project_info["site_location"] = {
                "latitude": (
                    getattr(sites[0].RefLatitude, "wrappedValue", None)
                    if hasattr(sites[0], "RefLatitude")
                    else None
                ),
                "longitude": (
                    getattr(sites[0].RefLongitude, "wrappedValue", None)
                    if hasattr(sites[0], "RefLongitude")
                    else None
                ),
            }

        # Get building
        buildings = ifc_file.by_type("IfcBuilding")
        if buildings:
            project_info["building_name"] = buildings[0].Name

        return project_info

    def extract_storeys(self, ifc_file: Any) -> List[Dict[str, Any]]:
        """Extract building storeys"""
        storeys = []

        for storey in ifc_file.by_type("IfcBuildingStorey"):
            storey_data = {
                "global_id": storey.GlobalId,
                "name": storey.Name or f"Storey-{len(storeys)+1}",
                "elevation": storey.Elevation if hasattr(storey, "Elevation") else 0.0,
                "description": storey.Description or "",
            }
            storeys.append(storey_data)

        # Sort by elevation
        storeys.sort(key=lambda x: x["elevation"])

        return storeys

    def extract_geometry(self, ifc_file: Any, element: Any) -> Optional[IFCGeometry]:
        """Extract element geometry"""
        try:
            settings = ifcopenshell.geom.settings()
            settings.set(settings.USE_WORLD_COORDS, True)

            shape = ifcopenshell.geom.create_shape(settings, element)

            # Get vertices
            verts = shape.geometry.verts
            vertices = [(verts[i], verts[i + 1], verts[i + 2]) for i in range(0, len(verts), 3)]

            # Get faces
            faces_raw = shape.geometry.faces
            faces = [list(faces_raw[i : i + 3]) for i in range(0, len(faces_raw), 3)]

            # Calculate volume and area
            volume = 0.0
            surface_area = 0.0

            # Get bounding box
            bbox = {
                "min": (
                    min(v[0] for v in vertices),
                    min(v[1] for v in vertices),
                    min(v[2] for v in vertices),
                ),
                "max": (
                    max(v[0] for v in vertices),
                    max(v[1] for v in vertices),
                    max(v[2] for v in vertices),
                ),
            }

            # Calculate volume from bounding box (approximation)
            dx = bbox["max"][0] - bbox["min"][0]
            dy = bbox["max"][1] - bbox["min"][1]
            dz = bbox["max"][2] - bbox["min"][2]
            volume = dx * dy * dz

            # Calculate surface area (approximation)
            surface_area = 2 * (dx * dy + dy * dz + dz * dx)

            return IFCGeometry(
                element_id=element.GlobalId,
                element_type=element.is_a(),
                vertices=vertices,
                faces=faces,
                volume=volume,
                surface_area=surface_area,
                bounding_box=bbox,
            )

        except Exception as e:
            self.logger.warning(f"Could not extract geometry for {element.GlobalId}: {e}")
            return None

    def extract_properties(self, ifc_file: Any, element: Any) -> Dict[str, Any]:
        """Extract element properties"""
        properties = {}

        try:
            # Get property sets
            psets = ifcopenshell.util.element.get_psets(element)

            for pset_name, pset_data in psets.items():
                for prop_name, prop_value in pset_data.items():
                    if prop_name != "id":  # Skip IFC internal id
                        properties[f"{pset_name}.{prop_name}"] = prop_value

        except Exception as e:
            self.logger.warning(f"Could not extract properties for {element.GlobalId}: {e}")

        return properties

    def extract_quantities(self, ifc_file: Any, element: Any) -> Dict[str, float]:
        """Extract element quantities"""
        quantities = {}

        try:
            # Get quantity sets
            for rel in element.IsDefinedBy:
                if rel.is_a("IfcRelDefinesByProperties"):
                    prop_def = rel.RelatingPropertyDefinition
                    if prop_def.is_a("IfcElementQuantity"):
                        for quantity in prop_def.Quantities:
                            qty_type = quantity.is_a()
                            qty_name = quantity.Name

                            if qty_type == "IfcQuantityLength":
                                quantities[qty_name] = quantity.LengthValue
                            elif qty_type == "IfcQuantityArea":
                                quantities[qty_name] = quantity.AreaValue
                            elif qty_type == "IfcQuantityVolume":
                                quantities[qty_name] = quantity.VolumeValue
                            elif qty_type == "IfcQuantityCount":
                                quantities[qty_name] = quantity.CountValue
                            elif qty_type == "IfcQuantityWeight":
                                quantities[qty_name] = quantity.WeightValue

        except Exception as e:
            self.logger.warning(f"Could not extract quantities for {element.GlobalId}: {e}")

        return quantities

    def extract_material(self, ifc_file: Any, element: Any) -> Optional[str]:
        """Extract element material"""
        try:
            material_associations = [
                rel for rel in element.HasAssociations if rel.is_a("IfcRelAssociatesMaterial")
            ]

            if material_associations:
                material = material_associations[0].RelatingMaterial
                if material.is_a("IfcMaterial"):
                    return material.Name
                elif material.is_a("IfcMaterialLayerSetUsage"):
                    layers = material.ForLayerSet.MaterialLayers
                    return ", ".join([layer.Material.Name for layer in layers])

        except Exception as e:
            self.logger.warning(f"Could not extract material for {element.GlobalId}: {e}")

        return None

    def get_element_storey(self, element: Any) -> Optional[str]:
        """Get element's building storey"""
        try:
            for rel in element.ContainedInStructure:
                if rel.RelatingStructure.is_a("IfcBuildingStorey"):
                    return rel.RelatingStructure.Name
        except AttributeError as e:
            # Element doesn't have ContainedInStructure relationship
            self.logger.debug(f"Element storey retrieval failed: {e}")
        except Exception as e:
            self.logger.warning(f"Unexpected error getting element storey: {type(e).__name__}: {e}")

        return None

    def process_ifc_file(self, file_path: str, extract_geometry: bool = True) -> IFCProject:
        """Process complete IFC file"""
        self.logger.info(f"Processing IFC file: {file_path}")

        # Load file
        ifc_file = self.load_ifc_file(file_path)

        # Extract project info
        project_info = self.extract_project_info(ifc_file)

        # Extract storeys
        storeys = self.extract_storeys(ifc_file)
        storey_names = [s["name"] for s in storeys]

        # Extract elements
        elements = []
        total_volume = 0.0
        total_area = 0.0

        element_types = [
            "IfcWall",
            "IfcSlab",
            "IfcBeam",
            "IfcColumn",
            "IfcWindow",
            "IfcDoor",
            "IfcRoof",
            "IfcStair",
        ]

        for element_type in element_types:
            self.logger.info(f"Extracting {element_type} elements...")

            for element in ifc_file.by_type(element_type):
                # Extract geometry (optional, can be slow)
                geometry = None
                if extract_geometry:
                    geometry = self.extract_geometry(ifc_file, element)
                    if geometry:
                        total_volume += geometry.volume
                        total_area += geometry.surface_area

                # Extract properties
                properties = self.extract_properties(ifc_file, element)

                # Extract quantities
                quantities = self.extract_quantities(ifc_file, element)

                # Extract material
                material = self.extract_material(ifc_file, element)

                # Get storey
                storey = self.get_element_storey(element)

                ifc_element = IFCElement(
                    global_id=element.GlobalId,
                    element_type=element.is_a(),
                    name=element.Name,
                    description=element.Description,
                    properties=properties,
                    geometry=geometry,
                    material=material,
                    quantities=quantities,
                    storey=storey,
                )

                elements.append(ifc_element)

        self.logger.info(f"Extracted {len(elements)} elements")

        return IFCProject(
            project_name=project_info["project_name"],
            project_id=project_info["project_id"],
            site_name=project_info.get("site_name"),
            building_name=project_info.get("building_name"),
            storeys=storey_names,
            elements=elements,
            total_volume=total_volume,
            total_area=total_area,
            ifc_version=project_info["ifc_version"],
        )

    def export_to_json(self, ifc_project: IFCProject, output_path: str):
        """Export IFC project to JSON"""
        self.logger.info(f"Exporting to JSON: {output_path}")

        data = {
            "project_name": ifc_project.project_name,
            "project_id": ifc_project.project_id,
            "site_name": ifc_project.site_name,
            "building_name": ifc_project.building_name,
            "storeys": ifc_project.storeys,
            "ifc_version": ifc_project.ifc_version,
            "total_volume": ifc_project.total_volume,
            "total_area": ifc_project.total_area,
            "element_count": len(ifc_project.elements),
            "elements": [],
        }

        for element in ifc_project.elements:
            elem_data = {
                "global_id": element.global_id,
                "type": element.element_type,
                "name": element.name,
                "description": element.description,
                "material": element.material,
                "storey": element.storey,
                "properties": element.properties,
                "quantities": element.quantities,
            }

            if element.geometry:
                elem_data["geometry"] = {
                    "volume": element.geometry.volume,
                    "surface_area": element.geometry.surface_area,
                    "bounding_box": element.geometry.bounding_box,
                    "vertex_count": len(element.geometry.vertices),
                    "face_count": len(element.geometry.faces),
                }

            data["elements"].append(elem_data)

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        self.logger.info(f"JSON export complete: {output_path}")

    def get_element_statistics(self, ifc_project: IFCProject) -> Dict[str, Any]:
        """Get element statistics"""
        stats = {
            "total_elements": len(ifc_project.elements),
            "by_type": {},
            "by_storey": {},
            "by_material": {},
            "total_volume": ifc_project.total_volume,
            "total_area": ifc_project.total_area,
        }

        for element in ifc_project.elements:
            # By type
            elem_type = element.element_type
            stats["by_type"][elem_type] = stats["by_type"].get(elem_type, 0) + 1

            # By storey
            if element.storey:
                stats["by_storey"][element.storey] = stats["by_storey"].get(element.storey, 0) + 1

            # By material
            if element.material:
                stats["by_material"][element.material] = (
                    stats["by_material"].get(element.material, 0) + 1
                )

        return stats


# Convenience functions for integration


def load_and_process_ifc(file_path: str, extract_geometry: bool = True) -> IFCProject:
    """Load and process IFC file - production function"""
    processor = IFCProcessor()
    return processor.process_ifc_file(file_path, extract_geometry=extract_geometry)


def ifc_to_orion_format(ifc_project: IFCProject) -> Dict[str, Any]:
    """Convert IFC project to ORION format for structural analysis"""

    # Extract structural elements
    beams = [e for e in ifc_project.elements if e.element_type == "IfcBeam"]
    columns = [e for e in ifc_project.elements if e.element_type == "IfcColumn"]
    slabs = [e for e in ifc_project.elements if e.element_type == "IfcSlab"]
    walls = [e for e in ifc_project.elements if e.element_type == "IfcWall"]

    orion_data = {
        "project": {
            "name": ifc_project.project_name,
            "id": ifc_project.project_id,
            "building": ifc_project.building_name,
            "storeys": ifc_project.storeys,
        },
        "structural_elements": {
            "beams": [
                {
                    "id": e.global_id,
                    "name": e.name,
                    "material": e.material,
                    "volume": e.geometry.volume if e.geometry else 0.0,
                    "length": e.quantities.get("Length", 0.0),
                }
                for e in beams
            ],
            "columns": [
                {
                    "id": e.global_id,
                    "name": e.name,
                    "material": e.material,
                    "volume": e.geometry.volume if e.geometry else 0.0,
                    "height": e.quantities.get("Height", 0.0),
                }
                for e in columns
            ],
            "slabs": [
                {
                    "id": e.global_id,
                    "name": e.name,
                    "material": e.material,
                    "area": e.geometry.surface_area if e.geometry else 0.0,
                    "thickness": e.quantities.get("Depth", 0.0),
                }
                for e in slabs
            ],
            "walls": [
                {
                    "id": e.global_id,
                    "name": e.name,
                    "material": e.material,
                    "area": e.geometry.surface_area if e.geometry else 0.0,
                    "thickness": e.quantities.get("Width", 0.0),
                }
                for e in walls
            ],
        },
        "totals": {
            "volume": ifc_project.total_volume,
            "area": ifc_project.total_area,
            "element_count": len(ifc_project.elements),
        },
    }

    return orion_data


if __name__ == "__main__":
    # Example usage
    logging.basicConfig(level=logging.INFO)

    if IFC_AVAILABLE:
        print("✅ IFC Processing Available (ifcopenshell installed)")
        print("Ready for production IFC file processing")
    else:
        print("❌ IFC Processing NOT Available")
        print("Install with: pip install ifcopenshell")


# ---------------------------------------------------------------------------
# Pure-Python STEP/IFC Fallback Parser
# Used when ifcopenshell is not installed.
# Parses the ASCII STEP format (ISO 10303-21) that all IFC files use.
# ---------------------------------------------------------------------------

import re


class StepIFCParser:
    """
    Minimal STEP (ISO 10303-21) parser for IFC files.
    Extracts entities without geometry — just metadata and element counts.
    Works without ifcopenshell.
    """

    # IFC entity types we care about
    _ELEMENT_TYPES = {
        "IFCWALL", "IFCWALLSTANDARDCASE", "IFCSLAB", "IFCBEAM", "IFCCOLUMN",
        "IFCWINDOW", "IFCDOOR", "IFCROOF", "IFCSTAIR", "IFCRAILING",
        "IFCSPACE", "IFCBUILDING", "IFCBUILDINGSTOREY", "IFCPROJECT", "IFCSITE",
        "IFCMATERIAL", "IFCMATERIALLAYER",
    }

    def parse(self, file_path: str) -> "StepIFCResult":
        """Parse an IFC file and return structured metadata."""
        result = StepIFCResult()

        try:
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
        except OSError as e:
            raise ValueError(f"Cannot read IFC file: {e}")

        # Detect IFC schema version from FILE_SCHEMA
        schema_match = re.search(r"FILE_SCHEMA\s*\(\s*\(\s*'([^']+)'", content)
        result.ifc_schema = schema_match.group(1) if schema_match else "IFC4"

        # Detect project name from IFCPROJECT — 3rd attribute (Name), handles $=null args
        proj_match = re.search(
            r"IFCPROJECT\('[^']*'\s*,\s*(?:'[^']*'|\$)\s*,\s*'([^']*)'",
            content,
        )
        result.project_name = proj_match.group(1) if proj_match else "Unnamed Project"

        # Count entity types
        for etype in self._ELEMENT_TYPES:
            count = len(re.findall(rf"\b{etype}\s*\(", content, re.IGNORECASE))
            if count:
                result.entity_counts[etype] = count

        # Extract storeys — 3rd attribute is Name, 2nd can be $ (null)
        storey_pattern = re.compile(
            r"IFCBUILDINGSTOREY\('[^']*'\s*,\s*(?:'[^']*'|\$)\s*,\s*'([^']*)'",
            re.IGNORECASE,
        )
        for m in storey_pattern.finditer(content):
            name = m.group(1).strip()
            if name and name not in result.storey_names:
                result.storey_names.append(name)

        # Extract materials — 2nd attribute is Name, 1st can be $ (null)
        mat_pattern = re.compile(
            r"IFCMATERIAL\s*\(\s*(?:'[^']*'|\$)\s*,\s*'([^']*)'",
            re.IGNORECASE,
        )
        for m in mat_pattern.finditer(content):
            mat = m.group(1).strip()
            if mat and mat not in result.materials:
                result.materials.append(mat)

        # Extract quantities from IfcQuantityArea (GrossFloorArea etc.)
        qty_pattern = re.compile(
            r"IFCQUANTITYAREA\('[^']*','([^']*)'[^,]*,[^,]*,([0-9.]+)", re.IGNORECASE
        )
        total_area = 0.0
        for m in qty_pattern.finditer(content):
            try:
                val = float(m.group(2))
                total_area += val
            except ValueError:
                pass
        result.total_area_m2 = total_area

        # Approximate volume from IfcQuantityVolume
        vol_pattern = re.compile(
            r"IFCQUANTITYVOLUME\('[^']*','[^']*'[^,]*,[^,]*,([0-9.]+)", re.IGNORECASE
        )
        total_vol = 0.0
        for m in vol_pattern.finditer(content):
            try:
                total_vol += float(m.group(1))
            except ValueError:
                pass
        result.total_volume_m3 = total_vol

        # Count file lines for size estimation
        result.file_lines = content.count("\n")

        return result


class StepIFCResult:
    """Result of StepIFCParser."""

    def __init__(self):
        self.ifc_schema: str = "IFC4"
        self.project_name: str = "Unknown"
        self.entity_counts: Dict[str, int] = {}
        self.storey_names: List[str] = []
        self.materials: List[str] = []
        self.total_area_m2: float = 0.0
        self.total_volume_m3: float = 0.0
        self.file_lines: int = 0

    def element_counts_display(self) -> Dict[str, int]:
        """Return display-friendly element counts (mapped to IFC type names)."""
        mapping = {
            "IFCWALL": "IfcWall", "IFCWALLSTANDARDCASE": "IfcWall",
            "IFCSLAB": "IfcSlab", "IFCBEAM": "IfcBeam",
            "IFCCOLUMN": "IfcColumn", "IFCWINDOW": "IfcWindow",
            "IFCDOOR": "IfcDoor", "IFCROOF": "IfcRoof",
            "IFCSTAIR": "IfcStair", "IFCSPACE": "IfcSpace",
        }
        result: Dict[str, int] = {}
        for raw, display in mapping.items():
            if raw in self.entity_counts:
                result[display] = result.get(display, 0) + self.entity_counts[raw]
        return result


def parse_ifc_fallback(file_path: str) -> StepIFCResult:
    """
    Parse IFC file without ifcopenshell.
    Returns metadata, element counts, materials, storey names.
    """
    return StepIFCParser().parse(file_path)

