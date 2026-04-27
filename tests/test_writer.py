import pytest
import os
import locale
import numpy as np
from src.writer import write_pointcloud, WriterOptions

def test_write_comment_header(tmp_path):
    pts = np.random.rand(100, 3)
    out_path = tmp_path / "out.xyz"
    
    opts = WriterOptions(
        format="xyz",
        delimiter="\t",
        precision=6,
        header="comment"
    )
    
    write_pointcloud(str(out_path), pts, opts)
    
    with open(out_path, "r") as f:
        lines = f.readlines()
        
    assert len(lines) == 101
    assert lines[0] == "// X Y Z\n"
    # Data line check
    parts = lines[1].strip().split("\t")
    assert len(parts) == 3
    for p in parts:
        assert "." in p
        assert len(p.split(".")[1]) == 6

def test_write_pts_format(tmp_path):
    pts = np.random.rand(100, 3)
    out_path = tmp_path / "out.pts"
    
    opts = WriterOptions(
        format="pts",
        delimiter=" ",
        precision=4
    )
    
    write_pointcloud(str(out_path), pts, opts)
    
    with open(out_path, "r") as f:
        lines = f.readlines()
        
    assert lines[0] == "100\n"
    assert len(lines) == 101

def test_locale_independence(tmp_path):
    pts = np.array([[1.234, 2.345, 3.456]])
    out_path = tmp_path / "locale.xyz"
    
    try:
        # Simulate French locale if available on OS, else it might fail to set
        locale.setlocale(locale.LC_ALL, "fr_FR.UTF-8")
    except locale.Error:
        pass # If OS doesn't have it, skip strict failure, but we still test the pin
        
    # The pin that main.py does
    locale.setlocale(locale.LC_NUMERIC, "C")
    
    opts = WriterOptions(delimiter=" ", precision=3)
    write_pointcloud(str(out_path), pts, opts)
    
    with open(out_path, "r") as f:
        line = f.read().strip()
        
    assert line == "1.234 2.345 3.456"
    assert "," not in line
