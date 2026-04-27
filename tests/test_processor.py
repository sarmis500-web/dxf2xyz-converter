import pytest
import numpy as np
from src.reader import read_dxf, ReaderOptions
from src.processor import process, ProcessOptions, voxel_thin

def test_dedupe_mesh_cube():
    res = read_dxf("tests/fixtures/mesh_cube.dxf", ReaderOptions())
    # A cube mesh has 24 vertices (6 faces * 4 verts) before dedupe
    pres = process(res.points, ProcessOptions(dedupe=True, dedupe_epsilon=1e-6))
    assert pres.count_out == 8

def test_dedupe_polyface_sphere():
    res = read_dxf("tests/fixtures/polyface_sphere.dxf", ReaderOptions())
    pres = process(res.points, ProcessOptions(dedupe=True, dedupe_epsilon=1e-6))
    
    # Check that output count is roughly the unique vertices of the sphere
    # ezdxf forms.sphere count=16 stacks=8 -> 16*7 + 2 = 114 vertices
    assert pres.count_out > 0
    assert pres.count_out < len(res.points)
    # The dedupe should collapse shared vertices exactly
    unique_verts = len(np.unique(res.points.round(5), axis=0))
    assert pres.count_out == unique_verts

def test_voxel_thinning():
    # Generate 100k random points in a 1x1x1 cube
    np.random.seed(42)
    pts = np.random.rand(100000, 3)
    
    # Leaf size 0.1 -> 10x10x10 = 1000 voxels
    thin_first = voxel_thin(pts, 0.1, "first")
    thin_centroid = voxel_thin(pts, 0.1, "centroid")
    
    assert len(thin_first) <= 1000
    assert len(thin_centroid) <= 1000
    
    # Verify roughly 1000
    assert len(thin_first) > 900
    
    # Check centroid lies inside voxel bounds
    keys_centroid = np.floor(thin_centroid / 0.1)
    keys_first = np.floor(thin_first / 0.1)
    
    # Since these are the representative points, their voxel keys should be unique
    assert len(np.unique(keys_first, axis=0)) == len(thin_first)
    assert len(np.unique(keys_centroid, axis=0)) == len(thin_centroid)
