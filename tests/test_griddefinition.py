import pytest
from easi_grid import GridDefinition
from pydantic import ValidationError

# Test data for happy path scenarios
happy_cases_data = [
    ("valid_epsg_6931", "6931", (0., 100., 0., 100.), 10.),
    ("valid_epsg_3857", "6931", (-5_000_000., 5_000_000., -5_000_000., 5_000_000.), 10_000.),
]


# Test data for error cases (should be catched by input data validation)
error_cases_data = [
    ("zero_extent", "6931", (0, 0, 0, 0), 10),
    ("invalid_epsg", "A", (0, 100, 0, 100), 10),
    ("negative_resolution", "6931", (0, 100, 0, 100), -10),
    ("extent_resolution_mismatch", "6931", (-5_000_000., 5_000_000., -5_000_000., 5_000_000.), 3_333.),
]


@pytest.mark.parametrize("test_id, epsg, extent_m, resolution_m", happy_cases_data)
def test_GridDefData_happy_path(test_id, epsg, extent_m, resolution_m):
    # Arrange

    # Act
    grid_def_data = GridDefinition(epsg=epsg, extent_m=extent_m, resolution_m=resolution_m)

    # Assert
    assert grid_def_data.epsg == epsg
    assert grid_def_data.extent_m == extent_m
    assert grid_def_data.resolution_m == resolution_m
    assert grid_def_data.crs is not None  # Ensures crs property is created successfully
    assert grid_def_data.proj is not None  # Ensures proj property is created successfully


@pytest.mark.parametrize("test_id, epsg, extent_m, resolution_m", error_cases_data)
def test_GridDefData_error_cases(test_id, epsg, extent_m, resolution_m):
    with pytest.raises(ValidationError):
        GridDefinition(epsg=epsg, extent_m=extent_m, resolution_m=resolution_m)
