import numpy as np
from dataclasses import dataclass
from typing import Optional, Tuple

@dataclass
class ProcessOptions:
    dedupe: bool = True
    dedupe_epsilon: float = 1e-6
    voxel_size: Optional[float] = None
    voxel_mode: str = "first"
    scale: float = 1.0
    center_on_origin: bool = False
    swap_yz: bool = False
    flip_x: bool = False
    flip_y: bool = False
    flip_z: bool = False

@dataclass
class ProcessResult:
    points: np.ndarray
    bounds: Tuple[np.ndarray, np.ndarray]
    count_in: int
    count_after_dedupe: int
    count_out: int

def _hash_keys(keys: np.ndarray) -> np.ndarray:
    # Spatial hash for fast np.unique on (i,j,k) integer triples.
    # Constants are arbitrary large primes (Teschner et al. 2003).
    k = keys.astype(np.int64)
    return k[:, 0] * 73856093 + k[:, 1] * 19349663 + k[:, 2] * 83492791

def voxel_thin(pts: np.ndarray, leaf: float, mode: str) -> np.ndarray:
    if pts.size == 0:
        return pts
    keys = np.floor(pts / leaf).astype(np.int64)
    packed = _hash_keys(keys)
    if mode == "first":
        _, idx = np.unique(packed, return_index=True)
        return pts[idx]
    # centroid mode: group by packed, mean each group
    order = np.argsort(packed, kind="stable")
    sorted_packed = packed[order]
    sorted_pts = pts[order]
    boundaries = np.concatenate(([True], sorted_packed[1:] != sorted_packed[:-1]))
    group_ids = np.cumsum(boundaries) - 1
    counts = np.bincount(group_ids)
    sums = np.zeros((counts.size, 3), dtype=np.float64)
    np.add.at(sums, group_ids, sorted_pts)
    return sums / counts[:, None]

def process(points: np.ndarray, options: ProcessOptions) -> ProcessResult:
    count_in = len(points)
    if count_in == 0:
        return ProcessResult(
            points=points,
            bounds=(np.zeros(3), np.zeros(3)),
            count_in=0,
            count_after_dedupe=0,
            count_out=0
        )

    # 1. Dedupe
    if options.dedupe:
        points = voxel_thin(points, options.dedupe_epsilon, mode="first")
    count_after_dedupe = len(points)

    # 2. Voxel Thinning
    if options.voxel_size is not None and options.voxel_size > 0:
        points = voxel_thin(points, options.voxel_size, mode=options.voxel_mode)
    
    # 3. Scale
    if options.scale != 1.0:
        points = points * options.scale

    # 4. Center
    if options.center_on_origin and len(points) > 0:
        centroid = np.mean(points, axis=0)
        points = points - centroid

    # 5. Flips & Swaps
    if options.swap_yz:
        # Swap Y and Z columns
        points[:, [1, 2]] = points[:, [2, 1]]
    
    if options.flip_x:
        points[:, 0] = -points[:, 0]
    if options.flip_y:
        points[:, 1] = -points[:, 1]
    if options.flip_z:
        points[:, 2] = -points[:, 2]

    # Compute bounds
    count_out = len(points)
    if count_out > 0:
        min_xyz = points.min(axis=0)
        max_xyz = points.max(axis=0)
        bounds = (min_xyz, max_xyz)
    else:
        bounds = (np.zeros(3), np.zeros(3))

    return ProcessResult(
        points=points,
        bounds=bounds,
        count_in=count_in,
        count_after_dedupe=count_after_dedupe,
        count_out=count_out
    )
