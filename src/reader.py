import ezdxf
from ezdxf import recover
from ezdxf.math import Vec3
from ezdxf.path import make_path
from ezdxf.render import MeshBuilder
from dataclasses import dataclass, field
from typing import List, Dict, Tuple
import numpy as np

@dataclass
class ReaderOptions:
    spline_distance: float = 0.05
    arc_distance: float = 0.05
    sample_face_interior: bool = False
    face_sample_density: float = 0.1
    expand_blocks: bool = True

@dataclass
class ReadResult:
    points: np.ndarray
    entity_counts: Dict[str, int] = field(default_factory=dict)
    skipped_counts: Dict[str, int] = field(default_factory=dict)
    triangle_polyline_count: int = 0
    bounds: Tuple[np.ndarray, np.ndarray] = field(default_factory=lambda: (np.zeros(3), np.zeros(3)))
    units_warnings: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

def read_dxf(path: str, options: ReaderOptions) -> ReadResult:
    result = ReadResult(points=np.array([]))
    
    try:
        doc, auditor = recover.readfile(path)
    except Exception as e:
        result.warnings.append(f"Failed to read DXF: {e}")
        return result

    modelspace = doc.modelspace()
    points_list: List[Tuple[float, float, float]] = []
    
    def process_entity(entity, depth=0):
        if depth > 8:
            result.warnings.append("Max block recursion depth exceeded.")
            return

        dxftype = entity.dxftype()
        result.entity_counts[dxftype] = result.entity_counts.get(dxftype, 0) + 1

        if dxftype == "POINT":
            loc = entity.dxf.location
            points_list.append((loc.x, loc.y, loc.z))
        elif dxftype == "LINE":
            start = entity.dxf.start
            end = entity.dxf.end
            points_list.append((start.x, start.y, start.z))
            points_list.append((end.x, end.y, end.z))
        elif dxftype == "3DFACE":
            points_list.append(entity.dxf.vtx0)
            points_list.append(entity.dxf.vtx1)
            points_list.append(entity.dxf.vtx2)
            # vtx3 might be the same as vtx2 if it's a triangle
            points_list.append(entity.dxf.vtx3)
            # Handle interior sampling if requested
            if options.sample_face_interior:
                # Basic barycentric sampling could go here, but for now we just take vertices.
                pass
        elif dxftype == "POLYLINE":
            if entity.is_poly_face_mesh:
                # Dispatch virtual 3DFACEs
                for face in entity.virtual_entities():
                    process_entity(face, depth)
            elif entity.is_polygon_mesh:
                # Polymesh
                for i in range(entity.dxf.m_count):
                    for j in range(entity.dxf.n_count):
                        loc = entity.get_mesh_vertex(i, j).dxf.location
                        points_list.append((loc.x, loc.y, loc.z))
            else:
                # 3D polyline or 2D polyline (in OCS)
                # make_path handles OCS to WCS
                try:
                    p = make_path(entity)
                    for v in p.flattening(options.arc_distance):
                        points_list.append((v.x, v.y, v.z))
                except Exception:
                    # fallback
                    for vertex in entity.vertices:
                        loc = vertex.dxf.location
                        points_list.append((loc.x, loc.y, loc.z))
                        
                if entity.is_closed and len(entity.vertices) == 3:
                    result.triangle_polyline_count += 1
                    
        elif dxftype == "LWPOLYLINE":
            try:
                p = make_path(entity)
                # Flattening handles bulged segments and OCS to WCS translation
                for v in p.flattening(options.arc_distance):
                    points_list.append((v.x, v.y, v.z))
            except Exception:
                pass
                
            if entity.closed and len(entity) == 3:
                result.triangle_polyline_count += 1
                
        elif dxftype == "MESH":
            for v in entity.vertices:
                points_list.append((v[0], v[1], v[2]))
        elif dxftype in ("CIRCLE", "ARC", "ELLIPSE", "SPLINE"):
            dist = options.spline_distance if dxftype == "SPLINE" else options.arc_distance
            try:
                p = make_path(entity)
                for v in p.flattening(dist):
                    points_list.append((v.x, v.y, v.z))
            except Exception:
                pass
        elif dxftype == "INSERT":
            if options.expand_blocks:
                for child in entity.virtual_entities():
                    process_entity(child, depth + 1)
        else:
            result.entity_counts[dxftype] -= 1
            if result.entity_counts[dxftype] == 0:
                del result.entity_counts[dxftype]
            result.skipped_counts[dxftype] = result.skipped_counts.get(dxftype, 0) + 1

    for entity in modelspace:
        process_entity(entity)

    if "LWPOLYLINE" in result.entity_counts:
        lw_count = result.entity_counts["LWPOLYLINE"]
        if result.triangle_polyline_count >= 0.9 * lw_count and lw_count > 0:
            result.entity_counts["LWPOLYLINE→TRIANGLE"] = result.triangle_polyline_count
            result.entity_counts["LWPOLYLINE"] -= result.triangle_polyline_count

    if "POLYLINE" in result.entity_counts:
        pl_count = result.entity_counts["POLYLINE"]
        if result.triangle_polyline_count >= 0.9 * pl_count and pl_count > 0:
            result.entity_counts["POLYLINE→TRIANGLE"] = result.triangle_polyline_count
            result.entity_counts["POLYLINE"] -= result.triangle_polyline_count

    if points_list:
        result.points = np.asarray(points_list, dtype=np.float64)
        min_xyz = result.points.min(axis=0)
        max_xyz = result.points.max(axis=0)
        result.bounds = (min_xyz, max_xyz)
        
        span = np.linalg.norm(max_xyz - min_xyz)
        if span > 1000:
            result.units_warnings.append("Bounds span > 1000 — input may be in micrometers; consider scale factor 0.001")
        elif span < 1:
            result.units_warnings.append("Bounds span < 1 — input may be in meters; consider scale factor 1000")
    else:
        result.points = np.zeros((0, 3), dtype=np.float64)
        
    return result
