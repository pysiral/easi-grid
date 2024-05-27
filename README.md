# easi-grid

Equal Area Sea Ice Grids - A small python tool wrapping pyresample and pyproj functionality for commonly used spatial grids for sea ice remote sensing. 

## Scope

The purpose of `easi_grid` is to generate geospatial grids in a reproducible way. 
The implementation is driven by the specific needs of the
[pysiral project](https://github.com/pysiral) and errors might occur 
for more general geospatial grid applications. This 
project is optimized for:

- polar projections with roughly equal area grids 
  (Lambert Azimuthal Equal Area or Polar Stereographic)
- isotropic resolution
- Extent in x and y direction is a multiple of the spatial resolution

## Installation

Integration into the Python Package Index (PyPi) is currenlty not on the agenda. 
The `easi_grid` package should therefore be installed directly from git 

```commandline
pip install git+https://github.com/pysiral/easi_grid
```

or with full developer packages:

```commandline
pip install git+https://github.com/pysiral/easi_grid[dev,tests]
```

## Usage

See the [folder with example notebooks](https://github.com/pysiral/easi_grid/tree/main/examples)
for a tutorial of the functionality. 
