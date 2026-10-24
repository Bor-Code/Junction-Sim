from junction_sim.engine.idm import (
    DRIVER_PROFILES,
    DriverProfile,
    IDMParameters,
    compute_idm_acceleration,
    get_driver_profile,
    step_idm,
)


def test_driver_profiles_and_params() -> None:
    custom = IDMParameters()
    assert custom.v0 == 13.8
    assert custom.time_headway == 1.4
    assert len(DRIVER_PROFILES) == 3
    for prof in DriverProfile:
        params = DRIVER_PROFILES[prof]
        assert params.v0 > 0.0
        assert params.time_headway > 0.0
        assert params.min_gap >= 0.0
        assert params.max_accel > 0.0
        assert params.desired_decel > 0.0
        assert params.accel_exponent > 0.0
        assert params.max_decel > 0.0


def test_get_driver_profile_mappings() -> None:
    found_profiles = set()
    for i in range(200):
        vid = f"veh_{i}"
        prof, params = get_driver_profile(vid)
        found_profiles.add(prof)
        assert params == DRIVER_PROFILES[prof]
    assert found_profiles == {
        DriverProfile.CAUTIOUS,
        DriverProfile.NORMAL,
        DriverProfile.AGGRESSIVE,
    }


def test_compute_idm_acceleration_free_road() -> None:
    params = DRIVER_PROFILES[DriverProfile.NORMAL]
    acc_standstill = compute_idm_acceleration(0.0, None, 999.0, params)
    assert abs(acc_standstill - params.max_accel) < 1e-4

    acc_at_v0 = compute_idm_acceleration(params.v0, None, 999.0, params)
    assert abs(acc_at_v0) < 1e-4

    acc_overspeed = compute_idm_acceleration(params.v0 * 1.5, None, 999.0, params)
    assert acc_overspeed < 0.0

    acc_negative_v = compute_idm_acceleration(-5.0, None, 999.0, params)
    assert abs(acc_negative_v - params.max_accel) < 1e-4


def test_compute_idm_acceleration_with_lead_vehicle() -> None:
    params = DRIVER_PROFILES[DriverProfile.NORMAL]

    acc_standstill_close = compute_idm_acceleration(0.0, 0.0, 0.5, params)
    assert acc_standstill_close < 0.0

    acc_crash = compute_idm_acceleration(10.0, 5.0, 0.0, params)
    assert acc_crash == -params.max_decel

    acc_crash_neg = compute_idm_acceleration(10.0, 5.0, -2.0, params)
    assert acc_crash_neg == -params.max_decel

    acc_following = compute_idm_acceleration(12.0, 12.0, 30.0, params)
    assert -params.max_decel <= acc_following <= params.max_accel

    acc_closing_in = compute_idm_acceleration(15.0, 5.0, 10.0, params)
    assert acc_closing_in < 0.0


def test_step_idm_integration() -> None:
    params = DRIVER_PROFILES[DriverProfile.NORMAL]

    s1, v1, a1 = step_idm(0.0, 0.0, None, None, 0.2, params)
    assert s1 > 0.0
    assert v1 > 0.0
    assert a1 > 0.0

    s2, v2, a2 = step_idm(10.0, 5.0, 12.0, 0.0, 0.2, params)
    assert a2 < 0.0
    assert v2 < 5.0
    assert s2 > 10.0

    _, v3, _ = step_idm(10.0, 0.1, 10.5, 0.0, 1.0, params)
    assert v3 >= 0.0
