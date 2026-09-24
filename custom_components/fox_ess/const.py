"""Constants for the FoxESS integration."""

from datetime import timedelta

DOMAIN = "fox_ess"
MANUFACTURER = "FoxESS"

CONF_UNIT_ID = "unit_id"

DEFAULT_PORT = 502
# FoxESS inverters answer on 247 out of the box.
DEFAULT_UNIT_ID = 247

READINGS_INTERVAL = timedelta(seconds=10)
SETTINGS_INTERVAL = timedelta(minutes=1)

# Polls in a row where nothing answered before the link is recycled.
TIMEOUTS_BEFORE_DISCONNECT = 3
