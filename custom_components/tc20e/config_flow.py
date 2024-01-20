"""Config flow for Total Connect 2.0E integration."""
from __future__ import annotations

import base64
import re
from typing import Any

from bs4 import BeautifulSoup
import voluptuous as vol

from homeassistant import config_entries, core, exceptions
from homeassistant.const import CONF_AUTHENTICATION, CONF_PASSWORD, CONF_USERNAME
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import DOMAIN, LOGGER, TC20E_URL


async def validate_input(hass: core.HomeAssistant, auth_id: str) -> None:
    """Validate the user input allows us to connect."""

    async def logout():
        await websession.get(
            f"{TC20E_URL}/logout",
            headers={
                "Connection": "keep-alive",
            },
        )

    websession = async_get_clientsession(hass)

    await websession.get(TC20E_URL)

    response = await websession.get(
        f"{TC20E_URL}/validate",
        headers={
            "Authorization": auth_id,
        },
    )

    response_text = await response.text()

    if response_text != "#1home":
        LOGGER.error("Auth failure %s, status %s", response_text, response.status)
        raise AuthenticationError

    response = await websession.get(
        f"{TC20E_URL}/go/home",
        headers={
            "Connection": "keep-alive",
        },
    )
    response_text = await response.text()
    soup = BeautifulSoup(response_text, "html.parser")

    try:
        session_id = re.search(r"homeSessionId='(.*?)'", soup.prettify()).group(1)
    except AttributeError:
        LOGGER.error("Failed to retrieve Session ID: %d", response.status)
        await logout()
        raise CannotConnect

    if response.status not in (200, 204) or session_id is None:
        LOGGER.error("Failed to login to retrieve Session ID: %d", response.status)
        await logout()
        raise CannotConnect

    await logout()


class TC20EConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for TC20E integration."""

    VERSION = 1

    entry: config_entries.ConfigEntry | None

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            username = user_input[CONF_USERNAME]
            password = user_input[CONF_PASSWORD]

            auth_id = f"{username}:{password}:1:0"
            auth_id = base64.b64encode(auth_id.encode("utf-8"))
            auth_id = f"Basic {auth_id.decode('utf-8')}"

            try:
                await validate_input(self.hass, auth_id)
            except CannotConnect:
                errors = {"base": "connection_error"}
            except AuthenticationError:
                errors = {"base": "auth_error"}
            else:
                await self.async_set_unique_id(username)
                self._abort_if_unique_id_configured()

                LOGGER.debug("Login succesful. Config entry created")
                return self.async_create_entry(
                    title=f"Domonial ({username})",
                    data={
                        CONF_AUTHENTICATION: auth_id,
                    },
                )

        data_schema = vol.Schema(
            {vol.Required(CONF_USERNAME): str, vol.Required(CONF_PASSWORD): str}
        )

        return self.async_show_form(
            step_id="user", data_schema=data_schema, errors=errors
        )


class CannotConnect(exceptions.HomeAssistantError):
    """Error to indicate we cannot connect."""


class AuthenticationError(exceptions.HomeAssistantError):
    """Error to indicate authentication failure."""
