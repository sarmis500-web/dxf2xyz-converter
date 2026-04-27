import numpy as np
from dataclasses import dataclass
from typing import Optional, Tuple

@dataclass
class WriterOptions:
    format: str = "xyz" # "xyz" or "pts"
    delimiter: str = " "
    precision: int = 4
    header: str = "none" # "none", "count", "comment", "custom"
    header_text: str = ""
    intensity: Optional[float] = None
    intensity_from_z: bool = False
    rgb: Optional[Tuple[int, int, int]] = None
    line_ending: str = "\n"

def write_pointcloud(path: str, points: np.ndarray, options: WriterOptions) -> None:
    if points.size == 0:
        with open(path, "w", encoding="ascii", newline="") as f:
            pass
        return

    # Prepare data matrix
    cols = [points]
    
    # Optional columns
    if options.intensity_from_z:
        z = points[:, 2]
        z_min = z.min()
        z_max = z.max()
        z_range = z_max - z_min
        if z_range > 0:
            intensity = (z - z_min) / z_range
        else:
            intensity = np.zeros_like(z)
        cols.append(intensity[:, None])
    elif options.intensity is not None:
        intensity = np.full((len(points), 1), options.intensity, dtype=np.float64)
        cols.append(intensity)
        
    if options.rgb is not None:
        r, g, b = options.rgb
        rgb_arr = np.full((len(points), 3), [r, g, b], dtype=np.float64) # Using float to share fmt
        cols.append(rgb_arr)
        
    data = np.hstack(cols)

    # Format strings
    coord_fmt = f"%.{options.precision}f"
    fmt_list = [coord_fmt] * 3
    
    if options.intensity_from_z or options.intensity is not None:
        # Intensity uses same precision as coords or a fixed one, let's use same for simplicity
        fmt_list.append(coord_fmt)
        
    if options.rgb is not None:
        fmt_list.extend(["%d"] * 3)
        
    fmt = options.delimiter.join(fmt_list)

    # Determine header
    header_lines = []
    
    if options.format == "pts":
        # PTS format always starts with the count
        header_lines.append(str(len(points)))
    
    if options.header == "count" and options.format != "pts":
        header_lines.append(str(len(points)))
    elif options.header == "comment":
        h = "// X Y Z"
        if options.intensity is not None or options.intensity_from_z:
            h += " I"
        if options.rgb is not None:
            h += " R G B"
        header_lines.append(h)
    elif options.header == "custom" and options.header_text:
        header_lines.append(options.header_text)

    # Write file
    with open(path, "w", encoding="ascii", newline="") as f:
        for hl in header_lines:
            f.write(hl + options.line_ending)
            
        # savetxt respects locale.LC_NUMERIC pinned in main.py
        np.savetxt(f, data, fmt=fmt, delimiter="", newline=options.line_ending)
