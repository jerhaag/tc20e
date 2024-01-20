[![TC20e](https://github.com/jerhaag/tc20e/blob/master/icons/logo.png)](https://tc20e.total-connect.eu/)

[![version_badge](https://img.shields.io/github/v/release/jerhaag/tc20e?label=Latest%20release&style=for-the-badge&cacheSeconds=3600)](https://github.com/jerhaag/tc20e/releases/latest)
[![download_badge](https://img.shields.io/github/downloads/jerhaag/tc20e/total?style=for-the-badge&cacheSeconds=3600)](https://github.com/jerhaag/tc20e/releases/latest)

# Home Assistant Integration for Total Connect Europe 2.0E
This integration interacts with TC20e Total Connect Europe Wesbite https://tc20e.total-connect.eu/

Capabilities:
- Retrieve alarm status
- Total Arm (Arm Away)
- Partial Arm (Arm Home)
- Disarm

Update interval is 120sec (TC20E website is very slow).

> Warning: This code may break if the vendor is making changes to its website. If that's the case, please open up an issue. Otherwise, wait for an update, as for the foreseeable future, I will be using this integration myself.

## Configuration Options

- Username: Your username to connect to Total Connect 2.0E website.
- Password: Your password.

## Installation

Below your Home Assistant config folder create a new folder called custom_components if it does not already exist.

Below the new custom_components folder create a new folder called tc20e.

Upload the files/folders in custom_components/tc20e directory from this repository to the newly tc20e created folder.

Restart Home Assitant.

## Activate integration in HA

[![Add integrations](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start?domain=tc20e)

After installation go to "Integrations" page in HA, press + and search for Total Connect 2.0E.
Follow onscreen information to type username and password.
No restart needed