"""Analytic visibility and radiometry checks for disk quadrature."""
from __future__ import annotations

import math

import pytest

from selene_prime.errors import ConfigurationError
from selene_prime.radiometry import SolarDiskConfig, integrate_solar_disk


CFG = SolarDiskConfig(1361.0, 1.0, 0.0, "uniform synthetic benchmark", "synthetic bolometric", 256)
ALPHA = 0.01


def test_full_visibility_and_zero_visibility_limits() -> None:
    full = integrate_solar_disk(solar_angular_radius_rad=ALPHA, solar_azimuth_rad=0.4,
                                solar_elevation_rad=0.3, config=CFG)
    assert full.visible_fraction == 1.0
    assert full.earth_occluded_fraction == 0.0
    assert full.terrain_occluded_fraction == 0.0
    assert full.direct_normal_w_m2 == pytest.approx(1361.0)
    assert full.direct_horizontal_w_m2 == pytest.approx(1361.0 * math.sin(0.3) * (1 - ALPHA**2 / 4), abs=0.002)
    blocked = integrate_solar_disk(
        solar_angular_radius_rad=ALPHA, solar_azimuth_rad=0.4, solar_elevation_rad=0.3,
        config=CFG, earth_angular_radius_rad=2 * ALPHA,
        earth_azimuth_rad=0.4, earth_elevation_rad=0.3,
    )
    assert blocked.visible_fraction == 0.0
    assert blocked.earth_occluded_fraction == 1.0
    assert blocked.direct_normal_w_m2 == 0.0


def test_earth_overlap_matches_analytic_circle_area() -> None:
    earth_radius = 0.6 * ALPHA
    separation = 0.8 * ALPHA
    result = integrate_solar_disk(
        solar_angular_radius_rad=ALPHA, solar_azimuth_rad=0.0, solar_elevation_rad=0.4,
        config=CFG, earth_angular_radius_rad=earth_radius,
        earth_azimuth_rad=separation / math.cos(0.4), earth_elevation_rad=0.4,
    )
    d = math.hypot(separation, 0.0)
    r, s = ALPHA, earth_radius
    expected = (r*r*math.acos((d*d+r*r-s*s)/(2*d*r))
                + s*s*math.acos((d*d+s*s-r*r)/(2*d*s))
                - 0.5*math.sqrt((-d+r+s)*(d+r-s)*(d-r+s)*(d+r+s))) / (math.pi*r*r)
    assert result.earth_occluded_fraction == pytest.approx(expected, abs=0.003)
    assert result.combined_occluded_fraction == result.earth_occluded_fraction


def test_terrain_and_earth_masks_combine_pointwise() -> None:
    result = integrate_solar_disk(
        solar_angular_radius_rad=ALPHA, solar_azimuth_rad=0.0, solar_elevation_rad=0.0,
        config=CFG, horizon_elevation=lambda az: 0.0,
        earth_angular_radius_rad=0.7*ALPHA, earth_azimuth_rad=0.0,
        earth_elevation_rad=0.3*ALPHA,
    )
    assert 0.45 < result.terrain_occluded_fraction < 0.55
    assert result.earth_occluded_fraction > 0.0
    assert result.combined_occluded_fraction <= (
        result.earth_occluded_fraction + result.terrain_occluded_fraction
    )
    assert result.visible_fraction + result.combined_occluded_fraction == pytest.approx(1.0)


def test_input_validation_and_horizon_errors_fail_closed() -> None:
    with pytest.raises(ConfigurationError, match="source and passband"):
        SolarDiskConfig(1361, 1, 0, "", "", 32)
    with pytest.raises(ConfigurationError, match="provided together"):
        integrate_solar_disk(solar_angular_radius_rad=ALPHA, solar_azimuth_rad=0,
                             solar_elevation_rad=0.2, config=CFG, earth_azimuth_rad=0.0)
    with pytest.raises(ConfigurationError, match="horizon callback"):
        integrate_solar_disk(solar_angular_radius_rad=ALPHA, solar_azimuth_rad=0,
                             solar_elevation_rad=0.2, config=CFG,
                             horizon_elevation=lambda az: float("nan"))


def test_area_visibility_is_separate_from_limb_weighted_flux_visibility() -> None:
    darkened = SolarDiskConfig(1361.0, 1.0, 0.8, "synthetic linear law", "synthetic", 256)
    kwargs = dict(solar_angular_radius_rad=ALPHA, solar_azimuth_rad=0.0,
                  solar_elevation_rad=0.4, earth_angular_radius_rad=0.6*ALPHA,
                  earth_azimuth_rad=0.8*ALPHA / math.cos(0.4), earth_elevation_rad=0.4)
    uniform = integrate_solar_disk(config=CFG, **kwargs)
    limb_darkened = integrate_solar_disk(config=darkened, **kwargs)
    assert uniform.visible_fraction == pytest.approx(limb_darkened.visible_fraction, abs=1e-14)
    assert uniform.earth_occluded_fraction == pytest.approx(limb_darkened.earth_occluded_fraction, abs=1e-14)
    assert limb_darkened.irradiance_visible_fraction != pytest.approx(
        uniform.irradiance_visible_fraction, abs=1e-5
    )
