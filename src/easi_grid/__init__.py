# -*- coding: utf-8 -*-

import numpy as np
import xarray as xr
import contextlib
from typing import Tuple, Union, Dict, Optional, Literal
from pydantic import (
    BaseModel, Field, field_validator, model_validator, ConfigDict,
    computed_field, PositiveFloat
)
from pyproj import CRS, Proj
from pyproj.exceptions import CRSError
from functools import cached_property
from numbers import Real
from pyresample import geometry


from easi_grid.presets import GridPresets, GridPresetEntry


__all__ = ["Grid", "GridDefinition", "GridData", "GridPresets"]
__author__ = "Stefan Hendricks"


class GridDefinition(BaseModel):

    model_config = ConfigDict(arbitrary_types_allowed=True)

    epsg: int = Field(description="epsg code")
    extent_m: Tuple[Real, Real, Real, Real] = Field(
        description="[x_min, x_max, y_min, y_max] in projection coordinates (meter)"
    )
    resolution_m: PositiveFloat = Field(
        description="Spatial resolution in meter (isotropic grid resolution)"
    )
    id: Optional[str] = None

    @field_validator("epsg")
    @classmethod
    def valid_epsg_code(cls, value):
        try:
            crs = CRS.from_epsg(value)
        except CRSError:
            crs = None
        assert crs is not None
        return value

    @field_validator("extent_m")
    @classmethod
    def extent_positive(cls, value):
        x_min, x_max, y_min, y_max = value
        assert x_max > x_min
        assert y_max > y_min
        return value

    @model_validator(mode="after")
    @classmethod
    def extent_is_multiple_of_resolution(cls, values):
        x_min, x_max, y_min, y_max = values.extent_m
        assert np.mod((x_max-x_min)/values.resolution_m, 1) < 1e-13
        assert np.mod((y_max-y_min)/values.resolution_m, 1) < 1e-13
        return values

    @cached_property
    def crs(self) -> CRS:
        return CRS.from_epsg(self.epsg)

    @cached_property
    def proj(self) -> Proj:
        return Proj(self.crs)

    @computed_field
    @property
    def num_x(self) -> int:
        return int((self.extent_m[1]-self.extent_m[0])/self.resolution_m)

    @computed_field
    @property
    def num_y(self) -> int:
        return int((self.extent_m[3]-self.extent_m[2])/self.resolution_m)

    @computed_field
    @property
    def name(self) -> str:
        return self.crs.name

    @cached_property
    def repr(self) -> str:
        return f"{self.name} {self.extent_m} @ {self.resolution_m}m ({self.num_x}x{self.num_x}"


class GridData(object):

    def __init__(self, grid_def: GridDefinition):
        self.grid_def = grid_def
        self.lon, self.lat = self._compute_grid_coordinates()

    def get_nan_array(self) -> np.ndarray:
        return np.full((self.grid_def.num_y, self.grid_def.num_x), np.nan)

    def get_lonlat_nc_vars(self, y_reversed: bool = False) -> Dict[str, xr.Variable]:
        lon = np.flipud(self.lon) if y_reversed else self.lon
        lat = np.flipud(self.lat) if y_reversed else self.lat
        return {
            "lon": xr.Variable(
                dims=("xc", "yc"),
                data=lon,
                attrs={
                    "units": "degrees_east",
                    "long_name": "longitude coordinate",
                    "standard_name": "longitude",
                }
            ),
            "lat": xr.Variable(
                dims=("xc", "yc"),
                data=lat,
                attrs={
                    "units": "degrees_north",
                    "long_name": "latitude coordinate",
                    "standard_name": "latitude",
                }
            ),
        }

    def get_nc_coords(
            self,
            unit: Literal["m", "km"] = "km"
    ) -> Dict[str, xr.Variable]:

        if unit == "m":
            xc, yc = self.xc, self.yc
        elif unit == "km":
            xc, yc = self.xc_km, self.yc_km
        else:
            raise ValueError(f"Unknown {unit=}, must be `m` or `km`")

        coord_dict = {
            "xc": xr.Variable(
                dims=("xc",),
                data=xc,
                attrs={
                    "axis": "X",
                    "units": "km",
                    "long_name": "x coordinate in Cartesian system",
                    "standard_name": "projection_x_coordinate",
                }
            ),
            "yc": xr.Variable(
                dims=("yc",),
                data=yc,
                attrs={
                    "axis": "Y",
                    "units": "km",
                    "long_name": "y coordinate in Cartesian system",
                    "standard_name": "projection_y_coordinate",
                }
            )
        }
        return coord_dict

    def _compute_grid_coordinates(self) -> Tuple[np.ndarray, np.ndarray]:
        """
        Returns longitude/latitude points for each grid cell
        Note: mode keyword only for future use. center coordinates are
        returned by default

        :return: Longitude, Latitude arrays
        """
        xx, yy = np.meshgrid(self.xc, self.yc)
        lon, lat = self.grid_def.proj(xx, yy, inverse=True)
        return lon, lat

    @cached_property
    def grid_mapping(self) -> Tuple[str, Dict]:
        grid_mapping_dict = self.grid_def.crs.to_cf()
        with contextlib.suppress(UserWarning):
            grid_mapping_dict["proj4_str"] = self.grid_def.crs.to_proj4()
        grid_mapping_name = str(grid_mapping_dict["grid_mapping_name"])
        grid_mapping_dict.pop("crs_wkt")
        return grid_mapping_name, grid_mapping_dict

    @cached_property
    def xc(self):
        pad = self.grid_def.resolution_m/2.
        return np.linspace(
            self.grid_def.extent_m[0]+pad,
            self.grid_def.extent_m[1]-pad,
            num=self.grid_def.num_x
        )

    @cached_property
    def yc(self):
        pad = self.grid_def.resolution_m/2.
        return np.linspace(
            self.grid_def.extent_m[2]+pad,
            self.grid_def.extent_m[3]-pad,
            num=self.grid_def.num_y
        )

    @cached_property
    def xc_km(self):
        return self.xc/1000.

    @cached_property
    def yc_km(self):
        return self.yc/1000.


class Grid(object):
    """
    """

    def __init__(
            self,
            epsg: str,
            extent_m: Tuple[Real, Real, Real, Real],
            resolution_m: Real,
            grid_id: str = None
    ):
        self._def = GridDefinition(
            epsg=epsg,
            extent_m=extent_m,
            resolution_m=resolution_m,
            id=grid_id
        )
        self._data = GridData(
            self._def
        )

    @classmethod
    def from_preset(cls, preset_name_or_entry: Union[str, GridPresetEntry]) -> "Grid":
        """
        Returns initialized instance based on preset.

        Usage:

            grid = Grid.from_preset("cci_ease2_nh_25km")

            or

            grid = Grid.from_preset(GridPresets.cci_ease2_nh_25km)

        :param preset_name_or_entry: Either the name of the preset (see
            easi_grid.GridPreset.names() or a field of `easi_grid.GridPreset)

        :raises ValueError: Invalid input or grid preset name

        :return: Initialized easi_grid.Grid instance
        """
        if isinstance(preset_name_or_entry, str):
            preset_names = GridPresets.names()
            if preset_name_or_entry not in preset_names:
                raise ValueError(f"preset name {preset_name_or_entry} unknown [{preset_names=}]")
            preset_dict = getattr(GridPresets, preset_name_or_entry).asdict()
        elif isinstance(preset_name_or_entry, GridPresetEntry):
            preset_dict = preset_name_or_entry.asdict()
        else:
            raise ValueError(f"Invalid preset name of preset: {preset_name_or_entry=}")

        return cls(**preset_dict)

    def get_data(self) -> GridData:
        return self._data

    def get_nan_array(self, time_dim=False) -> np.ndarray:
        return self._data.get_nan_array() if not time_dim else [self._data.get_nan_array()]

    def get_pyresample_geometry(self) -> geometry.AreaDefinition:
        grid_def = self.get_definition()
        xmin, xmax, ymin, ymax = grid_def.extent_m
        return geometry.AreaDefinition(
            grid_def.id, grid_def.name, grid_def.crs.to_cf()["grid_mapping_name"],
            grid_def.crs.to_dict(), grid_def.num_x, grid_def.num_y,
            [xmin, ymin, xmax, ymax]
        )

    def get_definition(self) -> GridDefinition:
        return self._def

    def proj(
            self,
            longitude: np.ndarray,
            latitude: np.ndarray,
            **kwargs
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Get projection coordinates from longitude and latitude arrays

        :param longitude: Input longitude values in degrees
        :param latitude: Input latitude values in degrees
        :param kwargs: Keyword arguments accepted in `pyproj.Proj()`

        :return: (x, y) coordinates with the same shape as (longitude, latitude)
        """
        projx, projy = self._def.proj(longitude, latitude, **kwargs)
        return projx, projy

    @property
    def id(self) -> str:
        return str(self._def.id)

    @cached_property
    def array_shape(self) -> Tuple[int, int]:
        return self._def.num_x, self._def.num_y

    def __repr__(self) -> str:
        return f"easi_grid.Grid: {self._def.repr}"

#     def grid_indices(self, longitude, latitude):
#         """
#         Computes the grid indices the given lon/lat pairs would be sorted
#         into (no clipping)
#
#         :param longitude:
#         :param latitude:
#         :return:
#         """
#         projx, projy = self.proj(longitude, latitude)
#         extent = self.extent
#         xi = np.floor((projx + self._data.xsize/2.0)/self._data.resolution_m)
#         yj = np.floor((projy + self._data.ysize/2.0)/self._data.resolution_m)
#         return xi, yj
#

#
#     def set_extent(self, **kwargs):
#         self._extent_dict = kwargs
#
#     def _set_proj(self):
#         self._proj = Proj(**self._proj_dict)
#
#     @property
#     def hemisphere(self):
#         return self._metadata["hemisphere"]
#
#     @property
#     def grid_id(self):
#         return self._metadata["grid_id"]
#
#     @property
#     def grid_tag(self):
#         return self._metadata["grid_tag"]
#
#     @property
#     def grid_name(self):
#         return self._metadata["name"]
#
#     @property
#     def resolution_tag(self):
#         return self._metadata["resolution_tag"]
#
#     @property
#     def proj_dict(self):
#         return dict(self._proj_dict)
#
#     @property
#     def extent(self):
#         return AttrDict(self._extent_dict)
#
#     @property
#     def area_extent(self):
#         xmin, ymin = -1*self.extent.xsize/2.0, -1*self.extent.ysize/2.0
#         xmax, ymax = self.extent.xsize/2.0, self.extent.ysize/2.0
#         return [xmin, ymin, xmax, ymax]
#
#     @property
#     def resolution(self):
#         return self.extent.dx
#
#     @property
#     def pyresample_area_def(self):
#         """ Returns a pyresample.geometry.AreaDefinition instance """
#
#         area_def = None
#
#         if self._proj is not None:
#             # construct area definition
#             area_def = geometry.AreaDefinition(
#                     self.grid_id, self.grid_name, self.grid_id,
#                     self.proj_dict, self.extent.numx, self.extent.numy,
#                     self.area_extent)
#
#         return area_def
#
#     @property
#     def xc(self):
#         x0, numx, xsize, dx = (self.extent.xoff, self.extent.numx,
#                                self.extent.xsize, self.extent.dx)
#         xmin, xmax = x0-(xsize/2.)+dx/2., x0+(xsize/2.)-dx/2.
#         return np.linspace(xmin, xmax, num=numx)
#
#     @property
#     def yc(self):
#         y0, numy, ysize, dy = (self.extent.yoff, self.extent.numy,
#                                self.extent.ysize, self.extent.dy)
#         ymin, ymax = y0-(ysize/2.)+dy/2., y0+(ysize/2.)-dy/2.
#         return np.linspace(ymin, ymax, num=numy)
#
#     @property
#     def xc_km(self):
#         return self.xc/1000.
#
#     @property
#     def yc_km(self):
#         return self.yc/1000.
#
#     @property
#     def netcdf_vardef(self):
#         return self._metadata["netcdf_grid_description"]
#
