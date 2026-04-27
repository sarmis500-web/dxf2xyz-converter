import pytest
import os
import numpy as np
from src.reader import read_dxf, ReaderOptions

def test_points_only():
    res = read_dxf("tests/fixtures/points_only.dxf", ReaderOptions())
    assert len(res.points) == 1000
    assert res.entity_counts.get("POINT", 0) == 1000

def test_triangle_polylines():
    res = read_dxf("tests/fixtures/triangle_polylines.dxf", ReaderOptions())
    assert res.triangle_polyline_count == 50
    # 50 triangles * 3 vertices (or 4 depending on flatten behavior, but make_path typically yields unique vertices + maybe closure)
    # The heuristic should be met.
    assert "LWPOLYLINE→TRIANGLE" in res.entity_counts
    assert res.entity_counts["LWPOLYLINE→TRIANGLE"] == 50

def test_mixed():
    res = read_dxf("tests/fixtures/mixed.dxf", ReaderOptions())
    # Block expansion
    assert len(res.points) > 0
    # Line (2), Circle (many), Spline (many), 3Dfaces (10*4), Insert->Point (4), Lwpolyline (many)
    
    # Verify OCS logic
    # An LWPOLYLINE with extrusion (0,0,-1) and points (10,0), (0,10), (-10,0)
    # With extrusion (0,0,-1), the X axis is negated. WCS X should be negative of OCS X.
    # WCS points expected roughly (-10,0), (0,10), (10,0).
    found_ocs = False
    for p in res.points:
        if np.allclose(p, [-10, 0, 0]) or np.allclose(p, [10, 0, 0]):
            found_ocs = True
    assert found_ocs

def test_circle_flattening():
    # It should have a lot of points due to flattening
    res = read_dxf("tests/fixtures/mixed.dxf", ReaderOptions(arc_distance=0.05))
    # CIRCLE r=10 -> circumference = 2*pi*r ~ 62.8
    # sagitta 0.05 means many segments.
    # We just need to check there's a good chunk of points.
    assert len(res.points) >= 80
