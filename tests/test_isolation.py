import pytest
import os
import re

def test_no_tkinter_in_core():
    # Grep check to ensure tkinter is not imported in reader, processor, or writer
    core_files = ["src/reader.py", "src/processor.py", "src/writer.py"]
    
    for fpath in core_files:
        if os.path.exists(fpath):
            with open(fpath, "r", encoding="utf-8") as f:
                content = f.read()
            assert not re.search(r'\\bimport\\s+tkinter\\b', content), f"tkinter imported in {fpath}"
            assert not re.search(r'\\bfrom\\s+tkinter\\b', content), f"tkinter imported in {fpath}"

def test_no_cross_imports_in_core():
    # reader, processor, writer should not import each other
    core_modules = ["reader", "processor", "writer"]
    
    for mod in core_modules:
        fpath = f"src/{mod}.py"
        if os.path.exists(fpath):
            with open(fpath, "r", encoding="utf-8") as f:
                content = f.read()
            for other in core_modules:
                if mod != other:
                    assert not re.search(fr'\\bimport\\s+{other}\\b', content), f"{other} imported in {mod}.py"
                    assert not re.search(fr'\\bfrom\\s+{other}\\b', content), f"{other} imported in {mod}.py"
