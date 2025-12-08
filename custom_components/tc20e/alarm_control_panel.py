"""Alarm Control Panel for TC20E integration."""
from __future__ import annotations

from typing import Any

from homeassistant.components.alarm_control_panel import (
    AlarmControlPanelEntity,
    AlarmControlPanelEntityFeature,
    AlarmControlPanelState,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import TC20EUpdateCoordinator


# Mapping from TC20E numeric status codes to Home Assistant alarm states.
ALARM_STATE_MAP: dict[int, AlarmControlPanelState] = {
    # 101 = total arm (full arm)
    101: AlarmControlPanelState.ARMED_AWAY,
    # 102 = partial arm (home arm)
    102: AlarmControlPanelState.ARMED_HOME,
    # 100 = disarmed
    100: AlarmControlPanelState.DISARMED,
    # 0 = pending / unknown / in progress
    0: AlarmControlPanelState.PENDING,
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up alarm panel from a config entry."""
    coordinator: TC20EUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([TC20EAlarmPanel(coordinator)], False)


class TC20EAlarmPanel(
    CoordinatorEntity[TC20EUpdateCoordinator],
    AlarmControlPanelEntity,
):
    """TC20E Domonial alarm panel."""

    # Let HA use the device name instead of the entity name.
    _attr_has_entity_name = True
    _attr_name = None

    # Features supported by this alarm panel.
    _attr_supported_features = (
        AlarmControlPanelEntityFeature.ARM_HOME
        | AlarmControlPanelEntityFeature.ARM_AWAY
    )

    # No code is required to arm/disarm from HA.
    _attr_code_arm_required = False
    _attr_code_format = None

    # Static unique ID for this alarm panel instance.
    _attr_unique_id = "domonial_alarm_panel_1"

    def __init__(self, coordinator: TC20EUpdateCoordinator) -> None:
        """Initialize the Domonial alarm panel."""
        super().__init__(coordinator)

        self._displayname = "Domonial"

        # Device information exposed in the device registry.
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, "domonial_alarm_panel_1")},
            name="Domonial Alarm Panel",
            model="Domonial",
            manufacturer="Honeywell",
        )

    #
    # Core alarm state handling
    #

    @property
    def alarm_state(self) -> AlarmControlPanelState | None:
        """Return the current alarm state using the AlarmControlPanelState enum."""
        return ALARM_STATE_MAP.get(self.coordinator.alarmstatus)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional state attributes for the alarm panel."""
        return {
            "display_name": self._displayname,
        }

    #
    # Commands
    #

    async def async_alarm_disarm(self, code: str | None = None) -> None:
        """Disarm the alarm."""
        command = "disarm"
        await self.coordinator.setalarm(command)
        # Coordinator has updated alarmstatus; just push state to HA.
        self.async_write_ha_state()

    async def async_alarm_arm_away(self, code: str | None = None) -> None:
        """Arm the alarm in away mode."""
        command = "full"
        await self.coordinator.setalarm(command)
        self.async_write_ha_state()

    async def async_alarm_arm_home(self, code: str | None = None) -> None:
        """Arm the alarm in home / partial mode."""
        command = "partial"
        await self.coordinator.setalarm(command)
        self.async_write_ha_state()

    #
    # Coordinator callbacks
    #

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        # The coordinator updated self.coordinator.alarmstatus; just notify HA.
        self.async_write_ha_state()
        super()._handle_coordinator_update()

    @property
    def available(self) -> bool:
        """Return True if entity is available.

        Currently always True as long as the integration is loaded.
        """
        return True
