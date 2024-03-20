#  Copyright 2023 Canonical Limited
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
from unittest.mock import AsyncMock

import pytest

from cou.apps.core import Keystone
from cou.exceptions import (
    ApplicationError,
    HaltUpgradePlanGeneration,
    MismatchedOpenStackVersions,
)
from cou.steps import (
    ApplicationUpgradePlan,
    PostUpgradeStep,
    PreUpgradeStep,
    UnitUpgradeStep,
    UpgradeStep,
)
from cou.utils import app_utils
from cou.utils.openstack import OpenStackRelease


def test_application_eq(status, config, model, apps_machines):
    """Name of the app is used as comparison between Applications objects."""
    status_keystone_1 = status["keystone_focal_ussuri"]
    config_keystone_1 = config["openstack_ussuri"]
    status_keystone_2 = status["keystone_focal_wallaby"]
    config_keystone_2 = config["openstack_wallaby"]
    keystone_1 = Keystone(
        "keystone",
        status_keystone_1,
        config_keystone_1,
        model,
        "keystone",
        apps_machines["keystone"],
    )
    keystone_2 = Keystone(
        "keystone",
        status_keystone_2,
        config_keystone_2,
        model,
        "keystone",
        apps_machines["keystone"],
    )
    keystone_3 = Keystone(
        "keystone_foo",
        status_keystone_1,
        config_keystone_1,
        model,
        "keystone",
        apps_machines["keystone"],
    )

    # keystone_1 is equal to keystone_2 because they have the same name
    # even if they have different status and config.
    assert keystone_1 == keystone_2
    # keystone_1 is different then keystone_3 even if they have same status and config.
    assert keystone_1 != keystone_3


def assert_application(
    app,
    exp_name,
    exp_series,
    exp_status,
    exp_config,
    exp_model,
    exp_charm,
    exp_is_from_charm_store,
    exp_os_origin,
    exp_units,
    exp_channel,
    exp_current_os_release,
    exp_possible_current_channels,
    exp_target_channel,
    exp_new_origin,
    exp_apt_source_codename,
    exp_channel_codename,
    exp_is_subordinate,
    exp_is_valid_track,
    target,
):
    assert app.name == exp_name
    assert app.series == exp_series
    assert app.status == exp_status
    assert app.config == exp_config
    assert app.model == exp_model
    assert app.charm == exp_charm
    assert app.is_from_charm_store == exp_is_from_charm_store
    assert app.os_origin == exp_os_origin
    assert app.units == exp_units
    assert app.channel == exp_channel
    assert app.current_os_release == exp_current_os_release
    assert app.possible_current_channels == exp_possible_current_channels
    assert app.target_channel(target) == exp_target_channel
    assert app.new_origin(target) == exp_new_origin
    assert app.apt_source_codename == exp_apt_source_codename
    assert app.channel_codename == exp_channel_codename
    assert app.is_subordinate == exp_is_subordinate
    assert app.is_valid_track(app.channel) == exp_is_valid_track


def test_application_ussuri(status, config, units, model, apps_machines):
    target = OpenStackRelease("victoria")
    app_status = status["keystone_focal_ussuri"]
    app_config = config["openstack_ussuri"]
    exp_is_from_charm_store = False
    exp_os_origin = "distro"
    exp_units = units["units_ussuri"]
    exp_channel = app_status.charm_channel
    exp_series = app_status.series
    exp_current_os_release = "ussuri"
    exp_possible_current_channels = ["ussuri/stable"]
    exp_target_channel = f"{target}/stable"
    exp_new_origin = f"cloud:{exp_series}-{target}"
    exp_apt_source_codename = exp_current_os_release
    exp_channel_codename = exp_current_os_release
    exp_is_subordinate = False
    exp_is_valid_track = True

    app = Keystone(
        "my_keystone", app_status, app_config, model, "keystone", apps_machines["keystone"]
    )
    assert app.wait_for_model is True
    assert_application(
        app,
        "my_keystone",
        exp_series,
        app_status,
        app_config,
        model,
        "keystone",
        exp_is_from_charm_store,
        exp_os_origin,
        exp_units,
        exp_channel,
        exp_current_os_release,
        exp_possible_current_channels,
        exp_target_channel,
        exp_new_origin,
        exp_apt_source_codename,
        exp_channel_codename,
        exp_is_subordinate,
        exp_is_valid_track,
        target,
    )


def test_application_different_wl(status, config, model, apps_machines):
    """Different OpenStack Version on units if workload version is different."""
    exp_error_msg = (
        "Units of application my_keystone are running mismatched OpenStack versions: "
        r"'ussuri': \['keystone\/0', 'keystone\/1'\], 'victoria': \['keystone\/2'\]. "
        "This is not currently handled."
    )
    app_status = status["keystone_focal_ussuri"]
    app_status.units["keystone/2"].workload_version = "18.1.0"
    app_config = config["openstack_ussuri"]

    app = Keystone(
        "my_keystone", app_status, app_config, model, "keystone", apps_machines["keystone"]
    )
    with pytest.raises(MismatchedOpenStackVersions, match=exp_error_msg):
        app._check_mismatched_versions()


def test_application_cs(status, config, units, model, apps_machines):
    """Test when application is from charm store."""
    target = OpenStackRelease("victoria")

    app_status = status["keystone_focal_ussuri"]
    app_status.charm = "cs:amd64/focal/keystone-638"

    app_config = config["openstack_ussuri"]
    exp_os_origin = "distro"
    exp_units = units["units_ussuri"]
    exp_channel = app_status.charm_channel
    exp_is_from_charm_store = True
    exp_series = app_status.series
    exp_current_os_release = "ussuri"
    exp_possible_current_channels = ["ussuri/stable"]
    exp_target_channel = f"{target}/stable"
    exp_new_origin = f"cloud:{exp_series}-{target}"
    exp_apt_source_codename = exp_current_os_release
    exp_channel_codename = exp_current_os_release
    exp_is_subordinate = False
    exp_is_valid_track = True

    app = Keystone(
        "my_keystone", app_status, app_config, model, "keystone", apps_machines["keystone"]
    )
    assert_application(
        app,
        "my_keystone",
        exp_series,
        app_status,
        app_config,
        model,
        "keystone",
        exp_is_from_charm_store,
        exp_os_origin,
        exp_units,
        exp_channel,
        exp_current_os_release,
        exp_possible_current_channels,
        exp_target_channel,
        exp_new_origin,
        exp_apt_source_codename,
        exp_channel_codename,
        exp_is_subordinate,
        exp_is_valid_track,
        target,
    )


def test_application_wallaby(status, config, units, model, apps_machines):
    target = OpenStackRelease("xena")
    exp_units = units["units_wallaby"]
    exp_is_from_charm_store = False
    app_config = config["openstack_wallaby"]
    app_status = status["keystone_focal_wallaby"]
    exp_os_origin = "cloud:focal-wallaby"
    exp_channel = app_status.charm_channel
    exp_series = app_status.series
    exp_current_os_release = "wallaby"
    exp_possible_current_channels = ["wallaby/stable"]
    exp_target_channel = f"{target}/stable"
    exp_new_origin = f"cloud:{exp_series}-{target}"
    exp_apt_source_codename = exp_current_os_release
    exp_channel_codename = exp_current_os_release
    exp_is_subordinate = False
    exp_is_valid_track = True

    app = Keystone(
        "my_keystone", app_status, app_config, model, "keystone", apps_machines["keystone"]
    )
    assert_application(
        app,
        "my_keystone",
        exp_series,
        app_status,
        app_config,
        model,
        "keystone",
        exp_is_from_charm_store,
        exp_os_origin,
        exp_units,
        exp_channel,
        exp_current_os_release,
        exp_possible_current_channels,
        exp_target_channel,
        exp_new_origin,
        exp_apt_source_codename,
        exp_channel_codename,
        exp_is_subordinate,
        exp_is_valid_track,
        target,
    )


def test_application_no_origin_config(status, model, apps_machines):
    app = Keystone(
        "my_keystone",
        status["keystone_focal_ussuri"],
        {},
        model,
        "keystone",
        apps_machines["keystone"],
    )
    assert app.os_origin == ""
    assert app.apt_source_codename is None


def test_application_empty_origin_config(status, model, apps_machines):
    app = Keystone(
        "my_keystone",
        status["keystone_focal_ussuri"],
        {"source": {"value": ""}},
        model,
        "keystone",
        apps_machines["keystone"],
    )
    assert app.apt_source_codename is None


def test_application_unexpected_channel(status, config, model, apps_machines):
    target = OpenStackRelease("xena")
    app_status = status["keystone_focal_wallaby"]
    # channel is set to a previous OpenStack release
    app_status.charm_channel = "ussuri/stable"
    app = Keystone(
        "my_keystone",
        app_status,
        config["openstack_wallaby"],
        model,
        "keystone",
        apps_machines["keystone"],
    )
    with pytest.raises(ApplicationError):
        app.generate_upgrade_plan(target)


@pytest.mark.parametrize(
    "source_value",
    ["ppa:myteam/ppa", "cloud:xenial-proposed/ocata", "http://my.archive.com/ubuntu main"],
)
def test_application_unknown_source(status, model, source_value, apps_machines):
    app = Keystone(
        "my_keystone",
        status["keystone_focal_ussuri"],
        {"source": {"value": source_value}},
        model,
        "keystone",
        apps_machines["keystone"],
    )
    with pytest.raises(ApplicationError):
        app.apt_source_codename


@pytest.mark.asyncio
async def test_application_check_upgrade(status, config, model, apps_machines):
    target = OpenStackRelease("victoria")
    app_status = status["keystone_focal_ussuri"]
    app_config = config["openstack_ussuri"]

    # workload version changed from ussuri to victoria
    mock_status = AsyncMock()
    mock_status.return_value.applications = {"my_keystone": status["keystone_focal_victoria"]}
    model.get_status = mock_status
    app = Keystone(
        "my_keystone",
        app_status,
        app_config,
        model,
        "keystone",
        machines=apps_machines["keystone"],
    )
    await app._check_upgrade(target)


@pytest.mark.asyncio
async def test_application_check_upgrade_fail(status, config, model, apps_machines):
    exp_error_msg = "Cannot upgrade units 'keystone/0, keystone/1, keystone/2' to victoria."
    target = OpenStackRelease("victoria")
    app_status = status["keystone_focal_ussuri"]
    app_config = config["openstack_ussuri"]

    # workload version didn't change from ussuri to victoria
    mock_status = AsyncMock()
    mock_status.return_value.applications = {"my_keystone": app_status}
    model.get_status = mock_status
    app = Keystone(
        "my_keystone",
        app_status,
        app_config,
        model,
        "keystone",
        machines=apps_machines["keystone"],
    )
    with pytest.raises(ApplicationError, match=exp_error_msg):
        await app._check_upgrade(target)


def test_upgrade_plan_ussuri_to_victoria(status, config, model, apps_machines):
    target = OpenStackRelease("victoria")
    app_status = status["keystone_focal_ussuri"]
    app_config = config["openstack_ussuri"]
    app = Keystone(
        "my_keystone",
        app_status,
        app_config,
        model,
        "keystone",
        machines=apps_machines["keystone"],
    )
    upgrade_plan = app.generate_upgrade_plan(target)
    expected_plan = ApplicationUpgradePlan(
        description=f"Upgrade plan for '{app.name}' to {target}"
    )
    upgrade_packages = PreUpgradeStep(
        description=f"Upgrade software packages of '{app.name}' from the current APT repositories",
        parallel=True,
    )
    for unit in app.units:
        upgrade_packages.add_step(
            UnitUpgradeStep(
                description=f"Upgrade software packages on unit {unit.name}",
                coro=app_utils.upgrade_packages(unit.name, model, None),
            )
        )

    upgrade_steps = [
        upgrade_packages,
        PreUpgradeStep(
            description=f"Refresh '{app.name}' to the latest revision of 'ussuri/stable'",
            parallel=False,
            coro=model.upgrade_charm(app.name, "ussuri/stable", switch=None),
        ),
        UpgradeStep(
            description=f"Change charm config of '{app.name}' 'action-managed-upgrade' to False.",
            parallel=False,
            coro=model.set_application_config(app.name, {"action-managed-upgrade": False}),
        ),
        UpgradeStep(
            description=f"Upgrade '{app.name}' to the new channel: 'victoria/stable'",
            parallel=False,
            coro=model.upgrade_charm(app.name, "victoria/stable"),
        ),
        UpgradeStep(
            description=(
                f"Change charm config of '{app.name}' "
                f"'{app.origin_setting}' to 'cloud:focal-victoria'"
            ),
            parallel=False,
            coro=model.set_application_config(
                app.name, {f"{app.origin_setting}": "cloud:focal-victoria"}
            ),
        ),
        PostUpgradeStep(
            description=f"Wait 1800s for model {model.name} to reach the idle state.",
            parallel=False,
            coro=model.wait_for_active_idle(1800, apps=None),
        ),
        PostUpgradeStep(
            description=f"Check if the workload of '{app.name}' has been upgraded",
            parallel=False,
            coro=app._check_upgrade(target),
        ),
    ]
    expected_plan.add_steps(upgrade_steps)

    assert upgrade_plan == expected_plan


def test_upgrade_plan_ussuri_to_victoria_ch_migration(status, config, model, apps_machines):
    target = OpenStackRelease("victoria")

    app_status = status["keystone_focal_ussuri"]
    app_status.charm = "cs:amd64/focal/keystone-638"

    app_config = config["openstack_ussuri"]
    app = Keystone(
        "my_keystone", app_status, app_config, model, "keystone", apps_machines["keystone"]
    )
    upgrade_plan = app.generate_upgrade_plan(target)
    expected_plan = ApplicationUpgradePlan(
        description=f"Upgrade plan for '{app.name}' to {target}"
    )
    upgrade_packages = PreUpgradeStep(
        description=f"Upgrade software packages of '{app.name}' from the current APT repositories",
        parallel=True,
    )
    for unit in app.units:
        upgrade_packages.add_step(
            UnitUpgradeStep(
                description=f"Upgrade software packages on unit {unit.name}",
                coro=app_utils.upgrade_packages(unit.name, model, None),
            )
        )

    upgrade_steps = [
        upgrade_packages,
        PreUpgradeStep(
            description=f"Migration of '{app.name}' from charmstore to charmhub",
            parallel=False,
            coro=model.upgrade_charm(app.name, "ussuri/stable", switch="ch:keystone"),
        ),
        UpgradeStep(
            description=f"Change charm config of '{app.name}' 'action-managed-upgrade' to False.",
            parallel=False,
            coro=model.set_application_config(app.name, {"action-managed-upgrade": False}),
        ),
        UpgradeStep(
            description=f"Upgrade '{app.name}' to the new channel: 'victoria/stable'",
            parallel=False,
            coro=model.upgrade_charm(app.name, "victoria/stable"),
        ),
        UpgradeStep(
            description=(
                f"Change charm config of '{app.name}' "
                f"'{app.origin_setting}' to 'cloud:focal-victoria'"
            ),
            parallel=False,
            coro=model.set_application_config(
                app.name, {f"{app.origin_setting}": "cloud:focal-victoria"}
            ),
        ),
        PostUpgradeStep(
            description=f"Wait 1800s for model {model.name} to reach the idle state.",
            parallel=False,
            coro=model.wait_for_active_idle(1800, apps=None),
        ),
        PostUpgradeStep(
            description=f"Check if the workload of '{app.name}' has been upgraded",
            parallel=False,
            coro=app._check_upgrade(target),
        ),
    ]
    expected_plan.add_steps(upgrade_steps)

    assert upgrade_plan == expected_plan


def test_upgrade_plan_channel_on_next_os_release(status, config, model, apps_machines):
    target = OpenStackRelease("victoria")
    app_status = status["keystone_focal_ussuri"]
    app_config = config["openstack_ussuri"]
    # channel it's already on next OpenStack release
    app_status.charm_channel = "victoria/stable"
    app = Keystone(
        "my_keystone", app_status, app_config, model, "keystone", apps_machines["keystone"]
    )
    upgrade_plan = app.generate_upgrade_plan(target)

    expected_plan = ApplicationUpgradePlan(
        description=f"Upgrade plan for '{app.name}' to {target}"
    )
    # no sub-step for refresh current channel or next channel
    upgrade_packages = PreUpgradeStep(
        description=f"Upgrade software packages of '{app.name}' from the current APT repositories",
        parallel=True,
    )
    for unit in app.units:
        upgrade_packages.add_step(
            UnitUpgradeStep(
                description=f"Upgrade software packages on unit {unit.name}",
                coro=app_utils.upgrade_packages(unit.name, model, None),
            )
        )

    upgrade_steps = [
        upgrade_packages,
        UpgradeStep(
            description=f"Change charm config of '{app.name}' 'action-managed-upgrade' to False.",
            parallel=False,
            coro=model.set_application_config(app.name, {"action-managed-upgrade": False}),
        ),
        UpgradeStep(
            description=(
                f"Change charm config of '{app.name}' "
                f"'{app.origin_setting}' to 'cloud:focal-victoria'"
            ),
            parallel=False,
            coro=model.set_application_config(
                app.name, {f"{app.origin_setting}": "cloud:focal-victoria"}
            ),
        ),
        PostUpgradeStep(
            description=f"Wait 1800s for model {model.name} to reach the idle state.",
            parallel=False,
            coro=model.wait_for_active_idle(1800, apps=None),
        ),
        PostUpgradeStep(
            description=f"Check if the workload of '{app.name}' has been upgraded",
            parallel=False,
            coro=app._check_upgrade(target),
        ),
    ]
    expected_plan.add_steps(upgrade_steps)

    assert upgrade_plan == expected_plan


def test_upgrade_plan_origin_already_on_next_openstack_release(
    status, config, model, apps_machines
):
    target = OpenStackRelease("victoria")
    app_status = status["keystone_focal_ussuri"]
    app_config = config["openstack_ussuri"]
    # openstack-origin already configured for next OpenStack release
    app_config["openstack-origin"]["value"] = "cloud:focal-victoria"
    app = Keystone(
        "my_keystone", app_status, app_config, model, "keystone", apps_machines["keystone"]
    )
    upgrade_plan = app.generate_upgrade_plan(target)
    expected_plan = ApplicationUpgradePlan(
        description=f"Upgrade plan for '{app.name}' to {target}"
    )
    upgrade_packages = PreUpgradeStep(
        description=f"Upgrade software packages of '{app.name}' from the current APT repositories",
        parallel=True,
    )
    for unit in app.units:
        upgrade_packages.add_step(
            UnitUpgradeStep(
                description=f"Upgrade software packages on unit {unit.name}",
                coro=app_utils.upgrade_packages(unit.name, model, None),
            )
        )

    upgrade_steps = [
        upgrade_packages,
        PreUpgradeStep(
            description=f"Refresh '{app.name}' to the latest revision of 'ussuri/stable'",
            parallel=False,
            coro=model.upgrade_charm(app.name, "ussuri/stable", switch=None),
        ),
        UpgradeStep(
            description=f"Change charm config of '{app.name}' 'action-managed-upgrade' to False.",
            parallel=False,
            coro=model.set_application_config(app.name, {"action-managed-upgrade": False}),
        ),
        UpgradeStep(
            description=f"Upgrade '{app.name}' to the new channel: 'victoria/stable'",
            parallel=False,
            coro=model.upgrade_charm(app.name, "victoria/stable"),
        ),
        PostUpgradeStep(
            description=f"Wait 1800s for model {model.name} to reach the idle state.",
            parallel=False,
            coro=model.wait_for_active_idle(1800, apps=None),
        ),
        PostUpgradeStep(
            description=f"Check if the workload of '{app.name}' has been upgraded",
            parallel=False,
            coro=app._check_upgrade(target),
        ),
    ]
    expected_plan.add_steps(upgrade_steps)

    assert upgrade_plan == expected_plan


def test_upgrade_plan_application_already_upgraded(status, config, model, apps_machines):
    exp_error_msg = (
        "Application 'my_keystone' already configured for release equal to or greater "
        "than victoria. Ignoring."
    )
    target = OpenStackRelease("victoria")
    app_status = status["keystone_focal_wallaby"]
    app_status.can_upgrade_to = []
    app_config = config["openstack_wallaby"]
    app = Keystone(
        "my_keystone", app_status, app_config, model, "keystone", apps_machines["keystone"]
    )
    # victoria is lesser than wallaby, so application should not generate a plan.
    with pytest.raises(HaltUpgradePlanGeneration, match=exp_error_msg):
        app.generate_upgrade_plan(target)


def test_upgrade_plan_application_already_disable_action_managed(
    status, config, model, apps_machines
):
    target = OpenStackRelease("victoria")
    app_status = status["keystone_focal_ussuri"]
    app_config = config["openstack_ussuri"]
    app_config["action-managed-upgrade"]["value"] = False
    app = Keystone(
        "my_keystone", app_status, app_config, model, "keystone", apps_machines["keystone"]
    )
    upgrade_plan = app.generate_upgrade_plan(target)
    expected_plan = ApplicationUpgradePlan(
        description=f"Upgrade plan for '{app.name}' to {target}"
    )
    upgrade_packages = PreUpgradeStep(
        description=f"Upgrade software packages of '{app.name}' from the current APT repositories",
        parallel=True,
    )
    for unit in app.units:
        upgrade_packages.add_step(
            UnitUpgradeStep(
                description=f"Upgrade software packages on unit {unit.name}",
                coro=app_utils.upgrade_packages(unit.name, model, None),
            )
        )

    upgrade_steps = [
        upgrade_packages,
        PreUpgradeStep(
            description=f"Refresh '{app.name}' to the latest revision of 'ussuri/stable'",
            parallel=False,
            coro=model.upgrade_charm(app.name, "ussuri/stable", switch=None),
        ),
        UpgradeStep(
            description=f"Upgrade '{app.name}' to the new channel: 'victoria/stable'",
            parallel=False,
            coro=model.upgrade_charm(app.name, "victoria/stable"),
        ),
        UpgradeStep(
            description=(
                f"Change charm config of '{app.name}' "
                f"'{app.origin_setting}' to 'cloud:focal-victoria'"
            ),
            parallel=False,
            coro=model.set_application_config(
                app.name, {f"{app.origin_setting}": "cloud:focal-victoria"}
            ),
        ),
        PostUpgradeStep(
            description=f"Wait 1800s for model {model.name} to reach the idle state.",
            parallel=False,
            coro=model.wait_for_active_idle(1800, apps=None),
        ),
        PostUpgradeStep(
            description=f"Check if the workload of '{app.name}' has been upgraded",
            parallel=False,
            coro=app._check_upgrade(target),
        ),
    ]
    expected_plan.add_steps(upgrade_steps)

    assert upgrade_plan == expected_plan
