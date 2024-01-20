"""Alarm Control Panel for TC20E integration."""
from __future__ import annotations

from homeassistant.components.alarm_control_panel import (
    AlarmControlPanelEntity,
    AlarmControlPanelEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    STATE_ALARM_ARMED_AWAY,
    STATE_ALARM_ARMED_HOME,
    STATE_ALARM_DISARMED,
    STATE_ALARM_PENDING,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import TC20EUpdateCoordinator

ALARM_STATE_TO_HA_STATE = {
    101: STATE_ALARM_ARMED_AWAY,
    102: STATE_ALARM_ARMED_HOME,
    100: STATE_ALARM_DISARMED,
    0: STATE_ALARM_PENDING,
}


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up alarm panel from config entry."""

    coordinator: TC20EUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([TC20EAlarmPanel(coordinator)], False)


class TC20EAlarmPanel(
    CoordinatorEntity[TC20EUpdateCoordinator], AlarmControlPanelEntity
):
    """TC20E, Domonial Alarm Panel."""

    _attr_has_entity_name = True
    _attr_name = None

    def __init__(
        self,
        coordinator: TC20EUpdateCoordinator,
    ) -> None:
        """Initialize the Domonial Alarm panel."""
        super().__init__(coordinator)
        self._displayname = "Domonial"
        self._attr_supported_features = (
            AlarmControlPanelEntityFeature.ARM_HOME
            | AlarmControlPanelEntityFeature.ARM_AWAY
        )
        self._attr_code_arm_required = False
        self._attr_code_format = None
        self._attr_unique_id = "domonial_alarm_panel_1"
        self._attr_state = ALARM_STATE_TO_HA_STATE[self.coordinator.alarmstatus]
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, "domonial_alarm_panel_1")},
            name="Domonial Alarm Panel",
            model="Domonial",
            manufacturer="Honeywell",
        )

    @property
    def extra_state_attributes(self) -> dict:
        """Additional states for alarm panel."""
        return {
            "display_name": self._displayname,
        }

    async def async_alarm_disarm(self) -> None:
        """Disarm alarm."""
        command = "disarm"
        await self.coordinator.setalarm(command)
        self.async_write_ha_state()

    async def async_alarm_arm_away(self) -> None:
        """Arm alarm away."""
        command = "full"
        await self.coordinator.setalarm(command)
        self.async_write_ha_state()

    async def async_alarm_arm_home(self) -> None:
        """Arm alarm away."""
        command = "partial"
        await self.coordinator.setalarm(command)
        self.async_write_ha_state()

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        if alarm_state := self.coordinator.alarmstatus:
            self._attr_state = ALARM_STATE_TO_HA_STATE[alarm_state]
        super()._handle_coordinator_update()

    @property
    def available(self) -> bool:
        """Return entity available."""
        return True
