# -*- coding: utf-8 -*-

"""
This module contains grid presets for the most common sea ice remote sensing grid definitions
"""

from numbers import Real
from typing import List, Tuple
from dataclasses import dataclass, fields, asdict


@dataclass(frozen=True)
class GridPresetEntry:
    epsg: int
    extent_m: Tuple[Real, Real, Real, Real]
    resolution_m: Real
    grid_id: str

    def asdict(self):
        return asdict(self)


@dataclass(frozen=True)
class GridPresets:
    cci_ease2_nh_12p5km: GridPresetEntry = GridPresetEntry(
        6931,
        (-5_400_000, 5_400_000, -5_400_000, 5_400_000),
        12_500,
        "cci_ease2_nh_12p5km"
    )
    cci_ease2_nh_25km: GridPresetEntry = GridPresetEntry(
        6931,
        (-5_400_000, 5_400_000, -5_400_000, 5_400_000),
        25_000,
        "cci_ease2_nh_25km"
    )
    cci_ease2_sh_12p5km: GridPresetEntry = GridPresetEntry(
        6932,
        (-5_400_000, 5_400_000, -5_400_000, 5_400_000),
        12_500,
        "cci_ease2_sh_12p5km"
    )
    cci_ease2_sh_25km: GridPresetEntry = GridPresetEntry(
        6932,
        (-5_400_000, 5_400_000, -5_400_000, 5_400_000),
        25_000,
        "cci_ease2_sh_25km"
    )
    cci_ease2_sh_50km: GridPresetEntry = GridPresetEntry(
        6932,
        (-5_400_000, 5_400_000, -5_400_000, 5_400_000),
        50_000,
        "cci_ease2_sh_50km"
    )

    @classmethod
    def names(cls) -> List[str]:
        return [f.name for f in fields(cls)]
