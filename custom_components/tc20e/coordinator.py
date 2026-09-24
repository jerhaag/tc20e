"""TC20E alarm coordinator."""

from __future__ import annotations

import asyncio
from datetime import timedelta
import re

import aiohttp
from bs4 import BeautifulSoup

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_AUTHENTICATION
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, HomeAssistantError
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN, LOGGER, MIN_SCAN_INTERVAL, TC20E_URL

TIMEOUT = 15


class TC20EUpdateCoordinator(DataUpdateCoordinator):
    """TC20E Coordinator."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the TC20E Coordinator."""

        self.websession = async_get_clientsession(hass)
        self._authid: str = entry.data[CONF_AUTHENTICATION]
        self._session_id: str | None = None
        self._timesync = MIN_SCAN_INTERVAL
        self.alarmstatus = 0
        self._request_lock = asyncio.Lock()

        super().__init__(
            hass,
            LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=MIN_SCAN_INTERVAL),
        )

    async def setalarm(self, command: str) -> None:
        """Change status of alarm."""

        try:
            if command == "full":
                await self._request(
                    TC20E_URL + "/applicationservice/domoweb/panel/commands/arm"
                )
                self.alarmstatus = 101

            if command == "partial":
                await self._request(
                    TC20E_URL + "/applicationservice/domoweb/panel/commands/partialarm"
                )
                self.alarmstatus = 102

            if command == "disarm":
                await self._request(
                    TC20E_URL + "/applicationservice/domoweb/panel/commands/disarm"
                )
                self.alarmstatus = 100

        except SessionAlreadyExistsError as error:
            raise HomeAssistantError(
                "Cannot arm/disarm while another Total Connect session is active"
            ) from error

        except (UpdateFailed, ConfigEntryAuthFailed, CannotConnectError) as error:
            raise HomeAssistantError(
                f"Could not arm/disarm TC20E: {error!s}"
            ) from error

        # await self.async_request_refresh()

    async def _async_update_data(self) -> None:
        """Fetch info from TC20E."""

        LOGGER.debug("Trying to get Alarm status")

        try:
            await self._request(
                TC20E_URL + "/applicationservice/domoweb/panel/commands/status"
            )

        except SessionAlreadyExistsError as error:
            raise UpdateFailed(
                "Another Total Connect session is active"
            ) from error

        except (UpdateFailed, ConfigEntryAuthFailed, CannotConnectError) as error:
            raise UpdateFailed(
                f"Could not retrieve alarm status: {error!s}"
            ) from error

        # await self.async_request_refresh()

    async def _request(self, url: str) -> None:
        async with self._request_lock:
            await self._request_locked(url)

    async def _request_locked(self, url: str) -> None:

        try:
            async with asyncio.timeout(TIMEOUT):
                await self._login()

        except TimeoutError as error:
            LOGGER.warning("Timeout during login %s", str(error))
            raise CannotConnectError from error

        LOGGER.debug("Login passed")

        headers = {
            "x-session-token": self._session_id,
        }
        params = {
            "isBusy": "true",
            "checkCompletion": "true",
        }
        json = {
            "key": "",
            "value": "",
        }

        try:
            async with asyncio.timeout(TIMEOUT):
                response = await self.websession.put(
                    url, headers=headers, params=params, json=json
                )

        except TimeoutError as error:
            LOGGER.warning("Timeout when sending command to TC20E")
            await self._logout()
            raise CannotConnectError from error

        except Exception as error:
            LOGGER.debug("Exception on request: %s", error)
            await self._logout()
            raise UpdateFailed from error

        LOGGER.debug("Command response status: %s", response.status)

        if response.status == 200:
            try:
                json = await response.json()
                json_id = json["id"]
                json_status = json["status"]

            except aiohttp.ContentTypeError as error:
                LOGGER.debug("ContentTypeError on ok status: %s", error.message)
                response_text = await response.text()
                LOGGER.debug("Response (200) text is: %s", response_text)
                await self._logout()
                raise UpdateFailed from error

            if json_status != "success":
                LOGGER.warning(
                    "TC20E command was not accepted: %s",
                    json_status,
                )
                await self._logout()
                raise UpdateFailed(
                    f"TC20E command was not accepted: {json_status}"
                )

            LOGGER.debug("Command successfull, URL: %s", url)

            statuscode = 0
            poll_attempts = 0
            max_poll_attempts = 30

            while statuscode != 2:
                poll_attempts += 1

                if poll_attempts > max_poll_attempts:
                    LOGGER.warning(
                        "Timed out waiting for TC20E command completion"
                    )
                    await self._logout()
                    raise UpdateFailed(
                        "Timed out waiting for command completion"
                    )

                try:
                    async with asyncio.timeout(TIMEOUT):
                        response = await self.websession.get(
                            url + "/" + str(json_id) + "/status",
                            headers=headers,
                        )

                except TimeoutError as error:
                    LOGGER.warning("Timeout when sending command to TC20E")
                    await self._logout()
                    raise CannotConnectError from error

                except Exception as error:
                    LOGGER.debug("Exception on request: %s", error)
                    await self._logout()
                    raise UpdateFailed from error

                if response.status == 200:
                    LOGGER.debug("Command response status: %s", response.status)

                    try:
                        json = await response.json()
                        statuscode = json["statusCode"]
                        messagekey = json["messageKey"]
                        errorcode = json["errorCode"]

                    except aiohttp.ContentTypeError as error:
                        LOGGER.debug(
                            "ContentTypeError on ok status: %s", error.message
                        )
                        response_text = await response.text()
                        LOGGER.debug("Response (200) text is: %s", response_text)
                        await self._logout()
                        raise UpdateFailed from error

                    LOGGER.debug("Command response Status Code: %s", statuscode)

                await asyncio.sleep(1)

                if statuscode == 6:
                    LOGGER.debug("Status code is 6 -> Toolong, aborting")
                    await self._logout()
                    self.alarmstatus = 0
                    raise UpdateFailed

            LOGGER.debug("Status Code is: %s", statuscode)
            LOGGER.debug("Error Code is: %s", errorcode)
            LOGGER.debug("Message is: %s", messagekey)

            if errorcode is not None:
                self.alarmstatus = errorcode

            await self._logout()

            return

        if response.status == 201:
            try:
                json = await response.json()
                statuscode = json["statusCode"]
                messagekey = json["messageKey"]
                errorcode = json["errorCode"]

            except aiohttp.ContentTypeError as error:
                LOGGER.debug("ContentTypeError on ok status: %s", error.message)
                response_text = await response.text()
                LOGGER.debug("Response (200) text is: %s", response_text)
                await self._logout()
                raise UpdateFailed from error

            if statuscode == 6:
                LOGGER.debug("Status code is 6 -> Toolong, aborting")
                await self._logout()
                self.alarmstatus = 0
                raise UpdateFailed

            LOGGER.debug("Status Code is: %s", statuscode)
            LOGGER.debug("Error Code is: %s", errorcode)
            LOGGER.debug("Message is: %s", messagekey)

            if errorcode is not None:
                self.alarmstatus = errorcode

            await self._logout()
            return

        LOGGER.debug("Did not retrieve information properly")
        LOGGER.debug("request status: %s", response.status)
        response_text = await response.text()
        LOGGER.debug("request text: %s", response_text)
        await self._logout()
        raise UpdateFailed

    async def _logout(self) -> None:
        """Logout and always clear the local session state."""

        LOGGER.debug("Logout")

        try:
            async with asyncio.timeout(TIMEOUT):
                await self.websession.get(
                    f"{TC20E_URL}/logout",
                    headers={
                        "Connection": "keep-alive",
                    },
                )
        finally:
            self._session_id = None

    async def _login(self) -> None:
        """Login and retrieve session id."""

        LOGGER.debug("Trying to login")

        async with asyncio.timeout(TIMEOUT):
            await self.websession.get(TC20E_URL)

            response = await self.websession.get(
                f"{TC20E_URL}/validate",
                headers={
                    "Authorization": self._authid,
                },
            )

        response_text = await response.text()

        if response_text == "domoweb.error.session.already.exists":
            LOGGER.warning(
                "Another Total Connect session is already active"
            )
            self._session_id = None
            raise SessionAlreadyExistsError

        if response_text != "#1home":
            LOGGER.error(
                "Authentication failure: response %s, status %s",
                response_text,
                response.status,
            )
            self._session_id = None
            raise AuthenticationError

        response = await self.websession.get(
            f"{TC20E_URL}/go/home",
            headers={
                "Connection": "keep-alive",
            },
        )
        response_text = await response.text()
        soup = BeautifulSoup(response_text, "html.parser")

        try:
            self._session_id = re.search(
                r"homeSessionId='(.*?)'", soup.prettify()
            ).group(1)
        except AttributeError:
            LOGGER.error("Failed to retrieve Session ID: %d", response.status)
            await self._logout()
            raise CannotConnectError from AttributeError

        if self._session_id is None:
            LOGGER.error("Failed to retrieve Session ID: %d", response.status)
            await self._logout()
            raise CannotConnectError

        LOGGER.debug("Session id retrieved")

class UnauthorizedError(HomeAssistantError):
    """Exception to indicate an error in authorization."""


class CannotConnectError(HomeAssistantError):
    """Exception to indicate an error in client connection."""


class OperationError(HomeAssistantError):
    """Exception to indicate an error in operation."""


class AuthenticationError(HomeAssistantError):
    """Error to indicate authentication failure."""


class SessionAlreadyExistsError(HomeAssistantError):
    """Another Total Connect session is already active."""
