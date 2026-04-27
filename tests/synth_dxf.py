import ezdxf
from ezdxf.render import forms
import os
import random

def generate_fixtures():
    os.makedirs("tests/fixtures", exist_ok=True)
    
    # 1. points_only.dxf
    doc = ezdxf.new("R2010")
    msp = doc.modelspace()
    for _ in range(1000):
        msp.add_point((random.uniform(0, 10), random.uniform(0, 10), random.uniform(0, 10)))
    doc.saveas("tests/fixtures/points_only.dxf")
    
    # 2. mesh_cube.dxf
    doc = ezdxf.new("R2010")
    msp = doc.modelspace()
    cube = forms.cube()
    mesh = msp.add_mesh()
    with mesh.edit_data() as mesh_data:
        mesh_data.vertices = cube.vertices
        mesh_data.faces = cube.faces
    doc.saveas("tests/fixtures/mesh_cube.dxf")
    
    # 3. polyface_sphere.dxf
    doc = ezdxf.new("R2010")
    msp = doc.modelspace()
    sphere = forms.sphere(count=16, stacks=8, radius=10.0)
    sphere.render_polyface(msp)
    doc.saveas("tests/fixtures/polyface_sphere.dxf")
    
    # 4. triangle_polylines.dxf
    doc = ezdxf.new("R2010")
    msp = doc.modelspace()
    for i in range(50):
        msp.add_lwpolyline([(i, 0), (i+1, 0), (i, 1)], close=True)
    doc.saveas("tests/fixtures/triangle_polylines.dxf")
    
    # 5. mixed.dxf
    doc = ezdxf.new("R2010")
    msp = doc.modelspace()
    msp.add_line((0, 0, 0), (10, 10, 10))
    msp.add_circle((0, 0, 0), radius=10)
    msp.add_spline(fit_points=[(0, 0, 0), (1, 2, 0), (2, -1, 0), (3, 2, 0), (4, 0, 0)])
    
    for _ in range(10):
        msp.add_3dface([(0, 0, 0), (1, 0, 0), (0, 1, 0), (0, 1, 0)]) # vtx3=vtx2 means triangle
        
    block = doc.blocks.new(name="TestBlock")
    for _ in range(4):
        block.add_point((1, 1, 1))
    msp.add_blockref("TestBlock", insert=(5, 5, 5))
    
    # Non-Z extrusion
    pl = msp.add_lwpolyline([(10, 0), (0, 10), (-10, 0)], close=True)
    pl.dxf.extrusion = (0, 0, -1)
    
    doc.saveas("tests/fixtures/mixed.dxf")

if __name__ == "__main__":
    generate_fixtures()
