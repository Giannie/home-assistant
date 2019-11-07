"""Support for namecheap DNS services."""
from datetime import timedelta
import logging

import defusedxml.ElementTree as ET
import voluptuous as vol

from homeassistant.const import CONF_DOMAIN, CONF_HOST, CONF_PASSWORD
from homeassistant.helpers.aiohttp_client import async_get_clientsession
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.event import async_track_time_interval

_LOGGER = logging.getLogger(__name__)

DOMAIN = "namecheapdns"

INTERVAL = timedelta(minutes=5)

ATTR_HOST = "host"
ATTR_DOMAIN = "domain"
ATTR_PASSWORD = "password"
ATTR_IP = "ip"

UPDATE_URL = "https://dynamicdns.park-your-domain.com/update"

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {
                vol.Required(CONF_DOMAIN): cv.string,
                vol.Required(CONF_PASSWORD): cv.string,
                vol.Optional(CONF_HOST, default="@"): cv.string,
            }
        )
    },
    extra=vol.ALLOW_EXTRA,
)


async def async_setup(hass, config):
    """Initialize the namecheap DNS component."""
    host = config[DOMAIN][CONF_HOST]
    domain = config[DOMAIN][CONF_DOMAIN]
    password = config[DOMAIN][CONF_PASSWORD]

    session = async_get_clientsession(hass)

    result = await _update_namecheapdns(session, host, domain, password)

    if not result:
        return False

    async def update_domain_interval(now):
        """Update the namecheap DNS entry."""
        await _update_namecheapdns(session, host, domain, password)

    async def handle_update(call):
        """Handle service call to update the namecheap DNS entry."""
        service_host = call.data.get(ATTR_HOST, host)
        service_domain = call.data.get(ATTR_DOMAIN, domain)
        service_password = call.data.get(ATTR_PASSWORD, password)
        await _update_namecheapdns(
            session, service_host, service_domain, service_password
        )

    hass.services.async_register(DOMAIN, "update", handle_update)

    async_track_time_interval(hass, update_domain_interval, INTERVAL)

    return result


async def _update_namecheapdns(session, host, domain, password):
    """Update namecheap DNS entry."""
    params = {"host": host, "domain": domain, "password": password}
    _LOGGER.debug("Updating %s.%s using namecheapdns", host, domain)
    resp = await session.get(UPDATE_URL, params=params)
    xml_string = await resp.text()
    root = ET.fromstring(xml_string)
    err_count = root.find("ErrCount").text

    if int(err_count) != 0:
        _LOGGER.warning("Updating namecheap domain failed: %s", domain)
        return False
    else:
        _LOGGER.debug("Updated %s.%s", host, domain)

    return True
