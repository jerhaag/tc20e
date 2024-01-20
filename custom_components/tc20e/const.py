"""Constants for the Total Connect 2.0E integration."""

from __future__ import annotations

import logging

from homeassistant.const import Platform

DOMAIN = "tc20e"

LOGGER = logging.getLogger(__package__)

MIN_SCAN_INTERVAL = 180
UPDATE_INTERVAL = "timesync"

TC20E_URL = "https://tc20e.total-connect.eu"

PLATFORMS = [Platform.ALARM_CONTROL_PANEL]
